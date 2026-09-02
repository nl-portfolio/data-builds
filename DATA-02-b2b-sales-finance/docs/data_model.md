# Data Model: Anchorpoint B2B Sales Dataset

**Version: Phase 1.5 redesign, 2026-08-20. Supersedes the Phase 1 four-table model.**

Seven tables. Three are new (`sales_reps`, `deal_stage_history`, `sm_spend`), each added to fix a specific defect identified in `docs/plan_review.md`. No `dim_date` table; time cuts come from date columns directly.

---

## Grain and Scope

**Window:** 2024-07-01 through 2026-08-31, 26 months. Extended from Phase 1's 20 months so that a genuine pre-push Enterprise baseline sits inside the window and retention has more observation time.

**Grain of `deals`:** one row per closed opportunity, won or lost. A company that ran three opportunities has three rows.

**Volumes:**

| Table | Rows | Note |
|---|---|---|
| companies | 900 | up from 500 |
| sales_reps | 30 | new |
| deals | 2,200 closed | up from 1,200 |
| deal_stage_history | ~7,000 | new, one row per deal per stage entered |
| customers | = count of won deals | not an independent parameter |
| sales_pipeline | 400 open | up from 300 |
| sm_spend | 78 | new, 26 months x 3 segments |

**Segment mix of the 2,200 closed attempts:** Enterprise 420, Mid-Market 760, SMB 1,020.

**Won-deal counts are deliberately not specified.** They are an output of the mechanism, not an input. Phase 1's model fixed them at 340 with a per-segment breakdown; that was outcome encoding and has been removed.

### Why Enterprise volume went from 150 to 420

At 150 Enterprise attempts the central finding failed significance. With the window's true 6-month pre / 14-month post split, the pre-push arm held roughly 45 attempts and the comparison tested at p = 0.062 with a 95 percent confidence interval of [-0.7pp, +28.7pp], crossing zero. At 420 attempts with a realistic 25/75 volume ramp around the push date, the same comparison tests at roughly p = 0.001 with a confidence interval that clears zero comfortably. Full working in `docs/plan_review.md` section 2.1.

### Startup segment removed

Superseding the Phase 1 decision to run four segments. At any realistic volume the Startup tier produced too few wins to support analysis, contributed under half a percent of ARR, and was already excluded from the payback work. Its attempts were redistributed to the three remaining segments. See `docs/decisions.md`.

---

## Core Tables

### companies (900 rows)

`company_id`, `company_name`, `industry`, `region` (US / EU / APAC), `employee_count`, `founding_date`.

`region` is load-bearing now: one of the competing explanations the analysis must rule out is region specific. Distribution is US-heavy (roughly 62 / 26 / 12) since Anchorpoint is Austin based.

`employee_count` correlates with the segment a company's deals land in, because segment is derived from company size rather than drawn independently.

### sales_reps (30 rows), NEW

`rep_id`, `rep_name`, `segment`, `hire_date`, `prior_segment`, `has_enterprise_experience`, `playbook_type`, `quota_annual_usd`, `is_founder_led`.

**This table exists because rep capability is the independent variable of the entire analysis.** In Phase 1 the sales team was a comment in the generator, which made the core hypothesis untestable from the exported data. `playbook_type` (`multi_threaded` or `single_threaded`) is derived from `has_enterprise_experience`.

Composition: 8 Enterprise AEs with `hire_date` 2025-01-01, all `has_enterprise_experience = False` (6 promoted internally, 2 external non-enterprise hires); 2 founder-led reps flagged experienced who carry pre-push Enterprise deals; 10 Mid-Market and 10 SMB reps, tenured.

The single cleanest test in the whole case study is a win-rate comparison across `has_enterprise_experience`, holding segment constant.

### deals (2,200 rows)

`deal_id`, `company_id`, `rep_id`, `segment`, `region`, `acquisition_channel`, `deal_size_usd`, `opened_date`, `close_date`, `deal_won`, `loss_reason`, `stakeholders_required`, `stakeholders_engaged`, `sales_cycle_days`.

**`opened_date` is new and it matters.** Cohorting by open date versus close date is what separates the cause from the symptom, since the two are offset by a full enterprise sales cycle.

**`days_in_stage` has been removed.** Phase 1 carried a single scalar with that name, which could not answer the locked question about *where* deals stall. Per-stage timing now lives in `deal_stage_history`.

**`loss_reason`** takes `unqualified`, `stalled_no_decision`, `lost_to_competitor`, or null for wins. The split between `stalled_no_decision` and `lost_to_competitor` is the highest-signal field in the dataset: stalling points at execution, losing head-to-head points at positioning or price.

`stakeholders_required` and `stakeholders_engaged` expose the mechanism directly and let the analysis show engagement shortfall rather than just infer it.

### deal_stage_history (~7,000 rows), NEW

