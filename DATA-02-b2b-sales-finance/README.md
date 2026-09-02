# B2B Sales Finance: Diagnosing a Segment Failure Hidden by Healthy Aggregates

A synthetic B2B sales dataset (900 companies, 2,600 opportunities, 26 months) models how healthy aggregate metrics can structurally hide when one segment implodes. Blended win rate stayed healthy (20–32%) while Enterprise segment collapsed (35.2% → 10.2%), invisible to anyone reading the headline.

> **Report philosophy: this README stays concise.** It's the front door, not the full working record. All of the "why" (data generation methodology, first-look findings, and the reasoning behind every choice) lives in `docs/project_context.md` and `docs/decisions.md`. If you want the deep version, start there.

> **Data:** Synthetic, mechanism-generated from published benchmarks (rep experience, buyer complexity, cycle length). No win rate is an input; every outcome is measured. 900 companies, 2,600 opportunities, 26 months. See `docs/project_context.md` for the full methodology, source detail, and data-generation rationale.

---

## What this demonstrates

- **Synthetic data generation for controlled experiments**: designing a mechanism-based dataset where outcomes emerge from underlying processes rather than being specified directly, enabling ground-truth validation.
- **Cohort analysis and time-series diagnostics**: detecting breakpoints in metrics by disaggregating on multiple dimensions (segment, open date vs. close date, sales stage), revealing blind spots in conventional reporting.
- **Statistical inference and hypothesis testing**: confidence intervals on all claims, difference-in-differences tests for causal inference, and systematic ruling out of competing explanations (price, seasonality, channel mix, competitive entry).
- **Unit economics modeling**: LTV:CAC analysis with defensible capping methodology, payback period, CAC, sensitivity analysis on key assumptions.
- **Engineering practice**: reproducible pipeline, clear folder structure, consistent naming, a data dictionary, and a logged record of all design decisions and assumptions.

## Business questions answered

*(Locked 2026-08-21: framed from a growth-stage CFO or sales operations perspective; full rationale in `docs/project_context.md` §4.)*

1. What is the unit economics by segment (Enterprise vs. Mid-Market vs. SMB) and does one segment fail the 3:1 LTV:CAC bar?
2. Does blended unit economics mask divergence at the segment level, and if so, how wide is the gap?
3. Why doesn't close-date reporting catch segment breakage immediately, and what is the measurement-lag effect?
4. Where in the sales process do deals break post-decline, and what is the loss-reason mix shift?
5. Is the segment failure execution-driven (rep capability) or market-driven (competition, price sensitivity)?
6. What competing explanations can be ruled out with the data, and which ones survive statistical testing?
7. What does the pipeline currently look like, and how much forecast value is trapped in late-stage stalled deals?

---

## Key findings

**Enterprise win rate collapsed 25 points (35.2% → 10.2%, n=105 vs. n=315; 95% CI [15.4, 34.8]pp)** while Mid-Market and SMB remained stable. Blended rate stayed in a 20–32% band the entire window, making the failure structurally invisible.

**Reporting lag explains 2-quarter invisibility.** Mean deal cycle is 5.9 months. By close date, the break landed in Q2; by open date, it landed in Q4. Leadership teams reading Q2 closed deals discovered the problem a full quarter after it started, compounding damage.

**Deals stall, not crash faster.** Proposal stage duration: 34.4 → 57.5 days. Negotiation: 36.5 → 78.7 days. Loss reason shifted from "lost to competitor" (41.2% → 9.9%) to "stalled, no decision" (0% → 20.1%). This is a process failure, not a market failure.

**Rep experience explains the gap** (15.4pp, CI [1.5, 29.3]pp, n=38 experienced vs. n=277 inexperienced, same-period control). Inexperienced reps added post-decline carry the collapse; experienced reps holding steady show execution matters.

**Five competing explanations tested and ruled out:** Mid-Market/SMB decline (did not happen), region-specific decline (did not happen; effect shows everywhere), competitor pressure alone (losses to competitors actually fell), no rep-experience gap (gap was found and clears zero), and pre/post interval crossing zero (it does not, with wide margin).

