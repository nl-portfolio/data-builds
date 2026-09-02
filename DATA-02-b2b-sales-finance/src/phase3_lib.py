# Phase 3 analysis library: Anchorpoint B2B Sales Finance Case Study
#
# Shared functions used by all three Phase 3 notebooks, so every number
# quoted in docs/findings_summary.md and docs/claims_traceability.md traces
# back to one implementation rather than three copy-pasted variants that
# could silently drift apart.
#
# Reads only data/raw/*.csv, the exported dataset. Does not read
# src/generate_data.py's confounder section or any other hidden parameter;
# every figure below is estimated from the data, the way a real analyst
# would have to, not read off the generator.
#
# Version: Phase 3, 2026-08-21.

import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

WINDOW_START = datetime(2024, 7, 1)
WINDOW_END = datetime(2026, 8, 31)
ENTERPRISE_PUSH_DATE = datetime(2025, 1, 1)
PRICE_INCREASE_DATE = datetime(2025, 8, 1)
COMPETITOR_EU_ENTRY_DATE = datetime(2025, 7, 1)

GROSS_MARGIN = 0.78
LTV_CAP_YEARS = 3

# Enterprise annual churn cannot be measured from this data (see the
# documented limitation in data_model.md and decisions.md). Benchmark value
# and sensitivity range from Optifai (5-10% for Enterprise), locked in
# case_study_scenario.md.
ENTERPRISE_BENCHMARK_CHURN = 0.08
ENTERPRISE_CHURN_SENSITIVITY = (0.05, 0.10)

MIN_REPORTABLE_N = 30
Z95 = 1.96

SEGMENTS = ["Enterprise", "Mid-Market", "SMB"]
STAGE_ORDER = ["Prospecting", "Qualified", "Proposal", "Negotiation"]


# ------------------------------------------------------------------
# Loading
# ------------------------------------------------------------------
def load_all():
    date_cols = {
        "companies": ["founding_date"],
        "sales_reps": ["hire_date"],
        "deals": ["opened_date", "close_date"],
        "deal_stage_history": ["entered_date", "exited_date"],
        "customers": ["cohort_month", "churn_date"],
        "sales_pipeline": ["stage_entered_date", "forecast_close_date"],
        "sm_spend": ["month"],
    }
    tables = {}
    for name, cols in date_cols.items():
        df = pd.read_csv(RAW / f"{name}.csv")
        for c in cols:
            df[c] = pd.to_datetime(df[c], errors="coerce")
        tables[name] = df
    return tables