`deal_id`, `stage`, `entered_date`, `exited_date`, `days_in_stage`.

One row per stage a deal entered, across Prospecting, Qualified, Proposal, Negotiation. A deal that failed qualification never reaches Proposal, so row counts per deal vary.

**This table exists to make the root-cause question answerable at all.** It is also the natural place for Phase 3 to demonstrate window functions and gap-and-island logic. Reconciliation: `days_in_stage` summed per deal equals that deal's `sales_cycle_days`, within rounding.

### customers (one row per won deal)

`customer_id`, `deal_id`, `segment`, `cohort_month`, `annual_contract_value`, `churn_date` (nullable), `months_retained_observed`, `is_active_at_window_end`.

Row count equals the count of won deals exactly, and is therefore not an independent parameter.

**Documented limitation, carried into the honesty layer rather than hidden.** At 8 percent annual churn and roughly 60 to 80 Enterprise customers observed for an average of about 13 months, the dataset will contain roughly five observed Enterprise churn events. **Enterprise retention cannot be measured from this data.** Phase 3 must use benchmark churn with a stated sensitivity range and say plainly that it did so. Reporting a measured Enterprise retention curve off five events would be false precision. Mid-Market (~27 events) and SMB (~104 events) support real cohort work; Enterprise cohort analysis is quarterly grain only and always with confidence intervals.

### sales_pipeline (400 rows)

`opportunity_id`, `company_id`, `rep_id`, `segment`, `region`, `acquisition_channel`, `stage`, `stage_entered_date`, `days_in_current_stage`, `forecast_close_date`, `forecast_amount_usd`, `win_probability_pct`.

**This table now has a job.** In Phase 1 it was referenced by none of the six business questions. It now carries forward-looking evidence: aggregate pipeline coverage looks adequate while Enterprise coverage is inflated by opportunities sitting 90 days or more in Proposal and Negotiation. Same finding as the closed deals show in hindsight, visible before it lands in revenue.

### sm_spend (78 rows), NEW

`month`, `segment`, `spend_usd`.

Monthly spend rows, replacing Phase 1's annual scalar. Dividing an annual figure across a multi-month window made period-correct CAC impossible; trailing CAC by cohort needs spend attributed to the month that produced the win. Enterprise spend is scaled down before the push date (founder-led, no dedicated team) and flat afterward. **That flatness is the financial core of the case study: fixed cost, falling yield.**

---

## Derived Metrics (computed in Phase 3, never generated)

**CAC:** segment S&M spend over a period divided by new customers won in that period, from `sm_spend`. Report trailing 12-month and pre-push versus post-push cuts.

**LTV, primary method:** `annual_contract_value x 0.78 gross margin x min(1 / annual_churn, 3 years)`.

**LTV, contrast method:** naive `1 / churn` with no cap, reported **only** alongside the primary and explicitly labelled as the naive method. At 8 percent Enterprise churn the naive method implies a 12.5-year customer life and produces an LTV:CAC ratio that makes the struggling segment look healthy. Showing both, and explaining why the capped figure is the defensible one, is a deliberate design decision. See `docs/decisions.md`.

**Payback period:** `CAC / (ACV x 0.78) x 12`, in months, by segment and cohort.

**Win rate:** wins over closed attempts, cut by segment, by close-date period, by open-date period, and by rep experience. **Every headline win-rate comparison must carry a confidence interval.**

**Cohort retention:** by cohort quarter and segment, subject to the Enterprise limitation above.

**Stage duration:** from `deal_stage_history`, by segment, stage, and period.

---

## Relationships and Validation

`deals.company_id` and `sales_pipeline.company_id` reference `companies.company_id`. `deals.rep_id` and `sales_pipeline.rep_id` reference `sales_reps.rep_id`. `customers.deal_id` references `deals.deal_id` and only where `deal_won` is true. `deal_stage_history.deal_id` references `deals.deal_id`.

Hard checks, all exact:

- `len(deals)` equals 2,200; `len(sales_pipeline)` equals 400
- `len(customers)` equals `deals.deal_won.sum()`
- zero orphan `company_id` or `rep_id` in `deals` or `sales_pipeline`
- zero `customers.deal_id` missing from `deals` or pointing at a lost deal
- every `deal_stage_history.deal_id` present in `deals`
- `days_in_stage` per deal sums to `sales_cycle_days`, within rounding
- every `close_date` inside the window
- Enterprise deals opened before the push date are assigned only to founder-led reps, and those opened after only to the eight new AEs
- realized mean `deal_size_usd` within 15 percent of target per segment
- re-running under `SEED = 42` reproduces byte-identical CSVs

**Deliberately absent: any assertion about a realized win rate.** Asserting one would reintroduce outcome encoding. Win rates are reported against a plausibility band, not asserted. See `report_emergent_outcomes()` in `src/generate_data.py`.
