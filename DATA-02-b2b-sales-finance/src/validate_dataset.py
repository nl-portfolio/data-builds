"""Validation harness for the Anchorpoint B2B sales dataset.

Run this after EVERY phase. Not once at generation time.

    python src/validate_dataset.py --phase 1.5
    python src/validate_dataset.py --phase 2
    python src/validate_dataset.py --phase 3
    python src/validate_dataset.py --phase 4

Why a standalone script rather than a validate() call inside the
generator: Phase 3 transforms the data, and transformations introduce
their own bugs (dropped rows in a merge, a filter that silently removes
lost deals, a groupby that reorders a cohort). A check that only runs at
generation time cannot catch any of that. This script re-reads the CSVs
from disk every time, so it catches drift introduced later.

Six tiers, escalating from "the file is shaped right" to "nobody has
quietly reintroduced the design flaw this project exists to avoid":

    T0  structural       row counts, required columns, dtypes, nulls
    T1  referential      foreign keys, orphan rows
    T2  reconciliation   totals that must agree with each other
    T3  logical          dates, ordering, causal impossibilities
    T4  statistical      plausibility bands and power, REPORTS not fails
    T5  anti-regression  guards against outcome encoding creeping back in

T0 through T3 are HARD. Any failure blocks the phase.
T4 REPORTS. A win rate outside the band is a signal to investigate the
mechanism, never a reason to edit a number toward a nicer story.
T5 is HARD and is the most important tier in this file. See its docstring.

T5 runs with no data present, so this script is useful from the moment
Phase 1.5 implementation starts.
"""

import argparse
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DOCS = ROOT / "docs"
REPORTS = DOCS / "validation"

WINDOW_START = datetime(2024, 7, 1)
WINDOW_END = datetime(2026, 8, 31)
ENTERPRISE_PUSH_DATE = datetime(2025, 1, 1)

EXPECTED_ROWS = {
    "deals": 2200,
    "sales_pipeline": 400,
    "companies": 900,
    "sales_reps": 30,
    "sm_spend": 78,
}

REQUIRED_COLUMNS = {
    "companies": ["company_id", "company_name", "industry", "region",
                  "employee_count", "founding_date"],
    "sales_reps": ["rep_id", "rep_name", "segment", "hire_date", "prior_segment",
                   "has_enterprise_experience", "playbook_type",
                   "quota_annual_usd", "is_founder_led"],
    "deals": ["deal_id", "company_id", "rep_id", "segment", "region",
              "acquisition_channel", "deal_size_usd", "opened_date", "close_date",
              "deal_won", "loss_reason", "stakeholders_required",
              "stakeholders_engaged", "sales_cycle_days"],
    "deal_stage_history": ["deal_id", "stage", "entered_date", "exited_date",
                           "days_in_stage"],
    "customers": ["customer_id", "deal_id", "segment", "cohort_month",
                  "annual_contract_value", "churn_date",
                  "months_retained_observed", "is_active_at_window_end"],
    "sales_pipeline": ["opportunity_id", "company_id", "rep_id", "segment",
                       "region", "acquisition_channel", "stage",
                       "stage_entered_date", "days_in_current_stage",
                       "forecast_close_date", "forecast_amount_usd",
                       "win_probability_pct"],
    "sm_spend": ["month", "segment", "spend_usd"],
}

SEGMENTS = ["Enterprise", "Mid-Market", "SMB"]
DEAL_SIZE_TARGETS = {"Enterprise": 95_000, "Mid-Market": 32_000, "SMB": 11_000}
VALID_LOSS_REASONS = {"unqualified", "stalled_no_decision", "lost_to_competitor"}
STAGE_ORDER = ["Prospecting", "Qualified", "Proposal", "Negotiation"]

# Plausibility bands from the Phase 1.5 mechanism calibration. NOT targets.
WIN_RATE_BANDS = {
    "Enterprise_pre_push": (0.18, 0.34),
    "Enterprise_post_push": (0.06, 0.20),
    "Mid-Market": (0.22, 0.38),
    "SMB": (0.27, 0.43),
}

