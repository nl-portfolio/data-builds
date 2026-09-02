# Decisions Log

A dated record of assumptions and modeling choices. This is the habit that makes
analytics reproducible and reviewable.

---

**2026-07-07: Synthetic data over real data.**
Used a seeded Python generator rather than real records to avoid any privacy
exposure and keep the repo fully publishable and reproducible. Synthea is noted
in the README as an optional higher-realism swap.

**2026-07-07: DuckDB as the SQL engine.**
Chosen for zero setup (single file, no server), PostgreSQL-compatible syntax,
and strong analytical performance. The same SQL translates cleanly to Postgres,
Snowflake, or BigQuery with minor dialect changes.

**2026-07-07: Two fact tables at different grains.**
`fact_claims` (one row per claim line) is the source of truth for finance.
`fact_encounters` (one row per visit) carries rolled-up claim measures so
operational analysis doesn't need to re-aggregate claims every time. The two
share conformed dimensions (date, patient, provider, payer).

**2026-07-07: Integer date key (`YYYYMMDD`).**
Standard data-warehouse practice: a compact, sortable surrogate key for the date
dimension that joins efficiently and reads clearly.

**2026-07-07: Data-quality guards in staging.**
Rows missing `encounter_id`/`patient_id` are dropped, and claims with a negative
`billed_amount` are excluded. With the current generator these filters remove
zero rows, but they document the intended contract and would catch bad data if
a real source were swapped in.

**2026-07-07: Marts committed, raw/interim gitignored.**
Raw CSVs and the DuckDB file are regenerable, so they're excluded from version
control. The small processed marts are committed so reviewers can see results
without running the pipeline.

**2026-07-07: `age_years` computed against the current date.**
Patient age is derived at query time from `birth_date`, so it stays current on
each rebuild. Age bands (`0-17`, `18-34`, `35-49`, `50-64`, `65+`) follow common
healthcare reporting groupings.

---

### Reboot: real data, payer perspective

**2026-07-07: Reversed the earlier "synthetic data over real data" decision.**
Supersedes the 2026-07-07 entry above. Decided to rebuild the project on a
real, publicly available, de-identified dataset instead, specifically to
demonstrate working with data whose shape and quality issues weren't
engineered by us, a core part of the target job posting's "data quality"
pillar that a clean seeded generator couldn't actually prove.

**2026-07-07: Chose NY SPARCS over CMS Medicare data and Kaggle cleaning
datasets.** SPARCS (NY State hospital discharge records) is real government
data, genuinely messy at the field level, large enough to be credible, and
maps directly onto an operations/finance schema (charges, costs, LOS, payer,
facility). CMS Medicare provider data was ruled out as already fairly clean/
tabular (weaker cleaning story). A Kaggle "cleaning practice" dataset was
ruled out as an arbitrary upload with no institutional credibility behind it.

**2026-07-07: Scoped to one region, one year: `Capital/Adirondacks`, 2024
(143,613 rows).** The full statewide file is ~2.2M rows (~1.5-2GB), too large
to hand-download and sync through OneDrive, and more scale than a portfolio
piece needs. Pulled directly from the state's Socrata API filtered to
`health_service_area = 'Capital/Adirondacks'`, discharge year 2024. This
region was chosen over other regions of similar size because it contains a
genuine mix of one large academic medical center, mid-size community
hospitals, and several small rural hospitals, see
`docs/project_context.md` for the full regional rationale. Trade-off: a
single year means no year-over-year trend analysis is possible from this file
alone (`discharge_year` is constant); documented so the eventual dashboard
doesn't overclaim.

**2026-07-07: Reframed the project from hospital finance to a health
insurer's (payer) perspective.** Same underlying data, different lens: cost
concentration by severity, charge-to-cost ratio (markup), payer-mix/Medicaid
exposure, length of stay as a utilization-management signal, and urban-vs-
rural network adequacy, rather than a hospital's own revenue-cycle view.
Chosen because it's a more differentiated portfolio angle and because the
region's real Medicaid-funding exposure (documented in
`docs/project_context.md` §2) makes the payer framing substantively
meaningful, not just a stylistic choice. Business questions locked the same
day, see README "Business questions answered" and `docs/project_context.md`
§4.

**2026-07-07: No unique row/patient identifier exists in this file.**
Flagged as an open decision rather than resolved yet: apparent "duplicate"
rows may represent genuinely distinct real patients with matching recorded
characteristics, not copies. A mechanical dedupe would risk deleting real
cases. The actual handling approach will be decided during the full
profiling pass and documented here when settled.

---

### Profiling pass: findings and resolved decisions

Full profile run 2026-07-07 on all 143,613 rows / 33 columns. Four decisions
resolved below; see `docs/project_context.md` for the full profiling
write-up (nulls, cardinality, categorical breakdowns).

**2026-07-07: Payer field, coalesce to first non-null.**
59 rows are missing `payment_typology_1`. Of those, 33 actually have data in
`payment_typology_2` or `_3` (an ordering quirk, not a true gap) and 26 are
missing all three payer fields. Decision: treat the first non-null of
`payment_typology_1/2/3` as the effective primary payer, so the 33 rows keep
their real payer data instead of being misclassified as unknown. The
remaining 26 rows are genuinely unknown-payer and stay that way.

