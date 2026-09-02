# B2B Sales Finance Synthetic Data Generator (Anchorpoint)
#
# MECHANISM-BASED. Read this before changing anything.
#
# The governing rule of this file: it encodes CAUSES, never OUTCOMES.
# There is no win rate parameter anywhere below. There is no trigger date.
# Win rates, CAC, payback, and retention are MEASURED from the generated
# data in Phase 3; they are not inputs here and must never be added as
# inputs. If you find yourself wanting to add a parameter named
# win_rate_anything, stop: that is the exact failure this redesign exists
# to correct (see docs/plan_review.md and the 2026-08-20 Phase 1.5 entry
# in docs/decisions.md).
#
# What IS parameterized: how many stakeholders an enterprise buying group
# contains, how fast a rep engages them, how long a buyer will wait, how
# long a new AE takes to ramp, and how large the confounding effects are.
# Every one of those is calibrated against a published benchmark, cited
# inline. The win rate is whatever falls out.
#
# Version: Phase 1.5 redesign, 2026-08-20. Supersedes the outcome-encoded
# skeleton from Phase 1.

import math

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ============================================================
# SEEDS. Both of them. The Phase 1 skeleton set only random.seed(),
# while the generation plan calls for numpy draws, so reproducibility
# would have silently failed. Do not use the stdlib random module in
# this file at all; use the module level rng below for everything.
# ============================================================
SEED = 42
rng = np.random.default_rng(SEED)

# ============================================================
# SECTION 1: SCENARIO CONSTANTS
# Fixed inputs describing the company. Allowed to be stated up front
# because they are context, not findings. Anything in this section may
# appear in docs/case_study_scenario.md. Nothing in Section 2 or 3 may.
# ============================================================
WINDOW_START = datetime(2024, 7, 1)
WINDOW_END = datetime(2026, 8, 31)           # 26-month observation window
ENTERPRISE_PUSH_DATE = datetime(2025, 1, 1)  # the 8 Enterprise AEs start

# NOTE: ENTERPRISE_PUSH_DATE is a STAFFING EVENT, not a performance
# trigger. Nothing about win rate changes on this date. What changes is
# who owns newly opened Enterprise deals. The performance effect appears
# later, and how much later is determined by the sales cycle, not by this
# constant. That lag is itself a finding, so do not shortcut it.

NUM_COMPANIES = 900

# Locked. B2B SaaS median 75-80% (Orb 2025, SaaS Capital 2026).
# Previously undocumented; it silently determined every payback figure
# in the Phase 1 scenario.
GROSS_MARGIN = 0.78

# Primary LTV method caps customer life at 3 years. Naive 1/churn is
# also computed in Phase 3 purely as a labelled contrast, never as the
# headline. See docs/decisions.md decision 7.
LTV_CAP_YEARS = 3
DISCOUNT_RATE_ANNUAL = 0.12  # optional NPV variant in Phase 3

# ============================================================
# SECTION 2: SEGMENT STRUCTURE
# closed_attempts is a VOLUME parameter (how many opportunities the
# company worked), not an outcome parameter. Volume is a business fact;
# win rate is a result. Enterprise volume was raised from 150 to 420
# because at 150 the central finding failed significance (p = 0.062).
# See docs/plan_review.md section 2.1.
#
# The Startup segment was CUT in Phase 1.5, superseding the Phase 1
# four-segment decision. At any realistic volume it produced too few
# wins to support analysis and was already excluded from payback work.
# ============================================================
SEGMENTS = {
    "Enterprise": {
        "closed_attempts": 420,
        "deal_size_range": (50_000, 300_000),
        "deal_size_avg": 95_000,
        "annual_churn": 0.08,          # Optifai: Enterprise 5-10%
        # Buying group size. Gartner's widely cited finding is 6 to 10
        # stakeholders in a complex B2B purchase. Lognormal, median ~6.
        "stakeholders_mu": 1.80,
        "stakeholders_sigma": 0.35,
        # Buyer patience in months before the opportunity dies of its
        # own accord. Enterprise cycles run 6-9 months; median here ~7.4.
        "timeout_mu": 2.00,
        "timeout_sigma": 0.30,
        # Fraction surviving qualification (budget, authority, fit).
        # NOT a win rate: deals passing here still face the touch
        # mechanism and the competitive test.
        "qualification_rate": 0.50,
        # Given the buying group was fully engaged in time, probability
        # of beating the competitor. NOT a win rate on its own.
        "competitive_rate": 0.55,
        # Stakeholder touches per month a rep generates.
        "touches_per_month_experienced": 2.0,
        "touches_per_month_inexperienced": 1.0,
    },
    "Mid-Market": {
        "closed_attempts": 760,
        "deal_size_range": (20_000, 50_000),
        "deal_size_avg": 32_000,
        "annual_churn": 0.11,          # Optifai: Mid-Market 8-14%
        "stakeholders_mu": 1.05,
        "stakeholders_sigma": 0.35,
        "timeout_mu": 1.55,
        "timeout_sigma": 0.30,
        "qualification_rate": 0.55,
        "competitive_rate": 0.55,
        "touches_per_month_experienced": 2.4,
        "touches_per_month_inexperienced": 2.4,   # tenured team, no gap
    },
    "SMB": {
        "closed_attempts": 1020,
        "deal_size_range": (5_000, 20_000),
        "deal_size_avg": 11_000,
        "annual_churn": 0.27,          # Optifai: SMB 22-32%
        "stakeholders_mu": 0.45,
        "stakeholders_sigma": 0.30,
        "timeout_mu": 1.15,
        "timeout_sigma": 0.28,
        "qualification_rate": 0.60,
        "competitive_rate": 0.58,
        "touches_per_month_experienced": 3.0,
        "touches_per_month_inexperienced": 3.0,
    },
}

NUM_CLOSED_DEALS = sum(s["closed_attempts"] for s in SEGMENTS.values())  # 2200
NUM_PIPELINE_DEALS = 400
NUM_OPPORTUNITIES_TOTAL = NUM_CLOSED_DEALS + NUM_PIPELINE_DEALS         # 2600

# Enterprise volume ramps at the push. Roughly a quarter of Enterprise
# attempts predate ENTERPRISE_PUSH_DATE (occasional founder-led
# enterprise deals), three quarters follow it. This is a VOLUME ramp,
# not a performance change.
ENTERPRISE_PRE_PUSH_SHARE = 0.25

# ============================================================
# SECTION 3: THE CAUSAL MECHANISM
# The heart of the redesign. A deal is won when the rep engages the full
# buying group before the buyer loses patience, and then beats the
# competitor. Rep capability drives touch rate. Nothing else does.
# ============================================================