results = []


def check(tier, name, passed, detail="", hard=True):
    results.append({"tier": tier, "name": name, "passed": bool(passed),
                    "detail": detail, "hard": hard})
    return passed


def load(name):
    path = RAW / f"{name}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    for col in df.columns:
        if col.endswith(("_date", "_month")) or col == "month":
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


# ------------------------------------------------------------------
# T0 STRUCTURAL
# ------------------------------------------------------------------
def tier0(tables):
    for name, df in tables.items():
        if df is None:
            check("T0", f"{name}.csv exists", False, "file missing")
            continue
        check("T0", f"{name}.csv exists", True)

        expected = EXPECTED_ROWS.get(name)
        if expected is not None:
            check("T0", f"{name} row count == {expected}", len(df) == expected,
                  f"got {len(df)}")

        missing = set(REQUIRED_COLUMNS.get(name, [])) - set(df.columns)
        check("T0", f"{name} has all required columns", not missing,
              f"missing {sorted(missing)}" if missing else "")

        # Columns that are allowed to be null, everything else must not be.
        nullable = {"churn_date", "loss_reason", "exited_date", "prior_segment"}
        for col in df.columns:
            if col in nullable:
                continue
            n = int(df[col].isna().sum())
            check("T0", f"{name}.{col} has no nulls", n == 0, f"{n} nulls")

    # deals must NOT carry the removed ambiguous scalar
    deals = tables.get("deals")
    if deals is not None:
        check("T0", "deals does not carry legacy days_in_stage",
              "days_in_stage" not in deals.columns,
              "Phase 1's ambiguous scalar is back; per-stage timing belongs "
              "in deal_stage_history")


# ------------------------------------------------------------------
# T1 REFERENTIAL INTEGRITY
# ------------------------------------------------------------------
def tier1(t):
    companies, reps, deals = t.get("companies"), t.get("sales_reps"), t.get("deals")
    customers, pipeline = t.get("customers"), t.get("sales_pipeline")
    hist = t.get("deal_stage_history")
    if deals is None or companies is None or reps is None:
        return

    for tbl, label in [(deals, "deals"), (pipeline, "sales_pipeline")]:
        if tbl is None:
            continue
        orphan_c = ~tbl["company_id"].isin(companies["company_id"])
        check("T1", f"{label} has no orphan company_id", orphan_c.sum() == 0,
              f"{int(orphan_c.sum())} orphans")
        orphan_r = ~tbl["rep_id"].isin(reps["rep_id"])
        check("T1", f"{label} has no orphan rep_id", orphan_r.sum() == 0,
              f"{int(orphan_r.sum())} orphans")

    if customers is not None:
        orphan = ~customers["deal_id"].isin(deals["deal_id"])
        check("T1", "customers has no orphan deal_id", orphan.sum() == 0,
              f"{int(orphan.sum())} orphans")
        won_ids = set(deals.loc[deals["deal_won"].astype(bool), "deal_id"])
        bad = ~customers["deal_id"].isin(won_ids)
        check("T1", "no customer points at a lost deal", bad.sum() == 0,
              f"{int(bad.sum())} customers on lost deals")

    if hist is not None:
        orphan = ~hist["deal_id"].isin(deals["deal_id"])
        check("T1", "deal_stage_history has no orphan deal_id", orphan.sum() == 0,
              f"{int(orphan.sum())} orphans")


