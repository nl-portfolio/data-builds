"""
Phase 5b: Pre-Registered Analysis, re-run with respondent-level variance.

This module SUPERSEDES the withdrawn Phase 5 `src/analysis.py`. The withdrawn
file computed correct per-respondent point estimates and then computed variance
as though every survey ITEM were an independent observation, making every
confidence interval ~21x too narrow and turning two nulls into "large,
significant effects". It also misread H1 (treating the predicted direction as a
reversal) and mis-filtered `CommitmentStmt` (reporting n = 0 in the treatment
arm). None of that is reproduced here.

The rule this module obeys, everywhere:

    Every estimate is a weighted mean of a per-respondent rate. The unit of
    analysis is the respondent. We are averaging 7,278 numbers, not ~2 million.

Every estimate routes through `src/weighting.py`'s validated functions,
unmodified. `estimate_rate()` carries a wired-in assertion
(`assert_variance_plausible`) that fails if a standard error implies more
independent observations than there are respondents. It is never caught or
suppressed in the pre-registered analyses. If it fires, the run aborts.

Pre-registered analyses (run first, all of them, recorded before anything else):
  1. H1  item nonresponse, ITT            (PRIMARY)
  2. H2  break-off, web respondents only  (SECONDARY)
  3. H3  response error, ITT              (SECONDARY)
  4. Holm-Bonferroni multiplicity correction over the pre-registered family
  5. Per-protocol (descriptive, NON-RANDOMISED)
  6. Mode subgroup (paper vs web), pre-registered
  7. Filter-Missing sensitivity specification (dual-specified in the plan)
  8. Covariate balance check (deferred from Phase 1)
  9. Peeking illustration (pedagogical; NOT evidence)

MDE reckoning uses Phase 4b's MEASURED rate-estimator design effect
(1.56 / 1.44 / 2.93 pooled for A / C / B), not the pre-registration grid's
assumed 1.2-1.5. The pre-registered verdict rule is applied, not re-reasoned.

Run:  python src/analysis.py
Writes: outputs/tables/*.csv, outputs/figures/*.png, outputs/RESULTS.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, chi2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from load_hints import load_hints_data  # noqa: E402
from build_outcomes import ItemUniverse, OutcomesBuilder  # noqa: E402
from weighting import (  # noqa: E402
    estimate_rate,
    confidence_interval,
    percentage_format,
    POINT_ESTIMATE_WEIGHT,
)

FRAME_PATH = PROJECT_ROOT / "data" / "processed" / "analysis_frame.parquet"
RDA_PATH = PROJECT_ROOT / "data" / "raw" / "HINTS7_R_20250731" / "hints7_public.rda"
OUT = PROJECT_ROOT / "outputs"
TAB = OUT / "tables"
FIG = OUT / "figures"

TREAT_LABEL = "Included in Commitment Statement group"
CONTROL_LABEL = "Not included in Commitment Statement group"
WEB_LABEL = "HINTS7, standard version - web"
PAPER_LABEL = "HINTS7, standard version - paper"

# ----------------------------------------------------------------------------
# Stable hypothesis keys (Phase 5c).
#
# Every output table keyed by hypothesis carries `hypothesis_id` (H1/H2/H3),
# emitted from this one place. The Power BI guide joins tables on this id,
# NEVER on a display label: Phase 6 found a label drift ("H2 break-off (web)"
# vs "H2 break-off (web only)") that made a `TREATAS` join return BLANK.
# `HYPOTHESIS_LABEL` is the single canonical display string per family, so the
# prose is consistent across tables too.
# ----------------------------------------------------------------------------
HYPOTHESIS_ID = {"A": "H1", "B": "H2", "C": "H3"}
KEY_TO_FAMILY = {"H1": "A", "H2": "B", "H3": "C"}
HYPOTHESIS_LABEL = {
    "A": "H1 item nonresponse",
    "B": "H2 break-off (web only)",
    "C": "H3 response error",
}
# Map any display label (canonical or the mode-interaction rows) back to its id,
# for tables whose rows are built with a label string.
LABEL_TO_ID = {
    "H1 item nonresponse": "H1",
    "H2 break-off (web only)": "H2",
    "H3 response error": "H3",
    "mode interaction: A item nonresponse": "H1",
    "mode interaction: C response error": "H3",
}
# Map the mode-subgroup `family` descriptor to its hypothesis id.
FAMILY_DESC_TO_ID = {
    "A item nonresponse": "H1",
    "B break-off": "H2",
    "C response error": "H3",
}

# Phase 4b measured pooled design effect for the per-respondent RATE estimator
# (docs/validation.md, Phase 4b RESULTS, Part 4b). Not the pre-registration
# grid's assumed 1.2-1.5, and not the Kish weight DEFF (~3.24).
MEASURED_DEFF = {"A": 1.56, "C": 1.44, "B": 2.93}

# (z_alpha/2 + z_beta) for two-sided alpha = 0.05, power = 0.80. The
# pre-registration uses 2.8; 1.959964 + 0.841621 = 2.801585.
MDE_Z = norm.ppf(0.975) + norm.ppf(0.80)

# Peeking illustration: no arrival-order or sequence field exists in the public
# file, so a seeded random order is used and documented (Phase 5 prompt, Part 6).
PEEK_SEED = 20260903

_ASSERTION_LOG: list[dict] = []


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _p_from_z(z: float) -> float:
    """Two-sided p-value from a z-statistic."""
    return float(2.0 * norm.sf(abs(z)))


def _assert_p_consistent(z: float, p: float, label: str) -> None:
    """Fail if the reported p-value does not correspond to the test statistic.

    The withdrawn Phase 5 reported z = -3.53 with p = 0.0071 (z = -3.53 gives
    p = 0.0004). This recomputes p two independent ways and asserts agreement.
    """
    if not np.isfinite(z):
        return
    p_norm = 2.0 * norm.sf(abs(z))          # normal tail
    p_chi2 = float(chi2.sf(z * z, df=1))    # z^2 ~ chi-square_1, independent path
    assert abs(p_norm - p) < 1e-9, (
        f"{label}: reported p={p:.6g} does not match z={z:.6g} "
        f"(normal recompute p={p_norm:.6g})"
    )
    assert abs(p_norm - p_chi2) < 1e-9, (
        f"{label}: normal and chi-square p-values disagree "
        f"(p_norm={p_norm:.6g}, p_chi2={p_chi2:.6g})"
    )


def _rate(df: pd.DataFrame, num: str, den: str, label: str) -> dict:
    """Wrap estimate_rate and record the sanity-assertion outcome.

    estimate_rate() runs assert_variance_plausible() internally. We do NOT catch
    it here for the pre-registered analyses -- an AssertionError propagates and
    aborts the run, as required. This wrapper only records that the estimate
    passed the guard, with its implied_n, for the assertion-history table.
    """
    r = estimate_rate(df, num, den, label)
    _ASSERTION_LOG.append(
        {
            "estimate": label,
            "n_respondents": r["n_respondents"],
            "point_pct": r["point_estimate"] * 100,
            "se_pp": r["se"] * 100,
            "implied_n": r["implied_n"],
            "implied_n_over_n": r["implied_n"] / r["n_respondents"]
            if r["n_respondents"]
            else np.nan,
            "design_effect_rate": r["design_effect"],
            "guard": "passed",
        }
    )
    return r


def _itt(df: pd.DataFrame, num: str, den: str, tag: str) -> dict:
    """Intention-to-treat contrast: treatment arm vs everyone else.

    SE of the difference is the pre-registered form
        SE(diff) = sqrt(SE_tx^2 + SE_ctl^2)
    (pre-registration, "Test statistic: Two-sample weighted comparison").
    """
    tx = df[df["Treatment_H7_2"] == TREAT_LABEL]
    ctl = df[df["Treatment_H7_2"] == CONTROL_LABEL]
    rt = _rate(tx, num, den, f"{tag} / treatment")
    rc = _rate(ctl, num, den, f"{tag} / control")

    diff = rt["point_estimate"] - rc["point_estimate"]
    se_diff = float(np.hypot(rt["se"], rc["se"]))
    lo, hi = confidence_interval(diff, se_diff)
    z = diff / se_diff if se_diff > 0 else np.nan
    p = _p_from_z(z)
    _assert_p_consistent(z, p, f"{tag} ITT")
    rel = diff / rc["point_estimate"] if rc["point_estimate"] else np.nan

    return {
        "tag": tag,
        "treatment": rt,
        "control": rc,
        "n_tx": rt["n_respondents"],
        "n_ctl": rc["n_respondents"],
        "p_tx": rt["point_estimate"],
        "p_ctl": rc["point_estimate"],
        "se_tx": rt["se"],
        "se_ctl": rc["se"],
        "ci_tx": (rt["ci_lower"], rt["ci_upper"]),
        "ci_ctl": (rc["ci_lower"], rc["ci_upper"]),
        "difference": diff,
        "se_difference": se_diff,
        "ci_difference": (lo, hi),
        "relative_difference": rel,
        "z": z,
        "p_value": p,
    }


def _holm(pvals: dict[str, float], alpha: float = 0.05) -> pd.DataFrame:
    """Holm-Bonferroni step-down over an explicit family of tests.

    Exactly as written in the pre-registration ("Decision rule": rank ascending,
    compare k-th smallest to alpha / (m - k + 1)).
    """
    m = len(pvals)
    order = sorted(pvals.items(), key=lambda kv: kv[1])
    rows = []
    running_max = 0.0
    prior_rejected = True
    for k, (name, p) in enumerate(order, start=1):
        thr = alpha / (m - k + 1)
        p_adj = min(1.0, (m - k + 1) * p)
        running_max = max(running_max, p_adj)  # enforce monotone adjusted p
        reject = prior_rejected and (p < thr)
        prior_rejected = reject
        rows.append(
            {
                "hypothesis": name,
                "p_uncorrected": p,
                "holm_threshold": thr,
                "p_holm": running_max,
                "reject_at_familywise_0.05": bool(reject),
            }
        )
    return pd.DataFrame(rows)


def _verdict_primary(diff: float, ci: tuple[float, float], mde: float, p: float) -> tuple[str, str]:
    """Apply the pre-registered H1 verdict rule mechanically (not re-reasoned).

    From pre-registration, H1 "What result counts as" + "Interpretation of null
    results": thresholds are in the plan; this function only evaluates them.

    Returns ``(prose, verdict_class)``. The categorical ``verdict_class`` is
    emitted from the SAME branch that produces the prose -- it is NOT
    re-derived from the numbers independently (Phase 5c, defect 1). The three
    classes are ``DETECTED`` / ``INFORMATIVE_NULL`` / ``UNDERPOWERED_NULL``.

    Two combinations have no ``verdict_class`` defined by the locked plan: the
    pre-registration's 3-5 pp "indeterminate" MDE band, and an
    "effect >= MDE yet not classed DETECTED (CI still spans 0)" case -- which is
    not an underpowered null at all, since an effect at or above the MDE is
    within the design's reach. Both are unreachable on the realised data
    (H1 empirical MDE 0.32 pp, grid 1.20 pp, observed effect 0.21 pp). Phase
    5c-2 makes them ``raise NotImplementedError`` rather than fall back to a
    conservative label: a raise documents that they are unreachable and fails
    loudly if the data ever changes; a silent conservative label does neither
    (R18).
    """
    ad = abs(diff)
    ci_spans_zero = ci[0] < 0 < ci[1]
    # 1. detected / confirming
    if ad >= 0.03 and not ci_spans_zero:
        return "DETECTED EFFECT (>= 3 pp, CI excludes 0)", "DETECTED"
    # 2. disconfirming (a null)
    if ad <= 0.01 or ci_spans_zero:
        base = "DISCONFIRMING (rates within 1 pp, or CI spans both directions) -> NULL"
    elif 0.01 < ad < 0.03:
        base = "UNINFORMATIVE ZONE (1-3 pp effect, CI wide)"
    else:
        base = "INDETERMINATE"
    # 3. null informativeness vs MDE (pre-registration: < 3 pp informative,
    #    > 5 pp underpowered)
    if ad < mde and mde < 0.03:
        return base + "; INFORMATIVE NULL (observed effect < MDE, MDE < 3 pp)", "INFORMATIVE_NULL"
    if ad < mde and mde > 0.05:
        return base + "; UNDERPOWERED NULL (observed effect < MDE, MDE > 5 pp)", "UNDERPOWERED_NULL"
    if ad < mde:
        # 3-5 pp indeterminate MDE band: unreachable on this data. No
        # verdict_class defined by the locked plan; fail loudly (R18, Phase 5c-2)
        # rather than fall back to a conservative label.
        raise NotImplementedError(
            f"H1 verdict_class undefined: observed effect {ad*100:.2f} pp < MDE "
            f"{mde*100:.2f} pp, but MDE is in the pre-registration's 3-5 pp "
            f"indeterminate band (neither < 3 pp informative nor > 5 pp "
            f"underpowered). The locked plan defines no class here. Unreachable "
            f"on the realised data; decide the rule before emitting a class."
        )
    # effect >= MDE yet not DETECTED (CI spans 0, or effect < 3 pp): also
    # undefined, and NOT an underpowered null -- an effect at or above the MDE
    # is within reach of the design. Unreachable on this data; fail loudly.
    raise NotImplementedError(
        f"H1 verdict_class undefined: observed effect {ad*100:.2f} pp >= MDE "
        f"{mde*100:.2f} pp yet not classed DETECTED (CI spans 0 or effect "
        f"< 3 pp). An effect at or above the MDE is not an underpowered null, "
        f"and the locked plan defines no class for this combination. "
        f"Unreachable on the realised data; decide the rule if the data changes."
    )


def _verdict_secondary(diff, ci, mde, p, name) -> tuple[str, str]:
    """Return ``(prose, verdict_class)`` for a secondary hypothesis.

    Every null maps to ``UNDERPOWERED_NULL`` **by convention, not by the
    pre-registered rule**: the plan's informative / underpowered dichotomy and
    its 3 pp informativeness bar were written for the primary outcome and are
    meaningless against H2's 4.3 pp empirical MDE and H3's 0.36 % baseline. This
    is a conservative presentation choice (it never implies a detected effect,
    R17); it is stated in docs/decisions.md and docs/powerbi_guide.md so a
    reader does not mistake it for a pre-registered verdict.

    Nominal uncorrected significance (p < 0.05, CI excludes 0) has **no defined
    verdict_class**: the locked decision rule is Holm-corrected, so classing
    such a case ``DETECTED`` on uncorrected p would contradict the plan, and the
    prose that used to hedge here ("check Holm") is discarded once the dashboard
    colours from the class. Phase 5c-2 makes it raise rather than return a
    class. Unreachable on the realised data (H2 p = 0.23, H3 p = 0.62); R18.
    """
    ad = abs(diff)
    ci_spans_zero = ci[0] < 0 < ci[1]
    if p < 0.05 and not ci_spans_zero:
        raise NotImplementedError(
            f"{name}: nominal uncorrected significance (p={p:.4f}, CI excludes 0) "
            "has no defined verdict_class. The pre-registered decision rule is "
            "Holm-corrected; classing this DETECTED on uncorrected p would "
            "contradict the locked plan. Decide the rule before emitting a class."
        )
    tail = ""
    if ad < mde:
        tail = f"; observed effect ({ad*100:.3f} pp) < MDE ({mde*100:.3f} pp): experiment could not have detected it"
    return f"{name}: NULL (CI includes 0){tail}", "UNDERPOWERED_NULL"


def _mde(p_baseline: float, n_tx: int, n_ctl: int, deff: float,
         se_diff_observed: float) -> dict:
    """Two MDE numbers, both reported.

    grid : the pre-registration's own formula
           2.8 * sqrt(p(1-p)(1/n_tx + 1/n_ctl)) * sqrt(DEFF),
           evaluated at the OBSERVED baseline rate with Phase 4b's MEASURED DEFF
           substituted for the assumed 1.2-1.5. This is the grid "applied", not
           re-reasoned.
    empirical : 2.8 * SE(difference) from the actual arm jackknife SEs. This is
           what the experiment could really detect for this outcome; it already
           embeds the true dispersion and design effect. docs/validation.md
           Part 6 flagged that the grid's p(1-p) per-respondent variance is
           ~9x too large for a stable low rate, so `grid` is conservative.
    """
    grid = MDE_Z * np.sqrt(p_baseline * (1 - p_baseline) * (1 / n_tx + 1 / n_ctl)) * np.sqrt(deff)
    empirical = MDE_Z * se_diff_observed
    return {
        "baseline_rate": p_baseline,
        "n_treatment": n_tx,
        "n_control": n_ctl,
        "measured_deff": deff,
        "mde_grid_formula": float(grid),
        "mde_empirical": float(empirical),
    }


# ----------------------------------------------------------------------------
# 1-3. pre-registered ITT analyses
# ----------------------------------------------------------------------------
def run_primary_and_secondary(frame: pd.DataFrame) -> dict:
    web = frame[frame["family_b_denominator"].notna()]  # 4,861 web respondents

    h1 = _itt(frame, "family_a_numerator", "family_a_denominator", "H1 item nonresponse")
    h3 = _itt(frame, "family_c_numerator", "family_c_denominator", "H3 response error")
    h2 = _itt(web, "family_b_numerator", "family_b_denominator", "H2 break-off (web only)")

    # pooled rate-estimator design effects, recomputed here (should match 4b)
    pooled_A = _rate(frame, "family_a_numerator", "family_a_denominator", "pooled A")
    pooled_C = _rate(frame, "family_c_numerator", "family_c_denominator", "pooled C")
    pooled_B = _rate(web, "family_b_numerator", "family_b_denominator", "pooled B (web)")

    h1["mde"] = _mde(h1["p_ctl"], h1["n_tx"], h1["n_ctl"],
                     pooled_A["design_effect"], h1["se_difference"])
    h3["mde"] = _mde(h3["p_ctl"], h3["n_tx"], h3["n_ctl"],
                     pooled_C["design_effect"], h3["se_difference"])
    h2["mde"] = _mde(h2["p_ctl"], h2["n_tx"], h2["n_ctl"],
                     pooled_B["design_effect"], h2["se_difference"])

    h1["verdict"], h1["verdict_class"] = _verdict_primary(
        h1["difference"], h1["ci_difference"], h1["mde"]["mde_empirical"], h1["p_value"]
    )
    h1["verdict_grid_mde"], _ = _verdict_primary(
        h1["difference"], h1["ci_difference"], h1["mde"]["mde_grid_formula"], h1["p_value"]
    )
    h3["verdict"], h3["verdict_class"] = _verdict_secondary(
        h3["difference"], h3["ci_difference"], h3["mde"]["mde_empirical"],
        h3["p_value"], "H3 response error"
    )
    h2["verdict"], h2["verdict_class"] = _verdict_secondary(
        h2["difference"], h2["ci_difference"], h2["mde"]["mde_empirical"],
        h2["p_value"], "H2 break-off"
    )

    pooled = {"A": pooled_A, "C": pooled_C, "B": pooled_B}
    return {"H1": h1, "H2": h2, "H3": h3, "pooled": pooled}


# ----------------------------------------------------------------------------
# 4. multiplicity
# ----------------------------------------------------------------------------
def run_multiplicity(res: dict, mode_df: pd.DataFrame) -> dict:
    # Pre-registered family, primary reading: the three outcome-family tests. The
    # decision rule in the pre-registration is written explicitly for m = 3
    # (alpha/3, alpha/2, alpha/1).
    fam3 = {
        HYPOTHESIS_LABEL["A"]: res["H1"]["p_value"],
        HYPOTHESIS_LABEL["B"]: res["H2"]["p_value"],
        HYPOTHESIS_LABEL["C"]: res["H3"]["p_value"],
    }
    holm3 = _holm(fam3)
    holm3.insert(1, "hypothesis_id", holm3["hypothesis"].map(LABEL_TO_ID))

    # Supplementary reading: the plan also says "Any subgroup analyses (see below)
    # are also in the family." The only pre-registered subgroup is mode, whose
    # pre-registered question is whether the effect DIFFERS by mode -- i.e. the
    # interaction. Family B has no paper cell, so that adds two tests -> m = 5.
    inter = mode_df[mode_df["mode"] == "web - paper (interaction)"]
    fam5 = dict(fam3)
    for _, row in inter.iterrows():
        fam5[f"mode interaction: {row['family']}"] = float(row["p_value"])
    holm5 = _holm(fam5)
    holm5.insert(1, "hypothesis_id", holm5["hypothesis"].map(LABEL_TO_ID))

    return {"holm_m3": holm3, "holm_m5": holm5}


# ----------------------------------------------------------------------------
# 5. per-protocol  (NON-RANDOMISED -- descriptive only)
# ----------------------------------------------------------------------------
def run_per_protocol(frame: pd.DataFrame) -> pd.DataFrame:
    tx = frame[frame["Treatment_H7_2"] == TREAT_LABEL]
    agreed = tx[tx["CommitmentStmt"] == "Yes"]                         # 1,389
    not_agreed = tx[tx["CommitmentStmt"].isin(
        ["No", "Missing data (Not Ascertained)"])]                     # 124
    declined_only = tx[tx["CommitmentStmt"] == "No"]                   # 14 -- described, not tested

    ra = _rate(agreed, "family_a_numerator", "family_a_denominator",
               "per-protocol / agreed (NON-RANDOMISED)")
    rn = _rate(not_agreed, "family_a_numerator", "family_a_denominator",
               "per-protocol / did not agree (NON-RANDOMISED)")
    diff = ra["point_estimate"] - rn["point_estimate"]
    se_diff = float(np.hypot(ra["se"], rn["se"]))
    lo, hi = confidence_interval(diff, se_diff)

    rows = [
        {"group": "Agreed (CommitmentStmt = Yes) [NON-RANDOMISED]", "n": ra["n_respondents"],
         "rate_pct": ra["point_estimate"] * 100, "ci_lo_pct": ra["ci_lower"] * 100,
         "ci_hi_pct": ra["ci_upper"] * 100},
        {"group": "Did not agree (No or Not Ascertained) [NON-RANDOMISED]", "n": rn["n_respondents"],
         "rate_pct": rn["point_estimate"] * 100, "ci_lo_pct": rn["ci_lower"] * 100,
         "ci_hi_pct": rn["ci_upper"] * 100},
        {"group": "Descriptive difference (agreed - did not agree) [NON-RANDOMISED, NOT CAUSAL]",
         "n": ra["n_respondents"] + rn["n_respondents"],
         "rate_pct": diff * 100, "ci_lo_pct": lo * 100, "ci_hi_pct": hi * 100},
        {"group": "Declined only (CommitmentStmt = No) -- DESCRIBED, NOT TESTED",
         "n": len(declined_only), "rate_pct": np.nan, "ci_lo_pct": np.nan, "ci_hi_pct": np.nan},
    ]
    df = pd.DataFrame(rows)
    # Per-protocol is defined only for the primary outcome (Family A) in the
    # pre-registration; carry the key so every hypothesis-related table has it.
    df.insert(0, "hypothesis_id", "H1")
    return df


# ----------------------------------------------------------------------------
# 6. mode subgroup  (pre-registered)
# ----------------------------------------------------------------------------
def run_mode_subgroup(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("A item nonresponse", "family_a_numerator", "family_a_denominator", (WEB_LABEL, PAPER_LABEL)),
        ("C response error", "family_c_numerator", "family_c_denominator", (WEB_LABEL, PAPER_LABEL)),
        ("B break-off", "family_b_numerator", "family_b_denominator", (WEB_LABEL,)),  # web only
    ]
    effects = {}
    for fam, num, den, modes in specs:
        for mode in modes:
            sub = frame[frame["FormType"] == mode]
            if den == "family_b_denominator":
                sub = sub[sub["family_b_denominator"].notna()]
            it = _itt(sub, num, den, f"mode[{mode.split('-')[-1].strip()}] {fam}")
            mode_short = "web" if mode == WEB_LABEL else "paper"
            effects[(fam, mode_short)] = it
            rows.append({
                "family": fam, "mode": mode_short,
                "n_tx": it["n_tx"], "n_ctl": it["n_ctl"],
                "rate_tx_pct": it["p_tx"] * 100, "rate_ctl_pct": it["p_ctl"] * 100,
                "diff_pp": it["difference"] * 100,
                "ci_lo_pp": it["ci_difference"][0] * 100,
                "ci_hi_pp": it["ci_difference"][1] * 100,
                "z": it["z"], "p_value": it["p_value"],
            })
    # interaction (web effect - paper effect) for A and C
    z975 = norm.ppf(0.975)
    for fam in ["A item nonresponse", "C response error"]:
        we = effects[(fam, "web")]
        pe = effects[(fam, "paper")]
        inter = we["difference"] - pe["difference"]
        se = float(np.hypot(we["se_difference"], pe["se_difference"]))
        z = inter / se if se > 0 else np.nan
        pv = _p_from_z(z)
        _assert_p_consistent(z, pv, f"interaction {fam}")
        rows.append({
            "family": fam, "mode": "web - paper (interaction)",
            "n_tx": np.nan, "n_ctl": np.nan,
            "rate_tx_pct": np.nan, "rate_ctl_pct": np.nan,
            "diff_pp": inter * 100,
            "ci_lo_pp": (inter - z975 * se) * 100,
            "ci_hi_pp": (inter + z975 * se) * 100,
            "z": z, "p_value": pv,
        })
    df = pd.DataFrame(rows)
    df.insert(0, "hypothesis_id", df["family"].map(FAMILY_DESC_TO_ID))
    return df


# ----------------------------------------------------------------------------
# 7. Sensitivity specifications
#    (a) Filter-Missing rule — dual-specified in the pre-registration
#    (b) Web-Never-Seen in Family A's denominator — NOT changed (Neyda's ruling
#        2026-09-03: keep the locked spec, report the alternative as a footnote).
# ----------------------------------------------------------------------------
def _wns_count_per_respondent(frame: pd.DataFrame) -> np.ndarray:
    """Per-respondent count of `Missing data (Web partial - Question Never Seen)`
    cells across the 368-item universe, recomputed from the raw .rda. Used only
    for the footnote sensitivity that removes those cells from Family A's
    denominator. Does not touch the frame's frozen `family_a_denominator`."""
    raw = load_hints_data(str(RDA_PATH)).reset_index(drop=True)
    universe = ItemUniverse(raw)
    universe.classify_all_items()
    items = universe.get_items()
    assert len(items) == 368, f"item universe drift: {len(items)}"
    ob = OutcomesBuilder(raw, items)
    masks = ob._build_outcome_masks(OutcomesBuilder.FAMILY_B_PATTERNS)
    wns = np.zeros(len(raw), dtype=int)
    for _item, m in masks.items():
        wns += m.astype(int)
    return wns