# New AE ramp. Enterprise AE ramp to full productivity is commonly cited
# at 9-12 months (Bridge Group). A rep who has never run a multi-threaded
# enterprise motion and receives no formal enablement plateaus BELOW an
# experienced rep, so the ceiling is 0.85, not 1.0. That ceiling is why
# the problem persists rather than self-correcting, and it is what makes
# "hire more AEs" the wrong recommendation and "enable the ones you have"
# the right one.
RAMP_FLOOR = 0.42
RAMP_SLOPE_PER_MONTH = 0.036
RAMP_CEILING = 0.85


def ramp_multiplier(tenure_months):
    """Effectiveness of an inexperienced AE as a function of tenure."""
    return min(RAMP_CEILING, RAMP_FLOOR + RAMP_SLOPE_PER_MONTH * max(0.0, tenure_months))


# Per-deal and per-rep execution noise. Without this the mechanism is
# deterministic given inputs, every deal of the same shape resolves the
# same way, and the analysis becomes trivially clean.
EXECUTION_NOISE_SIGMA = 0.25

# ============================================================
# SECTION 4: CONFOUNDERS
# Phase 3 has to rule these out. One is partially real; three are not.
# Their true contributions are recorded here ONLY so the generator can
# apply them. Phase 3 must not read this file. The whole exercise is that
# the analyst MEASURES these effects rather than looking them up.
# ============================================================

# CONFOUNDER A: PARTIALLY REAL. A well-funded competitor enters EU in
# Q3 2025 and genuinely takes EU Enterprise deals. It explains part of
# the Enterprise decline but nowhere near all of it, and does not touch
# US or APAC. An analyst who stops at "a competitor showed up" gets the
# diagnosis wrong and recommends the wrong fix.
COMPETITOR_EU_ENTRY_DATE = datetime(2025, 7, 1)
COMPETITOR_EU_ENTERPRISE_PENALTY = 0.35   # multiplier on competitive_rate,
                                          # EU Enterprise only, post-entry

# CONFOUNDER B: RED HERRING. A list price increase lands Aug 2025, close
# in time to when the Enterprise decline becomes visible. Applies to
# every segment equally with only a small uniform effect. Ruled out by
# noticing Mid-Market and SMB absorbed the same increase without damage.
PRICE_INCREASE_DATE = datetime(2025, 8, 1)
PRICE_INCREASE_PCT = 0.12
PRICE_INCREASE_COMPETITIVE_PENALTY = 0.96  # tiny, all segments

# CONFOUNDER C: RED HERRING. Seasonality. Q4 pull-forward and a Q1
# trough in both volume and close behaviour. Makes any naive
# month-over-month read of early 2026 look like decline. Ruled out by
# year-over-year comparison or by de-seasonalising.
SEASONALITY_BY_MONTH = {
    1: 0.80, 2: 0.88, 3: 1.05, 4: 0.95, 5: 1.00, 6: 1.10,
    7: 0.92, 8: 0.88, 9: 1.05, 10: 1.05, 11: 1.12, 12: 1.30,
}

# CONFOUNDER D: RED HERRING. Partnerships channel volume grows steadily
# across the window and brings slightly lower-fit leads. Looks like a
# plausible cause of declining quality. Cannot explain Enterprise,
# because Partnerships carries almost no Enterprise volume. Ruled out by
# cutting the channel effect within the Enterprise segment only.
PARTNERSHIPS_GROWTH_START_SHARE = 0.10
PARTNERSHIPS_GROWTH_END_SHARE = 0.28
PARTNERSHIPS_QUALIFICATION_PENALTY = 0.90

CHANNEL_MIX_BY_SEGMENT = {
    # Direct Sales carries essentially all Enterprise, per the scenario.
    "Enterprise": {"Direct Sales": 0.88, "Inbound": 0.08, "Partnerships": 0.04},
    "Mid-Market": {"Direct Sales": 0.45, "Inbound": 0.35, "Partnerships": 0.20},
    "SMB": {"Direct Sales": 0.15, "Inbound": 0.60, "Partnerships": 0.25},
}

REGIONS = ["US", "EU", "APAC"]
REGION_WEIGHTS = [0.62, 0.26, 0.12]   # Austin-based, US-heavy

# ============================================================
# SECTION 5: SALES TEAM
# The rep roster is now real exported data, not a comment. Rep
# attributes are the independent variable of the entire analysis and
# Phase 3 needs to join on them.
# ============================================================
# 8 Enterprise AEs start 2025-01-01. Six promoted internally from SMB or
# Mid-Market, two hired externally from non-enterprise roles. None has
# run a multi-stakeholder enterprise motion. Before the push, occasional
# Enterprise deals were founder-led and are attributed to two tenured
# reps flagged as experienced.
ENTERPRISE_AE_COUNT = 8
ENTERPRISE_FOUNDER_LED_REP_COUNT = 2
MID_MARKET_AE_COUNT = 10
SMB_REP_COUNT = 10

ENTERPRISE_AE_QUOTA_USD = 800_000   # Bridge Group median enterprise AE quota
COMMISSION_RATE = 0.08

# ============================================================
# SECTION 6: SALES AND MARKETING SPEND
# Emitted as a monthly table rather than an annual scalar. The Phase 1
# design divided an annual number across a multi-month window, which
# made period-correct CAC impossible. Monthly spend lets Phase 3 compute
# trailing CAC properly and attribute spend to the period that produced
# the win.
# ============================================================
MONTHLY_SM_SPEND_BY_SEGMENT = {
    "Enterprise": 3_200_000 / 12,   # 8 fully loaded AEs plus SE and deal desk
    "Mid-Market": 1_800_000 / 12,
    "SMB": 1_200_000 / 12,
}

# Enterprise spend does not scale down when its win rate falls. That
# rigidity is the financial core of the case study: fixed cost, falling
# yield. Before ENTERPRISE_PUSH_DATE, Enterprise spend is a small
# fraction of the above (founder-led, no dedicated team).
ENTERPRISE_PRE_PUSH_SPEND_FRACTION = 0.18

STAGES = ["Prospecting", "Qualified", "Proposal", "Negotiation"]

# ============================================================
# SECTION 7: IMPLEMENTATION HELPERS
# Everything below is mechanics for turning Sections 1-6 into rows. None of
# it is a scenario constant and none of it belongs in case_study_scenario.md.
# ============================================================

# Amendment confirmed by Neyda, 2026-08-21 (see docs/decisions.md). Without
# this, has_enterprise_experience is perfectly confounded with calendar
# period, since all 8 new AEs share a hire date, and Question 5 could not
# separate a rep effect from a time effect. The two founder-led reps keep
# carrying a slice of post-push Enterprise volume so that comparison has a
# contemporaneous control. This is a VOLUME/assignment parameter, not an
# outcome parameter: it does not touch win rate, it only decides who works
# the deal.
FOUNDER_LED_POST_PUSH_SHARE = 0.12

# companies() needs a name generator and an industry list. Cosmetic, no
# mechanism dependency.
INDUSTRIES = ["Software", "Financial Services", "Healthcare", "Manufacturing",
              "Retail", "Logistics", "Professional Services", "Media",
              "Telecommunications", "Energy"]