# ------------------------------------------------------------------
# T2 RECONCILIATION
# ------------------------------------------------------------------
def tier2(t):
    deals, customers, hist = t.get("deals"), t.get("customers"), t.get("deal_stage_history")
    spend = t.get("sm_spend")

    if deals is not None and customers is not None:
        won = int(deals["deal_won"].astype(bool).sum())
        check("T2", "customers row count == won deals exactly",
              len(customers) == won, f"customers {len(customers)} vs won {won}")

    if deals is not None and hist is not None:
        per_deal = hist.groupby("deal_id")["days_in_stage"].sum()
        merged = deals.set_index("deal_id")["sales_cycle_days"].reindex(per_deal.index)
        drift = (per_deal - merged).abs()
        worst = float(drift.max()) if len(drift) else 0.0
        check("T2", "stage days sum to sales_cycle_days (within 1 day)",
              worst <= 1.0, f"worst drift {worst:.2f} days")

    if spend is not None:
        n_months = spend["month"].nunique()
        check("T2", "sm_spend covers 26 months x 3 segments",
              n_months == 26 and len(spend) == 78,
              f"{n_months} months, {len(spend)} rows")

    if deals is not None:
        counts = deals["segment"].value_counts().to_dict()
        expected = {"Enterprise": 420, "Mid-Market": 760, "SMB": 1020}
        check("T2", "segment attempt counts match the locked mix",
              counts == expected, f"got {counts}")


# ------------------------------------------------------------------
# T3 LOGICAL CONSISTENCY
# ------------------------------------------------------------------
def tier3(t):
    deals, reps, hist = t.get("deals"), t.get("sales_reps"), t.get("deal_stage_history")
    customers = t.get("customers")
    if deals is None:
        return

    check("T3", "close_date >= opened_date for every deal",
          (deals["close_date"] >= deals["opened_date"]).all(),
          f"{int((deals['close_date'] < deals['opened_date']).sum())} violations")

    in_window = (deals["close_date"] >= WINDOW_START) & (deals["close_date"] <= WINDOW_END)
    check("T3", "every close_date inside the observation window", in_window.all(),
          f"{int((~in_window).sum())} outside")

    won = deals["deal_won"].astype(bool)
    check("T3", "won deals have null loss_reason", deals.loc[won, "loss_reason"].isna().all())
    lost_reasons = set(deals.loc[~won, "loss_reason"].dropna().unique())
    check("T3", "lost deals use only valid loss_reason values",
          lost_reasons <= VALID_LOSS_REASONS, f"unexpected {lost_reasons - VALID_LOSS_REASONS}")

    check("T3", "stakeholders_engaged <= stakeholders_required",
          (deals["stakeholders_engaged"] <= deals["stakeholders_required"]).all())

    # THE CAUSAL IMPOSSIBILITY CHECK. An Enterprise deal opened before the
    # push cannot be worked by a rep who had not been hired yet. This is the
    # single easiest bug to introduce in generate_deals() and the hardest to
    # spot downstream, because the resulting numbers still look plausible.
    if reps is not None:
        m = deals.merge(reps[["rep_id", "hire_date"]], on="rep_id", how="left")
        leak = m["opened_date"] < m["hire_date"]
        check("T3", "no deal opened before its rep was hired", leak.sum() == 0,
              f"{int(leak.sum())} deals worked by a rep not yet hired")

        ent = m[m["segment"] == "Enterprise"]
        pre = ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]
        bad = pre["hire_date"] >= ENTERPRISE_PUSH_DATE
        check("T3", "pre-push Enterprise deals belong to founder-led reps",
              bad.sum() == 0, f"{int(bad.sum())} assigned to post-push AEs")

    if hist is not None:
        ranked = hist.copy()
        ranked["order"] = ranked["stage"].map({s: i for i, s in enumerate(STAGE_ORDER)})
        bad = ranked.groupby("deal_id")["order"].apply(lambda s: not s.is_monotonic_increasing)
        check("T3", "stage history is in forward stage order", (~bad).all(),
              f"{int(bad.sum())} deals out of order")

    if customers is not None:
        has_churn = customers["churn_date"].notna()
        check("T3", "churn_date is null exactly when customer is active",
              (has_churn != customers["is_active_at_window_end"].astype(bool)).all())


# ------------------------------------------------------------------
# T4 STATISTICAL PLAUSIBILITY. Reports, does not block.
# ------------------------------------------------------------------
def two_prop_ci(p1, n1, p2, n2):
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    return d, se, (d - 1.96 * se, d + 1.96 * se)