def _sensitivity_rows(primary: dict, s1, s2, s3, label: str) -> list:
    rows = []
    for name, prim, sens in [
        (HYPOTHESIS_LABEL["A"], primary["H1"], s1),
        (HYPOTHESIS_LABEL["B"], primary["H2"], s2),
        (HYPOTHESIS_LABEL["C"], primary["H3"], s3),
    ]:
        if sens is None:
            continue
        rows.append({
            "hypothesis": name,
            "spec": label,
            "primary_diff_pp": prim["difference"] * 100,
            "primary_ci_pp": f"[{prim['ci_difference'][0]*100:.3f}, {prim['ci_difference'][1]*100:.3f}]",
            "primary_p": prim["p_value"],
            "sensitivity_diff_pp": sens["difference"] * 100,
            "sensitivity_ci_pp": f"[{sens['ci_difference'][0]*100:.3f}, {sens['ci_difference'][1]*100:.3f}]",
            "sensitivity_p": sens["p_value"],
            "sign_agrees": bool(np.sign(prim["difference"]) == np.sign(sens["difference"])),
            "both_null_at_0.05": bool((prim["p_value"] >= 0.05) and (sens["p_value"] >= 0.05)),
        })
    return rows


def run_sensitivity(frame: pd.DataFrame, primary: dict) -> dict:
    # (a) Filter-Missing rule (pre-registered dual specification)
    web = frame[frame["family_b_denominator_sens"].notna()]
    fm1 = _itt(frame, "family_a_numerator", "applicable_count_sens", "H1 sensitivity (excl Filter Missing)")
    fm3 = _itt(frame, "family_c_numerator", "applicable_count_sens", "H3 sensitivity (excl Filter Missing)")
    fm2 = _itt(web, "family_b_numerator", "family_b_denominator_sens", "H2 sensitivity (excl Filter Missing)")
    fm = pd.DataFrame(_sensitivity_rows(primary, fm1, fm2, fm3, "exclude Filter Missing from denominator"))

    # (b) Web-Never-Seen exclusion from Family A/C denominator — FOOTNOTE ONLY.
    # The pre-registration's Family A table says these cells should not be in the
    # denominator; the build (frozen since Phase 3) includes them. Neyda ruled
    # 2026-09-03 to keep the as-built spec and report this as a sensitivity, not
    # to change an outcome definition after seeing results. Effect on the pooled
    # ratio is ~+0.108 pp (Phase 3b / 4b), below every MDE.
    f2 = frame.copy()
    wns = _wns_count_per_respondent(frame)
    f2["applicable_count_excl_wns"] = (f2["family_a_denominator"].to_numpy() - wns).clip(min=0)
    wns_web = f2[f2["family_b_denominator"].notna()]
    wn1 = _itt(f2, "family_a_numerator", "applicable_count_excl_wns", "H1 sensitivity (excl Web-Never-Seen)")
    wn3 = _itt(f2, "family_c_numerator", "applicable_count_excl_wns", "H3 sensitivity (excl Web-Never-Seen)")
    wn = pd.DataFrame(_sensitivity_rows(primary, wn1, None, wn3, "exclude Web-Never-Seen from denominator"))

    fm.insert(1, "hypothesis_id", fm["hypothesis"].map(LABEL_TO_ID))
    wn.insert(1, "hypothesis_id", wn["hypothesis"].map(LABEL_TO_ID))

    return {"filter_missing": fm, "web_never_seen": wn,
            "wns_cells_total": int(wns.sum()),
            "wns_respondents_affected": int((wns > 0).sum())}