**2026-07-07: `length_of_stay`, "120+" resolved to a floor value with a
censoring flag.** 57 rows contain the literal text `"120+"` instead of a day
count (SPARCS's own bucketing of very long stays), out of an otherwise clean
1-119 day numeric range. Decision: cast these to `120` and add a boolean
`is_los_censored` column, rather than dropping the rows or nulling the
field. These are plausibly among the highest-cost, highest-severity
discharges, which matters directly for the cost-concentration business
question, so they stay in every analysis with a visible caveat rather than
being silently excluded or silently understated.

**2026-07-07: Exact duplicate rows, kept, not deduped.**
70 rows sit in exact full-row duplicate groups (36 would be removed by a
keep-first dedupe, 0.05% of the data). Since SPARCS strips all patient/row
identifiers for privacy, an "exact duplicate" here cannot be distinguished
from two different real patients who happen to share every recorded,
fairly-coarse categorical field. Decision: keep all rows as published.
Deduping without a way to confirm true duplication risks silently deleting
real discharges.

**2026-07-07: Alice Hyde Medical Center, two facility IDs merged into one
`dim_facility` record.** `facility_name` has 24 distinct values but
`permanent_facility_id` has 25, traced to Alice Hyde Medical Center
(Franklin County) appearing under two IDs (`000325`, operating certificate
`1624000`, 445 rows; and `015485`, certificate `1624700`, 390 rows).
Investigated two hypotheses: (1) the 2016 UVM Health Network acquisition,
ruled out, wrong year, doesn't explain a mid-2024 split; (2) whether the two
IDs represent clinically distinct populations, ruled out, the two groups
have near-identical case mix (both dominated by pneumonia/heart failure/
respiratory failure), age skew (~55-60% age 70+ in both), and average charges
(~$16-17K in both). The exact administrative cause (likely a NY DOH
re-certification event) couldn't be confirmed from public sources, but the
clinical evidence strongly supports one physical hospital. Decision: merge
both IDs into a single `dim_facility` row keyed on `facility_name` (835
combined discharges), retaining both source `permanent_facility_id` and
`operating_certificate_number` values as an array/note on that row so the
source split stays traceable.

---

### Star schema design

Full schema (ER diagram, table grains) lives in `docs/data_dictionary.md`.
Three design forks resolved here:

**2026-07-07: Demographics kept flat on `fact_discharges`, no
`dim_patient_profile`.** Age/gender/race/ethnicity describe the discharge,
not a stable patient (there's no patient ID in this file), so a separate
patient-profile dimension would be normalizing fields that don't represent
a real recurring entity. Simpler model, fewer joins, more honest about what
the data actually is.

**2026-07-07: Added `payer_category` to `dim_payer`.** Groups the 9 raw
`payment_typology_1` labels into Government / Commercial / Self-Pay / Other,
directly supporting business question #3 (payer-mix/Medicaid exposure) as a
one-level rollup instead of a re-derived CASE statement in every query.
Caveat logged in the data dictionary: `Managed Care, Unspecified` is
categorized `Commercial` by default but can sometimes represent Medicaid
managed-care in SPARCS data, worth revisiting if that category turns out
to carry a lot of volume.

**2026-07-07: No `dim_date`; `discharge_year` dropped from the model
entirely.** This public file has no exact admission/discharge date, only
the constant `discharge_year = 2024`. A date dimension has nothing to key
on, and a 100%-constant column has zero analytical value, so it's dropped
rather than carried through every table. The single-year scope is stated
once (README/dashboard) instead.

**2026-07-07: `dim_procedure` uses a `"NONE"` sentinel row instead of a
nullable FK.** 38.7% of discharges have no CCSR procedure code. Rather than
allowing `procedure_key` to be null on the fact table, a sentinel
`"NONE"` row was added to `dim_procedure` so every fact row has a valid FK,
standard practice for optional dimension relationships.

**2026-07-07: Scoped out a full payer bridge table.** ~30% of discharges
have 2+ payers (`payment_typology_2`/`_3` populated). Modeling all payers
per stay properly would need a bridge/associative table, which is real
complexity for a business-question set that only needs primary-payer
exposure (question #3). Raw secondary/tertiary labels are retained directly
on the fact table for anyone who needs them later; a bridge table is noted
as a possible extension, not built now.

---

### SQL layer build: one real bug found and fixed during first run

**2026-07-07: MDC is not a stable attribute of DRG, split into its own
dimension.** The first build of `dim_drg` carried `apr_mdc_code`/
`apr_mdc_description` as attributes of the DRG (324 codes), which produced
390 distinct rows instead of 324 and fanned `fact_discharges` out to
157,194 rows (more than the 143,613 raw rows) when joined. Root cause,
confirmed by inspection: six APR-DRG codes, 004 and 005 (tracheostomy with/
without prolonged mechanical ventilation), 009 (ECMO), and 950/951/952
("O.R. procedure unrelated to principal diagnosis," extensive/moderate/
non-extensive), are defined by the APR-DRG grouper methodology itself to
span many different MDCs, since a patient can need a tracheostomy or an
unrelated procedure regardless of their underlying diagnosis. This is
correct real-world grouper behavior, not a data error. Fix: `dim_mdc` is
now its own independent dimension (26 rows), joined onto `fact_discharges`
directly from the staging layer rather than through `dim_drg`. Re-validated
after the fix: `fact_discharges` = 143,613 rows (matches raw exactly), zero
orphan foreign keys across all six dimensions.

**2026-07-07: Pipeline validated end-to-end.** `src/run_pipeline.py` runs
staging → dimensions → fact → marts against the real SPARCS extract with
automated checks (staging/fact row counts must equal the raw row count;
zero orphan FKs across all dimension joins) and both pass. All six marts
spot-checked: percentage columns sum to 100 where expected (severity cost
shares, regional volume shares, per-facility payer-mix shares all confirmed).

---

### Power BI guide rewrite: design decisions

**2026-07-07: Power BI model built on the star schema with live DAX, not on
the marts.** The six `mart_*` tables are loaded into the `.pbix` for
validation only (known-correct numbers to spot-check DAX against), not as
the reporting layer. Reason: the marts are six unrelated flat tables, each
built to answer one question in isolation, so loading them directly would
mean a filter clicked on one page has no effect on any other page. Building
measures over `fact_discharges` plus the six dimensions instead means every
page cross-filters every other page through one shared model, which is both
more useful to a reviewer and a truer demonstration of the Power BI
data-modeling and DAX skills this project is meant to prove.

**2026-07-07: Dashboard paginated as one overview page plus one page per
locked business question (six pages total), not fewer thematic pages.**
The five questions genuinely call for different visual shapes (a Pareto
curve is not the same kind of answer as a scorecard matrix), so each gets
full-page focus rather than being crowded together.

**2026-07-07: Three global, cross-page slicers: `facility_name`,
`sub_region`, `apr_severity_of_illness`.** These are the two lenses the
whole project is framed around (facility/region) plus the clinical control
variable (severity) that most of the five questions need held constant to
be a fair comparison. `payer_category` (Q3) and
`emergency_department_indicator`/`type_of_admission` (Q5) are page-specific
filters instead, since they're only meaningful on the pages where that
breakdown is the point.

**2026-07-07: DRG-level Pareto ranking uses `ALL`, the severity-tier Pareto
ranking uses `ALLSELECTED`.** Severity cost concentration is meant to stay
reactive to the global facility/region slicers (a reviewer filtering to one
sub-region should see that subset's own Pareto curve), so it uses
`ALLSELECTED`. The DRG ranking instead needs to stay fixed across the full
324-DRG population regardless of slicer state, because it sits on the same
visual as a Top N display filter, and a Top N visual filter combined with an
`ALLSELECTED`-based running total is a known DAX conflict. `ALL` keeps the
DRG ranking and its cumulative-% denominator correct regardless of what's
displayed, matching how the SQL mart computed it originally (a static,
unfiltered calculation).

**2026-07-07: No new "facility size" or "academic/community/rural" category
invented for the dashboard.** `dim_facility` has no such attribute, and
adding one would be an undocumented business rule. Instead, `Total
Discharges` (a real column, not a new category) is used as a bubble-chart
size to represent facility size, on the Q2 charge-to-cost-ratio page.

**2026-07-07: Two scatter/bubble visuals chosen specifically to avoid
proxy categories: Q2's markup-vs-volume bubble chart, and Q3's
Medicaid-share-vs-volume scatter chart.** The latter is the direct visual
answer to question 3's second half (which facilities are both
Medicaid-concentrated and small enough to be financially exposed): plotting
`Medicaid Share` against `Total Discharges` shows this directly from real
columns, rather than needing a new "at risk" flag that isn't in the data
dictionary.

---

### Power BI dashboard build: findings from the actual build session

Everything below comes from actually building the `.pbix` in Power BI
Desktop, not from planning. Several of these are genuine tool/DAX gotchas
worth keeping on record so they don't get rediscovered the hard way on a
later project.

**2026-07-09: Disabled "Autodetect new relationships after data is loaded"
before importing anything.** Found under File > Options and settings >
Options > Current File > Data Load. Reason: several `mart_*` tables carry
columns with the exact same names as columns in the star schema
(`facility_name`, `sub_region`, `apr_severity_of_illness`, and others),
since the marts were deliberately built as flat, self-contained validation
copies (see "Power BI model built on the star schema with live DAX, not on
the marts" above). With autodetect on, Power BI could silently create
relationships between a mart and a dimension or fact table on first load,
which would break the documented "marts stay unrelated" design without any
visible warning. Left off for the rest of the build.

**2026-07-09: `Get Data > Folder` is the wrong connector for this project,
confirmed by trying it.** Pointing the Folder connector at `data/processed/`
returns a file-listing table (`Name`, `Extension`, `Folder Path`, `Date
modified`, and a binary `Content` column), not the parsed CSV data. The
Folder connector's "Combine" step only works when every file shares one
schema (its intended use is many files with identical columns, like twelve
monthly exports), which doesn't apply here since the 13 files (six
dimensions, the fact table, six marts) all have different schemas. Corrected
by importing each file individually with `Get Data > Text/CSV`, exactly as
`docs/powerbi_guide.md` §1 already specified. No change to the guide needed
here, just a confirmed reason not to shortcut it with a folder import.

**2026-07-09: A Power Query parameter for the base folder path was set up,
then not carried through.** To keep the 13 source queries portable if this
repo ever moves off this machine, a `ProcessedDataFolder` text parameter was
created (pointing at the absolute `data/processed` path) with the intent of
having every query's `Source` step reference it instead of a hardcoded path.
The parameter was not saved before the CSVs were reloaded manually with
plain hardcoded paths, so the model currently does not use it. Decision:
leave it as-is rather than retrofit 13 already-working queries; revisit only
if the repo folder actually moves or gets cloned elsewhere, at which point
re-adding the parameter and editing each `Source` step is a cheap fix.

**2026-07-09: `ALLSELECTED` does not strip a visual-level filter on the same
column, discovered while building the Page 2 "Extreme-tier cost share" KPI
card.** The original plan (`docs/powerbi_guide.md` §5, Page 2) called for a
card showing `[Pct of Total Cost (Severity)]` with a visual-level filter
pinning `apr_severity_of_illness` to `"Extreme"`. This always returned
exactly 1.00 no matter which severity value was filtered to. Root cause:
`[Total Costs (Severity Context)]`'s denominator uses
`CALCULATE ( [Total Costs], ALLSELECTED ( fact_discharges[apr_severity_of_illness] ) )`,
and `ALLSELECTED` treats a filter added directly to a visual (via the
Filters pane) the same as an externally selected context, such as a slicer,
so it does not remove it. That means both the numerator and the denominator
ended up scoped to the same single filtered category, which always cancels
to 1.00 regardless of which category is chosen. This is not a bug in the
original measure: `[Pct of Total Cost (Severity)]` is correctly designed for
its intended use (the Page 2 Pareto chart, where severity sits on the
chart's own axis and `ALLSELECTED` is exactly what's wanted, so the running
total stays reactive to the global facility/region slicers). It simply
cannot be reused with a hardcoded visual-level filter to isolate one
category.

Fix: added a new, dedicated measure that hardcodes both sides of the ratio
directly in DAX instead of depending on a visual filter:

```DAX
Extreme Tier Cost Share =
DIVIDE (
    CALCULATE ( [Total Costs], fact_discharges[apr_severity_of_illness] = "Extreme" ),
    CALCULATE ( [Total Costs], ALL ( fact_discharges[apr_severity_of_illness] ) )
)
```

Verified against the raw data (`fact_discharges.csv`): Extreme-tier total
costs are $559,246,582.62 against a grand total of $2,265,824,365.27, a
24.68% share, matching this measure exactly (and matching
`mart_severity_cost_concentration`'s rounded 24.7%). The general pattern:
any future KPI card that needs to pin one hardcoded category value (rather
than showing every category, as the Pareto chart does) should use this
"hardcode both branches of a `CALCULATE`" pattern, not a Filters-pane filter
combined with an `ALLSELECTED`-based share measure.

**2026-07-09: Several column names repeat, identically, across
`fact_discharges` and multiple `mart_*` tables, and Power BI does not
distinguish them for you when you drag a field.** `apr_severity_of_illness`,
for one example, exists in `fact_discharges`, `mart_severity_cost_concentration`,
and `mart_los_by_facility_severity`. Since the marts are deliberately left
unrelated to the star schema, dragging the wrong table's copy of a
same-named column into a Filters pane produces a filter that silently has
zero effect (there's no relationship for it to propagate through), rather
than an error. Symptom observed: a visual-level filter that showed as
correctly applied ("is Extreme") in the Filters pane, on a card that never
changed value no matter what was selected. Whenever a field is dragged into
a Filter, Value, or Axis well anywhere in this model, confirm which table it
came from (hover for the tooltip, or check the Fields pane's table
grouping) before assuming it's wired to the right place.

**2026-07-09: Reviewed an external Power BI dashboard template (a generic
hospital-admissions demo) for design ideas; adopted nothing from it.** Two
reasons. First, it leans on year-over-year percentage deltas and
month-by-month trend lines, both of which need a date dimension and
multiple time periods; this project deliberately has neither (see "No
`dim_date`" above), so replicating that pattern would mean implying a
trend-analysis capability the data doesn't support. Second, it includes an
invented "Normal / Inconclusive / Abnormal" reading classification with no
stated rule behind it, exactly the kind of undocumented business rule this
project has consistently avoided (see the facility-size note above). The
one pattern it shares with this dashboard, a heat-shaded matrix table, was
already independently planned for Page 6 and needed no change.

---

### Dashboard scope upgrade: synthesis over sprawl

Following a portfolio-value review conducted 2026-07-09 (a review of the
analytical framing and dashboard plan, not a rebuild of the SQL layer or star
schema), several additions were locked. None of the five original locked
business questions were removed or renumbered; everything below extends them
or adds a synthesis layer on top. The original question list in
`docs/project_context.md` §4 stays intact as the project's core contract; see
that file for a pointer to this section rather than a rewrite of the
questions themselves.

**2026-07-09: Dashboard stays at six pages; new elements are folded into
existing pages, not appended as new ones.** A draft of this review considered
two new pages (a synthesis/risk-score page and a recommendations page).
Decision: reject that in favor of upgrading Page 1 from a plain "Overview"
into an "Executive Summary" that carries both the facility risk ranking and a
short recommendations panel. Reasoning: a six-page dashboard that opens with a
genuine decision-ready synthesis reads as more senior than an eight-page
dashboard that simply has more pages; page count was not the thing that
needed to grow.

**2026-07-09: New measure, Facility Risk Score, an equal-weighted percentile
composite.** Combines three signals already in the model, each converted to a
0-100 percentile rank across the 24 facilities, then averaged:

- Medicaid dependency (Medicaid share of discharges at the facility level,
  higher share ranked as higher risk)
- Size fragility (total discharges at the facility level, inverted so the
  smallest facilities rank as highest risk)
- Cost complexity (Extreme-severity cost share at the facility level, higher
  share ranked as higher risk)

Equal weighting was chosen deliberately over an arbitrary weighted formula: it
follows the same logic as composite indices like the CDC's Social
Vulnerability Index, transparent and defensible because every component
counts the same, rather than asserting a business-judgment weighting the data
itself can't justify. Caveat, stated plainly rather than hidden: a real
payer's medical-economics team would likely weight these by strategic or
actuarial priority; equal weighting here is a documented simplifying
assumption, not a claim that it is the "correct" weighting.

Computed directly from `fact_discharges.csv` and `dim_facility.csv`
(2026-07-09, ahead of the actual DAX build, so the dashboard has a
known-correct target to validate against, the same practice as §7a in
`docs/powerbi_guide.md`). Top of the ranking:

| Facility | Sub-region | Discharges | Medicaid Share | Extreme-Tier Cost Share | Risk Score |
|---|---|---:|---:|---:|---:|
| Nathan Littauer Hospital | Mohawk Valley | 2,282 | 30.1% | 17.0% | 63.8 |
| St. Mary's Healthcare - Amsterdam Memorial Campus | Mohawk Valley | 259 | 36.3% | 1.0% | 63.8 |
| St. Peter's Hospital - SPARC | Capital District | 266 | 78.9% | 0.4% | 63.8 |
| Ellis Hospital | Capital District | 9,552 | 19.2% | 33.2% | 62.3 |
| Samaritan Hospital | Capital District | 9,912 | 27.0% | 26.3% | 60.9 |

Lowest-risk end, for contrast: Albany Medical Center Hospital (33.3; the
region's largest facility by volume, so simply too large to score as fragile
despite a high Extreme-tier cost share) and Saratoga Hospital (37.7; high
markup but low Medicaid dependency and mid-size volume). The three-way tie at
the top (63.8) is expected behavior of a percentile-based composite at n=24,
not a bug; show it as a tie on the dashboard rather than forcing an
arbitrary tiebreak.

**2026-07-09: Charge-to-Cost Ratio's narrative reframed; the measure itself is
unchanged.** The original framing (`docs/project_context.md` §4, Q2) implied a
payer cares about hospital markup as its own cost exposure. That is not quite
accurate: payers negotiate contracted rates, not chargemaster billed charges,
so this measure is more precisely a hospital pricing-behavior / price-
transparency signal, most directly relevant to self-pay patients,
out-of-network claims, and price-transparency-rule contexts, not the payer's
own reimbursement cost. No DAX or KPI changes, only the caption/narrative on
Page 3 changes. This supersedes the implicit framing in the original Q2
wording without editing that wording itself; the locked question list stays
as written, the correction lives here and in the Page 3 build note in
`docs/powerbi_guide.md`.

**2026-07-09: External benchmark added to Page 3, two independently sourced
reference points.** Cited rather than invented, since an internal-only number
doesn't mean much to a reviewer without something to compare it to:

- National average cost-to-charge ratio, around 0.32 in 2020 (CMS-based
  cost-to-charge ratio trend data), equivalent to a charge-to-cost ratio near
  3.1x.
- Bai and Anderson, *Health Affairs* (2015, using 2012 Medicare cost report
  data): the typical US hospital charged 3.4x Medicare-allowable cost (mode
  2.4x).

This project's own portfolio-wide Charge to Cost Ratio (2.9544) sits at or
slightly below both reference points, worth stating directly on the
dashboard: this region's hospitals mark up charges somewhat less aggressively
than the national average. Caveat, logged rather than smoothed over: the two
benchmarks use different denominators (Medicare-allowable cost vs. a
hospital's own reported cost-to-charge ratio) and different vintages (2012
and 2020) than this project's 2024 SPARCS-based figure, so the comparison is
directional, not a precise apples-to-apples statistic.

**2026-07-09: Per-capita utilization measure added to Page 6, sourced from
Census Bureau / ACS county population estimates (2023-2024 vintage).**
Sub-region totals, summed from county-level figures not previously in this
file (Capital District's ~906,000 was already documented from earlier
regional research):

| Sub-region | Population | Source counties |
|---|---:|---|
| Capital District | ~906,000 | Albany, Schenectady, Rensselaer, Saratoga (already documented) |
| North Country/Adirondack | ~227,450 | Warren 65,288 + Clinton 78,493 + Essex 36,973 + Franklin 46,696 |
| Central NY/Catskill Foothills | ~194,914 | Otsego 60,100 + Delaware 44,410 + Schoharie 30,105 + Columbia 60,299 |
| Mohawk Valley | ~101,721 | Montgomery 49,648 + Fulton 52,073 |

Important caveat, carried directly from the existing `hospital_county` field
note (`docs/project_context.md` §2): this is discharges per capita of the
sub-region **where the hospital is located**, not per capita of the patients
who live there, since no patient-residence field exists in this data. This
matters most for Capital District, which hosts the region's academic medical
center and likely draws referred patients from the surrounding rural
sub-regions, inflating its per-capita figure beyond what its own residents
actually use. Label this measure "discharges per 10,000 population, by
hospital location" on the dashboard, not "utilization by residents of," to
avoid overclaiming.

Computed rates (discharges per 10,000 population): Capital District 1,080.8;
North Country/Adirondack 1,058.9; Central NY/Catskill Foothills 783.6;
Mohawk Valley 624.1.

Notable finding worth calling out in the write-up: Mohawk Valley has both the
lowest per-capita inpatient utilization of any sub-region **and** (per the
existing `mart_regional_utilization`) the highest ED-utilization share
(71.5%). Read together this is a sharper story than raw ED% alone: Mohawk
Valley residents are hospitalized less often overall, but when they are, they
disproportionately arrive through the ED rather than through elective or
scheduled care, a pattern more consistent with constrained non-emergency
access than with "a sicker population" or "more utilization overall."

**2026-07-09: `apr_risk_of_mortality` added as a secondary cross-cut on
Page 2 (Q1).** Severity of illness and risk of mortality are related but
distinct APR classifications on the same 5-tier scale, and can diverge for a
given condition (a surgical case can be high-severity, low-mortality-risk; a
frail medical patient can be the reverse). Crossing the two surfaces which
high-cost conditions are utilization-management candidates (high cost, low
mortality risk) versus unavoidable complex care (high cost, high mortality
risk), a more useful cut than severity alone for a payer audience.

**2026-07-09: `patient_disposition` added as a supporting cross-cut on
Page 5 (Q4).** Moves the "post-acute access" claim from an inference drawn
only from length of stay to direct evidence of where patients actually go
after discharge. Open item, not resolved in this session: the 19 raw
`patient_disposition` values need to be reviewed and grouped into a small
number of categories (for example, home, post-acute facility, hospice or
expired, other) before this can be built; that grouping wasn't finalized here
since the full list of 19 values wasn't re-enumerated during this review,
flagged as the first thing to do when building this cross-cut.

**2026-07-09: Small-n statistical-stability flag, threshold set at 1,000
annual discharges.** Nine of the 24 facilities fall under 1,000 discharges
(Margaretville 100, O'Connor 180, Delaware Valley 180, St. Mary's Amsterdam
259, St. Peter's SPARC 266, St. Peter's Addiction Recovery 397, Cobleskill
Regional 455, UVM Elizabethtown 736, Alice Hyde 835), a natural break in this
dataset since the remaining 15 facilities are all comfortably above it (next
lowest is A.O. Fox Memorial at 1,399). Any per-facility ranked or ratio visual
(Page 1's Facility Risk Score table, Page 3's markup bubble chart) should
visibly flag these nine as low-volume, since a ratio computed on a few hundred
discharges is far less stable than one computed on tens of thousands. The
threshold is a judgment call grounded in this dataset's own distribution, not
a universal statistical rule; documented as such rather than presented as a
formula.

---

### Page 1 Executive Summary build: two real DAX bugs found in the Facility
Risk Score composite, plus the population table and remaining measures added

**2026-07-09: `_SubRegionPopulation` reference table and its relationship
built in Power BI.** A 4-row manually-entered table (`sub_region`,
`population`), per `docs/powerbi_guide.md` §1, with a single relationship
`dim_facility[sub_region]` (many) → `_SubRegionPopulation[sub_region]` (one),
active, single-direction. This is a standalone reference table, not part of
the star schema proper; see `docs/data_dictionary.md` for its entry.

**2026-07-09: All 11 remaining measures from `docs/powerbi_guide.md` §4.8-4.11
added to `_Measures`**, including `Facility Medicaid Share`, `Facility Extreme
Cost Share`, the three percentile measures, `Facility Risk Score`,
`Sub-Region Population`, `Discharges per 10k Population`, the two national
charge-to-cost benchmark measures, and `Is Low Volume Facility`.

**2026-07-09: DAX bug #1, blank `Facility Risk Score` on every row except the
grand total, found while building the Page 1 table visual.** The three
percentile measures (`Medicaid Dependency Percentile`, `Size Fragility
Percentile`, `Cost Complexity Percentile`), copied verbatim from
`docs/powerbi_guide.md` §4.8, compute `FacilityCount` as
`DISTINCTCOUNT ( dim_facility[facility_name] )` with no `ALL()` wrapper. In a
facility-row context, such as a table visual with `facility_name` on it, this
evaluates to 1 (just the current row), so
`DIVIDE ( FacilityRank - 1, FacilityCount - 1 )` becomes a division by zero on
every row, and Power BI renders that as blank. Only the unfiltered grand-total
row (no row context) computed a real number. Diagnosed by adding the three
percentile measures as temporary debug columns on the table and observing all
rows blank except Total. Fix: wrapped `FacilityCount` in
`CALCULATE ( DISTINCTCOUNT ( dim_facility[facility_name] ), ALL ( dim_facility ) )`
in all three measures, so the count is always computed over the full,
unfiltered facility population regardless of row context. **This bug exists
in `docs/powerbi_guide.md` §4.8 as written and should be corrected there** so
a future build (or a reviewer following the guide) doesn't hit it again.

**2026-07-09: DAX bug #2, Facility Risk Score values exceeding 100 and a false
three-way tie at exactly 100.00, found immediately after fixing bug #1.** Once
`FacilityCount` used `ALL ( dim_facility )` (the whole table), the RANKX table
argument in the same three measures still used
`ALL ( dim_facility[facility_name] )` (one column only). The Page 1 table
visual has both `facility_name` and `sub_region` in it, so its row context
filters both columns of `dim_facility` at once; clearing only the
`facility_name` filter leaves the `sub_region` filter in place, so RANKX and
FacilityCount were scoped to just the current row's sub-region (as few as 3
facilities in Mohawk Valley) instead of all 24. That produced impossible
percentile values (up to 150 on a 0-100 scale) and collapsed the real,
documented three-way tie at 63.8 into a false tie at 100.00. Fix: changed
`ALL ( dim_facility[facility_name] )` to `ALL ( dim_facility )` (the whole
table) in both the RANKX table argument and the FacilityCount CALCULATE, in
all three percentile measures. **This bug is also present in
`docs/powerbi_guide.md` §4.8 as written**, for the same reason as bug #1, and
should be corrected there alongside it: any measure meant to rank across "all
facilities" needs `ALL()` on the whole dimension table, not a single column,
whenever the visual using it might filter more than one column of that table
at once.

Re-validated after both fixes against the reference table already documented
in "New measure, Facility Risk Score" above: top three tied at 63.77 (rounds
to 63.8) — Nathan Littauer Hospital, St. Mary's Healthcare - Amsterdam
Memorial Campus, St. Peter's Hospital - SPARC — and the low end matching
within rounding (Albany Medical Center Hospital 33.33, Saratoga Hospital
37.68). Confirms both the original reference calculation and the corrected
DAX are right; the guide's formula, not the reference values, was the error.

**2026-07-09: Page 1 rebuilt as the Executive Summary.** Tab renamed
"Overview" → "Executive Summary." The optional treemap (documented as
"keep if there's room, drop if the page feels crowded" in
`docs/powerbi_guide.md` §5) was dropped in favor of the new Facility Risk
Score table, to avoid crowding. Built a table visual with `facility_name`,
`sub_region`, `Total Discharges`, `Facility Medicaid Share`, `Facility
Extreme Cost Share`, `Facility Risk Score`, `Is Low Volume Facility`
(`Medicaid Share`/`Extreme Cost Share` formatted as percentage), filtered to
the top 8 rows by `Facility Risk Score` via a Top N visual-level filter.
Verified the resulting 8 rows match the documented top of the ranking. Added
a text box, "Recommended focus areas," with three lines written from the
actual validated numbers (the 63.8-tied top three, the two of those three
that are also flagged low-volume, and Nathan Littauer Hospital as the
volume-plus-risk pricing/contract-review candidate), not a template.

**Not yet done, carried into the next session:** final layout polish on
Page 1. The recommendations text box was drawn across the full page width and
was overlapping the existing "Total Discharges by Sub Region" bar chart at
the point this session ended; it still needs to be resized/repositioned so it
sits only in the empty space left of the bar chart, with a final visual check
that the KPI cards, table, text box, and bar chart don't feel crowded
together, before Task 3 (Rework Page 1) can be marked complete.

**2026-07-09: `docs/powerbi_guide.md` §4.8 corrected to match, same session.**
Both DAX bugs above were flagged as "also present in the guide as written."
Rather than leave that as an open flag, the guide's §4.8 was edited directly
to the corrected DAX (the `ALL ( dim_facility )`-scoped version shown above,
in both the RANKX arguments and the FacilityCount CALCULATE), with an inline
note explaining both bugs so a future build from the guide doesn't reproduce
either one. This is a correction to the guide's own worked example, not a
reversal of any modeling decision, the underlying design (equal-weighted
percentile composite, three components, `ALL(dim_facility)` scope) is
unchanged from "New measure, Facility Risk Score" above; only the previously
buggy DAX text is fixed. `portfolio_build_plan.md` Stage 4 updated to check
off the DAX-measures milestone accordingly.

---

### A third real bug: Facility Risk Score under the global severity slicer,
plus a mis-bound table field found while testing it

**2026-07-09: found by deliberately testing the global `apr_severity_of_illness`
slicer against the finished Page 1 table, later the same session.** Selecting
any severity other than the unfiltered default, tested directly with
"Undetermined", produced `Facility Extreme Cost Share` values as large as
7,404,622% for Albany Medical Center Hospital and 461,036% for Samaritan
Hospital, alongside blank cells for the 15 facilities with no Undetermined-
severity discharges at all. Confirmed independently against
`fact_discharges.csv` before touching any DAX: only 24 of the 143,613
discharges in the whole dataset are severity `"Undetermined"`, spread across
9 of the 24 facilities, so any measure that ends up dividing by a subset that
small will misbehave if the numerator and denominator aren't scoped the same
way.

**Root cause.** `Facility Extreme Cost Share`'s numerator,
`CALCULATE ( [Total Costs], fact_discharges[apr_severity_of_illness] = "Extreme" )`,
is a boolean filter argument on a column, which DAX evaluates by clearing any
existing filter on that exact column and replacing it, so the numerator
always means "this facility's all-time Extreme-severity cost" regardless of
what the slicer has selected. That is the same, correct pattern already used
in `Extreme Tier Cost Share` (§4.2). The bug was that the *denominator*,
plain `[Total Costs]`, had no such override and stayed subject to whatever
the slicer picked. With the slicer on "Undetermined," the measure became (this
facility's all-time Extreme cost) ÷ (this facility's tiny Undetermined-only
cost), two unrelated numbers divided against each other. `Facility Medicaid
Share` had a milder version of the same issue: neither its numerator nor
denominator overrides the severity filter, so both sides simply recompute on
whatever severity subset is selected, mathematically consistent (no absurd
percentages) but conceptually wrong for a page meant to synthesize each
facility's overall risk profile, not its risk profile "if we only count
Undetermined-severity cases."

**Design decision, confirmed before fixing:** two options were
possible. Add `KEEPFILTERS` so the "Extreme" condition intersects with
whatever the slicer selects instead of overriding it (technically correct,
but the practical effect is the whole risk table goes blank whenever the
slicer excludes "Extreme"). Or lock the three Facility Risk Score inputs to
always evaluate across every severity, ignoring the slicer entirely, so Page
1 stays a stable, portfolio-wide synthesis no matter what a reviewer has
selected elsewhere. Chose the second, matching the existing precedent for the
Page 2 DRG cost ranking, which already deliberately uses `ALL` instead of
`ALLSELECTED` for the same reason: a ranking/synthesis view shouldn't shift
under a filter that doesn't make sense applied to it.

**Fix, applied directly in the live `.pbix` and validated:**

```DAX
Facility Medicaid Share =
DIVIDE (
    CALCULATE (
        [Total Discharges],
        dim_payer[payer_name] = "Medicaid",
        ALL ( fact_discharges[apr_severity_of_illness] )
    ),
    CALCULATE ( [Total Discharges], ALL ( fact_discharges[apr_severity_of_illness] ) )
)

Facility Extreme Cost Share =
DIVIDE (
    CALCULATE ( [Total Costs], fact_discharges[apr_severity_of_illness] = "Extreme" ),
    CALCULATE ( [Total Costs], ALL ( fact_discharges[apr_severity_of_illness] ) )
)
```

`Size Fragility Percentile`'s `RANKX` referenced the general-purpose
`[Total Discharges]` directly, which also reacts to the severity slicer and
had to be locked the same way, inline, since `[Total Discharges]` itself must
stay reactive everywhere else in the model (Page 2's severity Pareto depends
on that):

```DAX
Size Fragility Percentile =
VAR FacilityRank =
    RANKX (
        ALL ( dim_facility ),
        CALCULATE ( [Total Discharges], ALL ( fact_discharges[apr_severity_of_illness] ) ),
        , DESC, Dense
    )
VAR FacilityCount =
    CALCULATE ( DISTINCTCOUNT ( dim_facility[facility_name] ), ALL ( dim_facility ) )
RETURN
DIVIDE ( FacilityRank - 1, FacilityCount - 1 ) * 100
```

`Medicaid Dependency Percentile` and `Cost Complexity Percentile` needed no
direct changes: they call `[Facility Medicaid Share]` and `[Facility Extreme
Cost Share]` respectively, which are now locked at the source.

**A second, separate problem found while verifying this fix:** even after
correcting the DAX, the Page 1 table's "Medicaid %" column still changed
under the severity slicer. Checking the Data pane's field-usage indicator
for the selected table visual showed why: the column was bound to the
general-purpose `[Medicaid Share]` measure (§4.5, the portfolio Q3 measure,
never locked and not meant to be), not `[Facility Medicaid Share]`, a
mis-binding from when the table was originally built. Fixed by removing that
field from the visual and adding `[Facility Medicaid Share]` in its place,
in the same column position, reformatted as Percentage (the newly-added field
defaulted to General format). Re-validated with "Undetermined" selected on
the slicer: `Facility Medicaid Share`, `Facility Extreme Cost Share`, and
`Facility Risk Score` all now read identically to the unfiltered baseline
(the 63.8-tied top three, Albany Medical Center Hospital and Saratoga
Hospital at the low end); only the raw `Discharges` column still reacts to
the slicer, which is expected and not misleading on its own.

**General lesson, worth carrying into pages 3-6:** whenever a measure
combines an explicit `CALCULATE` filter on a column with a plain reference to
another measure on the same fact table, check whether that other measure is
implicitly exposed to the same slicer the explicit filter is trying to
control. And whenever a table visual's column looks like it should be a
"Facility-level" measure from §4.8, confirm which exact field is bound by
checking the Data pane's per-visual usage indicator, not just the column
header text, since two similarly-named measures (`Medicaid Share` vs.
`Facility Medicaid Share`) can produce plausible-looking but wrong numbers if
the wrong one gets dragged in.

---

### Page 2 (Cost concentration, Q1) build completed, 2026-07-09 scope
upgrade content added

**2026-07-09: Page 2 built out in full**, per `docs/powerbi_guide.md` §5
("Page 2, Cost concentration (Q1)") including the two 2026-07-09 additions
(discharge-level cost concentration, risk-of-mortality cross-cut). Final
visual set: the two KPI cards (`Total Costs`, `Extreme Tier Cost Share`),
the severity Pareto combo chart, the Top 15 DRG table with a Top N = 15
visual filter, a separate full 324-DRG cumulative curve, three new discharge-
level KPI cards (`Top 1/5/10% Discharge Cost Share`), and a new clustered
column chart crossing `apr_severity_of_illness` by `apr_risk_of_mortality` on
`Total Costs`. All values checked against `docs/powerbi_guide.md` §7a: the
`Extreme Tier Cost Share` card (24.68%), portfolio `Total Costs` card
(2.27bn), the severity Pareto's rank order and shape (Major, Moderate,
Extreme, Minor, Undetermined, cumulative 31.9/60.2/84.9/100/100), and the
Top 15 DRG table's rank 1 row (Septicemia and disseminated infections,
11,830 discharges, $220,967,975 total against the reference $220,967,976,
a $1 display-rounding difference, $18,678.61 avg cost per discharge,
matching exactly) all match the documented reference values.

**2026-07-09: risk-of-mortality cross-cut built as a clustered column chart,
not a matrix.** `docs/powerbi_guide.md` §5 allowed either ("a small matrix or
clustered chart"). The Matrix visual-type icon could not be reliably located
in the Visualizations pane's icon grid during this build session (see the
Table/Card workaround note below), so the clustered column chart option was
used instead: x-axis `apr_severity_of_illness`, legend `apr_risk_of_mortality`,
value `Total Costs`. This is a fully equivalent view of the same cross-cut and
satisfies the guide's stated intent (surfacing which severity/mortality-risk
combinations drive cost) without functional loss.

**2026-07-09: discharge-level cost concentration measures
(`Top 1/5/10% Discharge Cost Share`) confirmed already present in `_Measures`
from an earlier session; only the three KPI cards were new this session.**
Card values: Top 1% = 10.88%, Top 5% = 27.53%, Top 10% = 40.03% of portfolio-
wide `Total Costs`. These are new measures added under the 2026-07-09 scope
upgrade and have no prior reference table to check against; internal
consistency was confirmed instead (each wider percentile bucket's share is
larger than the next, as expected for a monotonic cost ranking).

**2026-07-09: Visualizations pane icon-grid workaround, Table and Card visual
types.** During this build session, the Table and Card visual-type icons
could not be reliably located by position in the icon grid (icon layout
reflows depending on pane width, and hovering to read tooltips was needed to
identify most icons by trial). Workarounds used instead: a Table visual is
created by checking a text field's checkbox in the Data pane with no visual
selected, which auto-creates a default Table; a new Card visual is created by
copying an existing, already-correct Card (Ctrl+C/Ctrl+V) and swapping its
Value field, always verifying the Selection pane's entry count increased
before editing the new copy, since an unverified copy-paste can silently
land edits back on the original visual instead of a new one. Both workarounds
are documented here so a future session doesn't lose time re-discovering
them; the Clustered column chart icon, by contrast, was locatable directly by
hovering the icon grid and reading tooltips (row 1, position 4 in the
Visualizations pane at default narrow width).

**2026-07-09: Page 2 layout finalized at 6 visuals plus the 2 header KPI
cards**, all confirmed non-overlapping by a full-page screenshot with the
Filters/Selection panes collapsed. No crowding; the new risk-of-mortality
chart sits below the three discharge-level cards, in previously empty space,
rather than beside the severity Pareto (no empty space remained directly
beside it once the DRG cumulative curve was placed underneath).

---

### Page 3 (Hospital pricing behavior, charge-to-cost markup, Q2) build
completed

**2026-07-09: Page 3 built out in full**, per `docs/powerbi_guide.md` §5
("Page 3, Hospital pricing behavior / charge-to-cost markup (Q2)"). The page
was created by manually duplicating the Page 2 tab, then stripped down to its
three shared slicers (`FACILITY NAME`, `SUB REGION`, `APR SEVERITY OF
ILLNESS`) and rebuilt with the Page 3-specific content: five KPI cards
(portfolio `Charge to Cost Ratio`, highest facility ratio, lowest facility
ratio, and the two national benchmark measures), a scatter/bubble chart, and
a ranked bar chart. All values checked against `docs/powerbi_guide.md` §7a:
portfolio ratio 2.95 (2.9544 underlying), highest 4.78 (Saratoga Hospital,
confirmed at the top of the sorted bar chart), lowest 1.03 (O'Connor
Hospital, confirmed at the bottom), national benchmarks 3.10 and 3.40, all
matching exactly.

**2026-07-09: highest/lowest facility ratio cards built with two new DAX
measures instead of the guide's originally-specified visual-level filter.**
`docs/powerbi_guide.md` §5 called for cards filtered to
`[Facility Markup Rank] = 1` and `= [Facility Count]` via the Filters pane's
advanced numeric filter. That control was unresponsive in this build session:
the comparator dropdown would not open and the numeric value text box would
not accept typed input under any tested interaction pattern (plain click,
double/triple-click, keyboard-only navigation, batched click+type), after
roughly 15 attempts. Rather than lose further time on a UI control that
appears broken in this session, two new self-contained measures were added to
`_Measures`, following the same "hardcode both branches" pattern already
established for `Extreme Tier Cost Share` (see the 2026-07-09 `ALLSELECTED`
entry above):

```DAX
Highest Facility Ratio =
MAXX ( ALL ( dim_facility[facility_name] ), CALCULATE ( [Charge to Cost Ratio] ) )

Lowest Facility Ratio =
MINX ( ALL ( dim_facility[facility_name] ), CALCULATE ( [Charge to Cost Ratio] ) )
```

The two "highest/lowest" cards' Value fields are bound directly to these
measures, with no visual-level filter needed. This is a deviation from the
guide's stated implementation mechanism but produces an identical, verified
end result (4.78 and 1.03). `docs/powerbi_guide.md` §5's Page 3 card
description should be read alongside this note; the guide's filter-based
approach is left as written there as the original design intent, not edited
out, since the failure looked session-specific (a non-functional control)
rather than a flaw in the filter approach itself.

**2026-07-09: bar chart built as a plain "Stacked bar chart" visual type, not
"Clustered bar chart."** The guide's phrasing ("Bar chart") does not specify
clustered vs. stacked. With only one value series (`Charge to Cost Ratio`,
no legend/breakdown field) bound to it, a Stacked bar chart renders
identically to a Clustered bar chart, since there is nothing for it to stack
against. Chosen pragmatically after the Visualizations pane's icon-grid
position for "Clustered bar chart" could not be relocated in this session
(icon layout reflows depending on Filters/Selection pane width, and a
remembered coordinate from earlier in the session pointed to a different
visual type after the panes were resized); "Stacked bar chart" was reliably
locatable at a stable icon position instead. Fields: Y-axis `facility_name`,
X-axis `Charge to Cost Ratio`, sorted descending by `Charge to Cost Ratio`
(Power BI's default sort for this visual, confirmed via the visual's own
"Sort by" context menu rather than changed).

**2026-07-09: Page 3 layout finalized at 2 charts plus 5 header KPI cards**,
all confirmed non-overlapping by a full-page screenshot with the Filters and
Data panes collapsed. Scatter chart at Height 280 / Width 760 / Horizontal
240 / Vertical 230; bar chart at Height 220 / Width 760 / Horizontal 240 /
Vertical 500 (the maximum vertical position Power BI allowed at that height,
auto-clamped to keep the visual within the 720pt-tall page rather than a
field-entry bug, confirmed by testing several typed values that all
resolved to the same clamped 500). No crowding.

---

### Page 4 (Payer mix and Medicaid exposure, Q3) build completed

**2026-07-09: page-numbering ambiguity found and resolved before any build
work started.** The build request that opened this session described "Page 4"
as answering business question 4 (length of stay), including a mention of the
`patient_disposition` open item. That does not match
`docs/powerbi_guide.md` §5 as written: the guide's actual Page 4 is "Payer
mix and Medicaid exposure (Q3)" (no 2026-07-09 scope-upgrade additions,
consistent with the guide's intro line "Page 4 is unchanged"), and the
LOS/Q4 content plus the `patient_disposition` cross-cut and its open grouping
item both belong to the guide's Page 5. Since pages 1 through 3 already match
the guide's page numbers exactly (Executive Summary, Q1, Q2), building LOS
content onto a tab labeled "Page 4" would have created a real, hard-to-reverse
mismatch between the tab and the documented page map. Flagged before
building anything, per this file's "confirm before building" rule. Confirmed:
Page 4 is Payer Mix (Q3) per the guide, and the LOS page (Q4, with the
`patient_disposition` cross-cut) is deferred to its own future session as
Page 5. The `patient_disposition` grouping remains exactly as documented
below, an open item, not touched this session.

**2026-07-09: Page 4 built out in full**, per `docs/powerbi_guide.md` §5
("Page 4, Payer mix and Medicaid exposure (Q3)"), which has no 2026-07-09
scope-upgrade additions. Page created by manually duplicating the Page 3 tab
(same pattern as Page 3's own creation from Page 2), then stripped down to
the three shared slicers (`FACILITY NAME`, `SUB REGION`, `APR SEVERITY OF
ILLNESS`) and rebuilt with the Page 4-specific content: two KPI cards
(`Government Share`, `Medicaid Share`, both portfolio-wide), a 100% stacked
bar chart (`facility_name` by `payer_category`, sorted descending by
`Government Share`), and a scatter chart (x-axis `Medicaid Share`, y-axis
`Total Discharges`, color `sub_region`, details `facility_name`). Added the
page-specific `payer_category` filter per §3. All values checked against
`docs/powerbi_guide.md` §7a: portfolio `Government Share` 64.83% and
`Medicaid Share` 16.38% (both cards), and two spot-checked scatter points
matched the documented per-facility detail exactly: St. Peter's Hospital -
SPARC (Medicaid Share 78.95%, Total Discharges 266, matching the reference's
78.9%/266) and Albany Medical Center Hospital (Medicaid Share 4.76%, Total
Discharges 36,882, matching the reference's 4.8% and the facility table's
36,882).

**2026-07-09: `Government Share` and `Medicaid Share` KPI cards built with
the copy-paste Card workaround already established on Page 2**, since no Card
visual existed yet on the fresh Page 4 to build from directly. Copied an
existing Card from Page 3, pasted onto Page 4, confirmed a genuinely new
visual via the Selection pane's entry count, then swapped the Value field.
Confirmed via the Data pane's per-visual usage indicator that the portfolio-
wide `Medicaid Share` measure (§4.5) was used, not `Facility Medicaid Share`
(§4.8, the Page 1 Facility Risk Score component); the two are easy to
confuse and the guide's own Page 1 note warns about exactly this mix-up.
Both measures required setting number format to Percentage directly on the
measure (Measure tools ribbon, since neither had been used in a Card before
this session); this changes the format at the measure level in `_Measures`,
consistent with the guide's "format every Pct/Share/Ratio measure as a
percentage" instruction, and applies wherever else either measure is used.

**2026-07-09: the 100% stacked bar chart's "sort by `Government Share`"
requirement needed a workaround, a new real Power BI gotcha found this
session.** Power BI's visual-level "Sort by" menu only lists fields already
bound to that visual (its axis, values, or legend wells); `Government Share`
was not one of the chart's bound fields (`facility_name`, `Total Discharges`,
`payer_category`), so it did not appear as a sort option even though it
exists in the model. Fix: dragged `Government Share` into the visual's
Tooltips well first (a field well that does not change the chart's shape but
does register the field as "on the visual"), after which it appeared in the
Sort by submenu and could be set to Sort descending. Confirmed the resulting
order is plausible and expected: the top rows are the small, high-government-
payer-share facilities (St. Peter's Hospital - SPARC, St. Mary's Healthcare -
Amsterdam Memorial Campus, Margaretville Hospital), consistent with `Total
Discharges` being small enough at these facilities for a handful of
Medicare/Medicaid cases to dominate the payer mix. Note this ranking is by
`Government Share` (Medicare plus Medicaid plus other government payers), not
`Medicaid Share` alone, so it does not exactly reproduce the `docs/decisions.md`
"highest Medicaid-share facilities" list from the scope-upgrade section;
Margaretville Hospital appearing near the top here despite having the lowest
documented Medicaid share (1.0%) is not a contradiction, since a facility can
be low-Medicaid and still high-government-share if its non-Medicaid
government payer share (chiefly Medicare) is high, plausible for a very
small, likely older-skewing patient population. The general pattern (adding
a field to Tooltips solely to make it available as a sort key) is worth
reusing on a future page if the same "sort by a measure not otherwise on the
visual" need comes up again.

**2026-07-09: the scatter chart was built from a copy of Page 3's
scatter/bubble chart, then remapped, rather than located by icon.** Page 3's
scatter chart already uses the "Scatter chart" visual type with the exact
field-well structure Page 4 needed (Values/X Axis/Y Axis/Legend), so instead
of hunting the Visualizations pane's icon grid for the right chart type (the
documented icon-instability gotcha from Pages 2 and 3), the Page 3 visual was
copied, pasted onto Page 4, and its fields remapped: X Axis changed from
`Charge to Cost Ratio` to `Medicaid Share`; `Total Discharges` moved from the
Size well to the Y Axis well (Page 4 needed a true two-axis scatter, not a
bubble-sized-by-volume chart, per the guide's explicit "y-axis `[Total
Discharges]`" wording); `sub_region` legend and `facility_name` details
carried over unchanged; the `Is Low Volume Facility` tooltip from Page 3 was
removed, since the guide's Page 4 spec lists exactly four fields for this
chart and did not call for that tooltip.

**2026-07-09: both charts confirmed built on `dim_facility[facility_name]`
and `dim_payer[payer_category]`, not a same-named mart column**, per the
standing gotcha documented earlier in this file (several mart tables carry
columns with identical names to the star schema, and dragging the wrong
table's copy silently filters nothing). Confirmed via the Data pane's table
grouping before adding each field.

**2026-07-09: Page 4 layout finalized at 2 charts plus 2 header KPI cards**,
all confirmed non-overlapping by a full-page screenshot with the Filters,
Selection, and Data panes collapsed. Bar chart at Height 480 / Width 500 /
Horizontal 190 / Vertical 220; scatter chart at Height 480 / Width 500 /
Horizontal 700 / Vertical 220 (side by side, matching heights). No crowding.
Saved with Ctrl+S; title bar's "Last saved" timestamp updated to confirm.

**Not yet done, carried into a future session:** Page 5 (Length of stay by
facility and severity, Q4), including the `patient_disposition` grouping
open item (19 raw values need review and categorization before that page's
cross-cut visual can be built; see "`patient_disposition` added as a
supporting cross-cut on Page 5" above, still unresolved), and Page 6 (Urban
vs. rural utilization, Q5).

---

### `patient_disposition` grouping resolved (2026-07-10, ahead of the Page 5 build)

**2026-07-10: `patient_disposition`, 19 raw values grouped into 5 categories,
resolving the open item carried since the 2026-07-09 scope-upgrade session.**
The full 19-value distribution was pulled directly from `fact_discharges.csv`
before any grouping was proposed (143,613 rows, matching the row count
exactly):

| Count | Raw value |
|---:|---|
| 99,434 | Home or Self Care |
| 13,927 | Skilled Nursing Home |
| 11,502 | Home w/ Home Health Services |
| 4,653 | Expired |
| 3,791 | Short-term Hospital |
| 3,178 | Inpatient Rehabilitation Facility |
| 2,522 | Left Against Medical Advice |
| 981 | Hospice - Home |
| 582 | Hosp Basd Medicare Approved Swing Bed |
| 571 | Hospice - Medical Facility |
| 570 | Court/Law Enforcement |
| 487 | Psychiatric Hospital or Unit of Hosp |
| 423 | Facility w/ Custodial/Supportive Care |
| 421 | Another Type Not Listed |
| 202 | Medicaid Cert Nursing Facility |
| 185 | Medicare Cert Long Term Care Hospital |
| 85 | Critical Access Hospital |
| 55 | Cancer Center or Childrens Hospital |
| 44 | Federal Health Care Facility |

Two grouping options were considered, a 4-category version matching
the guide's original literal suggestion (home, post-acute facility,
hospice/expired, other) and a 5-category version that splits "other" into a
distinct "Transfer to Another Hospital" bucket. The 5-category version was
chosen. Reasoning: Q4's post-acute-access claim is specifically about whether
rural patients can get into skilled nursing, rehab, or long-term-care beds
after discharge, not about acute-to-acute hospital transfers (a patient
transferred to a psychiatric unit or a cancer center is not a post-acute-
access story in the same sense). Folding both into one "Other" bucket, as the
4-category option would, would blur that distinction on the chart itself.
Keeping them separate costs one extra category and is more precise for the
exact claim this page is making.

**Finalized grouping** (`patient_disposition_group`, 5 categories):

| Group | Raw values included | Discharges | Share |
|---|---|---:|---:|
| Home | Home or Self Care; Home w/ Home Health Services | 110,936 | 77.2% |
| Post-Acute Facility | Skilled Nursing Home; Inpatient Rehabilitation Facility; Hosp Basd Medicare Approved Swing Bed; Medicaid Cert Nursing Facility; Medicare Cert Long Term Care Hospital; Facility w/ Custodial/Supportive Care | 18,497 | 12.9% |
| Hospice/Expired | Expired; Hospice - Home; Hospice - Medical Facility | 6,205 | 4.3% |
| Transfer to Another Hospital | Short-term Hospital; Psychiatric Hospital or Unit of Hosp; Critical Access Hospital; Cancer Center or Childrens Hospital; Federal Health Care Facility | 4,462 | 3.1% |
| Other/Unplanned | Left Against Medical Advice; Court/Law Enforcement; Another Type Not Listed | 3,513 | 2.4% |

Sums to 143,613 across all five groups, matching the raw row count exactly.
Built as a Power Query conditional column (`patient_disposition_group`) on
`fact_discharges`, rather than a DAX calculated column, so it behaves as a
native filterable/sliceable text field with no calculation-engine overhead,
consistent with how other categorical rollups (`payer_category` on
`dim_payer`) were handled earlier in the project. This column lives on the
fact table, not a dimension, since `patient_disposition` itself is already
flat on `fact_discharges` (no separate disposition dimension exists in the
star schema).

---

### Post-review documentation hygiene & planned fixes

**2026-07-10: Documentation hygiene pass (from the senior-review findings in
`docs/review_findings_and_fixes.md`).** Three factual/consistency corrections,
none of which change any computed number:

1. `README.md` "How to reproduce" step 4 and the repository-layout note for
   `powerbi_guide.md` previously said the guide was "pending update… still
   describes the old synthetic model." The guide was in fact rewritten against
   the real SPARCS star schema and the full six-page dashboard was built from
   it. Both lines corrected to say the guide is current.
2. The duplicate-row count wording in `docs/project_context.md` §6 (Phase 2)
   and `docs/data_dictionary.md` (staging table) said "70 exact-duplicate
   rows," which conflated two counts. Verified by recomputing from the raw
   file: **70 rows sit in exact-duplicate groups, of which 36 would be removed
   by a keep-first dedupe** (0.05% of the data). This is exactly what this
   file's 2026-07-07 "Exact duplicate rows" entry already said; the two
   front-facing docs were reworded to match it.
3. `docs/project_context.md` §2 carried "Hamilton County: 25% of residents
   65+," which `docs/sources.md` §5 had already flagged as stale. Current
   Census Bureau QuickFacts (2024 vintage) puts it in the ~34-36% range.
   Updated the figure in `project_context.md` to the 2024 vintage with an
   inline pointer to this entry and `sources.md` §5. Note (as `sources.md`
   already records) Hamilton County has no facility in this project's dataset,
   so no number computed from the actual `fact_discharges` changes.

**2026-07-10: `facility_role` classification added for the Facility Risk Score
fix (SQL finalized; pipeline re-run and Power BI wiring still pending).** The
QA pass (`docs/review_findings_and_fixes.md`, Fix 3) found the Page 1
Facility Risk Score is dominated by sub-300-discharge specialty/satellite units
(St. Mary's – Amsterdam Memorial Campus, 259 discharges; St. Peter's Hospital –
SPARC, 266) because the `Size Fragility Percentile` deterministically rewards
smallness and does not distinguish a specialty campus of a solvent system from a
genuine rural sole-community hospital. Fix: a `facility_role` column on
`dim_facility` (SQL in `sql/02_dimensions/02_dimensions.sql`) so the Page 1
ranking can exclude non-general-acute units and compare like with like.

An initial draft split the 18 general-acute facilities into `Community Acute` /
`Rural / Sole-Community Acute` by size and geography and was flagged
provisional. Per the 2026-07-10 sign-off, that split was **replaced with each
facility's actual CMS designation**, so "sole-community" is a checkable federal
status rather than a size judgment. Sources (both added to `docs/sources.md`
§6): NY State DOH "Critical Access Hospital and Sole Community Hospital
Outpatient Rate Add-ons, 4/1/2024–3/31/2025," cross-checked against the Flex
Monitoring Team CAH Locations List. Final five-value taxonomy (24 facilities):

| `facility_role` | n | Facilities |
|---|---:|---|
| Academic Medical Center | 1 | Albany Medical Center |
| Community Acute (PPS) | 8 | St. Peter's, Glens Falls, Saratoga, Samaritan (Troy), Ellis, St. Mary's (Amsterdam), Columbia Memorial, Nathan Littauer |
| Critical Access Hospital | 6 | Cobleskill Regional, Delaware Valley, Margaretville, O'Connor, Alice Hyde, Elizabethtown Community |
| Sole Community Hospital | 4 | Adirondack Medical Center–Saranac Lake, A.O. Fox, Mary Imogene Bassett, Champlain Valley Physicians |
| Specialty / Satellite | 5 | St. Peter's Addiction Recovery Center, St. Peter's–SPARC, Sunnyview Rehab, Ellis–Bellevue Woman's Care, St. Mary's–Amsterdam Memorial Campus |

Corrections the CMS basis forced versus the size-based draft: **Nathan Littauer**
moved to Community/PPS (small and independent but holds no federal rural
designation); **Mary Imogene Bassett** and **Champlain Valley Physicians** moved
up to Sole Community Hospital (large but federally SCH, distance-based). Trap
avoided: the SCH list's "Samaritan Medical Center" is the Watertown (Jefferson
County) hospital, not this dataset's Samaritan Hospital in Troy (Rensselaer),
which is standard PPS.

**Still pending** (not yet done): re-run `src/run_pipeline.py` so `facility_role`
lands in the exported `dim_facility.csv`; add the column to the Power BI model;
change the Page 1 Facility Risk Score table to exclude
`facility_role = "Specialty / Satellite"`; and update the three percentile
measures so their `RANKX`/denominator scope is the general-acute set, not
`ALL ( dim_facility )` over all 24 (otherwise the display filters but the
percentile math still ranks against the excluded units). Full rationale and the
top-3 evidence table are in `docs/review_findings_and_fixes.md`, Fix 3.

---

### Page 5 (Length of stay by facility and severity, Q4) built (2026-07-10)

**2026-07-10: Page 5 built following the same duplicate-and-strip pattern as
Pages 2 through 4.** The Page 4 tab was duplicated, then every visual except
the three shared slicers (`facility_name`, `sub_region`,
`apr_severity_of_illness`) was removed before new content was added. This
build hit one data-loss incident partway through: a stray click near the
ribbon closed the file without a visible save prompt, discarding the
in-progress slicer-stripping work. The stripped-down stub was manually
recreated and saved, and the build resumed from that confirmed state. Every
save after that point was confirmed via Ctrl+S and a title-bar timestamp
check before moving to the next visual.

**Visuals built, final layout:**

- Three KPI cards (top row): `Avg Length of Stay (Days)` = 5.45,
  `Median Length of Stay (Days)` = 3.00, `Pct Censored Stays` = 0.04%. The
  `Pct Censored Stays` card initially rendered as "0.00" because the
  measure's number format was General rather than Percentage; fixed via the
  Measure Tools ribbon's "%" quick-format button.
- A small multiples clustered column chart: x-axis
  `apr_severity_of_illness`, y-axis `[Avg Length of Stay (Days)]`, small
  multiples by `sub_region`. Spot-checked against the guide's §7a reference
  table via tooltip on three panels: Capital District/Extreme = 12.64,
  Mohawk Valley/Extreme = 7.64, both exact matches.
- A Matrix visual substituting for the guide's suggested "Table," same
  deviation already used on Page 2 for the same reason (no plain Table icon
  could be located in the Visualizations pane's icon grid; six icon
  positions were tried and undone before settling on Matrix). Rows =
  `facility_name`, `apr_severity_of_illness`; Values = `Total Discharges`,
  `Avg Length of Stay (Days)`, `Median Length of Stay (Days)`,
  `Pct Censored Stays`. Validated in focus mode against
  `mart_los_by_facility_severity.csv` directly: Albany Medical Center
  Hospital / Extreme matches exactly (4,227 discharges, 16.07 avg days, 11.00
  median days, 15 censored stays = 0.35%, all four exact). The Total row
  (143,613 discharges, 5.45 avg, 3.00 median, 0.04% censored) matches the
  page's own KPI cards exactly.
- A 100% stacked bar chart for the `patient_disposition_group` cross-cut,
  built by copying Page 4's payer-mix 100% stacked bar and remapping: y-axis
  `sub_region`, x-axis `Total Discharges`, legend
  `patient_disposition_group`, the old Government Share tooltip removed.
  Spot-checked via tooltip: Capital District / Home = 77,106 discharges
  (78.75% within that region), consistent with the overall 110,936 / 77.2%
  Home share logged above.

**Layout:** three KPI cards top row, small multiples chart below spanning
most of the page width, then a two-column row with the Matrix table (left)
and the disposition chart (right). This two-column bottom layout was chosen
over three stacked full-width visuals because Power BI auto-clamps a
visual's vertical position to keep it within the page's 720px height (the
same auto-clamp gotcha already logged for Page 3), which made a third full
stacked row impossible without shrinking everything below a readable size.
Confirmed non-overlapping via a full-page screenshot with the Filters,
Selection, and Data panes collapsed. Saved with Ctrl+S; title bar's "Last
saved" timestamp updated to confirm.

**2026-07-10, same session: Page 5 stress-tested under the global slicers,
no bugs found.** Given that every real DAX bug found earlier in this project
(three `ALL()`/`ALLSELECTED` scoping bugs plus one mis-bound field, all on
Page 1) only surfaced under slicer interaction, not in the default
unfiltered view, Page 5 was deliberately re-opened after its initial build
and exercised the same way: `apr_severity_of_illness` = Extreme alone,
`sub_region` = Capital District alone, `facility_name` = Saratoga Hospital
alone, then Saratoga Hospital + Extreme combined. After every filter change,
the three KPI cards, the Matrix's Total row, and (for the severity and
facility cases) a specific data row were independently recomputed from
`fact_discharges.csv` joined to `dim_facility.csv` in Python and compared:

| Filter | Avg LOS | Median LOS | Pct Censored | Matches |
|---|---:|---:|---:|---|
| Extreme only | 12.34 | 9.00 | 0.18% | exact (12.3389 / 9.0 / 0.1791%) |
| Capital District only | 5.56 | 3.00 | 0.03% | exact (5.5598 / 3.0 / 0.0306%) |
| Saratoga Hospital only | 4.54 | 3.00 | 0.02% | exact (4.5371 / 3.0 / 0.0193%), and matches the unfiltered Matrix's own Saratoga row |
| Saratoga Hospital + Extreme | 11.45 | 9.00 | 0.12% | exact (11.4481 / 9.0 / 0.1208%) |

All four cases matched exactly, with no `ALL()`/`ALLSELECTED` override
behavior: every measure on this page (`Avg Length of Stay (Days)`,
`Median Length of Stay (Days)`, `Pct Censored Stays`, `Total Discharges`) is
a plain reactive aggregate, unlike Page 1's Facility Risk Score composite,
which was deliberately designed to ignore the severity slicer and had bugs
in doing so. The small multiples chart and the Matrix table were also
checked mid-filter (e.g., the Matrix's Extreme-filtered Total row read
13,958 / 12.34 / 9.00 / 0.18%, matching the KPI cards under the same filter)
and behaved correctly with no blanks, duplicated panels, or stale values.
The severity slicer's option list also correctly shrank to exclude
"Undetermined" once Saratoga Hospital was selected, confirmed against the
raw data as a real fact (Saratoga has zero Undetermined-severity discharges)
rather than a slicer bug. All filters were cleared afterward, the page
returned to its original unfiltered values (5.45 / 3.00 / 0.04%) exactly,
and the file was re-saved in that neutral state.

### Page 6 (Urban vs. rural utilization, Q5) built (2026-07-10)

**2026-07-10: Page 6 built following the same duplicate-and-strip pattern as
Pages 2 through 5.** The Page 5 tab was duplicated, then every visual except
the three shared slicers (`facility_name`, `sub_region`,
`apr_severity_of_illness`) was removed. A leftover `payer_category`
page-level filter, inherited from the Page 4 to Page 5 to Page 6 duplication
chain and missed during the earlier stub-creation pass, was found under
"Filters on this page" and removed before the two Page 6-specific filters
were added.

**Visuals built, final layout:**

- Two portfolio-wide KPI cards (top row): `ED Utilization Pct` = 61.85%,
  `High Severity Pct` = 37.22%. Both initially rendered as raw decimals
  (0.62, 0.37) because the measures' number format was General rather than
  Percentage; fixed via the Measure Tools ribbon's Percentage format, applied
  to each measure individually since format is stored at the measure level.
- A single Matrix visual (the same Table-to-Matrix substitution already
  logged for Pages 2 and 5, since no plain Table icon could be located in
  the Visualizations pane's icon grid). Rows = `dim_facility[sub_region]`;
  Values (7 columns, in order) = `Total Discharges`, `Pct of Total Volume`,
  `ED Utilization Pct`, `High Severity Pct`, `Avg Length of Stay (Days)`,
  `Avg Cost per Discharge`, `Discharges per 10k Population`, with data bars
  applied to every numeric column. The 7th column was labeled exactly
  "Discharges per 10,000 population, by hospital location" per the locked
  labeling decision above, not "utilization by residents of." Building this
  matrix hit two field-well mistakes, both caught immediately via screenshot
  and corrected: `mart_facility_financials[sub_region]` was added to Rows
  instead of `dim_facility[sub_region]` (the documented same-named-column
  gotcha), and the "X" remove icon was clicked instead of the "v" dropdown
  chevron twice while opening conditional-formatting menus, dropping
  `Total Discharges` once and `Pct of Total Volume` once from the Values
  well; both were re-added and drag-reordered back into position.
- Two page-specific filters: `fact_discharges[emergency_department_indicator]`
  and `fact_discharges[type_of_admission]`, both left in their default
  unfiltered ("is (All)") state.
- A callout text box surfacing the Mohawk Valley finding: lowest per-capita
  inpatient utilization of any sub-region (623.96 discharges per 10,000
  population, by hospital location, versus 1,080.70 in Capital District),
  yet the highest ED-utilization share (71.50% of its discharges originate
  in the ED, versus 59.40% in Capital District), framed as the opposite of
  what an "urban core vs. rural periphery" story would predict before
  looking at the actual numbers.

**Layout:** two KPI cards top row, the seven-column Matrix below spanning
most of the page width (with a minor internal horizontal scroll, judged
acceptable and not true crowding), the callout text box in the lower half
beside the shared slicers. The Matrix's Width and Horizontal position
required iterative adjustment (945/970/1010 width against 335/300/260
horizontal position) to avoid Power BI's auto-clamp behavior, the same
gotcha already logged for Page 3. Confirmed non-overlapping via a full-page
screenshot with the Filters, Selection, and Data panes collapsed. Saved with
Ctrl+S; title bar's "Last saved" timestamp updated to confirm.

**2026-07-10, same session: two real DAX bugs found and fixed during Page 6's
build and stress test.**

1. **`Sub-Region Population` returning wrong values under the Matrix's row
   context** (e.g. Capital District showing 684.65 discharges per 10,000
   population instead of the expected ~1,080). Root cause: the
   `_SubRegionPopulation` to `dim_facility` relationship is documented
   single-direction (filters flow from `_SubRegionPopulation`, the "1" side,
   to `dim_facility`, the "many" side, not the reverse needed for the
   Matrix's `sub_region` row context to reach the population table). Per this
   file's standing rule against unilateral changes to locked modeling
   decisions, the relationship's cross-filter direction was left untouched
   (Manage Relationships dialog opened to confirm the setting, then
   cancelled without changes). The measure was fixed instead:

   ```
   Sub-Region Population =
   CALCULATE (
       SUM ( _SubRegionPopulation[population] ),
       CROSSFILTER ( dim_facility[sub_region], _SubRegionPopulation[sub_region], BOTH )
   )
   ```

   Verified against an independent Python recomputation from
   `fact_discharges.csv` joined to `dim_facility.csv`: corrected
   Discharges per 10k Population values are Capital District 1,080.70,
   Central NY / Catskill Foothills 783.68, Mohawk Valley 623.96, North
   Country / Adirondack 1,058.69, matching the Python math to the decimal.
   The guide's own §7b reference table (1,080.8 / 783.6 / 624.1 / 1,058.9)
   shows minor (~0.1 to 0.25) rounding imprecision by comparison; this was
   judged a guide-reference rounding artifact, not a dashboard bug.

2. **`High Severity Pct` reading 382.95% under an Extreme-only severity
   slicer selection** (found during the Task 9 stress test, an impossible
   value for a percentage measure). Root cause: `High Severity Discharges`
   used a bare boolean `CALCULATE` filter on
   `fact_discharges[apr_severity_of_illness]`, which by standard DAX
   filter-context semantics replaces any existing filter on that exact same
   column, including the slicer's own Extreme-only selection, rather than
   intersecting with it. Fixed by wrapping the filter argument in
   `KEEPFILTERS`:

   ```
   High Severity Discharges =
   CALCULATE (
       [Total Discharges],
       KEEPFILTERS ( fact_discharges[apr_severity_of_illness] IN { "Major", "Extreme" } )
   )
   ```

   Verified against an independent Python recomputation: under an
   Extreme-only filter, every Extreme-filtered discharge is trivially a
   member of the {Major, Extreme} superset, so the mathematically correct
   value is exactly 100.0%. After the fix, both the KPI card and the
   Matrix's Total row read 100.00%, matching. This is the same root-cause
   pattern (a `CALCULATE` filter override colliding with external filter
   context) already seen three times on Page 1's Facility Risk Score
   measure, now confirmed on a fourth, independent measure.

**Full stress test, run after both fixes were applied:**

| Filter | Total Discharges | Pct of Total Volume (row) | ED Util Pct | High Severity Pct | Avg LOS | Avg Cost | Discharges/10k |
|---|---:|---:|---:|---:|---:|---:|---:|
| Extreme only (Total row) | 13,958 | 100.00% | 81.51% | 100.00% | 12.34 | 40,066.38 | n/a (Total row) |
| Mohawk Valley only | 6,347 | 4.42% | 71.50% | 32.85% | 4.90 | 11,307.33 | 623.96 |
| All filters cleared (baseline) | 143,613 | 100.00% | 61.85% | 37.22% | 5.45 | 15,777.29 | n/a (Total row) |

The Extreme-only scenario's per-sub-region Total Discharges breakdown
(Central NY / Catskill Foothills 1,188, Mohawk Valley 441, North Country /
Adirondack 1,745) also reconciled arithmetically against the Total row
(1,188 + 441 + 1,745 + 10,584 Capital District = 13,958), matching an
independent Python recomputation. The Mohawk Valley-only scenario's KPI
cards and all seven Matrix columns matched the Python recomputation exactly,
including `Discharges per 10,000 population, by hospital location`
(623.96), confirming the CROSSFILTER fix holds under single-region
filtering as well as the unfiltered baseline. Clearing all filters restored
every value to the exact baseline logged above, with no residual state.
The file was re-saved in that neutral, unfiltered state.

**Portfolio-wide reference values confirmed against guide §7a in the
unfiltered baseline:** Total Discharges 143,613, ED Utilization Pct 61.85%,
High Severity Pct 37.22%, matching both KPI cards and the Matrix's Total
row exactly.

With Page 6 complete, all six dashboard pages for this project are now
built. The next phase per `docs/powerbi_guide.md` §6 is saving the `.pbix`
into `powerbi/` and exporting page screenshots into `outputs/` (both
currently empty placeholder folders), followed by a final documentation
pass. That phase has not yet been started and will need to be confirmed
before beginning, per this file's standing build-in-stages rule.

### Full six-page QA pass (2026-07-10, same session)

**2026-07-10: ran a completeness and correctness pass across all six
dashboard pages after Page 6 was finished.** For each
page, checked the Selection pane's full visual inventory and the Filters
pane's page-level filters against `docs/powerbi_guide.md` §5's per-page
spec, rather than relying on a visual scan alone, since a missing visual is
easy to miss on a page that otherwise looks populated.

**Finding: Page 1 (Executive Summary) was missing 4 of its 5 specified
top-row KPI cards.** The guide's §5 spec for Page 1 calls for five cards,
`[Total Discharges]`, `[Facility Count]`, `[County Count]`, `[Total Costs]`,
`[Charge to Cost Ratio]`, explicitly marked "unchanged, still the right
orientation numbers" from before the page's 2026-07-09 Executive Summary
rework. The live page had only one, `Total Costs`. Checked
`docs/decisions.md`'s own Page 1 build entries for a documented decision to
drop the other four and found none: the entry logging the rework
("2026-07-09: Page 1 rebuilt as the Executive Summary") describes the new
Facility Risk Score table and recommendations text box in detail but never
mentions the top-row KPI cards at all, and a later "not yet done" note from
the same session only flags the recommendations text box's overlap with the
bar chart, not any missing card. The most likely explanation is that the
four cards were simply never rebuilt when the page was reworked from the
original "Overview," rather than a considered removal; since no dated entry
records intentionally dropping them and the guide still specifies all five,
this was treated as a gap to fix, not a locked decision to preserve.

**Fix: rebuilt the four missing cards.** Used the existing `Total Costs`
card as a template (copy-paste, the same pattern used throughout this
project for new Card visuals), placed all five cards in a single row from
Horizontal 361 (aligned with the Facility Risk Score table's own left edge,
clear of the slicer panel) to Horizontal 1226, each 165 wide with a 10px
gap, Height 79, Vertical 14: `Total Discharges` (144K), `Facility Count`
(24), `County Count` (14), `Total Costs` (2.27bn), `Charge to Cost Ratio`
(2.95). All five values were checked against an independent Python
recomputation from `fact_discharges.csv` and `dim_facility.csv` before
accepting them: 143,613 discharges, 24 distinct facilities, 14 distinct
`hospital_county` values, $2,265,824,365.27 total costs, and a 2.9544
charge-to-cost ratio, all matching to the same precision already documented
in the guide's own §7a reference table. Confirmed the new cards react
correctly to cross-filtering (briefly triggered by clicking a Facility Risk
Score table row during layout work; all five cards updated together, e.g.
4K/1/1/43.21M/2.41 for St. Mary's Healthcare alone) and that clearing the
selection restores the exact baseline. Saved with Ctrl+S; title bar's "Last
saved" timestamp updated to confirm.

**Pages 2 through 6, all confirmed complete against the guide's spec, no
other gaps found:**

- Page 2 (Cost concentration, Q1): 5 KPI cards (Total Costs, Extreme Tier
  Cost Share, and the three 2026-07-09 discharge-level percentile cards),
  the severity Pareto combo chart, the Top 15 DRG table, the full DRG
  cumulative curve, and the risk-of-mortality clustered chart. All present.
- Page 3 (Hospital pricing behavior, Q2): 5 KPI cards (portfolio ratio,
  highest, lowest, two national benchmarks), the scatter/bubble chart, and
  the ranked bar chart. All present.
- Page 4 (Payer mix and Medicaid exposure, Q3): 2 KPI cards, the 100%
  stacked bar chart, the scatter chart, and the page-specific
  `payer_category` filter (confirmed present in the Filters pane, "is
  (All)"). All present.
- Page 5 (Length of stay by facility and severity, Q4): 3 KPI cards, the
  small multiples chart, the Matrix table, and the `patient_disposition_group`
  100% stacked bar chart. All present.
- Page 6 (Urban vs. rural utilization, Q5): 2 KPI cards, the seven-column
  Matrix, the callout text box, and both page-specific filters
  (`emergency_department_indicator`, `type_of_admission`, both "is (All)").
  Re-confirmed still at its exact validated baseline (143,613 / 61.85% /
  37.22% / 5.45 / $15,777.29) from the prior session's stress test.

**Re-verified Page 1's severity-slicer stability while on the page for this
pass.** Selected `apr_severity_of_illness = "Undetermined"` alone (the
exact case that surfaced the third real DAX bug on 2026-07-09) and confirmed
`Facility Medicaid Share`, `Facility Extreme Cost Share`, and
`Facility Risk Score` all still read identically to the unfiltered baseline
for every visible facility, with only the raw `Discharges` column reacting,
consistent with the fix already in place; no regression.

**Investigated one more potential concern before ruling it out: Page 2's
`Extreme Tier Cost Share` card also stays fixed (24.68%) under a
severity-slicer selection (tested with `Major` alone), which looked at
first like it might be the same class of bug already found and fixed
elsewhere.** Checked the measure's actual DAX in `docs/powerbi_guide.md`
§4.2:

```
Extreme Tier Cost Share =
DIVIDE (
    CALCULATE ( [Total Costs], fact_discharges[apr_severity_of_illness] = "Extreme" ),
    CALCULATE ( [Total Costs], ALL ( fact_discharges[apr_severity_of_illness] ) )
)
```

Both the numerator (a boolean filter on the severity column, which replaces
any existing filter on that same column by standard DAX semantics) and the
denominator (an explicit `ALL()` on the severity column) are deliberately
insulated from the severity slicer by design, not a bug: the guide's own
Page 2 spec calls this out directly ("no visual-level filter needed or
wanted"). This is different from the real `High Severity Pct` bug fixed on
Page 6, which had no `ALL()`/`KEEPFILTERS` protection on its denominator at
all. Confirmed this card does still react normally to non-severity slicers
(facility, sub-region), since neither `CALCULATE` argument touches those
columns. No fix needed; documenting the investigation so it isn't
re-flagged as a false positive in a future session.

**No other bugs, missing visuals, blank cards, or crowding issues found
across any of the six pages during this pass.**

---

### Fix 3 finished: `facility_role` wired into the Facility Risk Score (2026-07-10)

**2026-07-10: pipeline re-run, `facility_role` confirmed in the exported
model.** `src/run_pipeline.py` re-run from a clean state (`data/interim/warehouse.duckdb`
recreated; the prior file plus its `.wal` could not be deleted in this
session's environment, likely a locked/cloud-sync-protected handle, so they
were renamed out of the way instead of removed — cosmetic only, `data/interim/`
is gitignored and not part of the deliverable). Validated: `fact_discharges`
143,613 rows (matches raw exactly), zero orphan FKs across all six dimension
joins, `dim_facility.csv` now has 7 columns with `facility_role` populated
1/8/6/4/5 (Academic Medical Center / Community Acute (PPS) / Critical Access
Hospital / Sole Community Hospital / Specialty / Satellite), matching
`sql/02_dimensions/02_dimensions.sql` exactly. Confirmed no other of the 12
remaining exported CSVs reference `facility_role` (`grep`-verified) and none
of the other files' schemas changed.

**Power BI refresh hit a real Power Query bug, found and fixed before A2-A4
could proceed.** Refreshing `dim_facility` failed with `Expression.Error:
The column 'source_operating_certificates' of the table wasn't found`.
Root cause, confirmed in the Advanced Editor: the `dim_facility` query's
`Csv.Document` step had a hardcoded `Columns=6` (and `QuoteStyle=QuoteStyle.None`)
left over from when the CSV had 6 columns, from before `facility_role`
existed. With `Columns=6` fixed, Power Query truncated every row to its
first 6 raw fields after the header re-promote, silently dropping the 7th
column (`source_operating_certificates`) project-wide rather than erroring
per-row, which is what actually surfaced as a "column not found" error at
the `Changed Type` step. `QuoteStyle=QuoteStyle.None` was a second latent
problem in the same options record: it disables CSV quote-awareness, which
would have mis-split Alice Hyde's quoted, comma-containing
`source_facility_ids` value (`"000325, 015485"`) into extra raw columns if
the fixed count hadn't already truncated the row first. Fix, applied
directly in the Advanced Editor for the `dim_facility` query: `Columns=6` →
`Columns=7`, `QuoteStyle=QuoteStyle.None` → `QuoteStyle=QuoteStyle.Csv`
(the default, quote-aware behavior), and added `{"facility_role", type
text}` to the `Changed Type` step's column list for consistency with the
guide's "every categorical field is Text" convention (§1). Refreshed clean
afterward: `dim_facility` loads all 7 columns / 24 rows, `facility_role`
confirmed visible in the Fields pane with the exact 1/8/6/4/5 split.
**General lesson for this project's own future re-runs:** any time a SQL
change adds or removes a column from a table already wired into a Power BI
Text/CSV query, check that query's `Csv.Document` options for a hardcoded
`Columns=` count before assuming a plain refresh will pick up the change;
Power BI does not auto-detect column-count changes on an existing query the
way it does on first import.

**Page 1 Facility Risk Score table filtered to general-acute facilities
(A3).** Added a visual-level filter, `dim_facility[facility_role] is not
"Specialty / Satellite"` (Advanced filtering, "is not"), to the table.
In-scope facility count goes 24 → 19. Title updated to "Facility risk score
— top 8 of 19 (general acute)."

**All three percentile measures rescoped to the general-acute population
(A4), the substantive part of this fix.** As flagged in the review, the
visual-level filter alone only changed what's *displayed*; the percentile
math in `Medicaid Dependency Percentile`, `Size Fragility Percentile`, and
`Cost Complexity Percentile` still ranked every facility against the full
`ALL ( dim_facility )` (24, including the 5 excluded Specialty/Satellite
units). Confirmed this exact stale-ranking symptom before applying the fix:
immediately after A3, the table displayed 19 rows but the Score column still
read the old values (63.77-tied top three, now missing two of its three
original members from the visible rows since they're Specialty/Satellite,
which on its own would have been a confusing, silently-wrong display). Fix:
each measure now computes a `GeneralAcute` variable —
`FILTER ( ALL ( dim_facility ), dim_facility[facility_role] <> "Specialty / Satellite" )`
— and both the `RANKX` table argument and the `FacilityCount` `CALCULATE`
use `GeneralAcute` instead of `ALL ( dim_facility )`. Exact DAX for all
three measures is in `docs/powerbi_guide.md` §4.8 (2026-07-10 note).

**Independent Python recomputation, run before touching the DAX, used as the
target to validate against (A5).** Computed directly from
`data/processed/fact_discharges.csv` + `dim_facility.csv`, replicating the
DAX's exact dense-rank/percentile formula but scoped to the 19 facilities
where `facility_role <> "Specialty / Satellite"`. Before trusting this
methodology on the new 19-facility scope, it was first re-run unfiltered
across all 24 facilities and confirmed to reproduce the already-documented
63.77-tied top three and the 33.33/37.68 low end exactly, ruling out a
methodology error before using the same code on the rescoped population.
New top of the 19-facility ranking:

| Rank | Facility | Sub-region | Discharges | Medicaid Share | Extreme-Tier Cost Share | Risk Score |
|---|---|---|---:|---:|---:|---:|
| 1 (tie) | Ellis Hospital | Capital District | 9,552 | 19.20% | 33.21% | 68.52 |
| 1 (tie) | Nathan Littauer Hospital | Mohawk Valley | 2,282 | 30.15% | 17.00% | 68.52 |
| 3 | Samaritan Hospital | Capital District | 9,912 | 26.99% | 26.32% | 66.67 |
| 4 (tie) | UVM Health Network - Champlain Valley Physicians Hospital | North Country/Adirondack | 8,072 | 18.64% | 25.05% | 61.11 |
| 4 (tie) | St. Mary's Healthcare | Mohawk Valley | 3,806 | 28.35% | 15.34% | 61.11 |
| 6 (tie) | Columbia Memorial Hospital | Central NY/Catskill Foothills | 3,051 | 15.37% | 21.87% | 57.41 |
| 6 (tie) | St. Peter's Hospital | Capital District | 24,768 | 20.85% | 26.00% | 57.41 |
| 8 | Mary Imogene Bassett Hospital | Central NY/Catskill Foothills | 9,910 | 16.17% | 23.91% | 53.70 |

Low end, for contrast: UVM Elizabethtown Community Hospital (31.48),
Margaretville Hospital (33.33), Albany Medical Center Hospital (33.33, still
the region's largest facility by volume, so still too large to score as
fragile despite a high Extreme-tier cost share). None of the new top 8 are
flagged low-volume (`[Is Low Volume Facility]`, all above the 1,000-discharge
threshold), a direct, intended consequence of excluding the sub-300-discharge
specialty units — the ranking now surfaces genuine scale risk at real
general-acute hospitals, which is what Fix 3 set out to do. Built table in
Power BI matched this Python recompute exactly (68.52/68.52/66.67/61.11/
61.11/57.41/57.41/53.70) before being accepted.

**The stale "three-way tie at 63.8" note is retired, not corrected in place.**
The old top-3 (Nathan Littauer / St. Mary's - Amsterdam / St. Peter's -
SPARC) is no longer a coherent ranking to reference: two of those three are
now excluded from the general-acute comparison entirely, and Nathan Littauer
alone moved from 63.8 (against 24 facilities) to 68.5 (against 19). The old
top-5 reference table in `docs/powerbi_guide.md` §7b is superseded and
removed; the new 19-facility top-8 table is the single reference for the
Facility Risk Score going forward. `docs/powerbi_guide.md` §4.8's validation
paragraph updated accordingly.

**"Recommended focus areas" text box on Page 1 rewritten to match.** The
prior three lines referenced the retired top-3 (63.8 tie) and the two
now-excluded Specialty/Satellite low-volume flags, both facts that are no
longer true of the displayed table. Rewritten to name Ellis Hospital and
Nathan Littauer Hospital's tie at 68.5, Samaritan Hospital's volume-plus-risk
profile at 66.7, and the fact that none of the current top 8 are flagged
low-volume (a genuine, checkable finding, not a template line).

**Stress-tested per this project's standing rule (every real DAX bug in this
project's history surfaced under slicer interaction, not the unfiltered
default).** Tested individually and combined, on the live Page 1 table after
both DAX and display changes were in place:

