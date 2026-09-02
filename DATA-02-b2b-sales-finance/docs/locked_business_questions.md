# Locked Business Questions: Anchorpoint

**Version: Phase 1.5 rewrite, 2026-08-20. Supersedes the Phase 1 version.**

These seven questions are what Phase 3 answers and what the Phase 4 case study is structured around. They are locked; changing one requires a dated entry in `docs/decisions.md`, not a silent edit.

---

## What changed in this rewrite, and why it is the most important change in Phase 1.5

The Phase 1 version of this file carried a section under every question titled **"What the answer will show,"** stating each result to the specific number before a single row of data existed. It said Enterprise win rate would fall from roughly 28 percent to roughly 14 percent, and payback would stretch from roughly 13 to roughly 26 months.

Those were not predictions. They were the generator's parameters, restated as expected discoveries. A file that records the answers in advance is the clearest possible evidence that no analysis took place, and it is the first thing a skeptical reader would notice.

Every one of those sections has been deleted. Each question now carries:

- **What this tests**, the analytical move required
- **What would falsify it**, the result that kills the hypothesis
- **Minimum rigor**, the standard the answer must meet to be reportable

**Standing rule for Phases 2, 3, and 4: no expected result may be written into this file, `docs/case_study_scenario.md`, or `docs/data_model.md`. Results are recorded in `docs/findings_summary.md` after they are measured, and nowhere before.**

---

## Question 1: Unit economics overall

What are Anchorpoint's blended CAC, LTV, and CAC payback period, and what does the aggregate view suggest about the health of the business?

**What this tests:** modelling unit economics from raw sales and spend data, including the judgment call in choosing an LTV method.

**What would falsify it:** nothing. This is the baseline the rest of the analysis is measured against.

**Minimum rigor:** CAC computed from `sm_spend` by period, not from an annual constant divided arbitrarily. LTV reported using the 3-year capped method as the headline, with naive `1/churn` shown alongside and explicitly labelled, plus a sentence on why the capped figure is the defensible one.

## Question 2: Segment divergence

How do win rate and CAC payback differ across Enterprise, Mid-Market, and SMB, and is any difference large enough to be distinguishable from noise?

**What this tests:** whether the analyst reports a difference or reports a difference *with uncertainty attached*. At the volumes in this dataset, the second clause is the whole question.

**What would falsify it:** confidence intervals on the segment comparison that overlap. If they overlap, there is no segment story, and the case study says so.

**Minimum rigor:** every headline win-rate figure carries a 95 percent confidence interval. State the n behind each. If a cut is too thin to support a claim, say it is too thin rather than reporting the point estimate alone.

## Question 3: Cause versus symptom, open date versus close date

Does the timing of any Enterprise decline shift when deals are cohorted by `opened_date` instead of `close_date`, and if so, by how much?

**What this tests:** understanding that win rate by close date is a lagging indicator that lags by a full sales cycle. This is the most transferable insight in the project and applies to any business with a long cycle.

**What would falsify it:** the break appearing at the same point under both cohorting methods, which would mean the cause is contemporaneous with the symptom and the sales-cycle-lag explanation is wrong.

**Minimum rigor:** show both cuts side by side. Quantify the lag in months rather than describing it. Enterprise cohorts at quarterly grain only, never monthly; monthly Enterprise cuts do not carry enough volume to be readable and must not be published even if they look tidy.

## Question 4: Where in the process deals fail

At which stage do Enterprise deals that fail spend their time, and what is the mix of loss reasons by segment and period?

**What this tests:** turning "win rate fell" into "deals stall at a specific stage for a specific reason," which is the difference between an observation and a diagnosis. Requires `deal_stage_history` and window functions.

**What would falsify it:** failed Enterprise deals showing no stage concentration, or losses concentrated in `lost_to_competitor` rather than `stalled_no_decision`. Losing head to head is a positioning or pricing problem and points away from execution entirely.

**Minimum rigor:** stage durations compared against the same segment's earlier period and against other segments in the same period. One comparison alone proves nothing.

## Question 5: Does rep capability explain it

Do deals worked by reps with prior enterprise experience outperform deals worked by reps without it, holding segment and deal size constant?

**What this tests:** the causal hypothesis directly. This is the single cleanest test in the case study and the one an interviewer is most likely to probe.

**What would falsify it:** no difference between the two rep groups. That falsifies the mechanism outright and the case study follows the evidence elsewhere.

**Minimum rigor:** control for deal size and region, since experienced reps may have drawn different deals. State the n in each group. Acknowledge that rep experience is confounded with time period, since the inexperienced reps all started on the same date, and say what that confounding does and does not allow you to conclude.

## Question 6: Ruling out the competing explanations

How much of any Enterprise decline is accounted for by each of the four competing explanations: EU competitive entry, the August 2025 price increase, seasonality, and Partnerships channel mix?

**What this tests:** the actual work of diagnosis. Anyone can find a correlation; the job is eliminating the alternatives.

**What would falsify it:** one of the four accounting for most of the decline, in which case that becomes the headline and the rep-capability hypothesis is demoted.

**Minimum rigor:** each explanation addressed explicitly with a number attached, not dismissed in prose. **You do not know in advance which of these are real and which are not, and you must not assume the answer is "none of them."** At least one is expected to carry genuine explanatory weight. Quantify how much, and be equally rigorous about the ones that turn out to be nothing.

## Question 7: Why the dashboard missed it, and what it costs

What does the aggregate view look like across the same period, why would a normal monthly business review have missed any segment-level problem, and what is the budget consequence?

**What this tests:** the insight most likely to land with a hiring manager. A composition shift hiding inside a healthy aggregate is a common and expensive failure mode, and it generalizes far beyond this dataset.

**What would falsify it:** the aggregate view also deteriorating visibly, which would mean the problem was never actually hidden.

**Minimum rigor:** show the aggregate chart a board would have seen next to the segment decomposition. Attach the budget figure: Enterprise share of S&M against Enterprise share of won deals and of ARR. Pair with the pipeline-coverage cut from `sales_pipeline` so the finding is forward looking, not only retrospective.
