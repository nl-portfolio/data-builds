# Neyda Larson — Data Builds

I turn real, messy data into decisions: SQL depth, dimensional modeling, and
BI dashboards built around business questions, not table dumps. This repo is
a set of case studies from real data-analysis builds, with the full pipeline
shown, from raw source through star schema to dashboard.

Most people applying for data roles can talk about SQL and Power BI. This is
a record of me building both on real, unclean, public data: sourcing it,
profiling it, documenting every cleaning decision, modeling a real star
schema, and validating every headline number twice.

- **Location:** Las Vegas, NV (remote)
- **Email:** hello@neydalarson.com
- **Portfolio:** neydalarson.com
- **LinkedIn:** [linkedin.com/in/neydalarson](https://www.linkedin.com/in/neydalarson)
- **Languages:** English (fluent), Spanish (native)

---

## What is in here

| Build | What it is | Detail level |
|---|---|---|
| [Healthcare Operations & Finance Dashboard](case-studies/01-healthcare-ops-finance.md) | A six-page Power BI dashboard on 143,613 real 2024 NY hospital discharge records, built as a validated star schema and read the way a health insurer's medical-economics team would read it | Full technical (pipeline, SQL, and dashboard included) |

The project code, SQL, docs, and dashboard file live in
[`projects/`](projects/).

---

## Toolset

**Data and BI:** SQL (PostgreSQL / DuckDB dialect), dimensional modeling
(star schema), Power BI, DAX, Python and pandas, data profiling and quality
validation.

**Engineering practice:** reproducible pipelines, data dictionaries, dated
decision logs, independent cross-validation of headline metrics.

**Certifications:** Google Data Analytics (2024), Microsoft Data Analytics (2024).

---

## A note on what is shown

The healthcare project runs on real, publicly available, de-identified data
(NY State SPARCS hospital discharge records, no PHI), so nothing here is
redacted: the raw pull script, every SQL layer, every documented cleaning and
modeling decision, the Power BI file, and the write-up are all published in
full. Raw and interim data files are excluded from the repo (see
`.gitignore`) because they are large and exactly reproducible from the public
API; the processed, analysis-ready tables are committed so the results are
visible without re-running anything.