| Filter | What was checked | Result |
|---|---|---|
| `apr_severity_of_illness = "Undetermined"` alone | The historical bug trigger (third real bug, 2026-07-09) | Score and both share columns identical to the unfiltered baseline for every visible facility; only the raw `Discharges` column reacted, as expected. No regression. |
| `sub_region = "Mohawk Valley"` alone | Whether `GeneralAcute`'s `ALL ( dim_facility )` still clears a sub_region slicer | Nathan Littauer Hospital (68.52) and St. Mary's Healthcare (61.11) both matched the unfiltered baseline exactly. |
| `facility_name = "A.O. Fox Memorial Hospital"` alone (a facility outside the visible top 8) | Whether the rescoped percentile is correct for a non-top-8 general-acute facility, not just the displayed rows | 37.04, matching the Python recompute for that facility exactly. |
| `sub_region = "Capital District"` + `apr_severity_of_illness = "Extreme"` combined | Combined slicer interaction, the scenario that has broken this composite three times before | All 5 Capital District general-acute facilities' scores (68.52 / 66.67 / 57.41 / 37.04 / 33.33) matched the unfiltered baseline exactly. |

All filters cleared afterward; the page returned to the exact unfiltered
baseline (144K / 24 / 14 / 2.27bn / 2.95 KPI row, top-8 table as documented
above) with no residual state. Saved with Ctrl+S; title bar's "Last saved"
timestamp confirmed.