COMPANY_NAME_PREFIXES = ["Bright", "North", "Summit", "Vertex", "Clear", "Blue",
                          "Meridian", "Cascade", "Anchor", "Granite", "Silver",
                          "Cobalt", "Harbor", "Ridge", "Elevate", "Pioneer",
                          "Lumen", "Atlas", "Forge", "Crest"]
COMPANY_NAME_CORES = ["Path", "Works", "Field", "Point", "Line", "Gate", "Wave",
                       "Bridge", "Core", "Stream", "Hub", "Loop", "Peak", "Well",
                       "Grove", "Yard"]
COMPANY_NAME_SUFFIXES = ["Inc", "LLC", "Group", "Co", "Partners", "Systems",
                          "Solutions", "Holdings", ""]

# employee_count bands used to both draw company size and, deterministically,
# to recover which segment a company belongs to later (no extra column
# needed; the classification is a pure function of employee_count so it
# cannot drift out of sync with how the company was generated).
EMPLOYEE_COUNT_BANDS = {
    "Enterprise": (1000, 20000, 3000),
    "Mid-Market": (100, 999, 300),
    "SMB": (10, 99, 35),
}


def _segment_from_employee_count(employee_count):
    if employee_count >= 1000:
        return "Enterprise"
    if employee_count >= 100:
        return "Mid-Market"
    return "SMB"


def _companies_by_segment(companies):
    segs = companies["employee_count"].apply(_segment_from_employee_count)
    return {seg: companies.loc[segs == seg, "company_id"].to_numpy()
            for seg in ["Enterprise", "Mid-Market", "SMB"]}


# Company-count weights mirror the segment mix of closed attempts, so the
# pool of eligible companies per segment is proportionate to demand.
_company_seg_weight_total = sum(s["closed_attempts"] for s in SEGMENTS.values())
SEGMENT_PROBS_FOR_COMPANIES = {
    seg: SEGMENTS[seg]["closed_attempts"] / _company_seg_weight_total
    for seg in SEGMENTS
}

# Rep quotas for Mid-Market and SMB are not locked anywhere upstream (only
# the Enterprise AE quota is, at $800k, Bridge Group). Invented at a scale
# consistent with smaller average deal sizes in those segments. Logged in
# docs/decisions.md rather than left as a silent assumption.
MM_QUOTA_USD = 400_000
SMB_QUOTA_USD = 200_000

# Stage-duration allocation. A stalled deal spends most of its excess time
# in Proposal and Negotiation, because that is where the stakeholder-touch
# mechanism actually plays out. Deals allocate across all four stages
# except 'unqualified' losses, which never clear Prospecting.
STAGE_DAY_PROPORTIONS_NORMAL = {
    "Prospecting": 0.12, "Qualified": 0.18, "Proposal": 0.35, "Negotiation": 0.35,
}
STAGE_DAY_PROPORTIONS_STALLED = {
    "Prospecting": 0.08, "Qualified": 0.12, "Proposal": 0.30, "Negotiation": 0.50,
}

# Deal size: lognormal clipped to the segment range. Clipping shifts the
# mean (see AGENT-BUILD-GUIDE.md 7.7), so the mu is calibrated empirically
# against the realized post-clip mean rather than set analytically, and
# cached per segment since it only needs to be solved once.
DEAL_SIZE_SIGMA = 0.45
_DEAL_SIZE_MU_CACHE = {}


def _calibrate_deal_size_mu(target_mean, lo, hi, sigma, sample_size=4000, iterations=25):
    mu = math.log(target_mean)
    for _ in range(iterations):
        sample = rng.lognormal(mu, sigma, size=sample_size)
        clipped = np.clip(sample, lo, hi)
        current_mean = clipped.mean()
        if current_mean <= 0:
            break
        mu += math.log(target_mean / current_mean) * 0.7
    return mu


def _draw_deal_size(segment):
    lo, hi = SEGMENTS[segment]["deal_size_range"]
    target = SEGMENTS[segment]["deal_size_avg"]
    if segment not in _DEAL_SIZE_MU_CACHE:
        _DEAL_SIZE_MU_CACHE[segment] = _calibrate_deal_size_mu(target, lo, hi, DEAL_SIZE_SIGMA)
    mu = _DEAL_SIZE_MU_CACHE[segment]
    raw = rng.lognormal(mu, DEAL_SIZE_SIGMA)
    return float(np.clip(raw, lo, hi))


def _pick_channel(segment):
    mix = CHANNEL_MIX_BY_SEGMENT[segment]
    names = list(mix.keys())
    weights = list(mix.values())
    return names[rng.choice(len(names), p=weights)]


def _weighted_open_date(low, high):
    """Draw a date in [low, high) weighted by SEASONALITY_BY_MONTH.

    Wide, seasonality-weighted draws, combined with discarding purely on
    close_date window membership downstream, is what avoids the
    censoring bias described in AGENT-BUILD-GUIDE.md 7.1: long-cycle
    deals are never selected against, they are simply less likely to
    land in-window from a late open date, which is realistic, not a bias
    introduced by the generator.
    """
    if high <= low:
        return low
    months = []
    cur = datetime(low.year, low.month, 1)
    while cur < high:
        months.append(cur)
        cur = datetime(cur.year + 1, 1, 1) if cur.month == 12 else datetime(cur.year, cur.month + 1, 1)
    weights = np.array([SEASONALITY_BY_MONTH[m.month] for m in months], dtype=float)
    weights = weights / weights.sum()
    chosen_month = months[rng.choice(len(months), p=weights)]
    month_end = (datetime(chosen_month.year + 1, 1, 1) if chosen_month.month == 12
                 else datetime(chosen_month.year, chosen_month.month + 1, 1))
    day_low = max(low, chosen_month)
    day_high = min(high, month_end)
    span = (day_high - day_low).days
    if span <= 0:
        return day_low
    return day_low + timedelta(days=int(rng.integers(0, span)))