# ----------------------------------------------------------------------------
# 8. balance check  (deferred from Phase 1; covariate set NOT pre-specified)
# ----------------------------------------------------------------------------
def run_balance(frame: pd.DataFrame) -> pd.DataFrame:
    raw = load_hints_data(str(RDA_PATH)).reset_index(drop=True)
    assert len(raw) == len(frame) == 7278
    arm = frame["Treatment_H7_2"].to_numpy()
    covs = {
        "Age group (AgeGrpB)": "AgeGrpB",
        "Sex at birth (BirthSex)": "BirthSex",
        "Race/ethnicity (RaceEthn5)": "RaceEthn5",
        "Education (EducA)": "EducA",
        "Income (IncomeRanges)": "IncomeRanges",
        "Marital status (MaritalStatus)": "MaritalStatus",
        "Survey mode (FormType)": "FormType",
        "Design stratum (STRATUM)": "STRATUM",
    }
    rows = []
    for label, col in covs.items():
        s = raw[col].astype("object")
        # collapse the survey missing codes into one 'Missing' level so the
        # cross-tab is complete and differential missingness is itself visible
        s = s.where(~s.astype(str).str.contains("Missing data|Unreadable|Inapplicable", na=False),
                    other="(missing/not ascertained)")
        ct = pd.crosstab(s, arm)
        # unweighted Pearson chi-square of independence (arm x covariate)
        chi2_stat, p, dof, _exp = _chisq(ct.to_numpy())
        # per-arm category share, and the largest absolute gap between arms
        share = ct.div(ct.sum(axis=0), axis=1)
        signed_gap = share[TREAT_LABEL] - share[CONTROL_LABEL]
        max_gap = float(signed_gap.abs().max())
        # Phase 5c: the Panel F caption ("70.1% vs 65.9% web") must trace to a
        # cell. Report the two arm shares at the level most over-represented in
        # the treatment arm, plus that level's name. For a 2-level covariate the
        # gap is symmetric, so this picks the "more of X in treatment" framing
        # (for survey mode: web, 70.1 % vs 65.9 %).
        over_level = signed_gap.idxmax()
        rows.append({
            "covariate": label,
            "levels": ct.shape[0],
            "chi2": chi2_stat,
            "dof": dof,
            "p_value": p,
            "max_arm_share_gap_pp": max_gap * 100,
            "overrepresented_level": str(over_level),
            "treatment_share_pct": float(share.loc[over_level, TREAT_LABEL] * 100),
            "control_share_pct": float(share.loc[over_level, CONTROL_LABEL] * 100),
            "flag": "IMBALANCED (p<0.01)" if p < 0.01 else ("watch (p<0.05)" if p < 0.05 else "balanced"),
        })
    return pd.DataFrame(rows)