**Where logged:** this entry (decisions.md); `docs/powerbi_guide.md` §4.8
(DAX, validation paragraph, 2026-07-10 rescoping note) and §5 Page 1 spec
(visual-level filter, title); §7b (superseded reference table replaced);
`docs/data_dictionary.md` (`facility_role` added to the `dim_facility` ER
block and prose); `docs/review_findings_and_fixes.md` status board (Fix 3
marked done, see that file's own dated status-board entry).

---

### Fix 1 finished: Medicaid sensitivity band added to Page 4 (2026-07-10)

**2026-07-10: sourced a real NY Medicaid managed-care penetration rate to
replace the placeholder 0.5 midpoint the review spec called for.** Per
`docs/review_findings_and_fixes.md` Fix 1, the `payer_category` rollup
Commercial bucket includes `Managed Care, Unspecified` (15,382 discharges,
10.7107% of the portfolio), an ambiguous SPARCS payer code that plausibly
mixes Medicaid managed-care and commercial managed-care enrollees with no
way to split it at the row level. Rather than invent a 50/50 split, searched
for a real, dated NY-specific Medicaid MCO penetration statistic. Found: KFF
State Health Facts, "Total Medicaid MCO Enrollment" tracker (data as of July
1, 2024, sourced from CMS Medicaid Managed Care Enrollment and Program
Characteristics reports) — New York: 4,751,430 comprehensive risk-based
managed-care enrollees, 68% of the state's total Medicaid enrollment for
2024. Citation added to `docs/sources.md`. Used **0.68**, not the review
spec's placeholder 0.5, as the adjusted-midpoint weight.

**Independent Python recompute run first, before any DAX was written, per
this project's standing validation-before-building rule.** Computed directly
from `fact_discharges.csv` joined to `dim_payer.csv`:

| Quantity | Value |
|---|---:|
| Medicaid discharges | 23,522 |
| Medicaid Share (reported floor) | 16.3787% → 16.38% |
| Managed Care, Unspecified discharges | 15,382 |
| Managed Care Unspecified Share | 10.7107% → 10.71% |
| Medicaid Share (Upper Bound), all-MCO ceiling | 27.0894% → 27.09% |
| Medicaid Share (Adjusted Midpoint), 0.68 weight | 23.6644% → 23.66% |

**Flagged correction, not silently fixed, per this file's standing rule
against unilateral edits to existing written content.** The review spec in
`docs/review_findings_and_fixes.md`'s Fix 1 sensitivity table states the
floor as "16.36%" (with 30/50/70% derived figures built from that base). The
independent recompute above gives 16.3787%, rounding to **16.38%**, not
16.36%. This is corroborated by four independent sources already in this
project: this recompute, `docs/powerbi_guide.md` §7a, this file's own prior
entries, `docs/project_context.md`, and the live Page 4 `Medicaid Share` KPI
card, which reads exactly "16.38%" before any of this session's changes.
16.36% appears to be a stale or transcription-error figure in the review
document. Since 16.38% is directly load-bearing for this fix's own
deliverable, it was used rather than propagated; the review document itself
was left unedited, consistent with the rule that new issues get flagged, not
silently corrected in someone else's prior write-up.

**Three new DAX measures added to `_Measures`, all validated against the
Python recompute above before being accepted:**

```
Managed Care Unspecified Share =
DIVIDE (
    CALCULATE ( [Total Discharges], dim_payer[payer_name] = "Managed Care, Unspecified" ),
    [Total Discharges]
)

Medicaid Share (Upper Bound) = [Medicaid Share] + [Managed Care Unspecified Share]

Medicaid Share (Adjusted Midpoint) = [Medicaid Share] + 0.68 * [Managed Care Unspecified Share]
```

All three formatted as Percentage via the Measure Tools ribbon. Built values
in a temporary validation table matched the Python target to 2 decimals
exactly: 16.38% / 23.66% / 27.09% / 10.71%, before any Page 4 visuals were
touched.

**Page 4 changes:**

- The existing `Medicaid Share` KPI card was renamed (via the field's
  "Rename for this visual" option, not the Format pane's Label > Text field,
  which did not accept typed input in this session's environment — see
  general lesson below) to **"Medicaid Share (reported floor)"**, then
  widened slightly so the full label displays without truncation.
- A new table visual, titled **"Medicaid Share - Sensitivity Band"**, added
  showing `Medicaid Share (Adjusted Midpoint)` (renamed for this visual to
  "Central estimate (adjusted midpoint)") and `Medicaid Share (Upper Bound)`
  (renamed to "Ceiling (all-MCO)") side by side: 23.66% / 27.09%.
- A caption text box added: `"Managed Care, Unspecified" (10.7% of
  discharges) may include Medicaid managed care; the band shows the range.`
  Positioned below the two Page 4 charts in this session; the substantive
  work was finished first, with the text box's exact size/position adjusted
  in a follow-up pass, so its final placement is not yet pixel-tuned.

**General lesson for this session's environment:** the Format pane's visual
Label/Title "Text" override field intermittently did not accept typed input
via the automation tooling used this session (text stayed "Auto"/blank after
typing and pressing Enter/Tab), reproducible across multiple attempts on two
different visuals. Two reliable workarounds were found instead: (1) for a
card's value label, right-click the field pill in the Values well and use
"Rename for this visual" rather than the Format pane's Label > Text box; (2)
for a visual's Title text, the Format pane's Title > Text field did accept
input once a plain hyphen was used instead of an em dash in the typed
string, suggesting the em dash character was the specific trigger, not the
field generally. Noting this in case a future session hits the same
symptom.

**Stress-tested under all three global slicers, individually and combined,
per this project's standing rule that every real DAX bug found in this
project's history surfaced under slicer interaction:**

| Filter | Medicaid Share (floor) | Adjusted Midpoint | Upper Bound | Managed Care Unspec. Share | Notes |
|---|---:|---:|---:|---:|---|
| Baseline (all cleared) | 16.38% | 23.66% | 27.09% | 10.71% | Matches Python recompute exactly |
| `apr_severity_of_illness = "Extreme"` alone | 9.75% | 15.58% | 18.32% | 8.57% | Arithmetic checks: 9.75 + 0.68×8.57 = 15.58 ✓; 9.75 + 8.57 = 18.32 ✓ |
| `sub_region = "Mohawk Valley"` + `facility_name = "Nathan Littauer Hospital"` combined | 30.15% | 30.15% | 30.15% | (blank) | Nathan Littauer has zero `Managed Care, Unspecified` discharges, so `CALCULATE` returns BLANK for that filtered numerator; `DIVIDE` returns BLANK rather than 0%, and BLANK behaves as 0 in the additive Upper Bound / Adjusted Midpoint formulas, correctly collapsing all three measures to the floor value. Confirmed this is correct DAX behavior (an empty filtered category), not a bug. |

All filters cleared afterward; the four values returned to the exact
baseline (16.38% / 23.66% / 27.09% / 10.71%) with no residual state. Saved
with Ctrl+S; title bar's "Last saved" timestamp confirmed.

**Where logged:** this entry (decisions.md); `docs/sources.md` (KFF/CMS
Medicaid MCO penetration citation); `docs/data_dictionary.md` (`Managed
Care, Unspecified` caveat updated from "worth revisiting" to point here);
`docs/powerbi_guide.md` §4 (three new measures) and §5 Page 4 spec (band
table, relabeled card, caption); `docs/review_findings_and_fixes.md` status
board (Fix 1 marked done).

---

### Fix 2 finished: Page 3 reframed from "pricing behavior" to derived-cost charge-to-cost ratio (2026-07-10)

**The problem, per `docs/review_findings_and_fixes.md` Fix 2:** Page 3 was
titled "Hospital Pricing Behavior" and its charge-to-cost ratio was framed as
a measure of how aggressively each facility prices. But SPARCS `total_costs`
is not a hospital's actual accounting cost — it is an estimate SPARCS
produces by applying cost-to-charge ratios (CCRs) to `total_charges`. Within
a facility, log-charges explain a median R² of 0.92 of log-cost variance (per
the review's own testing, per-facility range approximately 0.77-0.95 across
the 12 largest facilities), so a facility's aggregate charge-to-cost ratio is
close to the inverse of its assigned CCR, not an independent observation of
pricing behavior. The signal is partly circular. This doesn't make the page
worthless — cross-facility CCR differences are real, and the national
benchmark comparison (`docs/sources.md` §3) is legitimate context — but the
"pricing behavior" label overclaimed what a derived-cost figure can show.

**Fix, framing and disclosure only, no measure changes (per the review spec's
own instruction, confirmed: no DAX was touched).**

1. The Power BI page tab was renamed from "Hospital Pricing Behavior (Q2)" to
   **"Charge-to-Cost Ratio (Q2)"**, matching this project's other tab-naming
   convention (`"<name> (Q#)"`).
2. A title/subtitle text box was added to the page canvas: bold title
   **"Charge-to-Cost Ratio (SPARCS derived-cost basis)"**, followed by the
   subtitle *"Ratio of billed charges to SPARCS estimated costs. SPARCS
   costs are derived from cost-to-charge ratios, so this reflects each
   facility's assigned CCR, not independently observed pricing."*
3. A second, separate caveat text box was added below it, exact copy from
   the review spec: *"SPARCS `total_costs` is estimated by applying
   cost-to-charge ratios to charges, not measured from hospital accounting.
   Within a facility, ~92% of cost variation is explained by charges, so
   this ratio largely restates each facility's assigned CCR. Read
   cross-facility differences as directional, and compare to the national
   benchmark rather than treating any single facility's ratio as a pricing
   decision."*
4. The national-benchmark reference lines (`docs/powerbi_guide.md` §4.9)
   were left untouched, per the review spec's explicit instruction that they
   are the correct mitigation and should stay.

**Layout note:** both text boxes were placed in the page's right-margin
whitespace (to the right of the bubble chart, below the KPI cards), the only
clear space available without overlapping an existing visual. This is not a
polished final layout — the same layout constraint was worked through on
Page 4 earlier in this session, with substantive content finished first and
exact sizing/position left for a follow-up pass, so these two boxes should
be expected to be resized/repositioned rather than read as the intended
final placement.

**`docs/data_dictionary.md` also updated** (per the review spec's own
"Where to log it" note, item 3): the `total_costs` field description now
states plainly that it is a CCR-derived estimate, not a hospital's actual
accounting cost, pointing to this entry and Page 3's caveat box.

**No stress test needed for this fix.** Per the review spec, no measures
changed, so there is no new DAX to validate against slicer interaction; the
existing Page 3 KPI cards, bubble chart, and ranked bar chart are unchanged
and were already covered by this project's full six-page QA pass logged
above. Confirmed visually after the edit that the four KPI cards (2.95 /
4.78 / 1.03 / 3.10 / 3.40) still match their pre-edit values exactly, since
only page text and the tab name changed.

**Where logged:** this entry (decisions.md); `docs/powerbi_guide.md` §5
Page 3 spec (title, subtitle, caveat box); `docs/data_dictionary.md`
(`total_costs` CCR-derived note); `docs/review_findings_and_fixes.md`
status board (Fix 2 marked done).

---

### Fix 4 finished: Page 6 per-capita callout reworded from fact to hypothesis (2026-07-10)

**The problem, per `docs/review_findings_and_fixes.md` Fix 4:** the Page 6
Mohawk Valley callout's body paragraph stated its "constrained non-emergency
access" explanation as a settled interpretation of the discharges-per-10k
finding, rather than flagging it as one plausible explanation among others.
The per-capita measure itself has a real numerator/denominator mismatch: it
counts discharges at hospitals located in a sub-region, not discharges
consumed by residents of that sub-region (patients travel for care), so a
low discharges-per-resident figure could reflect residents leaving the
region for planned care, genuinely lower utilization, or both — the
dashboard shouldn't assert one specific mechanism as fact.

**Fix, text-only, no measure or number changes.**

1. The callout's body paragraph (heading unchanged: "Mohawk Valley: lowest
   per-capita utilization, highest ED share") was replaced with the exact
   hypothesis-framed copy: *"Mohawk Valley shows the lowest
   discharges-per-resident and the highest ED share. Because this counts
   discharges where the hospital sits, not where the patient lives, this
   pattern is consistent with residents leaving the region for planned care
   and/or constrained non-emergency access — it is a signal to investigate,
   not a settled utilization rate."* Care was taken to select and replace
   only the body text, leaving the bold heading line intact (the same
   heading-preservation mistake made and caught earlier in this project's
   history, on the Page 1 "Recommended focus areas" box, was avoided here by
   using Home + Shift+Ctrl+End from the start of the body line rather than
   Ctrl+A on the whole box).
2. A footnote text box was added below the seven-column Matrix: *"Per-capita
   = discharges at in-region hospitals ÷ in-region residents; the two
   populations are not identical (patients travel). Directional only."*
   Positioned at the bottom of the page, below the callout box, the only
   clear space available; same layout caveat as Fixes 1 and 2 above, exact
   sizing left for a follow-up pass.

**No stress test needed.** No measures or numbers changed; the `Discharges
per 10,000 population, by hospital location` values (Capital District
1,080.70, Central NY/Catskill Foothills 783.68, Mohawk Valley 623.96, North
Country/Adirondack 1,058.69) and the two portfolio KPI cards (61.85% / 37.22%)
are unchanged from the values already validated in this file's Page 6 build
entry above. Confirmed visually unchanged after the edit.

**Where logged:** this entry (decisions.md); `docs/powerbi_guide.md` §5
Page 6 spec (reworded callout, new footnote); `docs/review_findings_and_fixes.md`
status board (Fix 4 marked done).

With Fixes 1 through 5 all now complete, the remaining work per
`docs/review_findings_and_fixes.md` is Task E's close-out: saving the
`.pbix` into `powerbi/`, exporting page screenshots into `outputs/`, and a
final documentation pass confirming `README.md`, `docs/project_context.md`
§5, and the status board all reflect the finished state.

---

### DRG cumulative cost curve: broken axis rebind traced to a filter-scope bug (2026-07-15)

**Symptom.** After rebinding Page 2's "Full DRG cumulative cost curve" x-axis
from `dim_drg[apr_drg_description]` (categorical, 324 unlabelable ticks) to a
new `DRG Cost Rank (Col)` calculated column on `dim_drg`
(`RANKX ( ALL ( dim_drg ), [Total Costs], , DESC, Dense )`, Continuous axis
type) so the chart would render as a proper numeric-x-axis Pareto curve, the
line came out flat/broken instead of a smooth cumulative curve.

**Root cause.** Three measures underlying the chart (`DRG Cost Rank`,
`Cumulative Cost (DRG)`, `Total Costs (All DRGs)`) all cleared filters with
`ALL ( dim_drg[apr_drg_description] )` — i.e., `ALL` scoped to one specific
column. That was fine when the chart's x-axis was that same column, but once
the axis was rebound to the different column `DRG Cost Rank (Col)`, `ALL`
scoped to `apr_drg_description` no longer cleared the filter the axis was
actually applying, so every DAX evaluation stayed pinned to a single DRG's
row context. `ALL ( table[column] )` only clears filters on that specific
column, not the whole table, which is easy to miss since it reads like it
should.

**Fix.** Widened all three measures to table-level `ALL ( dim_drg )` instead
of `ALL ( dim_drg[apr_drg_description] )`. Confirmed visually: the chart went
from a flat/broken plateau to a proper Pareto curve, rising steeply then
flattening toward 100% cost coverage across the full 324-DRG population.

**Also fixed while on this chart:** the Y-axis was showing raw decimals
instead of a percentage (applied the Percentage quick-format to
`Cumulative Pct of Total Cost (DRG)`), and the X-axis range minimum was left
at Power BI's auto default instead of `1` (set explicitly, so DRG rank 1
sits at the left edge instead of some auto-padded value below it).

