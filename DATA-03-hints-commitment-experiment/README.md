# DATA-03: Commitment Statement and Survey Data Quality

A re-analysis of a randomized controlled experiment embedded in the 2024
HINTS 7 survey (National Cancer Institute): did asking respondents to commit
to answering completely and accurately actually improve data quality?

## The question

NCI randomized a subset of HINTS 7 respondents (n = 1,513) to receive a
commitment statement at the start of the survey; the rest (n = 5,765)
received none. NCI's own methodology report says the statement was
"intended to improve response data quality by, for example, reducing item
nonresponse overall and break offs on web," then published only whether the
household response rate differed by arm (it didn't). The data quality
outcomes the experiment was built to move, item nonresponse, break-off, and
response error, are answerable from the same public file and were not
reported. This project answers them.

## The finding

Null, and informative. The commitment statement did not measurably reduce
item nonresponse: statement 1.22% vs. control 1.44%, a difference of -0.21
percentage points, 95% CI [-0.44, +0.01] pp, p = 0.063 uncorrected, p = 0.19
after the pre-registered Holm correction. The experiment could reliably
detect an effect of about 0.3 pp; the observed effect is smaller than that,
so an effect of the size anyone cared about is ruled out, not just
undetected. Break-off and response error are also null, but underpowered:
neither outcome's minimum detectable effect is small enough for its null to
be informative on its own. Full results in
[`outputs/RESULTS.md`](outputs/RESULTS.md) and `outputs/tables/`.

## Why the method matters

Analysis plans are easy to write after seeing which answer looks
interesting. The defense is to write the whole plan down first, commit it
publicly with a timestamp, and only then run it. The plan here was committed
before any arm-split statistic was computed: commit `238c6c8`,
2026-09-02 19:18 UTC. `docs/pre-registration.md` is the plan as committed;
Amendment 1 (commit `87db233`, 2026-09-03) is a dated, disclosed addendum,
not an edit to the original text. The build also surfaced and corrected four
independent defects, an item-level variance bug, a jackknife-formula bug, a
prose-matched dashboard color rule, and an uncorrected-p labeling rule, and
every one of them made a null look like a finding. None reached publication.
The full account is in [`case-study.md`](case-study.md).

## Data

HINTS 7 (2024), National Cancer Institute. Public use file, US federal
public domain, no restriction. n = 7,278 respondents, 515 columns, 368
analyzable survey items. Bundle `HINTS7_R_20250731`
(`hints7_public.rda` + NCI's codebook, methodology report, and annotated
questionnaire), fetched from NCI directly.

## Stack

Python (pandas, numpy) for the analysis pipeline and survey-weighting
engine; R (`survey` package) for an independent statistical cross-check;
Power BI (with Deneb/Vega-Lite visuals) for the scorecard.

## Reproduce

```bash
# 1) fetch the raw HINTS 7 bundle (idempotent)
python3 src/fetch_data.py

# 2) build the analysis frame (one row per respondent, 3 outcome families)
python3 src/load_hints.py
python3 src/build_outcomes.py

# 3) run the validation harness (30 assertions: synthetic fixture, negative
#    control, sanity checks, real-data self-consistency)
python3 src/validate_harness.py

# 4) run the pre-registered analysis (writes outputs/)
python3 src/analysis.py

# 5) optional: cross-check standard errors in R
Rscript src/crosscheck.R
```

`data/raw/` is gitignored (NCI's file, refetch with step 1);
`data/processed/analysis_frame.parquet` is committed so the results are
reproducible without a refetch.

## What is in each doc

- [`case-study.md`](case-study.md): the full write-up, the reconciliation,
  the denominator decisions, the error-direction pattern, the result.
- [`docs/pre-registration.md`](docs/pre-registration.md): the locked plan,
  hypotheses, outcome definitions, tests, MDE grid, and Amendment 1.
- [`docs/reconciliation.md`](docs/reconciliation.md): how the arm-size
  discrepancy between NCI's report and the data file was resolved.
- [`docs/data_dictionary.md`](docs/data_dictionary.md): every outcome
  family, denominator rule, and variable used.
- [`docs/validation.md`](docs/validation.md): the weighting engine's proof:
  synthetic fixture, negative control, R cross-check, published-figure
  reproduction.
- [`docs/decisions.md`](docs/decisions.md): every dated decision across the
  build, append-only.
- [`docs/risks-and-pitfalls.md`](docs/risks-and-pitfalls.md): every risk
  named in advance and its final status.
- [`docs/powerbi_guide.md`](docs/powerbi_guide.md): the scorecard's build
  spec and prohibition-pass checklist (no visual may recompute a statistic
  or imply significance).
- [`outputs/RESULTS.md`](outputs/RESULTS.md): the numeric results, all nine
  pre-registered analyses.
- [`powerbi/`](powerbi/): the Power BI project and exported PDF/PNGs.

## Limitations

Single survey cycle. Self-reported outcomes throughout; item nonresponse and
response error are proxies for data quality, not direct measures of it.
Per-protocol results are confounded with respondent engagement and education
and are reported descriptively, never causally. The secondary outcomes'
underpowered-null classification is a documented convention, not the
pre-registered decision rule itself. Full treatment in
[`case-study.md`](case-study.md#limitations).