def _fill_segment_deals(segment, target_count, open_low, open_high,
                         companies_by_seg, region_by_company, rep_fn, deal_counter):
    """Draw and resolve deals for one segment/period until target_count land
    inside the observation window.

    Discards purely on close_date window membership, never on a deal
    characteristic correlated with the outcome (see AGENT-BUILD-GUIDE.md
    7.1 and 7.2). The draw volume is what gets increased to hit the exact
    row count, never the selection criterion.
    """
    accepted = []
    company_pool = companies_by_seg[segment]
    max_attempts = target_count * 50 + 1000
    attempts = 0
    while len(accepted) < target_count and attempts < max_attempts:
        attempts += 1
        opened_date = _weighted_open_date(open_low, open_high)
        company_id = company_pool[rng.integers(0, len(company_pool))]
        region = region_by_company[company_id]
        channel = _pick_channel(segment)
        deal_size = _draw_deal_size(segment)
        if opened_date >= PRICE_INCREASE_DATE:
            deal_size *= (1 + PRICE_INCREASE_PCT)
        rep = rep_fn(opened_date)

        won, loss_reason, cycle_months, req, engaged = resolve_deal(
            segment, rep, opened_date, region, channel, deal_size)
        cycle_days = max(1, int(round(cycle_months * 30.44)))
        close_date = opened_date + timedelta(days=cycle_days)

        if close_date < WINDOW_START or close_date > WINDOW_END:
            continue

        deal_counter[0] += 1
        accepted.append({
            "deal_id": f"D{deal_counter[0]:06d}",
            "company_id": company_id,
            "rep_id": rep["rep_id"],
            "segment": segment,
            "region": region,
            "acquisition_channel": channel,
            "deal_size_usd": round(deal_size, 2),
            "opened_date": opened_date,
            "close_date": close_date,
            "deal_won": bool(won),
            "loss_reason": loss_reason,
            "stakeholders_required": req,
            "stakeholders_engaged": engaged,
            "sales_cycle_days": cycle_days,
        })

    if len(accepted) < target_count:
        raise RuntimeError(
            f"Could not fill {segment} deal quota: got {len(accepted)}/{target_count} "
            f"after {attempts} attempts. Widen the open-date range or raise max_attempts."
        )
    return accepted[:target_count]


# Pipeline stage mix. Enterprise deals owned by the new AE team skew toward
# Proposal/Negotiation with long days-in-stage, mirroring the closed-deal
# stall mechanism but visible before it lands in revenue. win_probability
# follows standard CRM stage convention regardless of who owns the deal,
# which is the point: the dashboard looks the same for a healthy and a
# stuck opportunity, and only days_in_current_stage tells them apart.
PIPELINE_STAGE_WEIGHTS = {
    ("Enterprise", "new_ae"): {"Prospecting": 0.10, "Qualified": 0.15, "Proposal": 0.35, "Negotiation": 0.40},
    ("Enterprise", "founder"): {"Prospecting": 0.25, "Qualified": 0.30, "Proposal": 0.25, "Negotiation": 0.20},
    ("Mid-Market", None): {"Prospecting": 0.25, "Qualified": 0.25, "Proposal": 0.25, "Negotiation": 0.25},
    ("SMB", None): {"Prospecting": 0.25, "Qualified": 0.25, "Proposal": 0.25, "Negotiation": 0.25},
}
STAGE_WIN_PROBABILITY = {"Prospecting": 10, "Qualified": 25, "Proposal": 50, "Negotiation": 70}
PIPELINE_SEGMENT_PROBS = dict(SEGMENT_PROBS_FOR_COMPANIES)


# ============================================================
# GENERATION FUNCTIONS
# ============================================================

def generate_companies():
    """900 B2B companies.

    Columns: company_id, company_name, industry, region, employee_count,
    founding_date.

    region is load-bearing now, since Confounder A is region specific.
    Use REGION_WEIGHTS. employee_count should correlate with the segment
    a company's deals land in, because segment is derived from company
    size rather than drawn independently.
    """
    seg_names = list(SEGMENT_PROBS_FOR_COMPANIES.keys())
    seg_probs = [SEGMENT_PROBS_FOR_COMPANIES[s] for s in seg_names]
    segments_drawn = [seg_names[i] for i in rng.choice(len(seg_names), size=NUM_COMPANIES, p=seg_probs)]

    rows = []
    for i in range(NUM_COMPANIES):
        seg = segments_drawn[i]
        lo, hi, median = EMPLOYEE_COUNT_BANDS[seg]
        raw = rng.lognormal(math.log(median), 0.5)
        employee_count = int(max(lo, min(hi, raw)))

        region = REGIONS[rng.choice(len(REGIONS), p=REGION_WEIGHTS)]

        prefix = COMPANY_NAME_PREFIXES[rng.integers(0, len(COMPANY_NAME_PREFIXES))]
        core = COMPANY_NAME_CORES[rng.integers(0, len(COMPANY_NAME_CORES))]
        suffix = COMPANY_NAME_SUFFIXES[rng.integers(0, len(COMPANY_NAME_SUFFIXES))]
        name = f"{prefix}{core}" + (f" {suffix}" if suffix else "")
        industry = INDUSTRIES[rng.integers(0, len(INDUSTRIES))]

        if seg == "Enterprise":
            founding_year = int(rng.integers(1995, 2016))
        elif seg == "Mid-Market":
            founding_year = int(rng.integers(2005, 2021))
        else:
            founding_year = int(rng.integers(2014, 2025))
        founding_date = datetime(founding_year, int(rng.integers(1, 13)), int(rng.integers(1, 28)))

        rows.append({
            "company_id": f"CO{i + 1:05d}",
            "company_name": name,
            "industry": industry,
            "region": region,
            "employee_count": employee_count,
            "founding_date": founding_date,
        })

    return pd.DataFrame(rows)


def generate_sales_reps():
    """NEW TABLE, 30 rows.

    Columns: rep_id, rep_name, segment, hire_date, prior_segment,
    has_enterprise_experience, playbook_type, quota_annual_usd,
    is_founder_led.

    playbook_type is 'multi_threaded' when has_enterprise_experience is
    True, else 'single_threaded'. This single field is the independent
    variable the entire diagnosis rests on, so it must be present in the
    exported data and joinable from deals.
    """
    rows = []
    counter = 1

    for _ in range(ENTERPRISE_FOUNDER_LED_REP_COUNT):
        rows.append({
            "rep_id": f"REP{counter:03d}", "rep_name": f"Founder Rep {counter}",
            "segment": "Enterprise", "hire_date": datetime(2021, 3, 1),
            "prior_segment": None, "has_enterprise_experience": True,
            "playbook_type": "multi_threaded", "quota_annual_usd": ENTERPRISE_AE_QUOTA_USD,
            "is_founder_led": True,
        })
        counter += 1

    # Six promoted internally from SMB or Mid-Market, two hired externally
    # from non-enterprise roles. None has run a multi-stakeholder motion.
    prior_pool = ["SMB"] * 3 + ["Mid-Market"] * 3 + ["External"] * 2
    for i in range(ENTERPRISE_AE_COUNT):
        rows.append({
            "rep_id": f"REP{counter:03d}", "rep_name": f"Enterprise AE {counter}",
            "segment": "Enterprise", "hire_date": ENTERPRISE_PUSH_DATE,
            "prior_segment": prior_pool[i], "has_enterprise_experience": False,
            "playbook_type": "single_threaded", "quota_annual_usd": ENTERPRISE_AE_QUOTA_USD,
            "is_founder_led": False,
        })
        counter += 1

    for _ in range(MID_MARKET_AE_COUNT):
        hire_date = datetime(int(rng.integers(2018, 2023)), int(rng.integers(1, 13)), 1)
        rows.append({
            "rep_id": f"REP{counter:03d}", "rep_name": f"Mid-Market AE {counter}",
            "segment": "Mid-Market", "hire_date": hire_date,
            "prior_segment": None, "has_enterprise_experience": False,
            "playbook_type": "single_threaded", "quota_annual_usd": MM_QUOTA_USD,
            "is_founder_led": False,
        })
        counter += 1

    for _ in range(SMB_REP_COUNT):
        hire_date = datetime(int(rng.integers(2018, 2023)), int(rng.integers(1, 13)), 1)
        rows.append({
            "rep_id": f"REP{counter:03d}", "rep_name": f"SMB Rep {counter}",
            "segment": "SMB", "hire_date": hire_date,
            "prior_segment": None, "has_enterprise_experience": False,
            "playbook_type": "single_threaded", "quota_annual_usd": SMB_QUOTA_USD,
            "is_founder_led": False,
        })
        counter += 1

    return pd.DataFrame(rows)