**Where logged:** this entry; `docs/powerbi_guide.md` §4.3 (DRG measures,
updated to the table-level `ALL` fix) and §5 Page 2 spec (axis rebind to
`DRG Cost Rank (Col)`, Continuous type, range minimum `1`).

---

### DRG/MDC cost fragmentation bug: found via a mockup-vs-live discrepancy, traced to the SQL source, fixed everywhere (2026-07-15)

**How it surfaced.** Comparing the `outputs/dashboard_six_page_mockup.html`
DRG cumulative curve against the live Power BI chart, at DRG rank 100 the
mockup read 79.9% cumulative cost while Power BI read 81.54%. Rather than
assume one side was simply stale, both were checked against ground truth
computed independently in Python/pandas directly from `fact_discharges.csv`
— which confirmed Power BI's 81.54% was correct and exposed that the
"ground truth" mart itself, `mart_drg_cost_concentration` (and by extension
the mockup values sourced from it), was wrong.

**Root cause.** Six specific APR-DRG codes — both tracheostomy DRGs, ECMO,
and the three "O.R. procedure unrelated to principal diagnosis" DRGs — don't
have one fixed MDC. An unrelated-to-principal-diagnosis procedure can occur
under any Major Diagnostic Category, so individual discharges under these
six DRGs carry different `mdc_key` values from each other.
`mart_drg_cost_concentration`'s SQL grouped directly by
`fact_discharges.mdc_key` alongside DRG, which silently split each of these
six DRGs' true total cost across up to 15 separate rows (one per MDC their
discharges happened to fall under), fragmenting their aggregate cost and
distorting the rank-ordered Pareto curve. Confirmed live in the .pbix: before
the fix, "Tracheostomy w/ Extensive Procedure" (true total $27.64M, true
rank 13) was appearing as a single $8.57M fragment, several ranks lower than
it should be.