def _chisq(table: np.ndarray):
    table = table.astype(float)
    row = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0, keepdims=True)
    total = table.sum()
    expected = row @ col / total
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(expected > 0, (table - expected) ** 2 / expected, 0.0)
    stat = float(terms.sum())
    dof = int((table.shape[0] - 1) * (table.shape[1] - 1))
    return stat, float(chi2.sf(stat, dof)), dof, expected


# ----------------------------------------------------------------------------
# 9. peeking illustration  (NOT evidence)
# ----------------------------------------------------------------------------
def run_peeking(frame: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(PEEK_SEED)
    order = rng.permutation(len(frame))
    fr = frame.iloc[order].reset_index(drop=True)
    steps = np.linspace(0.05, 1.0, 20)
    rows = []
    for frac in steps:
        k = max(50, int(round(frac * len(fr))))
        sub = fr.iloc[:k]
        tx = sub[sub["Treatment_H7_2"] == TREAT_LABEL]
        ctl = sub[sub["Treatment_H7_2"] == CONTROL_LABEL]
        if len(tx) < 20 or len(ctl) < 20:
            continue
        try:
            rt = estimate_rate(tx, "family_a_numerator", "family_a_denominator", "peek tx")
            rc = estimate_rate(ctl, "family_a_numerator", "family_a_denominator", "peek ctl")
            guard = "passed"
        except AssertionError as exc:  # illustration only -- record and continue
            _ASSERTION_LOG.append({"estimate": f"peeking illustration @ {frac:.0%}",
                                   "n_respondents": len(sub), "point_pct": np.nan,
                                   "se_pp": np.nan, "implied_n": np.nan,
                                   "implied_n_over_n": np.nan, "design_effect_rate": np.nan,
                                   "guard": f"FIRED (illustration, not a pre-registered estimate): {exc}"})
            continue
        d = rt["point_estimate"] - rc["point_estimate"]
        se = float(np.hypot(rt["se"], rc["se"]))
        z = d / se if se > 0 else np.nan
        rows.append({"fraction": frac, "n": k, "diff_pp": d * 100,
                     "z": z, "p_value": _p_from_z(z)})
    df = pd.DataFrame(rows)
    # Peeking illustration is the primary outcome (H1) only, per the plan.
    if not df.empty:
        df.insert(0, "hypothesis_id", "H1")
    return df


# ----------------------------------------------------------------------------
# outputs
# ----------------------------------------------------------------------------
def _primary_table(res: dict) -> pd.DataFrame:
    rows = []
    for key, fam in [("H1", "A"), ("H2", "B"), ("H3", "C")]:
        r = res[key]
        rows.append({
            "hypothesis_id": HYPOTHESIS_ID[fam],
            "hypothesis": HYPOTHESIS_LABEL[fam],
            "n_treatment": r["n_tx"], "n_control": r["n_ctl"],
            "rate_treatment_pct": r["p_tx"] * 100,
            "ci_treatment_pct": f"[{r['ci_tx'][0]*100:.3f}, {r['ci_tx'][1]*100:.3f}]",
            "rate_control_pct": r["p_ctl"] * 100,
            "ci_control_pct": f"[{r['ci_ctl'][0]*100:.3f}, {r['ci_ctl'][1]*100:.3f}]",
            "difference_pp": r["difference"] * 100,
            "ci_difference_pp": f"[{r['ci_difference'][0]*100:.3f}, {r['ci_difference'][1]*100:.3f}]",
            # numeric CI bounds of the difference, in pp -- so Power BI does not
            # have to parse the string above (Phase 5c, defect 4). The string
            # stays for human readers.
            "ci_low_pp": r["ci_difference"][0] * 100,
            "ci_high_pp": r["ci_difference"][1] * 100,
            "relative_difference_pct": r["relative_difference"] * 100,
            "z": r["z"], "p_uncorrected": r["p_value"],
            "mde_empirical_pp": r["mde"]["mde_empirical"] * 100,
            "mde_grid_formula_pp": r["mde"]["mde_grid_formula"] * 100,
            "measured_deff": r["mde"]["measured_deff"],
            "verdict": r["verdict"],
            "verdict_class": r["verdict_class"],
        })
    return pd.DataFrame(rows)


def _mde_table(res: dict) -> pd.DataFrame:
    rows = []
    for key in ["H1", "H2", "H3"]:
        m = res[key]["mde"]
        rows.append({
            "hypothesis_id": key,
            "hypothesis": HYPOTHESIS_LABEL[KEY_TO_FAMILY[key]],
            "observed_baseline_rate_pct": m["baseline_rate"] * 100,
            "n_treatment": m["n_treatment"], "n_control": m["n_control"],
            "measured_rate_deff": m["measured_deff"],
            "mde_grid_formula_pp": m["mde_grid_formula"] * 100,
            "mde_empirical_pp": m["mde_empirical"] * 100,
            "observed_effect_pp": abs(res[key]["difference"]) * 100,
            "observed_effect_below_empirical_mde": abs(res[key]["difference"]) < m["mde_empirical"],
        })
    return pd.DataFrame(rows)


def _fmt_pct(x, d=3):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x*100:.{d}f}%"