def resolve_deal(segment, rep, opened_date, region, channel, deal_size):
    """THE MECHANISM.

    Returns (won, loss_reason, cycle_months, stakeholders_required,
    stakeholders_engaged).

    Order of operations, all of which must stay in this order:

    1. stakeholders_required = max(1, round(lognormal(stakeholders_mu,
       stakeholders_sigma))). Larger deals draw larger buying groups, so
       scale mu modestly with deal_size within the segment range.

    2. timeout_months = lognormal(timeout_mu, timeout_sigma). How long
       the buyer will wait before the opportunity dies.

    3. Qualification gate. qualification_rate, reduced by
       PARTNERSHIPS_QUALIFICATION_PENALTY if channel is Partnerships.
       Failing gives loss_reason 'unqualified' and a short cycle.

    4. Touch rate. touches_per_month_experienced if
       rep.has_enterprise_experience else
       touches_per_month_inexperienced times
       ramp_multiplier(tenure at opened_date). Multiply by
       lognormal(0, EXECUTION_NOISE_SIGMA).

    5. months_to_engage = stakeholders_required / touch_rate.
       If months_to_engage > timeout_months the deal stalls out:
       won False, loss_reason 'stalled_no_decision', cycle_months
       timeout_months. THIS IS THE PRIMARY FAILURE PATH for the new
       Enterprise team and it is what makes Proposal and Negotiation
       durations blow out in the stage history.

    6. Competitive test. competitive_rate, multiplied by
       COMPETITOR_EU_ENTERPRISE_PENALTY if segment is Enterprise and
       region is EU and opened_date >= COMPETITOR_EU_ENTRY_DATE, and by
       PRICE_INCREASE_COMPETITIVE_PENALTY if opened_date >=
       PRICE_INCREASE_DATE. Losing here gives 'lost_to_competitor'.

    7. Won deals get loss_reason None and cycle_months equal to
       months_to_engage plus a short closing tail.

    Do NOT add any branch that reads a target win rate. There is none.
    """
    params = SEGMENTS[segment]

    # 1. buying group size, scaled modestly by deal size within the segment range
    lo, hi = params["deal_size_range"]
    size_frac = 0.5 if hi <= lo else min(1.0, max(0.0, (deal_size - lo) / (hi - lo)))
    mu_adj = params["stakeholders_mu"] * (1 + 0.3 * (size_frac - 0.5))
    stakeholders_required = max(1, int(round(rng.lognormal(mu_adj, params["stakeholders_sigma"]))))

    # 2. buyer patience
    timeout_months = float(rng.lognormal(params["timeout_mu"], params["timeout_sigma"]))

    # 3. qualification gate
    qual_rate = params["qualification_rate"]
    if channel == "Partnerships":
        qual_rate *= PARTNERSHIPS_QUALIFICATION_PENALTY
    if rng.random() > qual_rate:
        cycle_months = float(rng.uniform(0.2, 1.0))
        return False, "unqualified", cycle_months, stakeholders_required, 0

    # 4. touch rate. Ramp applies only to a rep without enterprise experience.
    if rep["has_enterprise_experience"]:
        base_touch = params["touches_per_month_experienced"]
    else:
        tenure_months = (opened_date - rep["hire_date"]).days / 30.44
        base_touch = params["touches_per_month_inexperienced"] * ramp_multiplier(tenure_months)
    noise = float(rng.lognormal(0.0, EXECUTION_NOISE_SIGMA))
    touch_rate = max(0.05, base_touch * noise)

    # 5. the engagement race against buyer patience. Primary failure path.
    months_to_engage = stakeholders_required / touch_rate
    if months_to_engage > timeout_months:
        stakeholders_engaged = min(stakeholders_required, int(touch_rate * timeout_months))
        return False, "stalled_no_decision", timeout_months, stakeholders_required, stakeholders_engaged

    # 6. competitive test
    comp_rate = params["competitive_rate"]
    if segment == "Enterprise" and region == "EU" and opened_date >= COMPETITOR_EU_ENTRY_DATE:
        comp_rate *= COMPETITOR_EU_ENTERPRISE_PENALTY
    if opened_date >= PRICE_INCREASE_DATE:
        comp_rate *= PRICE_INCREASE_COMPETITIVE_PENALTY
    closing_tail = float(rng.uniform(0.2, 0.8))
    if rng.random() > comp_rate:
        return False, "lost_to_competitor", months_to_engage + closing_tail, stakeholders_required, stakeholders_required

    # 7. won
    return True, None, months_to_engage + closing_tail, stakeholders_required, stakeholders_required