def tier4(t):
    deals, customers = t.get("deals"), t.get("customers")
    if deals is None:
        return
    won = deals["deal_won"].astype(bool)

    for seg in ["Mid-Market", "SMB"]:
        sub = deals[deals["segment"] == seg]
        if not len(sub):
            continue
        wr = sub["deal_won"].astype(bool).mean()
        lo, hi = WIN_RATE_BANDS[seg]
        check("T4", f"{seg} win rate inside plausibility band",
              lo <= wr <= hi, f"{wr:.1%} (band {lo:.0%}-{hi:.0%}, n={len(sub)})",
              hard=False)

    ent = deals[deals["segment"] == "Enterprise"]
    if len(ent):
        pre = ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]
        post = ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]
        if len(pre) and len(post):
            p1 = pre["deal_won"].astype(bool).mean()
            p2 = post["deal_won"].astype(bool).mean()
            for label, p, n in [("Enterprise_pre_push", p1, len(pre)),
                                ("Enterprise_post_push", p2, len(post))]:
                lo, hi = WIN_RATE_BANDS[label]
                check("T4", f"{label} win rate inside band", lo <= p <= hi,
                      f"{p:.1%} (band {lo:.0%}-{hi:.0%}, n={n})", hard=False)

            d, se, (clo, chi) = two_prop_ci(p1, len(pre), p2, len(post))
            z = d / se if se else 0.0
            check("T4", "Enterprise pre/post difference excludes zero",
                  clo > 0,
                  f"diff {d*100:.1f}pp, 95% CI [{clo*100:.1f}, {chi*100:.1f}]pp, "
                  f"z={z:.2f}, n={len(pre)}/{len(post)}", hard=False)

    for seg, target in DEAL_SIZE_TARGETS.items():
        sub = deals[deals["segment"] == seg]
        if not len(sub):
            continue
        mean = sub["deal_size_usd"].mean()
        check("T4", f"{seg} mean deal size within 15% of target",
              abs(mean - target) / target <= 0.15,
              f"${mean:,.0f} vs ${target:,.0f}", hard=False)

    # CENSORING BIAS. The single subtlest trap in generation. If deals whose
    # close_date fell outside the window were discarded, long-cycle deals get
    # dropped preferentially, and long-cycle deals are exactly the stalled
    # Enterprise ones. That would suppress the very signal being studied.
    # A healthy dataset shows stalled deals with LONGER cycles than won ones.
    if "sales_cycle_days" in deals.columns:
        stalled = deals[deals["loss_reason"] == "stalled_no_decision"]["sales_cycle_days"]
        wondeals = deals[won]["sales_cycle_days"]
        if len(stalled) and len(wondeals):
            check("T4", "stalled deals have longer cycles than won deals "
                  "(censoring-bias smoke test)",
                  stalled.mean() > wondeals.mean(),
                  f"stalled {stalled.mean():.0f}d vs won {wondeals.mean():.0f}d",
                  hard=False)

    if customers is not None and "churn_date" in customers.columns:
        ev = customers[customers["churn_date"].notna()].groupby("segment").size().to_dict()
        ent_ev = ev.get("Enterprise", 0)
        check("T4", "Enterprise churn events are too few to measure retention "
              "(expected, must be disclosed)", True,
              f"{ent_ev} Enterprise churn events. If this is under ~15, Phase 3 "
              f"MUST use benchmark churn with a sensitivity range and say so. "
              f"All segments: {ev}", hard=False)