**Same bug, independently, in the live "Top 15 DRGs" table.** The table's
Top N visual filter was correctly scoped to `dim_drg[apr_drg_description]`
(top 15 by `[Total Costs]`), but the table also had `dim_mdc[apr_mdc_description]`
as a second row-level Columns field. Adding multiple categorical fields to a
table's Columns creates one row per *distinct combination* present in the
data — so even with the Top N filter correctly ranking by DRG, the MDC field
fragmented the *displayed* total for any DRG that isn't 1:1 with MDC. Same
six DRGs, same symptom, different visual: a Top N filter scoped to one field
does not protect against a different row-level field silently splitting that
field's aggregate.

**Fix, applied at every layer instead of just patching the visible symptom:**

1. `sql/04_marts/04_marts.sql` — `mart_drg_cost_concentration` rewritten
   with a `drg_mdc_counts` / `primary_mdc` CTE pair that picks one
   representative ("primary") MDC per DRG — the MDC its discharges most
   often fall under — for *display* only, while the actual cost/discharge
   aggregation and `RANK()`/running-total window functions are grouped by
   DRG alone, so no DRG's cost is ever split across rows. Comment added
   in-file dated 2026-07-15 explaining the six-DRG root cause.
2. `data/processed/mart_drg_cost_concentration.csv` regenerated from the
   corrected SQL (via a standalone DuckDB script reading the existing
   `fact_discharges.csv`/`dim_drg.csv`/`dim_mdc.csv`, not a full pipeline
   re-run, to avoid touching unrelated already-correct processed files):
   324 rows (one per DRG, was 390 with fragmentation), verified against the
   independent Python recompute.