def generate_deals(companies, reps):
    """2,200 closed opportunities.

    Columns: deal_id, company_id, rep_id, segment, region,
    acquisition_channel, deal_size_usd, opened_date, close_date,
    deal_won, loss_reason, stakeholders_required, stakeholders_engaged,
    sales_cycle_days.

    There is no days_in_stage column any more. Per-stage timing lives in
    deal_stage_history, because the Phase 1 schema's single scalar could
    not answer the locked question about WHERE deals stall.

    opened_date: draw across a range wide enough that close_date lands
    inside the observation window, weighted by SEASONALITY_BY_MONTH.
    Enterprise opens split by ENTERPRISE_PRE_PUSH_SHARE around
    ENTERPRISE_PUSH_DATE. Deals whose close_date falls outside
    [WINDOW_START, WINDOW_END] are discarded and redrawn, so the exported
    table is exactly the deals that closed in the window.

    Rep assignment: Enterprise deals opened before ENTERPRISE_PUSH_DATE
    go to the founder-led experienced reps. Those opened on or after it
    go to the 8 new AEs, and tenure at opened_date drives their ramp
    multiplier. Other segments draw from their tenured pools.

    close_date = opened_date + sales_cycle_days. deal_size_usd from a
    lognormal clipped to the segment range, tuned so the realized mean
    lands within 15% of deal_size_avg. Deals opened on or after
    PRICE_INCREASE_DATE have deal_size_usd scaled by
    (1 + PRICE_INCREASE_PCT).
    """
    companies_by_seg = _companies_by_segment(companies)
    region_by_company = companies.set_index("company_id")["region"].to_dict()

    mm_reps = reps[reps["segment"] == "Mid-Market"].to_dict("records")
    smb_reps = reps[reps["segment"] == "SMB"].to_dict("records")
    founder_reps = reps[(reps["segment"] == "Enterprise") & (reps["is_founder_led"])].to_dict("records")
    new_ae_reps = reps[(reps["segment"] == "Enterprise") & (~reps["is_founder_led"])].to_dict("records")

    def enterprise_pre_push_rep_fn(opened_date):
        return founder_reps[rng.integers(0, len(founder_reps))]

    def enterprise_post_push_rep_fn(opened_date):
        # Amendment: founder-led reps keep carrying a slice of post-push
        # Enterprise volume so Question 5 has a contemporaneous control.
        if rng.random() < FOUNDER_LED_POST_PUSH_SHARE:
            return founder_reps[rng.integers(0, len(founder_reps))]
        return new_ae_reps[rng.integers(0, len(new_ae_reps))]

    def mid_market_rep_fn(opened_date):
        return mm_reps[rng.integers(0, len(mm_reps))]

    def smb_rep_fn(opened_date):
        return smb_reps[rng.integers(0, len(smb_reps))]

    deal_counter = [0]
    all_deals = []

    ent_target = SEGMENTS["Enterprise"]["closed_attempts"]
    ent_pre_target = int(round(ent_target * ENTERPRISE_PRE_PUSH_SHARE))
    ent_post_target = ent_target - ent_pre_target

    # Wide enough that a genuine pre-push baseline sits inside the window
    # and long-cycle deals opened near the start still have somewhere to
    # close from. See _weighted_open_date and _fill_segment_deals docstrings
    # for why this avoids censoring bias.
    open_floor = datetime(WINDOW_START.year, WINDOW_START.month, 1) - timedelta(days=365)

    all_deals += _fill_segment_deals(
        "Enterprise", ent_pre_target, open_floor, ENTERPRISE_PUSH_DATE,
        companies_by_seg, region_by_company, enterprise_pre_push_rep_fn, deal_counter)

    all_deals += _fill_segment_deals(
        "Enterprise", ent_post_target, ENTERPRISE_PUSH_DATE, WINDOW_END,
        companies_by_seg, region_by_company, enterprise_post_push_rep_fn, deal_counter)

    all_deals += _fill_segment_deals(
        "Mid-Market", SEGMENTS["Mid-Market"]["closed_attempts"], open_floor, WINDOW_END,
        companies_by_seg, region_by_company, mid_market_rep_fn, deal_counter)

    all_deals += _fill_segment_deals(
        "SMB", SEGMENTS["SMB"]["closed_attempts"], open_floor, WINDOW_END,
        companies_by_seg, region_by_company, smb_rep_fn, deal_counter)

    return pd.DataFrame(all_deals).sort_values("deal_id").reset_index(drop=True)


def generate_deal_stage_history(deals):
    """NEW TABLE, roughly 7,000 rows.

    Columns: deal_id, stage, entered_date, exited_date, days_in_stage.

    One row per stage a deal passed through, so four rows for a deal
    that reached Negotiation and fewer for one that died early.
    Allocate sales_cycle_days across STAGES with most of the excess time
    for a stalled deal landing in Proposal and Negotiation, since that
    is where stakeholder engagement actually happens. A deal that failed
    qualification never reaches Proposal.

    This table is what makes the root-cause question answerable. It is
    also the natural place for Phase 3 to demonstrate window functions.
    """
    rows = []
    for d in deals.itertuples(index=False):
        cycle_days = int(d.sales_cycle_days)
        opened = d.opened_date

        if d.loss_reason == "unqualified":
            rows.append({
                "deal_id": d.deal_id, "stage": "Prospecting",
                "entered_date": opened, "exited_date": opened + timedelta(days=cycle_days),
                "days_in_stage": cycle_days,
            })
            continue

        props = (STAGE_DAY_PROPORTIONS_STALLED if d.loss_reason == "stalled_no_decision"
                 else STAGE_DAY_PROPORTIONS_NORMAL)
        stage_days = {}
        running = 0
        for stage in STAGES[:-1]:
            days = int(math.floor(cycle_days * props[stage]))
            stage_days[stage] = days
            running += days
        stage_days[STAGES[-1]] = max(0, cycle_days - running)

        cur = opened
        for stage in STAGES:
            days = stage_days[stage]
            exited = cur + timedelta(days=days)
            rows.append({
                "deal_id": d.deal_id, "stage": stage,
                "entered_date": cur, "exited_date": exited,
                "days_in_stage": days,
            })
            cur = exited

    return pd.DataFrame(rows)


def generate_customers(deals):
    """One row per won deal.

    Columns: customer_id, deal_id, segment, cohort_month,
    annual_contract_value, churn_date, months_retained_observed,
    is_active_at_window_end.

    Churn from the segment's annual rate converted to a monthly hazard,
    applied over the months between close_date and WINDOW_END.

    KNOWN LIMITATION, do not paper over it: Enterprise will produce only
    about five observed churn events across the whole window. Enterprise
    retention therefore cannot be measured from this data, and Phase 3
    must say so and fall back to benchmark churn with a stated
    sensitivity range rather than reporting a measured Enterprise
    retention curve. This is deliberate and belongs in the honesty layer.
    """
    won = deals[deals["deal_won"]].reset_index(drop=True)
    rows = []
    for i, d in won.iterrows():
        annual_churn = SEGMENTS[d["segment"]]["annual_churn"]
        monthly_hazard = 1 - (1 - annual_churn) ** (1 / 12)
        close_date = d["close_date"]
        months_observed = max(0, int((WINDOW_END - close_date).days / 30.44))

        months_to_churn = int(rng.geometric(monthly_hazard)) if monthly_hazard > 0 else 10 ** 9

        if months_to_churn <= months_observed:
            churn_date = close_date + timedelta(days=int(round(months_to_churn * 30.44)))
            months_retained = months_to_churn
            is_active = False
        else:
            churn_date = pd.NaT
            months_retained = months_observed
            is_active = True

        rows.append({
            "customer_id": f"CUST{i + 1:05d}",
            "deal_id": d["deal_id"],
            "segment": d["segment"],
            "cohort_month": datetime(close_date.year, close_date.month, 1),
            "annual_contract_value": d["deal_size_usd"],
            "churn_date": churn_date,
            "months_retained_observed": months_retained,
            "is_active_at_window_end": is_active,
        })

    return pd.DataFrame(rows)


