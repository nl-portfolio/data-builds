# Case Study Scenario: Anchorpoint

**Diagnostic problem: Option A, Segment Divergence.**
**Design: mechanism-based. Version: Phase 1.5 redesign, 2026-08-20, supersedes the Phase 1 version.**

---

## Reading rule for this document

Everything below is either a **scenario constant** (a fact about the company, fixed as an input) or a **hypothesis** (what we believe the data will show, stated as a belief and testable). This document contains no findings. Win rates, CAC, payback periods, and retention figures are outputs of Phase 3 analysis and are written down only after they are measured.

If Phase 2's generated data contradicts a scenario constant stated here, **this document changes to match the data.** The narrative never overrides the dataset.

The Phase 1 version of this file violated that rule. It stated, before any data existed, that Enterprise win rate fell from 28 percent to 14 percent and that payback stretched from 13 months to 26 months. Those were generator parameters written up as discoveries. They have been removed.

---

## Company Overview

Anchorpoint is a B2B SaaS company selling deal-execution software: configure-price-quote and deal-desk tooling that helps sales teams price, quote, and close complex deals faster. Founded in Austin in 2021.

The company raised a $45M Series B in February 2025 and sits at roughly $14M ARR as of August 2026, the end of the 26-month window this dataset models (July 2024 through August 2026). Total burn is about $1.25M per month, leaving roughly 18 months of runway and putting a Series C conversation inside the planning horizon.

Anchorpoint grew up as an SMB and mid-market product: fast self-serve trials, single-line quotes, short cycles. Enterprise deals happened occasionally and were founder-led. In January 2025, leadership funded a dedicated push upmarket and hired eight Enterprise account executives, chasing larger contract values to accelerate ARR ahead of the Series C.

**How that team was staffed is the single most important fact in this scenario.** Six of the eight were promoted internally from SMB or Mid-Market. Two were hired externally from non-enterprise sales roles. None had run a multi-stakeholder enterprise motion before: security review, procurement, executive sponsor alignment, extended proof-of-value cycles. No formal enterprise enablement program was put in place. They ran the fast, single-threaded playbook that had worked in SMB.

## Scenario Constants

| Constant | Value | Source or rationale |
|---|---|---|
| Observation window | 2024-07-01 to 2026-08-31 (26 months) | Extended from 20 months so a genuine pre-push baseline sits inside the window and retention has more time to be observed |
| Enterprise push date | 2025-01-01 | Staffing event, not a performance trigger |
| ARR at window end | ~$14M | To be reconciled bottom-up in Phase 2, within 15 percent |
| Series B | $45M, February 2025 | Sized to a ~$14M ARR company |
| Total burn | ~$1.25M/month | Implies ~18 months runway remaining as of Aug 2026 |
| Gross margin | 78% | B2B SaaS median 75-80% (Orb 2025, SaaS Capital 2026). Newly locked; previously undocumented and silently driving every payback figure |
| Annual S&M | $6.2M (Ent $3.2M, MM $1.8M, SMB $1.2M) | 43% of ARR, inside the 27-45% benchmark (SaaS Capital 2026) |
| Sales team | 8 Enterprise AEs, 10 Mid-Market, 10 SMB | Enterprise sized so attempts per AE stays realistic at the new volume |
| Enterprise AE quota | $800k/year | Bridge Group median enterprise AE new-business quota |
| Opportunities | 2,200 closed, 400 open, 2,600 total | Enterprise raised to 420 closed attempts for statistical power |
| Segments | Enterprise, Mid-Market, SMB | Startup segment cut in Phase 1.5, see decisions.md |
| Deal sizes | Ent $50k-300k (avg ~$95k), MM $20k-50k (~$32k), SMB $5k-20k (~$11k) | Right-skewed, carried forward from Phase 1 |
| Annual logo churn | Ent 8%, MM 11%, SMB 27% | Optifai benchmark bands, carried forward from Phase 1 |
| LTV method | Contribution margin, customer life capped at 3 years | Naive 1/churn reported only as a labelled contrast |

