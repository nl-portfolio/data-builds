# Technical Summary: Healthcare Ops & Finance (SPARCS Inpatient 2024)

*Companion to `findings_summary.md`, written for a technical reviewer. It
covers how the numbers were derived, the sensitivity ranges around the soft
ones, the honest limit of each metric, and why the modeling choices were made.
Full detail lives in `docs/decisions.md`, `docs/data_dictionary.md`, and
`docs/review_findings_and_fixes.md`.*

### Data and cleaning

Real, public, de-identified NY SPARCS data (143,613 rows, 33 columns), pulled
from the state's Socrata API with a server-side filter on
`health_service_area = 'Capital/Adirondacks'`. Real messy data was chosen over
a synthetic generator specifically to demonstrate cleaning decisions that were
not engineered to be tidy. Four judgment calls were locked and logged rather
than applied mechanically:

- **Censored length of stay.** 57 rows carry the literal text `"120+"` (SPARCS
  top-coding). Floored to `120` with an `is_los_censored` flag rather than
  dropped or blindly cast, and surfaced on the dashboard as `Pct Censored
  Stays` (0.04%) so no LOS figure is read without its censoring context.
- **Duplicates kept, not deduped.** The file has no patient or row identifier,
  so 70 rows sitting in exact-duplicate groups (36 removable by a keep-first
  pass) cannot be distinguished from two real patients sharing every coarse
  categorical. Removing them would invent precision the data does not support.
- **Payer coalesced.** `primary_payer` is the first non-null of
  `payment_typology_1/2/3`; raw slots retained for anyone needing multi-payer
  detail.
- **Alice Hyde merged.** One physical hospital appearing under two
  `permanent_facility_id` values was merged after ruling out both an
  ownership-change and a distinct-population explanation; both source IDs are
  retained as traceability.

### Modeling (star schema, DuckDB)

Grain is one discharge with a generated `discharge_key` (no natural key
exists). Two choices are worth calling out. First, **no `dim_date`**:
`discharge_year` is constant (2024), so it was dropped entirely rather than
modeled, making this an explicitly cross-sectional design with no
time-intelligence. Second, **MDC is its own dimension, independent of DRG.**
Six APR-DRG codes (both tracheostomy DRGs, ECMO, and the three "O.R. procedure
unrelated to principal diagnosis" groups) legitimately span multiple MDCs by
grouper design; modeling MDC as a DRG attribute fanned the fact table out past
the raw row count. Sentinel dimension rows (`dim_procedure` "NONE" for the
38.7% of stays with no procedure, `dim_payer` "Unknown") keep every foreign key
non-nullable. The build validates end to end: fact row count equals the raw
extract exactly (143,613 = 143,613) with zero orphan foreign keys.

### Metric derivations

Charge-to-cost ratio is `SUM(total_charges) / SUM(total_costs)` using `DIVIDE`
(the DAX equivalent of the `NULLIF(...,0)` safe-division used in the SQL
marts). Cost concentration is measured at three grains: a 5-tier severity
Pareto and a 324-group DRG Pareto (both running totals via window functions),
plus discharge-level percentiles computed by ranking all 143,613 rows
(top 1% / 5% / 10% = 10.88% / 27.53% / 40.03% of spend), which is the
concentration statistic a payer audience actually recognizes. The Facility Risk
Score is the equal-weighted mean of three percentiles (Medicaid dependency,
size fragility, cost complexity), each a Dense `RANKX` mapped to `(rank-1) /
(count-1) * 100`.

### Sensitivity and the honest limit of each metric

- **Medicaid share is a band, not a point.** `Managed Care, Unspecified` is
  10.7% of discharges and is classified Commercial by default, but in NY it
  often carries Medicaid managed care. Rather than silently reclassify, the
  dashboard shows a floor of 16.38% (bucket as commercial), an adjusted
  midpoint of 23.66% (weighting the bucket by NY's 0.68 Medicaid MCO
  penetration rate, sourced from KFF/CMS rather than a guessed 0.5), and a
  ceiling of 27.09% (all-MCO).
- **Charge-to-cost is derived-cost, not pricing behavior.** SPARCS
  `total_costs` is estimated by applying cost-to-charge ratios to charges. A
  direct test showed within-facility log-charge explains a median R² of 0.92
  of log-cost (range 0.77 to 0.95), so the ratio largely restates each
  facility's assigned CCR. Read cross-facility differences as directional and
  benchmarked (2.95 versus national 3.1 and 3.4), never as a single facility's
  pricing decision.
- **Per-capita utilization mixes two populations.** The numerator counts
  discharges where the hospital sits; the denominator is residents of that
  sub-region. Because `hospital_county` is the facility's county and patients
  travel, referral centers inflate and patient-exporting regions deflate. Kept
  as directional only, with the Mohawk Valley finding framed as a hypothesis.
- **Risk Score is scoped and flagged.** Equal weighting is an explicit,
  documented default, not a tuned choice. The ranking is restricted to 19
  general-acute facilities (five specialty/satellite units excluded by actual
  CMS designation, not by size) so it compares like with like, and a small-n
  flag marks facilities under 1,000 discharges. At n=19 a percentile composite
  produces structural ties (Ellis and Nathan Littauer at 68.5), which are
  expected, not a bug.

### Correctness engineering

Measures are live DAX over the shared star schema (so every slicer cross-filters
every page); the six marts are loaded unrelated, as a known-correct validation
reference only. Most bugs found were one filter-context class: a `CALCULATE`
filter replacing rather than intersecting existing context. Fixes included
whole-table `ALL(dim_facility)` instead of column-scoped `ALL`, `KEEPFILTERS`
on boolean filters, and `CROSSFILTER(..., BOTH)` at the measure level (leaving
the locked relationship untouched). A separate class came from Power BI's Sort
By Column silently breaking `RANKX` over `ALL`/`ALLSELECTED`; the fix was to
precompute ranks as calculated columns, which are evaluated once at refresh,
outside any visual's filter context. Every headline KPI was independently
re-derived in Python/pandas from the raw file and stress-tested under multiple
slicer combinations, because every real bug in this project surfaced only under
slicer interaction. One SQL fan-out bug in `mart_drg_cost_concentration`
(grouping by `mdc_key` split those six multi-MDC DRGs across up to 15 rows,
390 rows instead of 324) was caught by a mockup-versus-live discrepancy and
fixed at the source, not just in the visual.

### Known scope limits

Single-year, cross-sectional (no trend). Primary-payer only (no payer bridge
table for the ~30% of stays with multiple payers). Demographics kept flat on
the fact table because no stable patient entity exists to key a dimension on.