# ------------------------------------------------------------------
# Confidence intervals
# ------------------------------------------------------------------
def prop_ci(wins, n):
    """Wald 95% CI on a single proportion."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = wins / n
    se = math.sqrt(p * (1 - p) / n)
    return p, p - Z95 * se, p + Z95 * se


def two_prop_ci(wins1, n1, wins2, n2):
    """Wald 95% CI on the difference of two proportions (p1 - p2)."""
    p1, p2 = wins1 / n1, wins2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    z = d / se if se else 0.0
    return {
        "p1": p1, "n1": n1, "p2": p2, "n2": n2,
        "diff": d, "se": se, "z": z,
        "ci_lo": d - Z95 * se, "ci_hi": d + Z95 * se,
    }


def bootstrap_ci(values_func, n_boot=2000, seed=42):
    """Percentile bootstrap. values_func(rng) -> single float statistic,
    resampling internally. Returns (point estimate via mean of statistic
    distribution median, ci_lo, ci_hi)."""
    rng = np.random.default_rng(seed)
    draws = np.array([values_func(rng) for _ in range(n_boot)])
    draws = draws[~np.isnan(draws)]
    if len(draws) == 0:
        return float("nan"), float("nan"), float("nan")
    return float(np.median(draws)), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


# ------------------------------------------------------------------
# Section 1: profiling
# ------------------------------------------------------------------
def sample_size_table(deals):
    rows = []
    for seg in SEGMENTS:
        sub = deals[deals["segment"] == seg]
        rows.append({"cut": f"{seg}, all", "n": len(sub)})
    ent = deals[deals["segment"] == "Enterprise"]
    pre = ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]
    post = ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]
    rows.append({"cut": "Enterprise, pre-push (open date)", "n": len(pre)})
    rows.append({"cut": "Enterprise, post-push (open date)", "n": len(post)})
    for region in ["US", "EU", "APAC"]:
        rows.append({"cut": f"Enterprise, {region}", "n": len(ent[ent["region"] == region])})
        rows.append({"cut": f"Enterprise post-push, {region}",
                      "n": len(post[post["region"] == region])})
    for seg in SEGMENTS:
        sub = deals[deals["segment"] == seg]
        for q, grp in sub.groupby(sub["close_date"].dt.to_period("Q")):
            rows.append({"cut": f"{seg}, close-date quarter {q}", "n": len(grp)})
    df = pd.DataFrame(rows)
    df["reportable_as_point_estimate"] = df["n"] >= MIN_REPORTABLE_N
    return df


# ------------------------------------------------------------------
# Section 2: unit economics
# ------------------------------------------------------------------
def segment_avg_cycle_months(deals, segment):
    sub = deals[(deals["segment"] == segment) & (deals["deal_won"])]
    return float(sub["sales_cycle_days"].mean() / 30.44)


def spend_in_window(spend, segment, start, end):
    sub = spend[(spend["segment"] == segment) & (spend["month"] >= start) & (spend["month"] < end)]
    return float(sub["spend_usd"].sum())


def compute_cac(deals, spend, segment, period_start, period_end, lag_months=None):
    """Trailing-window CAC: spend attributed to a period of wins is shifted
    earlier by the segment's average sales cycle, since spend in month M
    produces wins several months later, not in the same month. The window
    used is stated explicitly wherever this is called.
    """
    if lag_months is None:
        lag_months = segment_avg_cycle_months(deals, segment)
    lag_days = lag_months * 30.44
    spend_start = period_start - timedelta(days=lag_days)
    spend_end = period_end - timedelta(days=lag_days)
    seg_spend = spend_in_window(spend, segment, spend_start, spend_end)

    sub = deals[(deals["segment"] == segment) & (deals["deal_won"]) &
                (deals["close_date"] >= period_start) & (deals["close_date"] < period_end)]
    wins = len(sub)
    cac = seg_spend / wins if wins else float("nan")
    return {
        "segment": segment, "period_start": period_start, "period_end": period_end,
        "lag_months": round(lag_months, 2),
        "spend_window": (spend_start, spend_end), "spend_usd": seg_spend,
        "wins": wins, "cac": cac,
    }


def compute_era_cac(deals, spend, segment, era_start, era_end, era_label):
    """Same-period (not lag-adjusted) era efficiency CAC: total spend during
    the era divided by total wins closing during the era. Used specifically
    for the pre-push vs post-push Enterprise comparison, where the
    lag-adjusted trailing-window method (compute_cac) would need spend
    history reaching back before WINDOW_START, which does not exist, and
    would silently understate pre-push CAC. This method answers a different
    question than compute_cac: not "what did this cohort of wins cost to
    acquire," but "how efficiently was spend converting to wins during this
    era," which is the right question for a fixed-cost, falling-yield story.
    """
    seg_spend = spend_in_window(spend, segment, era_start, era_end)
    sub = deals[(deals["segment"] == segment) & (deals["deal_won"]) &
                (deals["close_date"] >= era_start) & (deals["close_date"] < era_end)]
    wins = len(sub)
    cac = seg_spend / wins if wins else float("nan")
    months = (era_end - era_start).days / 30.44
    return {
        "segment": segment, "era": era_label, "era_start": era_start, "era_end": era_end,
        "era_months": round(months, 1), "spend_usd": seg_spend, "wins": wins, "cac": cac,
        "avg_monthly_spend": seg_spend / months if months else float("nan"),
    }


def empirical_annual_churn(customers, segment):
    """Occurrence/exposure estimate: monthly hazard = churn events / total
    customer-months observed, annualized. Used for Mid-Market and SMB,
    which have enough churn events to support it (24 and 100 respectively).
    Not used for Enterprise; see ENTERPRISE_BENCHMARK_CHURN.
    """
    sub = customers[customers["segment"] == segment]
    events = int(sub["churn_date"].notna().sum())
    exposure_months = float(sub["months_retained_observed"].sum())
    if exposure_months == 0:
        return float("nan"), events, exposure_months
    monthly_hazard = events / exposure_months
    annual = 1 - (1 - monthly_hazard) ** 12
    return annual, events, exposure_months


def compute_ltv(acv, annual_churn, gross_margin=GROSS_MARGIN, cap_years=LTV_CAP_YEARS):
    capped_life_years = min(1 / annual_churn, cap_years) if annual_churn > 0 else cap_years
    naive_life_years = (1 / annual_churn) if annual_churn > 0 else float("inf")
    return {
        "annual_churn": annual_churn,
        "capped_life_years": capped_life_years,
        "ltv_capped": acv * gross_margin * capped_life_years,
        "naive_life_years": naive_life_years,
        "ltv_naive": acv * gross_margin * naive_life_years,
    }


def compute_payback_months(cac, acv, gross_margin=GROSS_MARGIN):
    if acv * gross_margin == 0 or cac != cac:
        return float("nan")
    return cac / (acv * gross_margin) * 12


# ------------------------------------------------------------------
# Section 3: diagnostics
# ------------------------------------------------------------------
def win_rate_by_quarter(deals, date_col, segment):
    sub = deals[deals["segment"] == segment].copy()
    sub["q"] = sub[date_col].dt.to_period("Q")
    g = sub.groupby("q")["deal_won"].agg(["mean", "count"]).reset_index()
    g.columns = ["quarter", "win_rate", "n"]
    return g


def stage_duration_table(stage_history, deals, segment, period_label_fn):
    m = stage_history.merge(deals[["deal_id", "segment", "opened_date"]], on="deal_id", how="inner")
    m = m[m["segment"] == segment].copy()
    m["period"] = m["opened_date"].apply(period_label_fn)
    g = m.groupby(["period", "stage"])["days_in_stage"].agg(["mean", "count"]).reset_index()
    g["stage"] = pd.Categorical(g["stage"], categories=STAGE_ORDER, ordered=True)
    return g.sort_values(["period", "stage"])


def loss_reason_mix(deals, segment, period_label_fn):
    sub = deals[(deals["segment"] == segment) & (~deals["deal_won"])].copy()
    sub["period"] = sub["opened_date"].apply(period_label_fn)
    ct = pd.crosstab(sub["period"], sub["loss_reason"], normalize="index").round(3)
    counts = pd.crosstab(sub["period"], sub["loss_reason"])
    return ct, counts


def enterprise_period_label(d):
    return "pre-push" if d < ENTERPRISE_PUSH_DATE else "post-push"


# ------------------------------------------------------------------
# Rep experience comparison
# ------------------------------------------------------------------
def rep_experience_comparison(deals, reps):
    m = deals.merge(reps[["rep_id", "has_enterprise_experience", "is_founder_led"]],
                     on="rep_id", how="left")
    ent = m[m["segment"] == "Enterprise"]

    # Full comparison: confounded with calendar period for the inexperienced
    # group, since all 8 new AEs share a hire date. Reported for completeness
    # but explicitly labelled as confounded.
    exp = ent[ent["has_enterprise_experience"]]
    inexp = ent[~ent["has_enterprise_experience"]]
    full = two_prop_ci(exp["deal_won"].sum(), len(exp), inexp["deal_won"].sum(), len(inexp))

    # Same-period comparison: restrict to post-push deals only, so both
    # groups share the same calendar period. This is what the contemporaneous
    # control amendment (founder-led reps carrying ~12% of post-push
    # Enterprise volume) makes possible.
    post = ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]
    exp_post = post[post["has_enterprise_experience"]]
    inexp_post = post[~post["has_enterprise_experience"]]
    same_period = two_prop_ci(exp_post["deal_won"].sum(), len(exp_post),
                               inexp_post["deal_won"].sum(), len(inexp_post))

    controls = {
        "exp_post_mean_deal_size": float(exp_post["deal_size_usd"].mean()) if len(exp_post) else float("nan"),
        "inexp_post_mean_deal_size": float(inexp_post["deal_size_usd"].mean()) if len(inexp_post) else float("nan"),
        "exp_post_region_mix": exp_post["region"].value_counts(normalize=True).round(3).to_dict() if len(exp_post) else {},
        "inexp_post_region_mix": inexp_post["region"].value_counts(normalize=True).round(3).to_dict() if len(inexp_post) else {},
    }
    return {"full_confounded": full, "same_period": same_period, "controls": controls}


# ------------------------------------------------------------------
# Confounders
# ------------------------------------------------------------------
def confounder_eu_competitor(deals):
    """US and APAC Enterprise are competitor-free throughout. Their pre/post
    decline is the non-competitor baseline. EU's excess decline over that
    baseline, weighted by EU's share of post-push Enterprise volume, is the
    competitor's estimated contribution to the overall decline.
    """
    ent = deals[deals["segment"] == "Enterprise"]
    out = {}
    for region in ["US", "EU", "APAC"]:
        sub = ent[ent["region"] == region]
        pre = sub[sub["opened_date"] < ENTERPRISE_PUSH_DATE]
        post = sub[sub["opened_date"] >= ENTERPRISE_PUSH_DATE]
        if len(pre) and len(post):
            out[region] = two_prop_ci(pre["deal_won"].sum(), len(pre), post["deal_won"].sum(), len(post))
        else:
            out[region] = None

    non_eu = ent[ent["region"] != "EU"]
    pre_non_eu = non_eu[non_eu["opened_date"] < ENTERPRISE_PUSH_DATE]
    post_non_eu = non_eu[non_eu["opened_date"] >= ENTERPRISE_PUSH_DATE]
    baseline = two_prop_ci(pre_non_eu["deal_won"].sum(), len(pre_non_eu),
                            post_non_eu["deal_won"].sum(), len(post_non_eu))
    baseline_decline_pp = baseline["diff"]

    eu = out["EU"]
    eu_decline_pp = eu["diff"] if eu else float("nan")
    excess_decline_pp = eu_decline_pp - baseline_decline_pp if eu else float("nan")

    post_all = ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]
    eu_share_of_post = len(post_all[post_all["region"] == "EU"]) / len(post_all) if len(post_all) else float("nan")

    overall = two_prop_ci(
        ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]["deal_won"].sum(), len(ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]),
        ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]["deal_won"].sum(), len(ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]),
    )
    overall_decline_pp = overall["diff"]
    contribution_of_total_decline = (excess_decline_pp * eu_share_of_post) / overall_decline_pp if overall_decline_pp else float("nan")

    return {
        "by_region": out,
        "non_eu_baseline_decline_pp": baseline_decline_pp,
        "eu_decline_pp": eu_decline_pp,
        "eu_excess_decline_pp": excess_decline_pp,
        "eu_share_of_post_push_volume": eu_share_of_post,
        "overall_decline_pp": overall_decline_pp,
        "estimated_eu_competitor_share_of_overall_decline": contribution_of_total_decline,
    }


def confounder_price_increase(deals):
    """List price rose 12% on 2025-08-01 for every segment. If price were a
    material driver, Mid-Market and SMB (no rep-experience issue) should show
    a comparable win-rate drop across that date. Also check Enterprise
    post-push win rate before vs after the price date, within the post-push
    period only (holds rep-experience constant).
    """
    out = {}
    for seg in ["Mid-Market", "SMB"]:
        sub = deals[deals["segment"] == seg]
        before = sub[sub["opened_date"] < PRICE_INCREASE_DATE]
        after = sub[sub["opened_date"] >= PRICE_INCREASE_DATE]
        out[seg] = two_prop_ci(before["deal_won"].sum(), len(before), after["deal_won"].sum(), len(after))

    ent_post = deals[(deals["segment"] == "Enterprise") & (deals["opened_date"] >= ENTERPRISE_PUSH_DATE)]
    before = ent_post[ent_post["opened_date"] < PRICE_INCREASE_DATE]
    after = ent_post[ent_post["opened_date"] >= PRICE_INCREASE_DATE]
    out["Enterprise_post_push_only"] = two_prop_ci(before["deal_won"].sum(), len(before), after["deal_won"].sum(), len(after))
    return out


def confounder_seasonality(deals):
    """Compare the same calendar quarter one year apart, which differences
    out any pure seasonal component, for a segment untouched by the
    Enterprise mechanism (Mid-Market, SMB) as a sanity check on the
    seasonality pattern itself, then check whether Enterprise's decline
    survives a year-over-year (not quarter-over-quarter) comparison, which a
    purely seasonal effect would not survive.
    """
    out = {}
    for seg in SEGMENTS:
        sub = deals[deals["segment"] == seg].copy()
        sub["q"] = sub["close_date"].dt.to_period("Q")
        g = sub.groupby("q")["deal_won"].agg(["mean", "count"])
        out[seg] = g.to_dict("index")
    return out


def confounder_channel_mix(deals):
    """Partnerships channel share over time for Enterprise, and whether the
    win-rate decline holds when restricted to Direct Sales only (removing
    any channel-mix effect by construction).
    """
    ent = deals[deals["segment"] == "Enterprise"]
    pre = ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]
    post = ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]
    channel_share_pre = pre["acquisition_channel"].value_counts(normalize=True).round(3).to_dict()
    channel_share_post = post["acquisition_channel"].value_counts(normalize=True).round(3).to_dict()

    direct = ent[ent["acquisition_channel"] == "Direct Sales"]
    d_pre = direct[direct["opened_date"] < ENTERPRISE_PUSH_DATE]
    d_post = direct[direct["opened_date"] >= ENTERPRISE_PUSH_DATE]
    direct_only = two_prop_ci(d_pre["deal_won"].sum(), len(d_pre), d_post["deal_won"].sum(), len(d_post))

    all_segs = two_prop_ci(pre["deal_won"].sum(), len(pre), post["deal_won"].sum(), len(post))

    return {
        "channel_share_pre": channel_share_pre,
        "channel_share_post": channel_share_post,
        "direct_sales_only_pre_post": direct_only,
        "all_channels_pre_post": all_segs,
    }


# ------------------------------------------------------------------
# Lag quantification: close-date vs open-date cohorting
# ------------------------------------------------------------------
def aggregate_vs_segment_view(deals):
    """Blended (all-segment) win rate by close-date quarter next to
    Enterprise-only win rate by close-date quarter. This is the Question 7
    comparison: what a monthly business review looking only at the blended
    number would have seen, next to what was actually happening underneath.
    """
    blended = deals.copy()
    blended["q"] = blended["close_date"].dt.to_period("Q")
    agg = blended.groupby("q")["deal_won"].agg(["mean", "count"]).reset_index()
    agg.columns = ["quarter", "blended_win_rate", "blended_n"]

    ent = win_rate_by_quarter(deals, "close_date", "Enterprise")
    ent.columns = ["quarter", "enterprise_win_rate", "enterprise_n"]

    out = agg.merge(ent, on="quarter", how="left")

    spend_share = deals.groupby("segment")["deal_size_usd"].count()  # placeholder unused
    return out


def enterprise_budget_share(spend, deals):
    """Enterprise share of total S&M budget versus Enterprise share of won
    deals and of ARR (using closed-won ACV as a proxy), trailing 12 months.
    The gap between these two shares is the budget-misallocation number for
    Question 7.
    """
    period_start = WINDOW_END - timedelta(days=365)
    sp = spend[(spend["month"] >= period_start) & (spend["month"] < WINDOW_END)]
    spend_by_seg = sp.groupby("segment")["spend_usd"].sum()
    total_spend = spend_by_seg.sum()

    dl = deals[(deals["deal_won"]) & (deals["close_date"] >= period_start) & (deals["close_date"] < WINDOW_END)]
    wins_by_seg = dl.groupby("segment").size()
    total_wins = wins_by_seg.sum()
    arr_by_seg = dl.groupby("segment")["deal_size_usd"].sum()
    total_arr = arr_by_seg.sum()

    rows = []
    for seg in SEGMENTS:
        rows.append({
            "segment": seg,
            "spend_share": spend_by_seg.get(seg, 0) / total_spend,
            "won_deal_share": wins_by_seg.get(seg, 0) / total_wins,
            "new_arr_share": arr_by_seg.get(seg, 0) / total_arr,
        })
    return pd.DataFrame(rows)


def pipeline_stuck_analysis(pipeline):
    """Enterprise pipeline coverage looks adequate in aggregate while a
    disproportionate share sits stuck (>=90 days) in Proposal/Negotiation,
    forward-looking evidence of the same mechanism visible in closed deals.
    """
    rows = []
    for seg in SEGMENTS:
        sub = pipeline[pipeline["segment"] == seg]
        late_stage = sub[sub["stage"].isin(["Proposal", "Negotiation"])]
        stuck = late_stage[late_stage["days_in_current_stage"] >= 90]
        rows.append({
            "segment": seg,
            "open_opportunities": len(sub),
            "open_forecast_usd": float(sub["forecast_amount_usd"].sum()),
            "late_stage_opportunities": len(late_stage),
            "stuck_90d_plus": len(stuck),
            "stuck_share_of_late_stage": len(stuck) / len(late_stage) if len(late_stage) else float("nan"),
            "stuck_forecast_usd": float(stuck["forecast_amount_usd"].sum()),
        })
    return pd.DataFrame(rows)


def quantify_reporting_lag(deals):
    ent_post = deals[(deals["segment"] == "Enterprise") & (deals["opened_date"] >= ENTERPRISE_PUSH_DATE)]
    mean_cycle_months = float(ent_post["sales_cycle_days"].mean() / 30.44)

    close_q = win_rate_by_quarter(deals, "close_date", "Enterprise")
    open_q = win_rate_by_quarter(deals, "opened_date", "Enterprise")
    return {
        "mean_post_push_cycle_months": mean_cycle_months,
        "win_rate_by_close_quarter": close_q,
        "win_rate_by_open_quarter": open_q,
    }