def generate_pipeline(companies, reps):
    """400 open opportunities.

    Columns: opportunity_id, company_id, rep_id, segment, region,
    acquisition_channel, stage, stage_entered_date,
    days_in_current_stage, forecast_close_date, forecast_amount_usd,
    win_probability_pct.

    This table now has a job. Open Enterprise deals owned by the new AEs
    should show materially higher days_in_current_stage in Proposal and
    Negotiation, so pipeline coverage looks adequate in aggregate while
    Enterprise coverage is inflated by opportunities sitting 90 days or
    more. That is forward-looking evidence for the same finding the
    closed deals show in hindsight.
    """
    companies_by_seg = _companies_by_segment(companies)
    region_by_company = companies.set_index("company_id")["region"].to_dict()

    founder_reps = reps[(reps["segment"] == "Enterprise") & (reps["is_founder_led"])].to_dict("records")
    new_ae_reps = reps[(reps["segment"] == "Enterprise") & (~reps["is_founder_led"])].to_dict("records")
    mm_reps = reps[reps["segment"] == "Mid-Market"].to_dict("records")
    smb_reps = reps[reps["segment"] == "SMB"].to_dict("records")

    seg_names = list(PIPELINE_SEGMENT_PROBS.keys())
    seg_probs = [PIPELINE_SEGMENT_PROBS[s] for s in seg_names]
    segments_drawn = [seg_names[i] for i in rng.choice(len(seg_names), size=NUM_PIPELINE_DEALS, p=seg_probs)]

    rows = []
    for i in range(NUM_PIPELINE_DEALS):
        segment = segments_drawn[i]
        company_pool = companies_by_seg[segment]
        company_id = company_pool[rng.integers(0, len(company_pool))]
        region = region_by_company[company_id]
        channel = _pick_channel(segment)

        if segment == "Enterprise":
            if rng.random() < FOUNDER_LED_POST_PUSH_SHARE:
                rep = founder_reps[rng.integers(0, len(founder_reps))]
                weight_key = ("Enterprise", "founder")
            else:
                rep = new_ae_reps[rng.integers(0, len(new_ae_reps))]
                weight_key = ("Enterprise", "new_ae")
        elif segment == "Mid-Market":
            rep = mm_reps[rng.integers(0, len(mm_reps))]
            weight_key = ("Mid-Market", None)
        else:
            rep = smb_reps[rng.integers(0, len(smb_reps))]
            weight_key = ("SMB", None)

        stage_weights = PIPELINE_STAGE_WEIGHTS[weight_key]
        stages = list(stage_weights.keys())
        probs = list(stage_weights.values())
        stage = stages[rng.choice(len(stages), p=probs)]

        if weight_key == ("Enterprise", "new_ae") and stage in ("Proposal", "Negotiation"):
            days_in_current_stage = int(rng.lognormal(math.log(70), 0.5))
        else:
            days_in_current_stage = int(rng.lognormal(math.log(25), 0.5))
        days_in_current_stage = max(1, min(days_in_current_stage, 400))

        stage_entered_date = WINDOW_END - timedelta(days=days_in_current_stage)
        forecast_close_date = WINDOW_END + timedelta(days=int(rng.integers(15, 120)))

        rows.append({
            "opportunity_id": f"OPP{i + 1:05d}",
            "company_id": company_id,
            "rep_id": rep["rep_id"],
            "segment": segment,
            "region": region,
            "acquisition_channel": channel,
            "stage": stage,
            "stage_entered_date": stage_entered_date,
            "days_in_current_stage": days_in_current_stage,
            "forecast_close_date": forecast_close_date,
            "forecast_amount_usd": round(_draw_deal_size(segment), 2),
            "win_probability_pct": STAGE_WIN_PROBABILITY[stage],
        })

    return pd.DataFrame(rows)


def generate_sm_spend():
    """NEW TABLE, 78 rows.

    Columns: month, segment, spend_usd.

    Monthly rows across the full window from
    MONTHLY_SM_SPEND_BY_SEGMENT, with Enterprise scaled by
    ENTERPRISE_PRE_PUSH_SPEND_FRACTION for months before
    ENTERPRISE_PUSH_DATE. Phase 3 computes CAC from this table, not from
    an annual constant.
    """
    rows = []
    cur = datetime(WINDOW_START.year, WINDOW_START.month, 1)
    end = datetime(WINDOW_END.year, WINDOW_END.month, 1)
    while cur <= end:
        for segment, monthly_amount in MONTHLY_SM_SPEND_BY_SEGMENT.items():
            amount = monthly_amount
            if segment == "Enterprise" and cur < ENTERPRISE_PUSH_DATE:
                amount = monthly_amount * ENTERPRISE_PRE_PUSH_SPEND_FRACTION
            rows.append({"month": cur, "segment": segment, "spend_usd": round(amount, 2)})
        cur = datetime(cur.year + 1, 1, 1) if cur.month == 12 else datetime(cur.year, cur.month + 1, 1)
    return pd.DataFrame(rows)


