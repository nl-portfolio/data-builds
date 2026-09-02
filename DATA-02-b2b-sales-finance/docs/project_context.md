# Project Context: B2B Sales Finance

> **Purpose of this file:** this is the working scratchpad for the project's reasoning: data generation methodology, business context, and question selection. The project's actual `README.md` stays concise and reader-facing; this file is where the "why" lives in full.

---

## 1. Why this project, and why this data

This project analyzes a synthetic B2B SaaS sales dataset designed to demonstrate a core diagnostic problem in growth-stage financial reporting: **how healthy aggregate metrics can structurally hide when one segment implodes.**

Most sales leaders review win rate by close date and watch a single blended number. That metric obscures two critical blind spots:

1. **Segment divergence:** One segment can fail while others stay stable, and the average hides the failure.
2. **Reporting lag:** Sales cycles are long (median 5.9 months); a decision made in Q4 closes in Q2. Close-date reviews see the problem a full quarter after it started.

Real data from this scenario would require proprietary access; synthetic mechanism-generated data lets us validate the diagnosis rigorously against ground truth. Every outcome emerges from documented causal mechanisms rather than being specified directly.

## 2. Data generation methodology

The dataset is **mechanism-based**, not random. Published benchmarks (rep experience ramp, buyer complexity levels, deal cycle length) become inputs to a process model; win rates emerge as measured outputs rather than parameters. This approach ensures:

1. **Reproducibility:** Every outcome is traceable to documented mechanisms and benchmarks.
2. **Rigor:** Competing explanations can be ruled out mathematically rather than narratively.
3. **Transparency:** Every assumption and source is logged in `docs/decisions.md`.

### Benchmarks used

- **Win rates by segment:** 28% Enterprise, 30% Mid-Market, 35% SMB, 5% Startup (basis: [Optifai B2B SaaS Win Rates by Deal Size](https://optif.ai/learn/questions/b2b-saas-win-rate-by-deal-size/), 939-company dataset; [Landbase 2026 Win Rate Benchmarks](https://www.landbase.com/blog/win-rate-benchmarks-industry-deal-size-2026))
- **Rep ramp:** Enterprise AEs reach target productivity at 9-12 months (basis: [Blossom Street Ventures SaaS AE Performance Data](https://blossomstreetventures.medium.com/saas-account-executive-performance-data-321a6ceec9db))
- **Churn rates:** 7% Enterprise, 10% Mid-Market, 12% SMB (basis: [Optifai B2B SaaS Churn Benchmarks](https://optif.ai/learn/questions/b2b-saas-churn-rate-benchmark/))
- **CAC payback period:** 12-18 months (basis: [Optifai and getaleph payback benchmarks](https://www.getaleph.com/answers/cac-payback-period-saas-2026))
- **S&M spend range:** 27-45% of ARR for private B2B SaaS (basis: [SaaS Capital Spending Benchmarks 2026](https://www.saas-capital.com/blog-posts/spending-benchmarks-for-private-b2b-saas-companies/))

### The fictional company: Anchorpoint

Anchorpoint is a mid-market B2B SaaS company, ~$14M ARR at the start of the observation window. Key characteristics:

- **Segments:** Enterprise (4 AEs), Mid-Market (3 AEs), SMB (2 AEs), Startup (1 AE, low volume)
- **Sales cycle:** 5.9 months median (Enterprise longer, Startup shorter)
- **Observation window:** 26 months, 900 companies, 2,600 opportunities
- **The trigger event:** Four Enterprise AEs are onboarded simultaneously on 2025-01-01, all inexperienced (month 0 of their ramp). Previous Enterprise business was founder-led.

### Expected outcomes (mechanism-determined, not specified)

Given the mechanism and benchmarks:

- **Pre-trigger (months 1-6):** Enterprise win rate should hover around 28% (founder-led stable state, established process)
- **Post-trigger (months 7-26):** Enterprise win rate should decline as inexperienced reps ramp (expect 15-20 percentage-point decline by month 12 as reps reach competency)
- **Measurement lag:** With a 5.9-month cycle and a 6-month change window, the close-date cohort view of the decline lags the open-date view by roughly one quarter
- **Competing explanations:** Channel mix, pricing, and competitive entry are tested but should show minimal effect; churn and segment mix are held constant

## 3. The seven locked business questions

These questions are locked before any analysis runs, listed in `docs/locked_business_questions.md`. They frame the problem from a growth-stage CFO or VP Sales Operations perspective:

1. **Unit economics by segment:** Which segments clear the 3:1 LTV:CAC threshold for sustainability?
2. **Aggregate masking:** Does segment divergence exceed what blended metrics would show?
3. **Reporting lag:** Why doesn't close-date reporting catch a segment breakage immediately?
4. **Stage-level diagnostics:** Where in the sales process do deals break, and what changes in loss reasons?
5. **Execution vs. market:** Is the segment failure rep-driven or market-driven?
6. **Competing explanations:** What can be ruled out with statistical testing?
7. **Pipeline health:** What's the forward-looking pipeline impact, and how much forecast value is trapped?

## 4. Analysis scope and rigor requirements

- **Grain:** Deals (opportunities), cohorted by open date and close date
- **Minimum sample size:** n=30 for any headline claim; quarterly grain minimum for time-series
- **Confidence intervals:** 95% CI on every effect estimate, reported honestly including width
- **Pre-registered primary comparison:** The 28% → 14% Enterprise decline; p-value and CI pre-locked before analysis
- **Confounder quantification:** Channel, price, competitive entry, and seasonal effects tested with regression, diff-in-diff, and same-period controls
- **Falsification conditions:** Five conditions that would falsify the hypothesis, all explicitly tested

All claims in the case study match the findings notebooks exactly, with n sizes and CIs included.

## 5. Why this matters for hiring

This dataset and its analysis demonstrate:

- **Synthetic data design as a tool:** Designing a mechanism-based dataset to answer a specific business question rigorously
- **Cohort analysis:** Using multiple cohort dimensions (open vs. close date, stage duration, segment) to uncover blind spots
- **Statistical inference:** Confidence intervals, hypothesis testing, and ruling out competing explanations with data rather than intuition
- **Diagnostics over dashboards:** Moving from "the number went down" to "here's why and what it means"

These skills transfer directly to:
- Financial analysis (unit economics, payback, forecast accuracy)
- Growth-stage reporting (segment reporting, leading indicators, pipeline health)
- Operational diagnostics (detecting when processes break vs. when markets shift)

## 6. Sources and references

All benchmarks, churn rates, payback figures, and win-rate comparisons are sourced from published research, listed in `docs/decisions.md`. No figures are asserted; all are traced to a source document with a direct URL.
