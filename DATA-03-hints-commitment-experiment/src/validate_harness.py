"""
Harness validation for the survey-weighted RATE estimator the analysis calls.

This is the Phase 4b gate. It replaces the Phase 4 script of the same name,
which only reproduced published single-variable proportions and never exercised
the per-respondent rate estimator or tested a standard error against a known
value -- which is why the Phase 5 unit-of-analysis error and the src/weighting.py
"/ 50" error both passed it. Declared in SITEMAP.md under Phase 4b.

What this script proves, in order:

  1. SYNTHETIC FIXTURE A -- jackknife_se() recovers an analytically known
     variance (the textbook SE of a mean) to machine precision.
  2. SYNTHETIC FIXTURE B (negative control) -- computing the same quantity the
     wrong way, pooling items across respondents as Phase 5 did, gives an answer
     sqrt(mean item count) times too small; the harness does NOT return it, and
     the wired-in sanity assertion fires on it.
  3. SANITY ASSERTION unit checks -- fires when implied n exceeds the respondent
     count, no-ops on degenerate input, passes on a correct estimate.
  4. REAL-DATA SELF-CONSISTENCY (arm-blind) -- Families A, B, C: weighted mean of
     the per-respondent rate, jackknife SE, the design effect FOR THIS ESTIMATOR
     (vs var(rate)/n, not p(1-p)/n), effective n, implied n <= respondents.
  5. PUBLISHED-FIGURE REPRODUCTION vs ASTP/ONC Data Brief 77, denominators
     matched to the brief's Notes: offered access (HCP or insurer) 77%, app use
     57%, HCP encouragement 89%. Tolerance +/- 0.5 pp (whole-percent publication).
  6. PHASE 3b FIGURE RECONCILIATION -- pooled ratios, denominator min/median/max,
     frame shape, recomputed from analysis_frame.parquet on disk.

Arm-blind: no statistic is split by Treatment_H7_2 anywhere in this file.
Section 5 uses only the public arm SIZES (1,513 / 5,765) for an MDE
approximation, never an arm-stratified outcome.

Run:  python src/validate_harness.py
Exits non-zero if any assertion fails.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from load_hints import load_hints_data
from weighting import (
    JACKKNIFE_MULTIPLIER,
    N_REPLICATES,
    POINT_ESTIMATE_WEIGHT,
    REPLICATE_WEIGHT_COLS,
    SANITY_N_TOLERANCE,
    assert_variance_plausible,
    confidence_interval,
    design_effect,
    estimate_rate,
    jackknife_se,
    weighted_proportion,
    weighted_variance,
)

PROJECT_ROOT = Path(__file__).parent.parent
RDA_PATH = PROJECT_ROOT / "data" / "raw" / "HINTS7_R_20250731" / "hints7_public.rda"
FRAME_PATH = PROJECT_ROOT / "data" / "processed" / "analysis_frame.parquet"
R_EXPORT_PATH = PROJECT_ROOT / "data" / "processed" / "analysis_frame_r_export.csv"

REPRO_TOLERANCE_PP = 0.5  # DB77 reports whole percentages -> rounding tolerance

_failures = []


def check(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f"  -- {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


# ======================================================================
# Section 1 + 2: synthetic fixtures and the sanity assertion
# ======================================================================

def _make_fixture(numerators, denominator=100):
    """n = N_REPLICATES respondents, base weight 1. Replicate i zeroes row i and
    rescales the rest to n/(n-1) so each replicate is the leave-one-out mean.

    For a weighted mean of a per-respondent value r_j this gives, exactly:
        theta_i - theta_0 = (mean(r) - r_i) / (n - 1)
        sum_i (theta_i - theta_0)^2 = s^2 / (n - 1)        (s^2 = var, ddof=1)
        Var_jk = 0.98 * s^2/(n-1) = (49/50) * s^2/49 = s^2/50
        SE_jk  = s / sqrt(n)                               <- textbook SE of a mean
    """
    n = len(numerators)
    assert n == N_REPLICATES, "fixture must have exactly N_REPLICATES rows"
    df = pd.DataFrame(
        {
            "num": np.asarray(numerators, dtype=float),
            "den": np.full(n, float(denominator)),
            POINT_ESTIMATE_WEIGHT: np.ones(n),
        }
    )
    for i in range(1, n + 1):
        w = np.full(n, n / (n - 1))
        w[i - 1] = 0.0
        df[f"PERSON_FINWT{i}"] = w
    return df


def section_1_synthetic_fixture():
    print("\n== Section 1: synthetic fixture, analytically known variance ==")

    # Fixture A: mild between-respondent variation. r in {0.02, 0.06}.
    nums_a = [2] * 25 + [6] * 25
    df_a = _make_fixture(nums_a)
    rates_a = df_a["num"].to_numpy() / df_a["den"].to_numpy()
    point_a = weighted_proportion(df_a, "num", "den")
    se_harness_a = jackknife_se(df_a, "num", "den", point_a)
    s_a = rates_a.std(ddof=1)
    se_analytic_a = s_a / np.sqrt(len(rates_a))

    check("fixture A point estimate == 0.04", np.isclose(point_a, 0.04, atol=1e-12),
          f"{point_a:.12f}")
    check(
        "fixture A: jackknife_se == analytic s/sqrt(n) to 1e-12",
        np.isclose(se_harness_a, se_analytic_a, rtol=0, atol=1e-12),
        f"harness={se_harness_a:.12e}  analytic={se_analytic_a:.12e}  "
        f"diff={abs(se_harness_a - se_analytic_a):.2e}",
    )
    se_srs_prop_a = np.sqrt(point_a * (1 - point_a) / len(rates_a))
    check(
        "fixture A: p(1-p)/n SE would be ~9.7x the truth (wrong reference)",
        se_srs_prop_a / se_analytic_a > 5,
        f"ratio {se_srs_prop_a / se_analytic_a:.2f}x",
    )

    # Fixture B (negative control): per-respondent rate is maximally clustered
    # (0/1), so pooling items across respondents understates the SE by sqrt(m).
    m = 100
    nums_b = [m] * 20 + [0] * 30
    df_b = _make_fixture(nums_b, denominator=m)
    rates_b = df_b["num"].to_numpy() / df_b["den"].to_numpy()
    point_b = weighted_proportion(df_b, "num", "den")
    se_harness_b = jackknife_se(df_b, "num", "den", point_b)
    se_analytic_b = rates_b.std(ddof=1) / np.sqrt(len(rates_b))

    sum_num, sum_den = df_b["num"].sum(), df_b["den"].sum()
    p_item = sum_num / sum_den
    se_item_pooled = np.sqrt(p_item * (1 - p_item) / sum_den)  # the Phase 5 way
    ratio = se_harness_b / se_item_pooled

    print("\n== Section 2: negative control (Phase 5 item-pooling) ==")
    check("fixture B point estimate == 0.40", np.isclose(point_b, 0.40, atol=1e-12),
          f"{point_b:.12f}")
    check(
        "fixture B: jackknife_se == analytic respondent-level SE to 1e-12",
        np.isclose(se_harness_b, se_analytic_b, rtol=0, atol=1e-12),
        f"harness={se_harness_b:.12e}",
    )
    check(
        "negative control: harness SE / item-pooled SE ~ sqrt(mean item count)",
        np.isclose(ratio, np.sqrt(m), rtol=0.05),
        f"ratio={ratio:.4f}  sqrt(m)={np.sqrt(m):.4f}  "
        f"(harness {se_harness_b:.3e} vs item-pooled {se_item_pooled:.3e})",
    )

    disp_b = weighted_variance(rates_b, df_b[POINT_ESTIMATE_WEIGHT].to_numpy())
    fired_on_wrong = False
    try:
        assert_variance_plausible(point_b, se_item_pooled, len(rates_b),
                                  dispersion=disp_b, label="neg-control")
    except AssertionError:
        fired_on_wrong = True
    check("sanity assertion FIRES on the item-pooled SE", fired_on_wrong,
          f"implied_n={disp_b / se_item_pooled**2:,.0f} vs n=50")

    passed_on_right = True
    try:
        assert_variance_plausible(point_b, se_harness_b, len(rates_b),
                                  dispersion=disp_b, label="neg-control-correct")
    except AssertionError:
        passed_on_right = False
    check("sanity assertion PASSES on the correct SE", passed_on_right,
          f"implied_n={disp_b / se_harness_b**2:,.0f} vs n=50")


def section_2b_sanity_unit():
    print("\n== Section 2b: sanity assertion unit checks ==")
    # obviously-too-small SE on a proportion -> fires
    fired = False
    try:
        assert_variance_plausible(0.5, 1e-4, 1000, label="tiny-se")
    except AssertionError:
        fired = True
    check("fires when implied_n (2.5e7) >> n (1000)", fired)

    # plausible SE -> passes
    ok = True
    try:
        assert_variance_plausible(0.5, np.sqrt(0.25 / 1000), 1000, label="srs-se")
    except AssertionError:
        ok = False
    check("passes at exactly the SRS SE (implied_n == n)", ok)

    # degenerate inputs -> no-op, never raises
    noop = True
    try:
        assert_variance_plausible(0.0, 0.0, 10, label="deg1")
        assert_variance_plausible(np.nan, 0.01, 10, label="deg2")
        assert_variance_plausible(0.5, -1.0, 10, label="deg3")
        assert_variance_plausible(0.5, 0.01, 10, dispersion=0.0, label="deg4")
    except AssertionError:
        noop = False
    check("no-ops on degenerate input (p in {0,1}, se<=0, nan, dispersion<=0)", noop)


# ======================================================================
# Section 3: real-data self-consistency (arm-blind)
# ======================================================================

def section_3_real_data(frame):
    print("\n== Section 3: real-data self-consistency (pooled, arm-blind) ==")
    rows = []
    specs = [
        ("Family A (item nonresponse)", "family_a_numerator", "family_a_denominator", frame),
        ("Family C (response error)", "family_c_numerator", "family_c_denominator", frame),
        ("Family B (break-off, web)", "family_b_numerator", "family_b_denominator",
         frame[frame["family_b_denominator"].notna()]),
    ]
    for name, num, den, data in specs:
        r = estimate_rate(data, num, den, name)
        rows.append((name, r))
        check(
            f"{name}: implied_n ({r['implied_n']:,.0f}) <= respondents ({r['n_respondents']:,})",
            r["implied_n"] <= r["n_respondents"] * SANITY_N_TOLERANCE,
        )
        check(
            f"{name}: rate-estimator DEFF in a sane range (0.8 - 6)",
            0.8 <= r["design_effect"] <= 6.0,
            f"DEFF={r['design_effect']:.3f}  (proportion-basis DEFF={r['design_effect_proportion']:.3f})",
        )
    print("\n  Summary (weighted mean of per-respondent rate):")
    print(f"  {'outcome':30s} {'estimate':>10s} {'SE (pp)':>9s} {'95% CI':>20s} "
          f"{'DEFF':>7s} {'n_eff':>9s}")
    for name, r in rows:
        ci = f"[{r['ci_lower']*100:.3f}, {r['ci_upper']*100:.3f}]"
        print(f"  {name:30s} {r['point_estimate']*100:9.4f}% {r['se']*100:9.4f} "
              f"{ci:>20s} {r['design_effect']:7.3f} {r['n_effective']:9,.0f}")
    return {name: r for name, r in rows}


# ======================================================================
# Section 4: published-figure reproduction vs ASTP/ONC Data Brief 77
# ======================================================================

def _wprop(indicator, universe, w0, wr):
    ind = np.asarray(indicator, dtype=float)
    uni = np.asarray(universe, dtype=bool)
    f = lambda w: np.sum(ind[uni] * w[uni]) / np.sum(w[uni])
    theta0 = f(w0)
    reps = np.array([f(wr[:, i]) for i in range(wr.shape[1])])
    se = np.sqrt(JACKKNIFE_MULTIPLIER * np.sum((reps - theta0) ** 2))
    return theta0, se, int(uni.sum())


def section_4_published(raw):
    print("\n== Section 4: reproduce ASTP/ONC Data Brief 77 (denominators per its Notes) ==")
    w0 = raw[POINT_ESTIMATE_WEIGHT].to_numpy(dtype=float)
    wr = raw[REPLICATE_WEIGHT_COLS].to_numpy(dtype=float)

    oa = raw["OfferedAccessHCP3"].astype(str)
    oi = raw["OfferedAccessInsurer3"].astype(str)
    he = raw["HCPEncourageOnlineRec2"].astype(str)
    ha = raw["HowAccessOnlineRecord2"].astype(str)

    valid_vals = ["Yes", "No", "Don't know"]
    offered_either = (oa == "Yes") | (oi == "Yes")
    either_valid = oa.isin(valid_vals) | oi.isin(valid_vals)

    targets = []

    # Figure 1: "Offered online access ... by HCP OR INSURER" = 77%.
    # Phase 4 used OfferedAccessHCP3 alone (-> 75.3%, the 1.7 pp miss). The brief's
    # measure combines the HCP and insurer questions; denominator = valid response
    # to at least one ("Denominator excludes missing responses", DB77 Notes).
    t, se, n = _wprop(offered_either, either_valid, w0, wr)
    targets.append(("Offered online access (HCP or insurer)", 77.0, t, se, n,
                    "num = HCP=Yes OR Insurer=Yes; denom = valid Y/N/DK to >=1 of the two"))

    # Figure 4: app-based access = 57%. Denominator = accessed portal >= once and
    # reported a method; "Used App" = app only or app+website. DK shown separately
    # in the brief, so excluded from the denominator.
    app = ha.isin(["App", "Both app and website"])
    method_given = ha.isin(["App", "Website", "Both app and website"])
    t, se, n = _wprop(app, method_given, w0, wr)
    targets.append(("Used an app to access records", 57.0, t, se, n,
                    "num = App or Both; denom = App/Website/Both (DK excluded)"))

    # Figure 3: HCP encouragement = 89%. Denominator = individuals offered access
    # by a HCP or insurer (DB77 Figure 3 Notes, verbatim).
    t, se, n = _wprop(he == "Yes", offered_either & he.isin(["Yes", "No"]), w0, wr)
    targets.append(("Encouraged by HCP to use portal", 89.0, t, se, n,
                    "num = encouraged=Yes; denom = offered (HCP or insurer)=Yes & enc in Y/N"))

    print(f"  tolerance: +/- {REPRO_TOLERANCE_PP} pp (DB77 publishes whole percentages)\n")
    print(f"  {'figure':40s} {'pub':>5s} {'python':>8s} {'delta':>7s} {'n':>6s}  verdict")
    for name, pub, est, se, n, rule in targets:
        delta = est * 100 - pub
        ok = abs(delta) <= REPRO_TOLERANCE_PP
        print(f"  {name:40s} {pub:4.0f}% {est*100:7.2f}% {delta:+6.2f} {n:6d}  "
              f"{'PASS' if ok else 'FAIL'}")
        print(f"       {rule}")
        check(f"reproduce '{name}' within {REPRO_TOLERANCE_PP} pp", ok,
              f"python {est*100:.2f}% vs published {pub:.0f}%")

    # Document the diagnosed gap explicitly.
    t_hcp_only, _, _ = _wprop(oa == "Yes", oa.isin(valid_vals), w0, wr)
    print(f"\n  Gap diagnosis: OfferedAccessHCP3 alone = {t_hcp_only*100:.2f}% "
          f"(Phase 4's 1.7 pp miss). Adding OfferedAccessInsurer3 -> "
          f"{targets[0][2]*100:.2f}%. The remainder is rounding.")


# ======================================================================
# Section 5: Phase 3b figure reconciliation (from the artifact on disk)
# ======================================================================

def section_5_reconcile(frame):
    print("\n== Section 5: recompute Phase 3b figures from analysis_frame.parquet ==")
    claims = {
        "pooled Family A ratio (sum num / sum den)": (
            frame["family_a_numerator"].sum() / frame["family_a_denominator"].sum() * 100,
            1.976, 0.01),
        "pooled Family C ratio": (
            frame["family_c_numerator"].sum() / frame["family_c_denominator"].sum() * 100,
            0.524, 0.01),
        "pooled Family A sensitivity": (
            frame["family_a_numerator"].sum() / frame["applicable_count_sens"].sum() * 100,
            1.988, 0.01),
        "pooled Family C sensitivity": (
            frame["family_c_numerator"].sum() / frame["applicable_count_sens"].sum() * 100,
            0.527, 0.01),
        "pooled Family B (web) ratio": (
            frame.loc[frame["family_b_denominator"].notna(), "family_b_numerator"].sum()
            / frame.loc[frame["family_b_denominator"].notna(), "family_b_denominator"].sum() * 100,
            7.671, 0.01),
    }
    for name, (got, claimed, tol) in claims.items():
        check(f"{name}: {got:.3f}% matches Phase 3b's {claimed}%",
              abs(got - claimed) <= tol, f"recomputed {got:.4f}%")

    ac = frame["applicable_count"]
    check("denominator min/median/max == 223 / 283 / 368",
          (ac.min(), ac.median(), ac.max()) == (223, 283.0, 368),
          f"{ac.min()} / {ac.median()} / {ac.max()}")
    check("frame shape == (7278, 72)", frame.shape == (7278, 72), str(frame.shape))
    check("FormType == 4861 web / 2417 paper",
          frame["FormType"].value_counts().to_dict().get("HINTS7, standard version - web") == 4861
          and frame["FormType"].value_counts().to_dict().get("HINTS7, standard version - paper") == 2417)
    cs = frame["CommitmentStmt"].value_counts().to_dict()
    check("CommitmentStmt == 1389 Yes / 14 No / 110 NA / 5765 Inapplicable",
          cs.get("Yes") == 1389 and cs.get("No") == 14
          and cs.get("Missing data (Not Ascertained)") == 110
          and cs.get("Inapplicable, not in treatment group") == 5765)
    check("family_a_numerator <= denominator for every respondent",
          bool((frame["family_a_numerator"] <= frame["family_a_denominator"]).all()))
    check("family_c_numerator <= denominator for every respondent",
          bool((frame["family_c_numerator"] <= frame["family_c_denominator"]).all()))
    check("all primary rates in [0, 1]",
          bool(frame["family_a_rate"].between(0, 1).all()
               and frame["family_c_rate"].between(0, 1).all()))


def export_for_r(frame):
    """Minimal CSV for the R cross-check: per-respondent rates only, joined to the
    .rda's weights by row order in crosscheck.R. Keeps the R check independent
    without re-deriving the frame in R or dragging 51 weight columns into a CSV."""
    cols = ["respondent_idx", "family_a_rate", "family_c_rate", "family_b_rate"]
    frame[cols].to_csv(R_EXPORT_PATH, index=False)
    print(f"\nWrote {R_EXPORT_PATH.name} for src/crosscheck.R  ({frame.shape[0]} rows)")


def main():
    print("=" * 72)
    print("PHASE 4b HARNESS VALIDATION  --  src/validate_harness.py")
    print("=" * 72)

    frame = pd.read_parquet(FRAME_PATH)
    raw = load_hints_data(str(RDA_PATH))

    section_1_synthetic_fixture()
    section_2b_sanity_unit()
    section_3_real_data(frame)
    section_4_published(raw)
    section_5_reconcile(frame)
    export_for_r(frame)

    print("\n" + "=" * 72)
    if _failures:
        print(f"HARNESS VALIDATION FAILED: {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("HARNESS VALIDATION PASSED: all checks green.")
    print("  - jackknife_se recovers a known analytic variance to machine precision")
    print("  - negative control confirms the harness does not return the item-pooled answer")
    print("  - the wired-in sanity assertion fires on the Phase 5 failure mode")
    print("  - published DB77 figures reproduced within 0.5 pp; 1.7 pp gap diagnosed")
    print("  - Phase 3b figures reconcile exactly from the frame on disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