def validate(companies, reps, deals, stage_history, customers, pipeline, spend):
    """Structural checks. HARD requirements, must pass exactly.

    - len(deals) == NUM_CLOSED_DEALS, len(pipeline) == NUM_PIPELINE_DEALS
    - len(customers) == deals['deal_won'].sum(), exactly
    - zero orphan company_id or rep_id in deals or pipeline
    - zero customers.deal_id absent from deals or pointing at a lost deal
    - every stage_history.deal_id exists in deals
    - stage_history days_in_stage per deal sums to that deal's
      sales_cycle_days, within rounding
    - every close_date inside [WINDOW_START, WINDOW_END]
    - no Enterprise deal opened before ENTERPRISE_PUSH_DATE assigned to a
      rep hired on or after it, and vice versa
    - realized mean deal_size_usd within 15% of deal_size_avg per segment
    - re-running with SEED reproduces byte identical CSVs

    DELIBERATELY ABSENT: any assertion about a realized win rate.
    Asserting one would reintroduce outcome encoding through the back
    door. Win rates are reported by report_emergent_outcomes() and judged
    against a plausibility band, not asserted.
    """
    errors = []

    if len(deals) != NUM_CLOSED_DEALS:
        errors.append(f"deals row count {len(deals)} != {NUM_CLOSED_DEALS}")
    if len(pipeline) != NUM_PIPELINE_DEALS:
        errors.append(f"pipeline row count {len(pipeline)} != {NUM_PIPELINE_DEALS}")

    won_count = int(deals["deal_won"].sum())
    if len(customers) != won_count:
        errors.append(f"customers row count {len(customers)} != won deals {won_count}")

    if not deals["company_id"].isin(companies["company_id"]).all():
        errors.append("deals has orphan company_id")
    if not deals["rep_id"].isin(reps["rep_id"]).all():
        errors.append("deals has orphan rep_id")
    if not pipeline["company_id"].isin(companies["company_id"]).all():
        errors.append("pipeline has orphan company_id")
    if not pipeline["rep_id"].isin(reps["rep_id"]).all():
        errors.append("pipeline has orphan rep_id")

    won_ids = set(deals.loc[deals["deal_won"], "deal_id"])
    if not customers["deal_id"].isin(deals["deal_id"]).all():
        errors.append("customers has orphan deal_id")
    if not customers["deal_id"].isin(won_ids).all():
        errors.append("a customer points at a lost deal")

    if not stage_history["deal_id"].isin(deals["deal_id"]).all():
        errors.append("deal_stage_history has orphan deal_id")

    per_deal = stage_history.groupby("deal_id")["days_in_stage"].sum()
    merged = deals.set_index("deal_id")["sales_cycle_days"].reindex(per_deal.index)
    drift = (per_deal - merged).abs()
    if len(drift) and drift.max() > 1:
        errors.append(f"stage days do not reconcile to sales_cycle_days, worst drift {drift.max()}")

    if not ((deals["close_date"] >= WINDOW_START) & (deals["close_date"] <= WINDOW_END)).all():
        errors.append("a close_date falls outside the observation window")

    merged_reps = deals.merge(reps[["rep_id", "hire_date"]], on="rep_id", how="left")
    leak = merged_reps["opened_date"] < merged_reps["hire_date"]
    if leak.sum() > 0:
        errors.append(f"{int(leak.sum())} deals worked by a rep not yet hired")
    ent = merged_reps[merged_reps["segment"] == "Enterprise"]
    pre = ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]
    bad = pre["hire_date"] >= ENTERPRISE_PUSH_DATE
    if bad.sum() > 0:
        errors.append(f"{int(bad.sum())} pre-push Enterprise deals assigned to post-push AEs")

    for segment, params in SEGMENTS.items():
        sub = deals[deals["segment"] == segment]
        if len(sub):
            mean = sub["deal_size_usd"].mean()
            target = params["deal_size_avg"]
            if abs(mean - target) / target > 0.15:
                errors.append(f"{segment} mean deal size {mean:.0f} outside 15% of target {target}")

    if errors:
        raise AssertionError("Generator validation failed:\n" + "\n".join(f"- {e}" for e in errors))

    print(f"In-generator validation passed: {len(deals)} deals, {len(customers)} customers, "
          f"{len(stage_history)} stage rows, {len(pipeline)} pipeline rows, {len(companies)} companies, "
          f"{len(reps)} reps, {len(spend)} spend rows.")


def report_emergent_outcomes(deals, customers, spend):
    """Print, do not assert, what the mechanism produced.

    Report at minimum: win rate by segment; Enterprise win rate split by
    whether opened_date precedes ENTERPRISE_PUSH_DATE, with a
    two-proportion confidence interval; loss_reason mix by segment and
    period; realized mean deal size by segment; blended win rate; count
    of observed churn events by segment.

    PLAUSIBILITY BAND, not a target. Calibration runs of this mechanism
    landed Enterprise experienced-motion win rate near 26%, new-team
    blended near 11%, Mid-Market near 29%, and SMB near 35%, all inside
    published benchmark ranges. Treat 18-34% for the experienced
    Enterprise motion and 6-20% for the new-team period as acceptable.

    If the output lands inside the band, ACCEPT IT AND RECORD THE ACTUAL
    NUMBERS. The case study is written from whatever these come out to
    be. Only if a figure lands outside the band should you suspect a
    mechanism bug, and even then you fix the mechanism, never nudge a
    number toward a nicer story.
    """
    def two_prop_ci(p1, n1, p2, n2):
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        d = p1 - p2
        z = d / se if se else 0.0
        return d, se, z, (d - 1.96 * se, d + 1.96 * se)

    print("\n" + "=" * 70)
    print("EMERGENT OUTCOMES (measured, not asserted)")
    print("=" * 70)

    for segment in ["Enterprise", "Mid-Market", "SMB"]:
        sub = deals[deals["segment"] == segment]
        print(f"{segment}: win rate {sub['deal_won'].mean():.1%} (n={len(sub)})")

    ent = deals[deals["segment"] == "Enterprise"]
    pre = ent[ent["opened_date"] < ENTERPRISE_PUSH_DATE]
    post = ent[ent["opened_date"] >= ENTERPRISE_PUSH_DATE]
    p1, p2 = pre["deal_won"].mean(), post["deal_won"].mean()
    d, se, z, (lo, hi) = two_prop_ci(p1, len(pre), p2, len(post))
    print(f"\nEnterprise pre-push (by open date): {p1:.1%} win rate, n={len(pre)}")
    print(f"Enterprise post-push (by open date): {p2:.1%} win rate, n={len(post)}")
    print(f"Difference: {d * 100:.1f}pp, 95% CI [{lo * 100:.1f}, {hi * 100:.1f}]pp, z={z:.2f}")

    print("\nLoss reason mix by segment (lost deals only):")
    print(deals[~deals["deal_won"]].groupby(["segment", "loss_reason"]).size())

    print("\nRealized mean deal size by segment:")
    print(deals.groupby("segment")["deal_size_usd"].mean().round(0))

    print(f"\nBlended win rate: {deals['deal_won'].mean():.1%} (n={len(deals)})")

    print("\nObserved churn events by segment:")
    print(customers[customers["churn_date"].notna()].groupby("segment").size())

    print("=" * 70)


def main(out_dir="data/raw"):
    companies = generate_companies()
    reps = generate_sales_reps()
    deals = generate_deals(companies, reps)
    stage_history = generate_deal_stage_history(deals)
    customers = generate_customers(deals)
    pipeline = generate_pipeline(companies, reps)
    spend = generate_sm_spend()

    validate(companies, reps, deals, stage_history, customers, pipeline, spend)
    report_emergent_outcomes(deals, customers, spend)

    # Explicit float_format, per PHASE-2-HANDOFF-PROMPT-V2.md and
    # AGENT-BUILD-GUIDE.md 7.5: float formatting is one of the ways
    # SEED = 42 alone fails to guarantee reproducible CSVs across pandas
    # versions. A content hash of these files is the real reproducibility
    # test, not a byte diff.
    import os
    os.makedirs(out_dir, exist_ok=True)
    companies.to_csv(f"{out_dir}/companies.csv", index=False, float_format="%.4f")
    reps.to_csv(f"{out_dir}/sales_reps.csv", index=False, float_format="%.4f")
    deals.to_csv(f"{out_dir}/deals.csv", index=False, float_format="%.4f")
    stage_history.to_csv(f"{out_dir}/deal_stage_history.csv", index=False, float_format="%.4f")
    customers.to_csv(f"{out_dir}/customers.csv", index=False, float_format="%.4f")
    pipeline.to_csv(f"{out_dir}/sales_pipeline.csv", index=False, float_format="%.4f")
    spend.to_csv(f"{out_dir}/sm_spend.csv", index=False, float_format="%.4f")

    print(f"Dataset generated in {out_dir}/. Record the emergent outcomes above in "
          "docs/project_context.md before proceeding to Phase 3.")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