---

## Architecture

```
companies.csv, deals.csv, →   Python generation library   →   Fact and dimension   →   Notebooks & analysis   →   Findings
customers.csv, sales_reps.csv   (mechanism-based, no        tables (CAC, LTV,          (pandas, NumPy,            (with
                                 win-rate parameter)         payback, stages)           statistical tests)         confidence intervals)
```

- **Engine:** Python, pandas, NumPy (synthetic data), Jupyter notebooks (analysis).
- **Grain:** `fact_opportunities` = one sales opportunity (2,600 rows).
- **Dimensions:** `dim_company`, `dim_sales_rep`, `dim_segment` (Enterprise / Mid-Market / SMB), temporal dimensions (open date, close date, cohort).
- **Analysis layers:** Unit economics marts (LTV:CAC by segment, payback), stage-duration analysis (by sales stage and period), loss-reason breakdown, cohort-based time-series (open vs. close date).
- **Validated:** All findings include 95% confidence intervals. Competing hypotheses systematically tested and reported honestly (including one suggestive, non-confirmed finding: EU competitive entry).

## How to reproduce

From the project root:

```bash
pip install pandas numpy jupyter

# 1) Generate the synthetic data (mechanism-based, not random)
python3 src/generate_data.py

# 2) Validate the dataset structure and distributions
python3 src/validate_dataset.py

# 3) Explore the data and reproduce the analysis
jupyter notebook notebooks/01_eda.ipynb
jupyter notebook notebooks/02_unit_economics.ipynb
jupyter notebook notebooks/03_diagnostics.ipynb
```

All findings in these notebooks match the case study. All figures include 95% confidence intervals.

## Repository layout

```
b2b-sales-finance/
├── README.md
├── case-study.md
├── .gitignore
├── src/
│   ├── generate_data.py        # synthetic data generation (mechanism-based, benchmarks-driven)
│   ├── validate_dataset.py     # data-quality validation and distribution checks
│   └── phase3_lib.py           # reusable statistical functions (LTV:CAC, CIs, tests)
├── sql/                        # (optional, if using a database layer)
│   ├── 01_staging/
│   ├── 02_dimensions/
│   ├── 03_facts/
│   └── 04_marts/
├── data/
│   ├── raw/                    # source CSV files (companies, deals, customers, etc.)
│   └── processed/              # analysis-ready tables and marts
├── notebooks/
│   ├── 01_eda.ipynb            # exploratory data analysis
│   ├── 02_unit_economics.ipynb # LTV:CAC, payback period, segment analysis
│   ├── 03_diagnostics.ipynb    # statistical hypothesis tests, competing explanations
│   └── figures/                # all PNG charts and visualizations
├── outputs/                    # exported dashboard screenshots and mockups
├── docs/
│   ├── project_context.md      # data-generation methodology, business context, locked questions
│   ├── data_dictionary.md      # every table/column, type, meaning, usage
│   ├── decisions.md            # every assumption and choice, dated (LTV cap, churn rate, etc.)
│   ├── data_model.md           # entity relationships, grain, foreign keys
│   ├── findings_summary.md     # all quantitative findings with n sizes and CIs
│   ├── locked_business_questions.md  # the 7 locked questions that drove the analysis
│   └── case_study_scenario.md  # five falsification conditions and what would change them
└── docs/
```

## Data generation notes

The dataset is mechanism-generated rather than purely random. Rep experience, buyer complexity, and cycle length come from published benchmarks; win rates emerge from those factors rather than being entered as parameters. This approach lets us:

1. **Validate against ground truth** — we know exactly why outcomes occurred
2. **Test the diagnosis rigorously** — competing explanations can be ruled out mathematically
3. **Make assumptions visible** — every choice (LTV cap at 3 years, churn at 8%, etc.) is documented and sensitivity-tested

See `docs/project_context.md` for the full methodology.
