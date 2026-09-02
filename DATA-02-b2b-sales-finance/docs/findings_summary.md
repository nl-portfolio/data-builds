# Findings Summary: Anchorpoint B2B Sales Finance Case Study

Phase 3, 2026-08-21. Measured results only. Every headline claim carries its n and a 95% confidence interval. Full computation lives in `src/phase3_lib.py` and the three notebooks in `notebooks/`; every number below traces to a specific notebook cell in `docs/claims_traceability.md`.

This file is written from what was measured in `data/raw/`, not from `docs/case_study_scenario.md`, which holds hypotheses. Where a measured figure differs from what the scenario hypothesized, the measured figure is what is reported here, per the standing "data wins over narrative" rule.

---

## Primary comparison (pre-registered)

Enterprise win rate, pre-push vs. post-push, cohorted by `opened_date`.

**Pre-push: 35.2% (n=105). Post-push: 10.2% (n=315). Difference: 25.1 percentage points, 95% CI [15.4, 34.8]pp, z=5.05, n=105/315.**

The confidence interval clears zero comfortably. This is the headline finding the rest of this document investigates the cause of, not the fact of.

One sampling note carried over from Phase 2: the pre-push figure (35.2%) sits 1.2 points above the plausibility band used to sanity-check the generator (18 to 34%). An isolated 30,000-trial simulation of the mechanism alone reproduced the calibration target almost exactly (27.0%), confirming this is small-sample noise at n=105, not a data defect. See `docs/decisions.md`, 2026-08-21.

---

## Question 1: unit economics overall