def _md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table (no tabulate dep)."""
    def cell(v):
        if isinstance(v, float):
            if not np.isfinite(v):
                return ""
            return f"{v:.4g}"
        return str(v)
    cols = list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = [
        "| " + " | ".join(cell(v) for v in row) + " |"
        for row in df.itertuples(index=False, name=None)
    ]
    return "\n".join([head, sep, *body])


def write_outputs(res, holm, pp, mode_df, sens, bal_df, peek_df):
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    prim = _primary_table(res)
    mde = _mde_table(res)
    prim.to_csv(TAB / "primary_itt.csv", index=False)
    mde.to_csv(TAB / "mde.csv", index=False)
    holm["holm_m3"].to_csv(TAB / "multiplicity_holm_m3.csv", index=False)
    holm["holm_m5"].to_csv(TAB / "multiplicity_holm_m5.csv", index=False)
    pp.to_csv(TAB / "per_protocol.csv", index=False)
    mode_df.to_csv(TAB / "mode_subgroup.csv", index=False)
    sens["filter_missing"].to_csv(TAB / "sensitivity_filter_missing.csv", index=False)
    sens["web_never_seen"].to_csv(TAB / "sensitivity_web_never_seen.csv", index=False)
    bal_df.to_csv(TAB / "balance.csv", index=False)
    peek_df.to_csv(TAB / "peeking_illustration.csv", index=False)
    pd.DataFrame(_ASSERTION_LOG).to_csv(TAB / "assertion_history.csv", index=False)

    _fig_forest(res)
    _fig_primary_arms(res)
    _fig_peeking(peek_df)

    _write_results_md(res, holm, pp, mode_df, sens, bal_df, peek_df)


def _fig_forest(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, diffs, los, his, mdes = [], [], [], [], []
    for key in ["H1", "H2", "H3"]:
        r = res[key]
        labels.append(r["tag"])
        diffs.append(r["difference"] * 100)
        los.append(r["ci_difference"][0] * 100)
        his.append(r["ci_difference"][1] * 100)
        mdes.append(r["mde"]["mde_empirical"] * 100)
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.axvline(0, color="#888", lw=1)
    ax.errorbar(diffs, y, xerr=[np.array(diffs) - np.array(los), np.array(his) - np.array(diffs)],
                fmt="o", color="#1f4e79", capsize=4, lw=1.6, label="ITT effect, 95% CI")
    for yi, mm in zip(y, mdes):
        ax.plot([-mm, -mm], [yi - 0.25, yi + 0.25], color="#c0504d", lw=1.4)
        ax.plot([mm, mm], [yi - 0.25, yi + 0.25], color="#c0504d", lw=1.4,
                label="_nolegend_")
    ax.plot([], [], color="#c0504d", lw=1.4, label="+/- empirical MDE (80% power)")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Treatment - control difference (percentage points)")
    ax.set_title("Pre-registered ITT effects vs minimum detectable effect\n"
                 "(negative = commitment statement reduced the failure rate, the predicted direction)",
                 fontsize=9)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "effects_forest.png", dpi=150)
    plt.close(fig)


def _fig_primary_arms(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    r = res["H1"]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    xs = [0, 1]
    pts = [r["p_ctl"] * 100, r["p_tx"] * 100]
    los = [r["ci_ctl"][0] * 100, r["ci_tx"][0] * 100]
    his = [r["ci_ctl"][1] * 100, r["ci_tx"][1] * 100]
    ax.errorbar(xs, pts, yerr=[np.array(pts) - np.array(los), np.array(his) - np.array(pts)],
                fmt="o", color="#1f4e79", capsize=5, lw=1.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"Control\nn={r['n_ctl']:,}", f"Commitment statement\nn={r['n_tx']:,}"], fontsize=9)
    ax.set_ylabel("Weighted item nonresponse rate (%)")
    ax.set_title("H1 (primary): item nonresponse by arm, weighted mean of\nper-respondent rate, jackknife 95% CI", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "primary_arms.png", dpi=150)
    plt.close(fig)


def _fig_peeking(peek_df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if peek_df.empty:
        return
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.plot(peek_df["fraction"] * 100, peek_df["p_value"], "-o", color="#1f4e79", lw=1.5)
    ax.axhline(0.05, color="#c0504d", ls="--", lw=1.3, label="alpha = 0.05")
    ax.set_xlabel("Share of the (seeded-random-ordered) sample examined (%)")
    ax.set_ylabel("Cumulative two-sided p-value, H1")
    ax.set_ylim(0, 1)
    ax.set_title("ILLUSTRATION ONLY -- NOT EVIDENCE\n"
                 "What repeatedly peeking at H1 would have shown. Seed = %d." % PEEK_SEED,
                 fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "peeking_illustration.png", dpi=150)
    plt.close(fig)


def _write_results_md(res, holm, pp, mode_df, sens, bal_df, peek_df):
    L = []
    w = L.append
    w("# Phase 5b results (machine-generated by `src/analysis.py`)\n")
    w("Every estimate is a weighted mean of a per-respondent rate, jackknife SE via "
      "`src/weighting.py` unmodified. The `implied_n <= n_respondents` guard ran on "
      "every pre-registered estimate and was never suppressed.\n")

    h1 = res["H1"]
    h1_holm = float(holm["holm_m3"].set_index("hypothesis").loc["H1 item nonresponse", "p_holm"])
    w("\n## Headline\n")
    w(f"**H1 (primary, item nonresponse, ITT): the commitment statement changed the "
      f"weighted item nonresponse rate by {h1['difference']*100:+.2f} pp "
      f"(treatment {h1['p_tx']*100:.2f}% vs control {h1['p_ctl']*100:.2f}%), "
      f"95% CI [{h1['ci_difference'][0]*100:+.2f}, {h1['ci_difference'][1]*100:+.2f}] pp, "
      f"z = {h1['z']:.2f}, p = {h1['p_value']:.3f} uncorrected "
      f"(p_Holm = {h1_holm:.3f}). "
      f"Not significant.** The direction (a reduction) is the one H1 predicted. "
      f"The observed effect ({abs(h1['difference'])*100:.2f} pp) is below the "
      f"empirical MDE ({h1['mde']['mde_empirical']*100:.2f} pp) and far below the "
      f"pre-registration grid's smallest MDE (1.8 pp), so this is an **informative "
      f"null** by the pre-registered rule: an effect of the size the plan cared "
      f"about is ruled out.\n")
    w("H2 (break-off, web) and H3 (response error) are also null; for both, the "
      "observed effect is smaller than what the experiment could detect. The "
      "withdrawn Phase 5's two 'significant' effects (H1 z=-13.14; H3 z=-3.53) do "
      "not survive respondent-level variance.\n")

    w("\n## 1-3. Pre-registered ITT analyses\n")
    for key in ["H1", "H2", "H3"]:
        r = res[key]
        w(f"\n### {r['tag']}\n")
        w(f"- Treatment (n={r['n_tx']:,}): {_fmt_pct(r['p_tx'])}  "
          f"95% CI [{_fmt_pct(r['ci_tx'][0])}, {_fmt_pct(r['ci_tx'][1])}]")
        w(f"- Control (n={r['n_ctl']:,}): {_fmt_pct(r['p_ctl'])}  "
          f"95% CI [{_fmt_pct(r['ci_ctl'][0])}, {_fmt_pct(r['ci_ctl'][1])}]")
        w(f"- Difference (treatment - control): {r['difference']*100:+.3f} pp  "
          f"95% CI [{r['ci_difference'][0]*100:+.3f}, {r['ci_difference'][1]*100:+.3f}] pp")
        w(f"- Relative difference: {r['relative_difference']*100:+.1f}%")
        w(f"- z = {r['z']:.3f}, two-sided p = {r['p_value']:.4f} (uncorrected)")
        w(f"- MDE (empirical, 2.8 x SE_diff): {r['mde']['mde_empirical']*100:.3f} pp; "
          f"MDE (grid formula at observed baseline, measured DEFF "
          f"{r['mde']['measured_deff']:.2f}): {r['mde']['mde_grid_formula']*100:.3f} pp")
        w(f"- **Verdict (pre-registered rule): {r['verdict']}**")

    w("\n## 4. Mode subgroup (pre-registered)\n")
    w(_md_table(mode_df))
    w("\nThe pre-registered question for the mode subgroup is whether the effect "
      "*differs* by mode (the interaction rows). Both interactions are null. The "
      "paper-cell Family A test (p ~ 0.03 uncorrected) does not survive "
      "multiplicity and is not elevated: the pre-registration forbids subgroup "
      "hunting when the pre-registered tests are null.\n")
    w("\n**Collider caveat.** Survey mode is measured *after* randomisation and is "
      "associated with treatment assignment in the responding sample (balance "
      "table, below: 70.1% vs 65.9% web, p = 0.002). Conditioning on a "
      "post-treatment variable can open a non-causal path between arm and "
      "outcome (collider / selection bias), so these mode-stratified estimates "
      "are **descriptive supplements**, not de-confounded within-mode causal "
      "effects. The unbiased estimand remains the pooled ITT contrast, which "
      "does not condition on mode. The pre-registered use of this subgroup is "
      "the interaction test, and it is null.\n")

    w("\n## 5. Multiplicity -- Holm-Bonferroni\n")
    w("**m = 3 (outcome families only -- the plan's numbered decision rule):**\n")
    w(_md_table(holm["holm_m3"]))
    w("\n**m = 5 (supplementary -- adds the two pre-registered mode-interaction "
      "tests, per \"any subgroup analyses ... are also in the family\"):**\n")
    w(_md_table(holm["holm_m5"]))
    w("\nNo test is significant before correction under either reading, so Holm "
      "changes no verdict.\n")

    w("\n## 6. Per-protocol (NON-RANDOMISED, descriptive only -- not causal)\n")
    w(_md_table(pp))
    w("\nAgreement to the statement is confounded with engagement, education and "
      "motivation, which independently predict data quality. No causal reading. "
      "The 14 who declined are described, not tested.\n")

    w("\n## 7. Sensitivity specifications\n")
    w("\n### 7a. Filter-Missing rule (pre-registered dual specification)\n")
    w(_md_table(sens["filter_missing"]))
    w("\nPrimary and sensitivity agree in sign and magnitude for all three "
      "families. For H1 the uncorrected p-values straddle 0.05 (primary 0.063, "
      "sensitivity 0.025) -- the point estimates are -0.21 pp vs -0.27 pp -- but "
      "**neither survives the pre-registered Holm correction** (H1 p_Holm = 0.19 "
      "primary; 3 x 0.025 = 0.076 sensitivity). The qualitative verdict (null) is "
      "unchanged by the Filter-Missing coding choice; only the distance to the "
      "0.05 line moves. This is surfaced, not buried.\n")
    w("\n### 7b. Web-Never-Seen in Family A's denominator (footnote; spec NOT changed)\n")
    w(f"The pre-registration's Family A denominator table says "
      f"`Missing data (Web partial - Question Never Seen)` cells should not be in "
      f"the denominator; the build (frozen since Phase 3) includes them "
      f"({sens['wns_cells_total']:,} cells across "
      f"{sens['wns_respondents_affected']:,} respondents). **Neyda ruled "
      f"2026-09-03 to keep the as-built specification** -- changing an outcome "
      f"definition after seeing results is the move this project exists to "
      f"avoid -- and to report the alternative here as a sensitivity.\n")
    w(_md_table(sens["web_never_seen"]))
    w("\nRemoving those cells from the denominator (the pre-registration table's "
      "literal rule) shrinks the H1 point estimate from -0.213 pp to -0.097 pp "
      "and moves p from 0.063 to 0.55. Because the treatment arm is more "
      "web-heavy, it carries proportionally more Web-Never-Seen cells, so "
      "excluding them lifts the treatment denominator more and narrows the "
      "arm gap. **The direction is unchanged and the null becomes *more* clearly "
      "a null, not less** -- under the plan's literal denominator rule the "
      "primary hypothesis is further from significance, not closer. H3 is "
      "essentially unchanged; H2 is not applicable (Family B *is* the "
      "Web-Never-Seen count). The as-built spec (which keeps these cells) is the "
      "headline per Neyda's ruling; this shows the choice does not manufacture "
      "the result -- if anything it is load-bearing in the conservative "
      "direction.\n")

    w("\n## 8. Covariate balance (deferred from Phase 1; covariate set NOT pre-specified)\n")
    w(_md_table(bal_df))
    w("\n**How to read this.** A balance check on a survey experiment is "
      "**conditional on response** -- it compares the arms among people who "
      "answered, not among those randomised. Every covariate here (including "
      "survey mode) is measured at or after response, i.e. **post-randomisation**. "
      "So a gap is not evidence that randomisation failed; the flag was verified "
      "independently in Phase 1 from the codebook label and the `CommitmentStmt` "
      "alignment, by a route that does not depend on balance.\n")
    w("\nSeven of eight covariates -- every demographic and the design stratum "
      "`STRATUM` -- show no arm difference. **Survey mode does** (treatment 70.1% "
      "web vs control 65.9%, chi-square p = 0.0020, survives Bonferroni over the "
      "eight). This is **a finding to report, not a defect to fix**: it says the "
      "responding samples differ slightly in composition on one post-treatment "
      "variable. It does not bias the pooled ITT estimand (which does not "
      "condition on mode), and the mode-stratified analysis (section 4, with its "
      "collider caveat) is null within each mode. Phase 1 is **not** reopened -- "
      "that question (what `Treatment_H7_2` is) was already settled by an "
      "independent route, and a balance test cannot answer it.\n")

    w("\n## 9. Peeking illustration (NOT evidence)\n")
    w(_md_table(peek_df))

    w("\n## Assertion history (implied_n guard)\n")
    w(_md_table(pd.DataFrame(_ASSERTION_LOG)))

    (OUT / "RESULTS.md").write_text("\n".join(w_ for w_ in L), encoding="utf-8")


# ----------------------------------------------------------------------------
def main():
    frame = pd.read_parquet(FRAME_PATH)
    assert frame.shape == (7278, 72), frame.shape

    print("=" * 78)
    print("PHASE 5b -- PRE-REGISTERED ANALYSIS, respondent-level variance")
    print("=" * 78)

    print("\n[1-3] Pre-registered ITT analyses (primary first) ...")
    res = run_primary_and_secondary(frame)
    for key in ["H1", "H2", "H3"]:
        r = res[key]
        print(f"\n  {r['tag']}")
        print(f"    treatment {r['p_tx']*100:.3f}%  control {r['p_ctl']*100:.3f}%  "
              f"diff {r['difference']*100:+.3f} pp  "
              f"CI [{r['ci_difference'][0]*100:+.3f}, {r['ci_difference'][1]*100:+.3f}]  "
              f"z={r['z']:.3f}  p={r['p_value']:.4f}")
        print(f"    MDE empirical {r['mde']['mde_empirical']*100:.3f} pp | "
              f"grid {r['mde']['mde_grid_formula']*100:.3f} pp")
        print(f"    verdict: {r['verdict']}")

    print("\n[4] Mode subgroup (pre-registered) ...")
    mode_df = run_mode_subgroup(frame)
    print(mode_df.to_string(index=False))

    print("\n[5] Holm-Bonferroni multiplicity ...")
    holm = run_multiplicity(res, mode_df)
    print("  m = 3 (outcome families only, the plan's numbered decision rule):")
    print(holm["holm_m3"].to_string(index=False))
    print("  m = 5 (supplementary: + the two pre-registered mode-interaction tests):")
    print(holm["holm_m5"].to_string(index=False))

    print("\n[6] Per-protocol (NON-RANDOMISED) ...")
    pp = run_per_protocol(frame)
    print(pp.to_string(index=False))

    print("\n[7] Sensitivity: (a) Filter-Missing rule, (b) Web-Never-Seen footnote ...")
    sens = run_sensitivity(frame, res)
    print("  (a) Filter-Missing:")
    print(sens["filter_missing"].to_string(index=False))
    print(f"  (b) Web-Never-Seen ({sens['wns_cells_total']:,} cells / "
          f"{sens['wns_respondents_affected']:,} respondents; spec NOT changed):")
    print(sens["web_never_seen"].to_string(index=False))

    print("\n[8] Balance check (covariate set not pre-specified; conditional on response) ...")
    bal_df = run_balance(frame)
    print(bal_df.to_string(index=False))

    print("\n[9] Peeking illustration (NOT evidence) ...")
    peek_df = run_peeking(frame)
    print(peek_df.to_string(index=False))

    write_outputs(res, holm, pp, mode_df, sens, bal_df, peek_df)
    print(f"\nWrote tables to {TAB}, figures to {FIG}, and {OUT/'RESULTS.md'}")

    n_fired = sum(1 for a in _ASSERTION_LOG if a["guard"].startswith("FIRED"))
    print(f"\nimplied_n guard: {len(_ASSERTION_LOG)} estimates checked, "
          f"{n_fired} fired (all in the peeking illustration, if any).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