## The Diagnostic Hypothesis

Stated as a belief to be tested, not a result.

Pipeline looks healthy. Total deal volume is up, closed-won revenue is up, and the company is adding more logos each quarter than a year ago. On a top-line view this is what a company approaching a Series C should be able to show.

We believe that underneath the headline, the Enterprise segment is performing materially worse than the aggregate suggests, and that the cause is the sales motion the new AE team is running rather than the market, the price, or the product.

**The mechanism we believe is operating.** An enterprise purchase involves a buying group, commonly six to ten people. Winning requires engaging that whole group before the buyer's patience runs out. A rep running a multi-threaded motion engages several stakeholders in parallel. A rep running the single-threaded SMB playbook works one champion at a time. On a two-week SMB deal that difference is invisible. On a seven-month enterprise deal with eight stakeholders, the single-threaded rep never finishes engaging the group, and the deal stalls in Proposal or Negotiation and eventually dies of no decision.

**Why we expect this was invisible for two full quarters.** Enterprise cycles run six to nine months. The team started in January 2025, so the first deals they opened did not close until roughly the middle of that year. Until then, the Enterprise deals *closing* were founder-led deals opened in 2024. Any dashboard reading win rate by close date would show nothing wrong until mid-2025, by which point two quarters of spend had already been committed.

**This lag is itself a finding, and possibly the most useful one.** Win rate by close date is a lagging indicator that lags by a full sales cycle. Cohorting the same deals by *open* date should move the break to January 2025, where the cause actually sits.

**Why it is expensive.** Enterprise absorbs roughly half the S&M budget for a small share of won deals. That cost is fixed: eight AEs plus deal-desk and sales-engineering support do not get cheaper when their win rate falls. If the hypothesis holds, the company is spending its largest sales line on the segment it currently closes least efficiently, while aggregate dashboards show the money working.

## What Would Falsify This

If any of the following turns out to be true in the data, the hypothesis is wrong and the case study changes to follow the evidence:

- Mid-Market and SMB win rates decline over the same period. That points to something company-wide (price, product, market) rather than Enterprise execution.
- The Enterprise decline is confined to one region. That points to competition rather than staffing.
- Enterprise losses are concentrated in `lost_to_competitor` rather than `stalled_no_decision`. Losing head-to-head is a positioning or pricing problem, not an execution one.
- Deals worked by reps with enterprise experience perform no better than deals worked by reps without it. That falsifies the mechanism directly and is the cleanest single test in the analysis.
- The win rate difference between pre-push and post-push Enterprise cohorts is not statistically distinguishable from zero. In that case there is no finding, and the honest case study says so.

## Competing Explanations the Analysis Must Rule Out

Four alternatives exist in the data and are plausible on their face. Phase 3 must address each explicitly and quantify how much of the decline it accounts for. The analyst does not know in advance which of these are real.

**A competitor entered EU.** A well-funded competitor began contesting EU enterprise deals in mid-2025.

**Prices went up.** List prices rose about 12 percent in August 2025, close in time to when the Enterprise decline becomes visible.

**Seasonality.** Deal flow has a Q4 peak and a Q1 trough. A naive month-over-month read of early 2026 looks like deterioration.

**Channel mix shifted.** The Partnerships channel grew across the window and brings lower-fit leads than Direct Sales.

## Why This Matters

This is the diagnosis a startup finance analyst has to be able to make: a business that looks healthy on the metrics a board glances at, while a specific and expensive part of it is quietly getting worse, and where several plausible explanations compete for the same evidence.

The decision it changes is concrete. If the cause is execution, the fix is enablement and the eight seats stay. If the cause is the market or the competitor, the fix is to cut the seats and redeploy the budget to segments where payback is fast. Those are opposite recommendations drawn from the same top-line numbers, and telling them apart is the entire job.