**Blended CAC (trailing 12 months, lag-adjusted by each segment's average sales cycle, window ending 2026-08-31): $22,963**, from $6.2M trailing spend against 270 wins across all three segments.

| Segment | CAC (trailing 12mo) | ACV | LTV, capped (headline) | LTV, naive (contrast) | LTV:CAC, capped | LTV:CAC, naive | Payback (months) |
|---|---|---|---|---|---|---|---|
| Enterprise | $110,345 (n=29 wins) | $99,868 | $233,692 | $973,716 | 2.12 | 8.82 | 17.0 |
| Mid-Market | $17,822 (n=101 wins) | $35,012 | $81,928 | $230,612 | 4.60 | 12.94 | 7.8 |
| SMB | $8,571 (n=140 wins) | $11,825 | $27,670 | $32,231 | 3.23 | 3.76 | 11.2 |

**LTV method.** Headline: `ACV x 0.78 gross margin x min(1/annual_churn, 3 years)`. Contrast: the same formula with the cap removed, labelled naive, never used as the headline. Annual churn is measured empirically for Mid-Market (11.8%, 24 churn events over 2,297 customer-months observed) and SMB (28.6%, 100 events over 3,610 customer-months), both close to the locked benchmark bands. Enterprise churn cannot be measured from this data (6 observed events) and uses the locked benchmark (8%, Optifai, 5 to 10% sensitivity range); at that range, Enterprise capped LTV moves from roughly $146,000 (10% churn) to $233,700 (8%) to a ceiling near $233,700 (5% churn hits the 3-year cap regardless, since 1/0.05 = 20 years, well above the cap).

**Why the capped LTV is the headline, not the naive one.** Naive `1/churn` gives Enterprise a 12.5-year implied customer life and an LTV:CAC ratio of 8.82, comfortably above the 3:1 rule of thumb most CFOs use as a health check. No five-year-old company (Anchorpoint, founded 2021) should book a 12.5-year customer life. The capped method (3-year ceiling) gives Enterprise an LTV:CAC of 2.12, below the 3:1 threshold. **Which method is used changes the recommendation this data supports**, from "keep spending" to "this segment does not clear the standard bar," which is exactly why the choice is disclosed and justified rather than made silently.

**Aggregate reading.** The blended CAC ($22,963) does not look alarming on its own. It is the decomposition that shows Enterprise CAC is roughly 5x Mid-Market's and 13x SMB's, and does not clear the standard LTV:CAC bar under the defensible method. This is the same pattern documented under Question 7: an aggregate view that does not, on its own, show the problem.

---

## Question 2: segment divergence

**Win rate.** See the primary comparison above (25.1pp difference, CI excludes zero). Mid-Market and SMB show no comparable decline over the same window (Question 6 addresses this directly, ruling out company-wide explanations).

**CAC and payback, pre-push vs. post-push era (same-period method, not lag-adjusted; see methodology note in `notebooks/02_unit_economics.ipynb`).** Enterprise pre-push era (2024-07-01 to 2025-01-01, 6.0 months, founder-led): CAC $11,520 (25 wins against $288,000 spend), payback 1.9 months. Post-push era (2025-01-01 to 2026-08-31, 19.9 months, new AE team): CAC $121,212 (44 wins against $5.33M spend), payback 18.1 months. **CAC rose roughly 10.5x era over era.**

The pre-push figure reflects a minimal, founder-led motion running on a small fraction of full spend (`ENTERPRISE_PRE_PUSH_SPEND_FRACTION`), not a scalable benchmark for running Enterprise sales at the company's current size; it was cheap because it was small. The post-push figure, against a fully staffed 8-AE team, is the relevant one for evaluating whether the current investment is working.

For contrast, Mid-Market and SMB CAC did not move in the same direction or magnitude over the identical calendar split (both segments' era-to-era CAC stayed within a narrow band), reinforcing that this is an Enterprise-specific shift, not a company-wide spend or pricing effect.

---

## Question 3: cause vs. symptom, open date vs. close date

**Reporting lag: approximately one quarter (about 3 months).** By close date, Enterprise win rate holds near baseline through 2025 Q1 (21.7%, n=46) and drops sharply in 2025 Q2 (7.1%, n=42). By open date, the break sits exactly at 2025 Q1 (8.5%, n=47), the push date, since that split defines the cohort boundary. A close-date-only monthly or quarterly review would have taken roughly one quarter longer to notice the change than an open-date view would.

**Mechanistic cycle length: 5.9 months** (n=117), the mean cycle for post-push Enterprise deals that reach a real outcome (stalled, lost to competitor, or won), which is longer than the 2.6-month mean across all post-push Enterprise deals because most post-push volume (198 of 315, 62.9%) is quick unqualified rejection that resolves in under a month and pulls the blended average down. The deals that seriously progress toward Proposal and Negotiation, which the stall mechanism affects, take substantially longer, and are the ones responsible for the reporting lag.

---

## Question 4: where deals fail, and the mix of loss reasons

**Stage duration, mean days, pre-push vs. post-push:**

| Stage | Pre-push (n=65 deals reaching Qualified+) | Post-push (n=117 deals reaching Qualified+) |
|---|---|---|
| Prospecting | 15.1 days (n=105) | 17.6 days (n=315) |
| Qualified | 17.4 days | 26.0 days |
| Proposal | 34.4 days | 57.5 days |
| Negotiation | 36.5 days | 78.7 days |

Prospecting moves modestly (+16%); Qualified, Proposal, and Negotiation blow out, with Negotiation more than doubling (36.5 to 78.7 days). This is stage-specific concentration, not a uniform slowdown.

**Loss reason mix, share of losses:**

| Loss reason | Pre-push (n=68 losses) | Post-push (n=283 losses) |
|---|---|---|
| `unqualified` | 58.8% (40) | 70.0% (198) |
| `stalled_no_decision` | 0.0% (0) | 20.1% (57) |
| `lost_to_competitor` | 41.2% (28) | 9.9% (28) |

**This is the single clearest result in the dataset.** `stalled_no_decision` did not exist pre-push and accounts for a fifth of post-push losses. `lost_to_competitor`'s share of losses fell, not rose. The Question 4 falsification condition (losses concentrating in `lost_to_competitor` rather than `stalled_no_decision`) is directly contradicted by the data: the opposite pattern holds.

---

## Question 5: does rep capability explain it

**Confounding, stated explicitly.** All 8 new Enterprise AEs share a hire date, so `has_enterprise_experience` is perfectly confounded with calendar period for that group in a naive comparison.

**Full comparison (confounded, reported for completeness only): experienced 32.2% (n=143) vs. inexperienced 8.3% (n=277). Difference 23.9pp, 95% CI [15.5, 32.2]pp, z=5.62.** Not usable as a causal estimate on its own, since every inexperienced-rep deal is also a post-push deal.

**Same-period comparison (post-push only; both groups share the identical calendar period, enabled by the contemporaneous control amendment, `docs/decisions.md` 2026-08-21): experienced (founder-led) 23.7% (n=38) vs. inexperienced (new AEs) 8.3% (n=277). Difference 15.4pp, 95% CI [1.5, 29.3]pp, z=2.17.** This clears zero, though with a wide interval given the small founder-led post-push sample.

**Controls.** Mean deal size: experienced-group deals averaged $91,219 vs. $105,186 for the inexperienced group; inexperienced reps were not handed systematically easier (smaller) deals. Region mix: inexperienced reps carried a somewhat larger EU share (23.5% vs. 18.4%), which, given the EU competitive pressure documented under Question 6, would work against the inexperienced group's win rate, not for it, meaning this control does not inflate the observed gap.

**Conclusion.** Rep capability is a real, statistically distinguishable, same-period contributor to the decline, on the order of 15 percentage points, though the interval is wide at this sample size and should not be read as a precise number.

---

## Question 6: quantifying the four competing explanations

| Explanation | Verdict | Evidence |
|---|---|---|
| Rep capability / execution | **Real, primary** | Same-period test, Question 5: 15.4pp, 95% CI [1.5, 29.3]pp, n=38/277 |
| EU competitive entry | **Partially real, minor** | See below |
| List price increase (Aug 2025, +12%) | **Ruled out** | See below |
| Seasonality | **Ruled out** | See below |
| Partnerships channel mix | **Ruled out** | See below |

**EU competitive entry.** Two methods were tried because the naive one is misleading here. Splitting Enterprise pre/post at the push date by region shows almost no EU-specific excess decline (EU: 24.6pp decline vs. a 24.9pp non-EU baseline, excess approximately 0), because that split dilutes the signal: many "post-push" EU deals were opened before the competitor actually arrived (2025-07-01). Restricting to the post-push cohort only and splitting at the competitor's actual entry date isolates the effect: EU win rate fell from 10.0% to 4.8% (n=30/42) after the competitor's entry, while non-EU rose from 8.5% to 12.2% (n=71/172) over the same window, a difference-in-differences of **-9.0 percentage points**. At this sample size the estimate does not reach conventional significance and should be read as suggestive. **Estimated contribution: single digits of the ~25pp overall decline, not the primary driver, but plausibly real.**

**List price increase.** Mid-Market (+2.7pp, 95% CI [-3.6, 9.1]pp, n=418/342) and SMB (+6.6pp, 95% CI [0.8, 12.3]pp, n=550/470) absorbed the identical increase with no negative movement, if anything a small positive one. Enterprise, restricted to the post-push period only, shows essentially no change across the price date (-0.4pp, 95% CI [-7.2, 6.4]pp, n=121/194). **Ruled out.**

**Seasonality.** Enterprise's decline is a sustained structural break persisting across five consecutive quarters (2025 Q2 through 2026 Q2) without reverting toward baseline. Neither Mid-Market nor SMB shows an analogous sustained decline over the same calendar window; both fluctuate within a band. A purely seasonal effect would revert and would show up comparably in every segment facing the same calendar. Neither holds. **Ruled out.**

**Partnerships channel mix.** Enterprise channel mix barely moved (Direct Sales 87.6% to 88.6% of volume, pre to post). Restricting the pre/post comparison to Direct Sales only, which removes any channel-mix effect by construction, reproduces virtually the same decline (24.0pp, 95% CI [13.6, 34.4]pp, n=92/279) as the all-channels comparison (25.1pp, CI [15.4, 34.8]pp, n=105/315). **Ruled out.**

**Apportioning the decline.** These do not sum cleanly to 25pp; rep capability and the EU competitor are not fully independent (some EU deals are also worked by inexperienced reps), and the same-period rep-capability estimate itself carries a wide interval. The defensible statement: execution is the dominant, statistically supported driver; the EU competitor plausibly adds a small amount on top; price, seasonality, and channel mix are not material.

---

## Question 7: why the dashboard missed it, and what it costs

**The aggregate view never signals a problem.** Blended (all-segment) win rate stays in a 20.0% to 32.4% band across all nine quarters in the window and shows no sustained trend. Enterprise alone falls from the 21.7% to 44.4% range (pre-push quarters) to the 7.1% to 16.1% range (post-push quarters) and stays there. A board or monthly business review watching only the blended number sees nothing wrong.

**Budget consequence (trailing 12 months, ending 2026-08-31).** Enterprise: 51.6% of S&M spend, 10.7% of won deals, 34.3% of new ARR. More than half the sales and marketing budget for close to a third of new revenue and about a tenth of the deals. Mid-Market: 29.0% of spend, 37.4% of deals, 44.3% of ARR. SMB: 19.4% of spend, 51.9% of deals, 21.4% of ARR.

**Forward-looking evidence, from open pipeline.** 38.6% of Enterprise late-stage (Proposal/Negotiation) open pipeline (22 of 57 opportunities) has been sitting 90 or more days in stage, representing $2.23M of forecast value, against 0.0% for Mid-Market and 2.1% for SMB. `win_probability_pct` follows a fixed stage-based convention for every opportunity, so the field a pipeline review typically leans on does not distinguish a healthy Proposal-stage deal from one stuck for three months. Only `days_in_current_stage`, a field most reviews do not surface prominently, reveals it.

---

## Documented limitations, carried forward from Phase 2

- **Enterprise retention cannot be measured** (6 observed churn events across the window). LTV uses the locked benchmark (8%, Optifai, 5 to 10% sensitivity range shown above), not a measured curve, and this is stated wherever Enterprise LTV appears.
- **Enterprise cohort analysis is quarterly grain only**, per the locked rigor requirement; monthly Enterprise cuts exist in the data but are never reported, since Enterprise monthly volume (roughly 7 deals per month) cannot support a readable estimate.
- **The EU competitor's contribution is a suggestive, not statistically confirmed, estimate** (n=30/42 per cell in the isolating test). It is reported as a range and a direction, not a precise number.
- **The same-period rep-experience comparison rests on a small founder-led post-push sample** (n=38), a direct consequence of the contemporaneous control amendment only assigning roughly 12% of post-push Enterprise volume to founder-led reps. The effect clears zero but the interval is wide.