3. Live Power BI "Top 15 DRGs" table: removed `dim_mdc[apr_mdc_description]`
   from the table's Columns entirely. Verified in Focus mode that all 15
   rows now show correct, non-fragmented values and correct rank order,
   including "Tracheostomy w/ Extensive Procedure" now at 140 discharges /
   $27,643,261.07 / $197,451.86 avg, correctly slotted between "CVA and
   Precerebral Occlusion with Infarction" ($28,997,607.68) and "Major Large
   Bowel Procedures" ($27,306,257.70).
4. `outputs/dashboard_six_page_mockup.html` DRG curve data array corrected
   to the true values: `[9.8, 44.1, 62.4, 73.7, 81.5, 90.7, 95.9, 98.7,
   100.0]` (was `[9.8, 43.8, 61.6, 72.3, 79.9, 89.0, 94.3, 97.4, 99.6]`).

**Prompted a fuller mockup audit** of all non-table visualizations across
all six mockup pages against ground truth (once the
first discrepancy was found). Two more real mismatches found and fixed on
Page 4:
- The government-share bar list had 12 wrong facilities with fake
  (formula-derived, not real) 60/40 payer splits; replaced with the actual
  top 12 facilities by real government share and real 4-way payer splits
  (Government/Commercial/Self-Pay/Other) read from
  `mart_payer_mix_by_facility.csv`, and the bar rendering updated from a
  2-segment fake split to the real 4-segment split.