# ------------------------------------------------------------------
# T5 ANTI-REGRESSION. The most important tier here.
# ------------------------------------------------------------------
def tier5():
    """Guards against the design flaw this project was rebuilt to remove.

    The Phase 1 build encoded its conclusion as a generator parameter and
    wrote the expected answers into the locked docs before any data existed.
    That is an easy mistake to reintroduce under time pressure, and it is
    invisible in the output: the numbers still look fine. These checks are
    the tripwire.
    """
    gen = ROOT / "src" / "generate_data.py"
    if gen.exists():
        src = gen.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in src.splitlines()
            if not line.lstrip().startswith("#")
        )
        for pattern, label in [
            (r'"win_rate[_a-z]*"\s*:', "a win_rate dict key"),
            (r'\bwin_rate_(pre|post)\b\s*=', "a win_rate_pre/post assignment"),
            (r'\bPROBLEM_TRIGGER_DATE\b', "PROBLEM_TRIGGER_DATE"),
        ]:
            hits = re.findall(pattern, code)
            check("T5", f"generator contains no {label}", not hits,
                  f"found {len(hits)}: outcome encoding has been reintroduced"
                  if hits else "")

    banned_phrases = [
        "what the answer will show",
        "the answer will show",
        "what this will show",
    ]
    for doc in ["locked_business_questions.md", "case_study_scenario.md",
                "data_model.md"]:
        p = DOCS / doc
        if not p.exists():
            continue
        low = p.read_text(encoding="utf-8").lower()
        # Scan only the body, not the preamble. The Phase 1.5 rewrite notes
        # legitimately quote the old "what the answer will show" heading while
        # explaining that it was deleted, and that meta-commentary is the
        # opposite of the failure being guarded against. A real prediction
        # would live inside a question or scenario section, so start there.
        anchors = ["## question 1", "## the diagnostic hypothesis", "## core tables"]
        start = min([low.find(a) for a in anchors if low.find(a) >= 0] or [0])
        body = low[start:]
        for phrase in banned_phrases:
            found = phrase in body
            check("T5", f"{doc} does not predict results ('{phrase}')",
                  not found,
                  "a locked doc is stating findings before they are measured"
                  if found else "")

    ctx = DOCS / "project_context.md"
    if ctx.exists():
        txt = ctx.read_text(encoding="utf-8")
        check("T5", "project_context.md has an entry dated today",
              datetime.now().strftime("%Y-%m-%d") in txt,
              "every session must log a dated entry before ending", hard=False)


# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="unspecified")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()

    names = ["companies", "sales_reps", "deals", "deal_stage_history",
             "customers", "sales_pipeline", "sm_spend"]
    tables = {n: load(n) for n in names}
    have_data = any(v is not None for v in tables.values())

    if have_data:
        tier0(tables)
        tier1(tables)
        tier2(tables)
        tier3(tables)
        tier4(tables)
    else:
        print("No CSVs found in data/raw. Running T5 doc and code checks only.\n")
    tier5()

    hard_fail = [r for r in results if r["hard"] and not r["passed"]]
    soft_fail = [r for r in results if not r["hard"] and not r["passed"]]

    lines = [f"# Validation report, phase {args.phase}",
             f"Run: {datetime.now().isoformat(timespec='seconds')}", ""]
    for tier in ["T0", "T1", "T2", "T3", "T4", "T5"]:
        rows = [r for r in results if r["tier"] == tier]
        if not rows:
            continue
        lines.append(f"## {tier}")
        for r in rows:
            mark = "PASS" if r["passed"] else ("WARN" if not r["hard"] else "FAIL")
            lines.append(f"- [{mark}] {r['name']}" + (f" :: {r['detail']}" if r["detail"] else ""))
        lines.append("")
    lines.append(f"**{len(hard_fail)} hard failures, {len(soft_fail)} warnings, "
                 f"{len(results)} checks total.**")
    report = "\n".join(lines)
    print(report)

    if not args.no_report:
        REPORTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = REPORTS / f"validation-phase{args.phase}-{stamp}.md"
        out.write_text(report, encoding="utf-8")
        print(f"\nWritten to {out.relative_to(ROOT)}")

    if hard_fail:
        print("\nBLOCKED. Hard failures must be fixed before this phase closes.")
        sys.exit(1)
    if soft_fail:
        print("\nPASSED WITH WARNINGS. Investigate the mechanism. Do not edit "
              "numbers to silence a warning.")
    sys.exit(0)


if __name__ == "__main__":
    main()