- The Medicaid-share bubble chart (`drawPage4Charts`, `fac` array) was
  missing 10 of the 24 facilities and had two rounding errors (Nathan
  Littauer 30.2 → 30.1, St. Mary's Healthcare 28.4 → 28.3); expanded to all
  24 facilities across all 4 sub-regions.

Everything else checked across the six-page audit (Page 1 KPIs, Page 3
charge-to-cost visuals, Page 5 LOS charts, Page 6 utilization charts) matched
ground truth already and needed no changes.

**Where logged:** this entry; `sql/04_marts/04_marts.sql` (inline comment,
2026-07-15); `docs/powerbi_guide.md` §5 Page 2 spec ("Top 15 DRGs" table,
MDC field removed).

---

### Custom category sort order added for payer_category, severity, and risk of mortality (2026-07-16)

**Ask:** display `apr_severity_of_illness` and `apr_risk_of_mortality`
in clinical order — Extreme, Major, Moderate, Minor,
Undetermined — rather than Power BI's default alphabetical order, the same
way `dim_payer[payer_category]` was supposed to display in
Government/Commercial/Self-Pay/Other order. Checking Page 4 live turned up
that the payer legend wasn't actually in that order either (it was plain
alphabetical: Commercial, Government, Other, Self-Pay), so all three fields
needed the same fix.

**`payer_category` fixed first, as the reference case.** Added a
`Payer Category Sort Order` calculated column to `dim_payer`. The first
version, a `SWITCH` keyed on `dim_payer[payer_category]` itself, threw *"A
circular dependency was detected: dim_payer[payer_category],
dim_payer[Payer Category Sort Order], dim_payer[payer_category]"* — Power
BI's Sort By Column feature creates a metadata dependency edge from the
sorted column to the sort column, and a sort-column formula that also reads
the sorted column closes that into a 2-node cycle. Fixed by rewriting the
`SWITCH` to key on `dim_payer[payer_key]` instead (a column with no
dependency relationship to `payer_category`), then set `payer_category`'s
Sort By Column to the new field. No circular dependency on this version;
applied successfully.

**Severity and risk of mortality: no natural key column to substitute,**
so a different pattern was used, mirroring this project's existing
`_SubRegionPopulation` precedent (`docs/powerbi_guide.md` §1) of a small
manually-entered reference table joined via a relationship: two new
Home > Enter Data tables, `_SeverityOrder` (`Severity`, `SortOrder`,
5 rows: Extreme=1 … Undetermined=5) and `_RiskOrder` (`Risk`, `SortOrder`,
same 5 values), each related one-to-many to `fact_discharges` on
`apr_severity_of_illness` / `apr_risk_of_mortality` respectively (single
cross-filter direction, lookup table filters the fact table). Two
calculated columns added to `fact_discharges`,
`Severity Sort Order = RELATED ( _SeverityOrder[SortOrder] )` and
`Risk Sort Order = RELATED ( _RiskOrder[SortOrder] )`, avoiding the
circular-dependency risk entirely since `RELATED()` pulls from a separate
table rather than self-referencing the sorted column. Sort By Column set on
both fields to their respective `*Sort Order` column; no errors.

**A stale visual-level sort override also needed fixing.** Once the model-
level sort order was in place, the Page 2 "Total Costs by Severity and Risk
of Mortality" chart still showed Major/Moderate/Extreme/Minor/Undetermined
(cost order) instead of the new tier order, because that specific visual had
its own explicit "Sort by Total Costs, descending" override (set via the
visual's `...` menu), which takes precedence over the column's default sort.
Switched the visual's sort to "by category" and then to ascending (it
initially came up descending, i.e. Undetermined→Extreme). The severity-tier
Pareto chart on the same page was left untouched — it's a genuine Pareto
chart, intentionally sorted by cost value rather than category order, and
that's correct.

**Verified across the report:** Page 3's payer legend now reads
Government → Commercial → Self-Pay → Other; Page 2's fixed stacked chart
and Page 4's small-multiples length-of-stay chart both read
Extreme → Major → Moderate → Minor → Undetermined; the Pareto chart on
Page 2 correctly stays cost-sorted. `_SeverityOrder`, `_RiskOrder`, and the
new calculated columns were left as one-line stray `Column1` (an accidental
extra blank column created via a stray Tab keystroke while entering
`_SeverityOrder`'s data — a cosmetic leftover, not wired into anything, safe
to delete later from Table view).

**Where logged:** this entry; `docs/powerbi_guide.md` §2 (new lookup tables
and relationships) and §4.5 (payer legend sort note).

---

### Severity Pareto rank/cumulative measures broken by the sort-order fix above — root-caused and fixed (2026-07-16)

**Symptom, reported immediately after the sort-order work above:** "the
pareto is now a straight line." The Page 2 "Cost Concentration by Severity
Tier (Pareto)" chart's cumulative-% line had gone from a proper rising curve
to flat, sitting at ~100% across every category.

**Diagnosis.** Built a temporary diagnostic matrix on the report canvas and
added throwaway test measures to inspect `[Severity Cost Rank]`'s actual
per-row output: it was returning `1` for every severity tier instead of a
distinct 1-5 rank, despite `[Total Costs]` itself displaying correctly and
differently per tier. A `CONCATENATEX` probe that listed what `[Total
Costs]` evaluated to for every severity from inside the same row context
that `RANKX` uses showed the real mechanism: for the "Extreme" row, only
"Extreme" came back with a real number — every *other* severity in the
comparison table came back blank. `RANKX` with Dense ranking, comparing a
value against a set where every other value is blank, has nothing to
distinguish "Extreme" from, so it (and everything else) rank as `1`.

**Root cause, confirmed by direct A/B test:** temporarily reverting
`apr_severity_of_illness`'s Sort By Column setting back to itself (removing
the custom order) made the exact same `RANKX`/`ALL`/`ALLSELECTED` formula
start working correctly again; re-applying the custom sort order broke it
again, reproducibly, in both directions. **Setting "Sort by Column" on a
field breaks `ALL()`/`ALLSELECTED()`'s ability to clear that field's row
filter for any measure that tries to iterate across that field's values
from inside a visual using it as an axis** — the visual's per-row filter and
the iterator's row-context filter end up ANDed together instead of the
iterator's replacing the visual's, so every comparison row except the
current one filters down to zero matching discharges (blank). This
reproduced identically regardless of *how* the comparison table was built —
plain `ALL(fact_discharges[apr_severity_of_illness])`,
`SUMMARIZE(ALL(fact_discharges), ...)`, and even iterating the unrelated
`_SeverityOrder` lookup table through its relationship all hit the same
wall — so this is specifically about Sort By Column's interaction with the
*current visual's row context*, not about which DAX table-function flavor
was used to build the comparison set.

**Fix: moved the rank calculation out of runtime iteration and into a
calculated column,** the same structural pattern already proven for the DRG
Pareto (`DRG Cost Rank (Col)` on `dim_drg`, see the 2026-07-15 entry above) —
calculated columns are computed once at data-refresh time, entirely outside
any report visual's filter context, so they're immune to this bug.

1. `_SeverityOrder[Severity Cost Rank (Col)]` (new calculated column):
   `RANKX ( ALL ( _SeverityOrder ), CALCULATE ( [Total Costs] ), , DESC, Dense )`.
2. `fact_discharges[Severity Cost Rank (Col)]` (new calculated column):
   `RELATED ( _SeverityOrder[Severity Cost Rank (Col)] )`.
3. `Severity Cost Rank` measure rewritten to
   `MAX ( fact_discharges[Severity Cost Rank (Col)] )` — a plain read of the
   precomputed column, no iteration.
4. `Cumulative Cost (Severity)` measure rewritten to filter
   `fact_discharges` directly on the precomputed rank column
   (`fact_discharges[Severity Cost Rank (Col)] <= CurrentRank`, inside
   `CALCULATE ( [Total Costs], ALLSELECTED ( fact_discharges ), ... )`)
   instead of iterating a table of severities.
5. `Total Costs (Severity Context)` needed no change — it was already using
   `ALLSELECTED` as a plain `CALCULATE` filter-modifier (not as a table
   passed into an iterator), which is the one usage pattern that was never
   affected by this bug; confirmed it returned the correct grand total
   throughout the diagnosis.

**Verified:** the Pareto chart's line is back to a proper rising cumulative
curve (Major → Moderate → Extreme → Minor → Undetermined by cost,
flattening toward 100%). Re-checked `Severity Cost Rank` directly in a
matrix (Extreme=3, Major=1, Moderate=2, Minor=4, Undetermined=5, matching
real cost order) and `Cumulative Cost (Severity)`'s running total
(721,948,240.88 → 1,364,188,633.47 → 1,923,435,216.09 → 2,265,709,042.64 →
2,265,824,365.27, each step matching the corresponding tier's `Total
Costs`). All eight throwaway diagnostic measures used during the
investigation were deleted afterward. Checked `apr_risk_of_mortality` and
the rest of the model for any other measure using the same
`ALL/ALLSELECTED`-iterating-a-sorted-column pattern; none exist (the only
other risk-of-mortality-adjacent measure, `Facility Risk Score`, doesn't
touch that field).

**Takeaway for future custom sort orders in this model:** if a field with a
custom Sort By Column ever needs a rank/running-total measure computed by
iterating its own values, compute the rank as a calculated column on a
dimension/lookup table (outside any visual's filter context) rather than as
a runtime `RANKX`/`FILTER` over `ALL`/`ALLSELECTED` of that field — the
runtime version is a live landmine that only surfaces once a visual using
that field as its axis actually renders.

**Where logged:** this entry; `docs/powerbi_guide.md` §4.2 (severity
measures, rewritten to the calculated-column pattern) and §2 (Sort By
Column gotcha noted alongside the new lookup tables).

---

### Mockup's "Total costs by severity and risk of mortality" chart didn't match the live Power BI axis (2026-07-16)

**Symptom:** the live Power BI chart's Y-axis is
`[Total Costs]`, i.e. dollars, but the mockup's `rom` chart plots a Y-axis
capped at 100 with the axis title `"% of tier cost"`.

**Cause.** The mockup chart was built as a normalized 100%-stacked bar
(`stacked:true, max:100`), showing each severity tier's risk-of-mortality
*composition* rather than the tier's actual dollar total split by risk.
Live Power BI's version (`X-axis apr_severity_of_illness`,
`Y-axis [Total Costs]`, `Legend apr_risk_of_mortality`, stacked column) plots
real stacked dollars, so the two axes were never going to visually agree —
Power BI's "Major" bar (highest total cost, ~$722M) reads taller than
"Extreme" (~$559M), while the mockup's normalized version made every bar the
same height (100%) by construction.

**Checked whether the underlying splits were even right first,** rather than
just re-scaling blindly: recomputed `SUM(total_costs)` grouped by
`apr_severity_of_illness` × `apr_risk_of_mortality` directly from
`fact_discharges.csv`. The mockup's existing within-tier *percentages* were
already accurate to within rounding (e.g. Extreme tier: 0.3/1.6/18.1/79.9
minor/moderate/major/extreme-risk vs. the recomputed 0.33/1.61/18.13/79.96) —
so only the chart's axis needed converting back to dollars, not the
underlying data.

**Fix:** rewrote the `rom` chart's five datasets from percentage shares to
actual `$M` values (each tier's risk-of-mortality dollar breakdown, e.g.
Extreme tier = Minor $1.8M / Moderate $9.0M / Major $101.3M / Extreme
$447.1M / Undetermined $0.0M, summing to the tier's known $559.2M total),
removed the `max:100` cap, and retitled the axis `"Total Costs ($M)"`.
Also corrected the chart's x-axis category order from the old
`['Minor','Moderate','Major','Extreme','Undetermined']` (neither
alphabetical nor clinical order — a leftover from before severity's Sort By
Column fix) to `['Extreme','Major','Moderate','Minor','Undetermined']`,
matching the now-corrected live Power BI clinical order (2026-07-16 entries
above). Verified per-tier stacked sums reproduce the known `Total Costs`
figures (Extreme 559.2, Major 722.0, Moderate 642.3, Minor 342.3,
Undetermined 0.1 — all within rounding of the validated per-severity
totals) via a standalone Node syntax/sum check.

**Where logged:** this entry; `outputs/dashboard_six_page_mockup.html`
(inline comment on the `rom` chart, dated 2026-07-16).

---

### Mockup regenerated to the post-review state — it still showed the pre-fix dashboard for Fixes 1-4 (2026-07-16)

**Why.** A review of the whole project surfaced that
`outputs/dashboard_six_page_mockup.html` had drifted from the live `.pbix`:
its subtitle said "verified 2026-07-10," but it predated the five
senior-review fixes (`docs/review_findings_and_fixes.md`) and so displayed the
*pre-fix* — in two cases now-known-wrong — version of the analysis. Since the
mockup is the one visual artifact a non-technical reviewer actually opens, the
drift meant the visible dashboard contradicted the documentation describing
it. Regenerated to match the finished state.

**What was stale, and what each page now shows:**

- **Page 1 (Executive Summary), Fix 3.** Was "Facility risk score — top 8 of
  **24**," led by the old three-way tie at 63.8 (Nathan Littauer / St. Mary's
  – Amsterdam / St. Peter's – SPARC) with four "Low volume" flags in the top
  eight — i.e. it showed exactly the specialty/satellite-dominated ranking Fix
  3 identified as a defect. Now "top 8 of **19** (general acute)," the five
  Specialty/Satellite units held out, led by Ellis Hospital and Nathan
  Littauer Hospital tied at 68.5, with zero low-volume flags in the top tier.
  The "Recommended focus areas" text and a new methodology footnote were
  rewritten from the rescoped numbers.
- **Page 3 (Q2), Fix 2.** Tab and title were still "Hospital pricing
  behavior." Now "Charge-to-cost ratio (Q2)," with the "SPARCS derived-cost
  basis" title/subtitle and the CCR caveat box (median within-facility R²=0.92
  disclosure) added.
- **Page 4 (Q3), Fix 1.** Only the 16.38% Medicaid floor card existed. The
  card is now labeled "Medicaid share (reported floor)" and a
  sensitivity-band table was added (floor 16.38% → adjusted midpoint 23.66% →
  ceiling 27.09%), plus the "Managed Care, Unspecified (10.7%)" caption.
- **Page 6 (Q5), Fix 4.** The Mohawk Valley callout stated its "constrained
  non-emergency access" reading as fact. Reworded to a hypothesis ("consistent
  with… a signal to investigate, not a settled utilization rate"), and the
  numerator/denominator "directional only" footnote was added under the
  Matrix.
- **Pages 2 and 5** already matched the live model (no fix touched them) and
  were left unchanged.

**Every regenerated number was re-derived from `data/processed/` before being
written into the mockup, not copied from the docs.** The Facility Risk Score
was recomputed independently in Python from `fact_discharges.csv` joined to
`dim_facility.csv` (using the built `facility_role` column) and `dim_payer.csv`,
following the §4.8 definition (three equal-weighted percentiles across the 19
general-acute facilities, Dense rank); the result reproduced the documented
anchors exactly (Ellis / Nathan Littauer 68.5, Samaritan 66.7, UVM
Elizabethtown 31.5 at the bottom). The Page 4 band figures (16.38 / 23.66 /
27.09) and Government share (64.83%) were likewise recomputed from
`fact_discharges.csv` joined to `dim_payer.csv` and matched the Fix 1 entry
above. Subtitle, Page 3 tab label, and footer note were updated to state the
post-fix state and the 2026-07-16 re-verification date.

**Note on scope:** this is a regeneration of the reference mockup to reflect
already-built, already-logged model changes — no new analysis, measure, or
data decision was introduced here; it only closes the gap between the visible
artifact and the finished `.pbix`. The broader Task E close-out
(`docs/review_findings_and_fixes.md`) — saving the `.pbix` into `powerbi/`
and exporting real page screenshots into `outputs/` — remains outstanding.

**Where logged:** this entry; `outputs/dashboard_six_page_mockup.html`
(page functions, subtitle, tab label, and footer note updated).
