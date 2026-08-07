# Power BI Build Guide

This walks from the exported CSVs in `data/processed/` to a six-page dashboard
built against the real star schema (`fact_discharges` plus six dimensions),
answering the five locked business questions in `README.md` and
`docs/project_context.md` §4. It supersedes the previous version of this
file, which still described the discarded synthetic schema
(`dim_patient`/`dim_provider`/two fact tables).

**Model philosophy:** the dimensions and `fact_discharges` are the primary
source. All measures below are computed live with DAX rather than imported
pre-aggregated, so every page can cross-filter every other page (click a
facility on one page, every other page updates). The six `mart_*` tables are
still loaded, but only as a validation reference: known-correct numbers
already computed in SQL, used to spot-check that the DAX is right, not as the
reporting layer itself. Full rationale in `docs/decisions.md`.

**Updated 2026-07-09** with a scope upgrade from a portfolio-value review:
new measures (§4.8-§4.11) and revised page layouts for Page 1, 2, 3, 5, and 6
(§5). The dashboard stays at six pages; nothing below adds a new page, every
addition is folded into one that already exists. Page 4 is unchanged. Full
rationale for every addition, every caveat, and the real computed reference
values behind them: `docs/decisions.md`, "Dashboard scope upgrade: synthesis
over sprawl."

---

## 1. Load the data

**Before importing anything**, turn off autodetect relationships: File >
Options and settings > Options > Current File > Data Load > uncheck
"Autodetect new relationships after data is loaded." Several `mart_*` tables
below share column names with the star schema on purpose (`facility_name`,
`sub_region`, `apr_severity_of_illness`, and others), since the marts are
self-contained flat copies for validation, not part of the model (see §2).
With autodetect left on, Power BI can silently wire up a relationship
between a mart and a dimension or fact table the moment the data loads,
which breaks the "marts stay unrelated" design without any visible warning.
Confirmed by hitting this directly during the build; see `docs/decisions.md`.

**Get Data > Text/CSV**, import from `data/processed/`, one file at a time:

- `dim_facility`, `dim_drg`, `dim_mdc`, `dim_diagnosis`, `dim_procedure`, `dim_payer`
- `fact_discharges`
- All six `mart_*` tables (`mart_severity_cost_concentration`,
  `mart_drg_cost_concentration`, `mart_facility_financials`,
  `mart_payer_mix_by_facility`, `mart_los_by_facility_severity`,
  `mart_regional_utilization`), for validation only, see §7

**New, 2026-07-09:** a 14th table, `_SubRegionPopulation`, needed for the
per-capita utilization measure in §4.9. This isn't a CSV in `data/processed/`
since it's small, manually-sourced reference data (Census Bureau / ACS
estimates), not derived from the SQL pipeline. Build it with **Home > Enter
Data**, same as `_Measures`, with two columns:

| sub_region | population |
|---|---:|
| Capital District | 906000 |
| North Country / Adirondack | 227450 |
| Central NY / Catskill Foothills | 194914 |
| Mohawk Valley | 101721 |

Match the `sub_region` text values exactly to `dim_facility[sub_region]`
(check the real casing/spacing in that column before typing these in, Power
BI relationships are case-sensitive on text keys). Full source citations and
the per-county breakdown behind each total: `docs/decisions.md`, "Per-capita
utilization measure added to Page 6."

**Do not use `Get Data > Folder`** pointed at `data/processed/` as a
shortcut for the 13 imports above. It was tried during the build and
returns a file-listing table (file name, extension, folder path, a binary
`Content` column) rather than the parsed CSV data. The Folder connector's
"Combine" step only works when every file in the folder shares one schema
(its intended use is many files with identical columns, like twelve monthly
exports), which doesn't hold here since the 13 files all have different
schemas. Thirteen individual `Text/CSV` imports is the correct approach, not
a workaround.

In Power Query, confirm data types before **Close & Apply**:

| Column(s) | Type | Note |
|---|---|---|
| `total_charges`, `total_costs` | Decimal Number | |
| `length_of_stay_days`, `birth_weight` | Whole Number | |
| `is_los_censored` | True/False | |
| `facility_key`, `drg_key`, `mdc_key`, `diagnosis_key`, `procedure_key`, `payer_key`, `discharge_key` | Whole Number | surrogate keys, not zero-padded, safe to type as numbers |
| everything else (names, descriptions, codes, categorical fields) | Text | including `apr_drg_code`, `apr_mdc_code`, `ccsr_*_code`, these are labels, not measures |

No `dim_date` and no date table: this is a single-year extract
(`discharge_year` was dropped entirely at the modeling stage, see
`docs/data_dictionary.md`), so there is nothing to mark as a date table and
no time-intelligence functions (YTD, MoM, moving averages) apply here. This
is a cross-sectional dashboard, not a trend dashboard, by design.

---

## 2. Build relationships (Model view)

Six one-to-many relationships, dimension (one) to fact (many), single
direction (dimension filters fact, not the reverse):

| From (1) | To (many) | On |
|---|---|---|
| `dim_facility[facility_key]` | `fact_discharges[facility_key]` | `facility_key` |
| `dim_drg[drg_key]` | `fact_discharges[drg_key]` | `drg_key` |
| `dim_mdc[mdc_key]` | `fact_discharges[mdc_key]` | `mdc_key` |
| `dim_diagnosis[diagnosis_key]` | `fact_discharges[diagnosis_key]` | `diagnosis_key` |
| `dim_procedure[procedure_key]` | `fact_discharges[procedure_key]` | `procedure_key` |
| `dim_payer[payer_key]` | `fact_discharges[payer_key]` | `payer_key` |

This is the star: six dimensions on the outside, `fact_discharges` in the
middle. Leave the `mart_*` tables unrelated to everything, on purpose: they
are a side reference for validation, not part of the model, so they should
not participate in cross-filtering.

**New, 2026-07-09:** one more relationship, `dim_facility[sub_region]` (many)
to `_SubRegionPopulation[sub_region]` (one), so `[Sub-Region Population]`
(§4.9) filters correctly through the existing `dim_facility` to
`fact_discharges` chain. This is the only new relationship the scope upgrade
needs; every other addition reuses measures and columns already in the star
schema.

**New, 2026-07-16:** two more small lookup tables, same pattern as
`_SubRegionPopulation` above, added to give `apr_severity_of_illness` and
`apr_risk_of_mortality` a fixed clinical display order (Extreme, Major,
Moderate, Minor, Undetermined) instead of Power BI's default alphabetical
order:

| From (1) | To (many) | On |
|---|---|---|
| `_SeverityOrder[Severity]` | `fact_discharges[apr_severity_of_illness]` | text match |
| `_RiskOrder[Risk]` | `fact_discharges[apr_risk_of_mortality]` | text match |

Each lookup table is just two columns (`Severity`/`Risk`, `SortOrder` 1-5),
entered via Home > Enter Data. `fact_discharges` gets two calculated columns,
`Severity Sort Order = RELATED ( _SeverityOrder[SortOrder] )` and
`Risk Sort Order = RELATED ( _RiskOrder[SortOrder] )`, and each field's
Sort By Column property points at its `*Sort Order` column.
`dim_payer[payer_category]` got the same treatment but via a calculated
column instead of a lookup table, `Payer Category Sort Order =
SWITCH ( dim_payer[payer_key], ... )` — keyed on `payer_key`, not
`payer_category` itself, because a `SWITCH` keyed on the column it will sort
throws a circular-dependency error (Sort By Column creates a metadata edge
from the sorted column to the sort column; a same-column `SWITCH` closes
that into a cycle). Full writeup: `docs/decisions.md`, "Custom category sort
order added for payer_category, severity, and risk of mortality"
(2026-07-16).

**Watch out: Sort By Column silently breaks `ALL()`/`ALLSELECTED()`-based
rank measures.** If a field has a custom Sort By Column set, any measure
that tries to `RANKX`/`FILTER` over `ALL(...)` or `ALLSELECTED(...)` of that
*same field*, evaluated from inside a visual using that field as its axis,
will return the same rank (typically 1, Dense) for every value — the
visual's row filter and the iterator's row-context filter end up ANDed
instead of the iterator's replacing the visual's, so every comparison value
except the current row silently evaluates to blank. This hit
`[Severity Cost Rank]` directly (see §4.2) once `apr_severity_of_illness`
got its Sort By Column above; the fix is to compute the rank as a
**calculated column** on a dimension/lookup table instead of a runtime
measure — calculated columns are computed once at refresh, outside any
visual's filter context, so they're immune. Full diagnosis and fix:
`docs/decisions.md`, "Severity Pareto rank/cumulative measures broken by the
sort-order fix above" (2026-07-16).

**Why live DAX over the star schema instead of importing the marts as the
reporting layer:** each mart was built in SQL to answer exactly one question
in isolation. Loaded as-is, clicking a filter on the Q1 page would have no
effect on the Q3 page, because they are six unrelated flat tables. Building
measures over the shared star schema means every slicer (facility,
sub-region, severity) filters every page consistently, which is both more
useful to a reviewer and a truer demonstration of Power BI data modeling and
DAX than reformatting six pre-computed tables into charts.

**Watch out: several column names repeat, identically, across
`fact_discharges` and multiple `mart_*` tables**, since the marts were built
by SQL to be readable on their own. `apr_severity_of_illness`, for one
example, exists in `fact_discharges`, `mart_severity_cost_concentration`,
and `mart_los_by_facility_severity`. Because the marts are deliberately left
unrelated to the star schema (previous paragraph), dragging the wrong
table's copy of a same-named column into a Filter, Value, or Axis well
produces no error, it just silently has no effect (there's no relationship
for it to filter through). Before trusting any field you've dragged in,
confirm which table it came from (hover it for a tooltip, or check its
grouping in the Fields pane). This bit the build directly: see the Page 2
KPI card note in §4.2.

---

## 3. Global filters (slicer panel, synced across all pages)

Three slicers, placed in a consistent left-hand rail on every page and
linked with **View > Sync Slicers** so a selection made on any page carries
to all six:

- `dim_facility[facility_name]`
- `dim_facility[sub_region]`
- `fact_discharges[apr_severity_of_illness]`

These three cut across all five business questions meaningfully: facility
and sub-region are the two lenses the entire project is framed around
(academic center vs. community vs. rural; urban core vs. rural periphery),
and severity is the clinical control variable every cost/LOS/utilization
comparison needs to hold constant to be a fair comparison.

**Page-specific filters** (not global, added only where relevant):

| Page | Extra filter | Why not global |
|---|---|---|
| Q3, Payer Mix | `dim_payer[payer_category]` | Only meaningful once you're already looking at payer breakdowns; forcing it everywhere adds noise to pages that aren't about payer mix |
| Q5, Utilization | `fact_discharges[emergency_department_indicator]`, `fact_discharges[type_of_admission]` | Utilization-specific lenses, not relevant to the cost or LOS pages |

---

## 4. DAX measures

Create a dedicated measures table (**Home > Enter Data**, name it
`_Measures`, delete the blank column) and put every measure below there, so
they're easy to find independent of which table they conceptually relate to.
Each block includes the DAX and the reasoning behind the approach, not just
the formula, per the project's documentation standard.

### 4.1 General (used across every page)

```DAX
Total Discharges = COUNTROWS ( fact_discharges )

Total Charges = SUM ( fact_discharges[total_charges] )

Total Costs = SUM ( fact_discharges[total_costs] )

-- DIVIDE returns BLANK on a zero denominator instead of erroring, the DAX
-- equivalent of the NULLIF(...,0) safe-division pattern used throughout the
-- SQL marts (see sql/04_marts/04_marts.sql).
Charge to Cost Ratio = DIVIDE ( [Total Charges], [Total Costs] )

Avg Cost per Discharge = DIVIDE ( [Total Costs], [Total Discharges] )

Avg Charge per Discharge = DIVIDE ( [Total Charges], [Total Discharges] )

Facility Count = DISTINCTCOUNT ( dim_facility[facility_name] )

County Count = DISTINCTCOUNT ( dim_facility[hospital_county] )
```

### 4.2 Q1, Cost concentration: severity tier (Pareto)

Answers: "what share of total spend comes from the highest-severity tier of
cases?"

```DAX
-- Updated 2026-07-16: the rank is now precomputed as a calculated column,
-- NOT a runtime RANKX over ALL/ALLSELECTED of apr_severity_of_illness. Once
-- that field got a custom Sort By Column (docs/decisions.md, 2026-07-16
-- entries), a runtime RANKX/FILTER iterating ALL()/ALLSELECTED() of that
-- same field -- evaluated inside a visual using it as an axis -- silently
-- returned the same rank for every value (the visual's row filter and the
-- iterator's row-context filter ANDed together instead of the iterator
-- replacing the visual's, so every comparison value except the current row
-- evaluated to blank). Calculated columns run once at refresh, outside any
-- visual's filter context, so they're immune. This mirrors the DRG fix in
-- §4.3 (DRG Cost Rank (Col) on dim_drg) -- same "precompute the rank as a
-- column, not a live measure" pattern, different trigger (sort order here,
-- axis rebind there).
--
-- On _SeverityOrder (the 5-row lookup table, §2):
--   Severity Cost Rank (Col) =
--   RANKX ( ALL ( _SeverityOrder ), CALCULATE ( [Total Costs] ), , DESC, Dense )
--
-- On fact_discharges, pulled across the relationship:
--   Severity Cost Rank (Col) = RELATED ( _SeverityOrder[Severity Cost Rank (Col)] )
Severity Cost Rank = MAX ( fact_discharges[Severity Cost Rank (Col)] )

-- Reproduces the SQL's SUM(...) OVER (ORDER BY total_costs DESC ROWS BETWEEN
-- UNBOUNDED PRECEDING AND CURRENT ROW): a running total keyed off the rank
-- above. Filters fact_discharges directly on the precomputed rank column
-- rather than iterating a table of severities, for the same reason as above.
Cumulative Cost (Severity) =
VAR CurrentRank = [Severity Cost Rank]
RETURN
CALCULATE (
    [Total Costs],
    ALLSELECTED ( fact_discharges ),
    fact_discharges[Severity Cost Rank (Col)] <= CurrentRank
)

-- Matches the SQL's grand_total_cost window (SUM() OVER() with no PARTITION):
-- the shared denominator for both the per-tier share and the cumulative share.
-- Unchanged by the 2026-07-16 fix: ALLSELECTED used here as a plain CALCULATE
-- filter-modifier (not as a table passed into an iterator) was never affected
-- by the Sort By Column bug described above.
Total Costs (Severity Context) =
CALCULATE ( [Total Costs], ALLSELECTED ( fact_discharges ) )

Pct of Total Cost (Severity) =
DIVIDE ( [Total Costs], [Total Costs (Severity Context)] )

Cumulative Pct of Total Cost (Severity) =
DIVIDE ( [Cumulative Cost (Severity)], [Total Costs (Severity Context)] )

-- Do NOT reuse [Pct of Total Cost (Severity)] above for a KPI card that
-- pins one hardcoded severity value (e.g. "show me Extreme's share").
-- ALLSELECTED in [Total Costs (Severity Context)]'s CALCULATE treats a
-- Filters-pane filter on the visual the same as an externally selected
-- context (like a slicer), so it does NOT strip that filter out. Put a
-- visual-level filter of apr_severity_of_illness = "Extreme" on a card
-- using the measure above, and both the numerator and the denominator end
-- up scoped to Extreme only, so the card always reads 1.00 no matter which
-- value is filtered to. Confirmed directly during the build; see
-- docs/decisions.md. Use this separate, self-contained measure instead for
-- any single-hardcoded-category KPI card:
Extreme Tier Cost Share =
DIVIDE (
    CALCULATE ( [Total Costs], fact_discharges[apr_severity_of_illness] = "Extreme" ),
    CALCULATE ( [Total Costs], ALL ( fact_discharges[apr_severity_of_illness] ) )
)
```

### 4.3 Q1, Cost concentration: DRG / condition (which conditions drive spend)

```DAX
-- Deliberately ALL here, not ALLSELECTED: unlike the severity ranking above,
-- this ranking should always reflect the complete 324-DRG population, not a
-- slicer-filtered subset, because it will sit on the same visual as a Top N
-- display filter (see §5). Mixing a Top N visual filter with an
-- ALLSELECTED-based running total is a known DAX conflict (the Top N filter
-- and ALLSELECTED can fight over what counts as "the selected context"), so
-- ALL keeps the ranking and cumulative-% denominator fixed and correct
-- regardless of what's shown, matching how the SQL mart computed it (a
-- static full-population calculation with no filters applied).
--
-- Updated 2026-07-15: table-level ALL ( dim_drg ), NOT column-level
-- ALL ( dim_drg[apr_drg_description] ). The column-level version broke once
-- the "Full DRG cumulative cost curve" chart's x-axis was rebound from
-- apr_drg_description to a new DRG Cost Rank (Col) calculated column
-- (Continuous axis type, so the 324-DRG curve renders as a real numeric
-- x-axis instead of 324 unreadable category ticks) -- ALL scoped to one
-- column only clears filters on that column, so once the axis applied a
-- filter through a *different* column of the same table, the old formula
-- stopped clearing it and every evaluation collapsed to a single DRG's row
-- context (flat/broken curve). Table-level ALL clears filters from any
-- column of dim_drg, regardless of which one the visual is currently
-- filtering through. Full diagnosis: docs/decisions.md, "DRG cumulative
-- cost curve: broken axis rebind traced to a filter-scope bug" (2026-07-15).
--
-- On dim_drg:
--   DRG Cost Rank (Col) = RANKX ( ALL ( dim_drg ), [Total Costs], , DESC, Dense )
DRG Cost Rank =
RANKX ( ALL ( dim_drg ), [Total Costs], , DESC, Dense )

Cumulative Cost (DRG) =
VAR CurrentRank = [DRG Cost Rank]
RETURN
CALCULATE (
    [Total Costs],
    FILTER ( ALL ( dim_drg ), [DRG Cost Rank] <= CurrentRank )
)

Total Costs (All DRGs) =
CALCULATE ( [Total Costs], ALL ( dim_drg ) )

Cumulative Pct of Total Cost (DRG) =
DIVIDE ( [Cumulative Cost (DRG)], [Total Costs (All DRGs)] )
```

### 4.4 Q2, Charge-to-cost ratio (markup) by facility

```DAX
-- Reactive to slicers on purpose (ALLSELECTED, not ALL): a reviewer filtering
-- to one sub-region should see facility markup ranked within that subset.
Facility Markup Rank =
RANKX (
    ALLSELECTED ( dim_facility[facility_name] ),
    [Charge to Cost Ratio], , DESC, Dense
)
```

`[Total Discharges]` doubles as a facility-size proxy here (see §5, the
bubble chart), so no new facility-size category needs to be invented. The
data dictionary has no notion of "academic / community / rural" as a formal
attribute; using discharge volume, a real column, to represent size avoids
introducing an undocumented business rule that would need its own dated
entry in `docs/decisions.md` before it could be trusted.

### 4.5 Q3, Payer mix and Medicaid exposure

```DAX
Government Discharges =
CALCULATE ( [Total Discharges], dim_payer[payer_category] = "Government" )

Government Share = DIVIDE ( [Government Discharges], [Total Discharges] )

-- Medicaid gets its own measure, not just folded into the Government
-- category rollup, because question 3 asks specifically about Medicaid
-- concentration, not government payers broadly (which also includes
-- Medicare, a very different financial-risk profile for a payer).
Medicaid Discharges =
CALCULATE ( [Total Discharges], dim_payer[payer_name] = "Medicaid" )

Medicaid Share = DIVIDE ( [Medicaid Discharges], [Total Discharges] )
```

### 4.6 Q4, Length of stay by facility and severity

```DAX
Avg Length of Stay (Days) = AVERAGE ( fact_discharges[length_of_stay_days] )

Median Length of Stay (Days) = MEDIAN ( fact_discharges[length_of_stay_days] )

-- Surfaces the "120+" censoring decision (docs/decisions.md) directly on the
-- dashboard instead of leaving it buried in documentation: any LOS
-- comparison should be read next to how much of it is censored data.
Censored Stay Count =
CALCULATE ( [Total Discharges], fact_discharges[is_los_censored] = TRUE )

Pct Censored Stays = DIVIDE ( [Censored Stay Count], [Total Discharges] )
```

### 4.7 Q5, Urban vs. rural utilization

```DAX
ED Discharges =
CALCULATE ( [Total Discharges], fact_discharges[emergency_department_indicator] = "Y" )

ED Utilization Pct = DIVIDE ( [ED Discharges], [Total Discharges] )

High Severity Discharges =
CALCULATE (
    [Total Discharges],
    fact_discharges[apr_severity_of_illness] IN { "Major", "Extreme" }
)

High Severity Pct = DIVIDE ( [High Severity Discharges], [Total Discharges] )

-- Matches the SQL mart's SUM(...) OVER() with no PARTITION: share of the
-- whole dataset's volume, not just the currently sliced sub-region.
Pct of Total Volume =
DIVIDE (
    [Total Discharges],
    CALCULATE ( [Total Discharges], ALL ( dim_facility[sub_region] ) )
)
```

### 4.8 Facility Risk Score (new, 2026-07-09): the Page 1 synthesis measure

Answers a question none of Q1-Q5 asks individually: which facilities, taken
together, look most exposed? Combines three signals already computed
elsewhere in this file into one 0-100 composite, so Page 1 can rank all 24
facilities instead of leaving five separate findings for the reader to
mentally combine themselves. Full methodology and the "why equal weighting"
reasoning: `docs/decisions.md`, "New measure, Facility Risk Score."

**Corrected 2026-07-09, after two real bugs surfaced while building this exact
DAX in Power BI Desktop.** The DAX below is the corrected version; full
root-cause writeup for both bugs is in `docs/decisions.md`, "Page 1 Executive
Summary build: two real DAX bugs found in the Facility Risk Score composite."
Summary of what changed and why, since an earlier draft of this section had
both bugs at once:

1. **`FacilityCount` must be wrapped in `CALCULATE ( ..., ALL ( dim_facility ) )`,
   not a bare `DISTINCTCOUNT`.** A bare `DISTINCTCOUNT ( dim_facility[facility_name] )`
   evaluates inside whatever row context the measure is used in. On the Page 1
   table (one row per facility), that row context collapses the count to 1,
   turning `DIVIDE ( FacilityRank - 1, FacilityCount - 1 )` into a division by
   zero, BLANK, on every row except the one unfiltered grand-total row. The
   `CALCULATE` + `ALL` wrapper forces the count back to the full, unfiltered
   facility population regardless of row context.
2. **Both `ALL()` calls (the `RANKX` table argument and the `FacilityCount`
   `CALCULATE`) must clear the whole `dim_facility` table, not just the
   `facility_name` column.** `ALL ( dim_facility[facility_name] )` only lifts
   the filter on that one column. The Page 1 table also has `dim_facility[sub_region]`
   on it, so its row context filters `sub_region` too, and `ALL` scoped to a
   single column leaves that second filter in place. In practice this meant
   RANKX and FacilityCount were silently computed within just the current
   row's sub-region (as few as 3 facilities) instead of across all 24,
   producing percentile values above 100 and collapsing the real, documented
   three-way tie at 63.8 into a false tie at 100.00. `ALL ( dim_facility )`
   (the whole table) clears every column at once and is the version to use
   whenever a visual might have more than one column of the same dimension
   table on it, which is the common case for a synthesis table like this one.

**Corrected again, later the same session (2026-07-09):** the DAX below also
locks both facility-level components against the global `apr_severity_of_illness`
slicer. Without this, selecting any severity other than the unfiltered
default reproduces a third real bug found while stress-testing the finished
Page 1 table: `Facility Extreme Cost Share`'s numerator has an explicit
`= "Extreme"` filter, which correctly overrides the slicer on its own (DAX
clears and replaces any existing filter on that exact column), but the
denominator had no such override and stayed scoped to whatever severity was
selected, so numerator and denominator ended up measuring two unrelated
subsets. With "Undetermined" selected (only 24 of 143,613 discharges
portfolio-wide), this produced values as large as 7,404,622%. Full
root-cause writeup: `docs/decisions.md`, "A third real bug: Facility Risk
Score under the global severity slicer." Both measures below now lock every
side of the ratio to all severities, matching the same precedent already
used for the Page 2 DRG ranking (`ALL` instead of `ALLSELECTED`, so a
synthesis/ranking view stays fixed regardless of slicer state).

**Corrected a fourth time (2026-07-10), rescoped to general-acute facilities
only.** My QA pass (`docs/review_findings_and_fixes.md`, Fix 3) found
the ranking below was dominated by sub-300-discharge specialty/satellite
units (St. Mary's – Amsterdam Memorial Campus, St. Peter's – SPARC) because
`Size Fragility Percentile` deterministically rewards smallness and didn't
distinguish a specialty campus of a solvent system from a genuine rural
sole-community hospital. Fix: a `facility_role` column was added to
`dim_facility` (CMS-designation-grounded; see `docs/data_dictionary.md` and
`docs/sources.md` §6), and all three percentile measures now rank within a
`GeneralAcute` variable — `FILTER ( ALL ( dim_facility ), dim_facility[facility_role]
<> "Specialty / Satellite" )` — instead of the full `ALL ( dim_facility )`
(24 facilities). This is layered on top of, not a replacement for, the
severity-slicer lock above: `GeneralAcute` still clears every column of
`dim_facility` (any slicer on `facility_name` or `sub_region`) the same way
`ALL ( dim_facility )` did, it just also drops the five Specialty/Satellite
rows from the ranking population before `RANKX`/`FacilityCount` run. The
Page 1 table's visual-level filter (`facility_role is not "Specialty /
Satellite"`, §5) only controls what's *displayed*; without this DAX change
the display would filter to 19 rows while the percentile math still ranked
against all 24, which was confirmed as a real, reproduced bug before this
fix (see `docs/decisions.md`, 2026-07-10).

```DAX
-- Facility-level components. These read correctly wherever dim_facility[facility_name]
-- is present as a row/axis field (a table, a bar chart, a bubble chart), since the
-- existing dim_facility -> fact_discharges relationship filters both automatically.
-- Both sides of both ratios are locked to ALL severities so Page 1 stays a stable
-- synthesis regardless of what's selected on the global severity slicer (see the
-- correction note above).
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

-- Percentile rank across the 19 general-acute facilities (excludes
-- Specialty/Satellite, see the 2026-07-10 note above), 0-100. ASC: the
-- facility with the LOWEST Medicaid share ranks 1st (percentile 0), the
-- highest ranks last (percentile 100). Higher Medicaid dependency should
-- read as higher risk, so this direction is correct as-is.
-- GeneralAcute = FILTER ( ALL ( dim_facility ), ... ) clears every column of
-- dim_facility first (same whole-table-ALL discipline as the corrected-
-- 2026-07-09 note above), then drops Specialty/Satellite rows before RANKX
-- and FacilityCount run, so this stays fixed at 19 regardless of what's
-- selected on any slicer.
Medicaid Dependency Percentile =
VAR GeneralAcute =
    FILTER ( ALL ( dim_facility ), dim_facility[facility_role] <> "Specialty / Satellite" )
VAR FacilityRank  = RANKX ( GeneralAcute, [Facility Medicaid Share], , ASC, Dense )
VAR FacilityCount = CALCULATE ( DISTINCTCOUNT ( dim_facility[facility_name] ), GeneralAcute )
RETURN DIVIDE ( FacilityRank - 1, FacilityCount - 1 ) * 100

-- DESC, not ASC: the LARGEST facility ranks 1st (percentile 0) and the
-- smallest ranks last (percentile 100), because smaller facilities should
-- read as higher risk (size fragility), the opposite direction from the
-- measure above.
-- [Total Discharges] itself must stay reactive to the severity slicer everywhere
-- else in the model (the Page 2 severity Pareto depends on that), so it can't be
-- locked at its source the way the two measures above were. Instead it's wrapped
-- inline here, in the RANKX argument only, so this one ranking stays fixed to all
-- severities without changing [Total Discharges] itself.
Size Fragility Percentile =
VAR GeneralAcute =
    FILTER ( ALL ( dim_facility ), dim_facility[facility_role] <> "Specialty / Satellite" )
VAR FacilityRank =
    RANKX ( GeneralAcute,
            CALCULATE ( [Total Discharges], ALL ( fact_discharges[apr_severity_of_illness] ) ),
            , DESC, Dense )
VAR FacilityCount = CALCULATE ( DISTINCTCOUNT ( dim_facility[facility_name] ), GeneralAcute )
RETURN DIVIDE ( FacilityRank - 1, FacilityCount - 1 ) * 100

-- ASC, same direction as Medicaid Dependency Percentile: higher Extreme-tier
-- cost share should read as higher risk.
Cost Complexity Percentile =
VAR GeneralAcute =
    FILTER ( ALL ( dim_facility ), dim_facility[facility_role] <> "Specialty / Satellite" )
VAR FacilityRank  = RANKX ( GeneralAcute, [Facility Extreme Cost Share], , ASC, Dense )
VAR FacilityCount = CALCULATE ( DISTINCTCOUNT ( dim_facility[facility_name] ), GeneralAcute )
RETURN DIVIDE ( FacilityRank - 1, FacilityCount - 1 ) * 100

-- Equal-weighted composite. Do not add strategic/actuarial weights here
-- without a dated decisions.md entry justifying the specific weights chosen;
-- equal weighting is the documented, defensible default.
Facility Risk Score =
( [Medicaid Dependency Percentile] + [Size Fragility Percentile] + [Cost Complexity Percentile] ) / 3
```

Validate against `docs/decisions.md`'s pre-computed ranking before trusting
the DAX (recomputed 2026-07-10 after the general-acute rescoping): **Ellis
Hospital and Nathan Littauer Hospital tie at the top (68.5)**, **Samaritan
Hospital is third (66.7)**, and **UVM Elizabethtown Community Hospital is at
the bottom (31.5)**. Two-way ties are expected behavior of a percentile-based
composite at n=19, not a bug to chase. If instead you see BLANK on every row,
or values above 100 with ties collapsed to 100.00, that is one of the earlier
bugs above, not a new problem. If the top of the ranking still shows the
stale three-way tie at 63.8 (Nathan Littauer / St. Mary's - Amsterdam / St.
Peter's - SPARC), the percentile measures have not been rescoped to
`GeneralAcute` yet — two of those three facilities are Specialty/Satellite
and should no longer appear in a general-acute ranking at all.

### 4.9 Per-capita utilization and external benchmark (new, 2026-07-09)

```DAX
-- Requires the dim_facility -> _SubRegionPopulation relationship (§2).
Sub-Region Population = SUM ( _SubRegionPopulation[population] )

Discharges per 10k Population =
DIVIDE ( [Total Discharges], [Sub-Region Population] ) * 10000

-- Two independently sourced reference points, both constants: see
-- docs/decisions.md, "External benchmark added to Page 3," for citations and
-- the caveat about differing methodology/vintage versus this project's own
-- 2024 SPARCS-based Charge to Cost Ratio.
National Avg Charge to Cost Ratio (CMS CCR-based, ~2020) = 3.1
National Avg Charge to Cost Ratio (Bai and Anderson, 2012 Medicare data) = 3.4
```

Validate `[Discharges per 10k Population]` against `docs/decisions.md`:
Capital District 1,080.8; North Country/Adirondack 1,058.9; Central
NY/Catskill Foothills 783.6; Mohawk Valley 624.1.

### 4.10 Risk-of-mortality cross-cut (new, 2026-07-09)

No new measure needed: `fact_discharges[apr_risk_of_mortality]` is already a
column, and `[Total Costs]`/`[Total Discharges]` already work against it the
same way they work against `apr_severity_of_illness`. Add a small matrix or
clustered chart on Page 2 crossing `apr_severity_of_illness` by
`apr_risk_of_mortality` with `[Total Costs]` as the value, to surface
high-cost/low-mortality-risk cases (utilization-management candidates)
separately from high-cost/high-mortality-risk cases (unavoidable complex
care). Rationale: `docs/decisions.md`, "`apr_risk_of_mortality` added as a
secondary cross-cut on Page 2."

### 4.11 Small-n statistical-stability flag (new, 2026-07-09)

```DAX
-- Threshold fixed at 1,000 discharges/year based on this dataset's own
-- natural break (9 facilities cleanly under it, the rest cleanly above), not
-- a universal statistical rule. Full reasoning: docs/decisions.md, "Small-n
-- statistical-stability flag."
Is Low Volume Facility =
IF ( [Total Discharges] < 1000, "Low volume, interpret with caution", "" )
```

Use this as a conditional-formatting rule or a visible tag on any per-facility
ranked or ratio visual (Page 1's Facility Risk Score table, Page 3's markup
bubble chart), so a ratio computed on a few hundred discharges isn't read
with the same confidence as one computed on tens of thousands.

Format every `Pct`/`Share`/`Ratio` measure as a percentage or decimal as
appropriate, and every `Total`/`Cost`/`Charge` measure as currency.

### 4.12 Medicaid sensitivity band (new, 2026-07-10, review Fix 1)

`payer_category`'s `Managed Care, Unspecified` bucket (10.71% of discharges,
`dim_payer[payer_name] = "Managed Care, Unspecified"`) is classified
`Commercial` by default, but this SPARCS label can plausibly include
Medicaid managed-care enrollees with no way to split it at the row level
(see `docs/data_dictionary.md`, `dim_payer` caveat). Rather than treat
`[Medicaid Share]` as the only Medicaid figure, three measures build a
floor-to-ceiling sensitivity band around it:

```DAX
Managed Care Unspecified Share =
DIVIDE (
    CALCULATE ( [Total Discharges], dim_payer[payer_name] = "Managed Care, Unspecified" ),
    [Total Discharges]
)

Medicaid Share (Upper Bound) = [Medicaid Share] + [Managed Care Unspecified Share]

-- 0.68 = NY comprehensive risk-based Medicaid MCO enrollment share, 2024
-- (KFF State Health Facts / CMS). Not this project's own data; a sourced
-- statewide proxy for the ambiguous bucket's likely Medicaid share. See
-- docs/sources.md §7 and docs/decisions.md, "Fix 1 finished: Medicaid
-- sensitivity band added to Page 4."
Medicaid Share (Adjusted Midpoint) = [Medicaid Share] + 0.68 * [Managed Care Unspecified Share]
```

All three formatted as Percentage. Validated against an independent Python
recomputation from `fact_discharges.csv` joined to `dim_payer.csv`: baseline
(unfiltered) values are `Managed Care Unspecified Share` 10.71%,
`Medicaid Share (Upper Bound)` 27.09%, `Medicaid Share (Adjusted Midpoint)`
23.66% — see `docs/decisions.md` for the full stress-test table under all
three global slicers.

---

## 5. Dashboard layout: six pages

One executive-summary/synthesis page plus one page per locked business
question. Each question gets full-page focus rather than being crowded onto
a shared page, since the five questions genuinely ask for different visual
logic (a Pareto curve is not the same shape of answer as a scorecard). Six
pages total, unchanged by the 2026-07-09 scope upgrade: every new element
below was folded into one of these six rather than added as a seventh or
eighth page (see `docs/decisions.md`, "Dashboard stays at six pages").

**Every page:** the synced slicer panel from §3 (facility, sub-region,
severity) on the left; consistent titles, consistent number formats, no
gridlines or 3D chart junk.

### Page 1, Executive Summary (revised 2026-07-09, was "Overview")

Renamed and rebuilt from a plain landing page into the dashboard's synthesis
page: a reviewer should be able to leave after Page 1 alone with "here are the
facilities I'd actually worry about, and why," not just an orientation to the
dataset. Rationale for upgrading this page instead of adding a new one:
`docs/decisions.md`, "Dashboard stays at six pages."

- KPI cards (top row): `[Total Discharges]`, `[Facility Count]`,
  `[County Count]`, `[Total Costs]`, `[Charge to Cost Ratio]` (unchanged,
  still the right orientation numbers)
- **New:** Facility Risk Score table, the page's lead visual: top 8
  facilities by `[Facility Risk Score]` descending, columns
  `dim_facility[facility_name]`, `dim_facility[sub_region]`,
  `[Total Discharges]`, `[Facility Medicaid Share]`,
  `[Facility Extreme Cost Share]`, `[Facility Risk Score]`. Apply
  `[Is Low Volume Facility]` as a visible tag column so a reviewer can see at
  a glance which high-ranked facilities are also low-volume (several of the
  top-ranked facilities are, see `docs/decisions.md`). **Use
  `[Facility Medicaid Share]`, not `[Medicaid Share]`** (§4.5's portfolio Q3
  measure): the two are easy to confuse in the Data pane and the wrong one
  was actually dragged in during the build, silently reintroducing
  slicer-reactivity into a page meant to stay fixed; see the field-binding
  note in `docs/decisions.md`, "A third real bug." If a KPI or column on this
  page ever looks like it's changing when it shouldn't, check which exact
  field is bound (Data pane's per-visual usage checkmarks), not just the
  visual's column header text. **Updated 2026-07-10 (Fix 3):** add a
  visual-level filter `dim_facility[facility_role] is not "Specialty /
  Satellite"` so the table's in-scope population is 19 general-acute
  facilities, not 24; title updated to "Facility risk score — top 8 of 19
  (general acute)." This filter only controls what's displayed — the three
  percentile measures must also be rescoped (§4.8's 2026-07-10 note) or the
  display and the underlying ranking math disagree.
- **New:** a text box, "Recommended focus areas," 3-4 short lines grounded in
  the actual ranked data once built, for example flagging the highest
  Medicaid-dependent, lowest-volume facilities for network-adequacy
  monitoring, and the highest-markup facility for a pricing/contract review.
  Write these from the real numbers once Page 1 is built, not from a
  template; a generic recommendation reads worse than none
- Bar chart: `[Total Discharges]` by `dim_facility[sub_region]`, sorted desc,
  showing the urban-core-vs-rural-periphery volume split at a glance
  (unchanged, kept for orientation)
- Treemap (optional, keep if there's room, drop if the page feels crowded):
  `[Total Costs]` by `dim_facility[facility_name]`, colored by
  `dim_facility[sub_region]`. The Facility Risk Score table above now does
  most of this visual's original job (where cost/risk concentrates by
  facility) more precisely, so this is no longer essential, just still
  useful context if it fits

### Page 2, Cost concentration (Q1)

- KPI cards: `[Total Costs]`, cost share of the `Extreme` severity tier
  (a card with the dedicated `[Extreme Tier Cost Share]` measure, §4.2,
  no visual-level filter needed or wanted, see that section for why a
  filtered `[Pct of Total Cost (Severity)]` card doesn't work here)
- Column chart with a line overlay (Pareto combo chart): x-axis
  `apr_severity_of_illness` sorted by `[Severity Cost Rank]`, columns
  `[Total Costs]`, line `[Cumulative Pct of Total Cost (Severity)]` on a
  secondary axis (0-100%)
- Table, Top 15 DRGs: `dim_drg[apr_drg_description]`, `[Total Discharges]`,
  `[Total Costs]`, `[Avg Cost per Discharge]`, sorted desc by
  `[Total Costs]`, with a **Top N visual filter** set to 15 by
  `[Total Costs]` (see the ALL-vs-ALLSELECTED note in §4.3 for why this
  table's ranking measure is safe to combine with a Top N filter). **Do not
  add `dim_mdc[apr_mdc_description]` as a second Columns field** — 6 DRGs
  (tracheostomy ×2, ECMO, and the three "O.R. procedure unrelated to
  principal diagnosis" DRGs) don't have one fixed MDC, so a second
  categorical column fragments those DRGs' totals across multiple rows even
  though the Top N filter is correctly scoped to the DRG field alone. Full
  writeup: `docs/decisions.md`, "DRG/MDC cost fragmentation bug" (2026-07-15).
- Separate small line/area chart, full 324-DRG cumulative curve (no Top N
  filter applied here): x-axis `dim_drg[DRG Cost Rank (Col)]` (the
  calculated column, not `apr_drg_description` — set the axis Type to
  Continuous and Range Minimum to `1` so the 324 DRGs render as a real
  numeric axis instead of 324 unreadable category ticks), y-axis
  `[Cumulative Pct of Total Cost (DRG)]`, to show the shape of the full
  Pareto curve (how many DRGs it takes to reach 80% of cost) even though the
  table above only lists the top 15 by name
- **New, 2026-07-09:** discharge-level cost concentration. The severity-tier
  Pareto above only has 5 buckets, which understates how concentrated cost
  really is at the level of individual discharges, the statistic ("the top
  X% of cases drive Y% of spend") most recognizable to a payer audience. Add
  a measure ranking individual discharges (not severity tiers or DRGs) by
  `total_costs` and bucket into percentiles (top 1%, top 5%, top 10%), shown
  as a small KPI card set or a compact bar chart next to the severity Pareto.
  This needs a new RANKX/percentile calculation over all 143,613 rows of
  `fact_discharges`, heavier than the tier-level ranking above; if DAX
  performance is a problem at that grain, compute it once in a new SQL mart
  instead (matching the existing "one mart per question" pattern) and import
  it for validation the same way the other six marts are used
- **New, 2026-07-09:** risk-of-mortality cross-cut, see §4.10. A small
  matrix or clustered chart, `apr_severity_of_illness` by
  `apr_risk_of_mortality`, value `[Total Costs]`, placed near the severity
  Pareto rather than replacing it. **Note, 2026-07-16:** if built as a
  clustered column chart, check the visual's own `...` > Sort by menu — it
  can carry an explicit "sort by value" override left over from before
  `apr_severity_of_illness` had a custom Sort By Column, which takes
  precedence over the field's default order and will keep showing cost order
  (Major, Moderate, Extreme, Minor, Undetermined) instead of tier order.
  Switch it to "sort by category" (ascending) to pick up
  Extreme → Major → Moderate → Minor → Undetermined.

### Page 3, Charge-to-Cost Ratio (Q2)

**Renamed narrative, 2026-07-09** (measure and title tag unchanged, page
title's framing corrected): describe this page as hospital pricing behavior
or a price-transparency signal, not as the payer's own cost exposure. Payers
negotiate contracted rates, they don't pay chargemaster billed charges, so
"markup" here is about how hospitals price relative to their own cost, most
relevant to self-pay and out-of-network contexts, not routine payer
reimbursement. Full reasoning: `docs/decisions.md`, "Charge-to-Cost Ratio's
narrative reframed."

**Reframed again, 2026-07-10 (review Fix 2), this time from "pricing
behavior" to a derived-cost disclosure.** SPARCS `total_costs` is not a
hospital's actual accounting cost — it's estimated by applying cost-to-charge
ratios (CCRs) to charges, and within a facility, charges explain a median R²
of 0.92 of cost variance, so the charge-to-cost ratio largely restates each
facility's assigned CCR rather than independently observed pricing. The page
tab was renamed from "Hospital Pricing Behavior (Q2)" to **"Charge-to-Cost
Ratio (Q2)"**. A title/subtitle text box was added to the canvas: bold title
**"Charge-to-Cost Ratio (SPARCS derived-cost basis)"**, subtitle *"Ratio of
billed charges to SPARCS estimated costs. SPARCS costs are derived from
cost-to-charge ratios, so this reflects each facility's assigned CCR, not
independently observed pricing."* A second caveat text box was added below
it: *"SPARCS `total_costs` is estimated by applying cost-to-charge ratios to
charges, not measured from hospital accounting. Within a facility, ~92% of
cost variation is explained by charges, so this ratio largely restates each
facility's assigned CCR. Read cross-facility differences as directional, and
compare to the national benchmark rather than treating any single facility's
ratio as a pricing decision."* No measure changes; the national-benchmark
reference cards below were kept exactly as specified. Full writeup:
`docs/decisions.md`, "Fix 2 finished: Page 3 reframed from 'pricing
behavior' to derived-cost charge-to-cost ratio."

- KPI cards: portfolio-wide `[Charge to Cost Ratio]`, highest and lowest
  facility ratio (cards filtered to `[Facility Markup Rank] = 1` and
  `= [Facility Count]`)
- **New, 2026-07-09:** a fifth KPI card pair for external context:
  `[National Avg Charge to Cost Ratio (CMS CCR-based, ~2020)]` and
  `[National Avg Charge to Cost Ratio (Bai and Anderson, 2012 Medicare data)]`
  (§4.9), placed next to the portfolio-wide ratio so a reviewer can see this
  region (2.95) sits at or below both national reference points. Caption the
  card with the vintage/methodology caveat from `docs/decisions.md`, don't
  present the comparison as exact
- Bubble/scatter chart: x-axis `[Charge to Cost Ratio]`, bubble size
  `[Total Discharges]`, color `dim_facility[sub_region]`, details/tooltip
  `dim_facility[facility_name]`. This is the single most information-dense
  visual on the page: it shows markup, facility size, and region together
  without inventing an "academic/community/rural" category the data
  dictionary doesn't define (see §4.4). **New, 2026-07-09:** add
  `[Is Low Volume Facility]` (§4.11) to the tooltip, so a reviewer sees the
  low-volume caveat on any small-bubble outlier before over-reading its ratio
- Bar chart: `[Charge to Cost Ratio]` by `dim_facility[facility_name]`,
  sorted desc, for reviewers who want the exact ranked list the bubble chart
  implies visually

### Page 4, Payer mix and Medicaid exposure (Q3)

- KPI cards: `[Government Share]`, `[Medicaid Share]` (renamed for this
  visual to "Medicaid Share (reported floor)", per below), both
  portfolio-wide
- 100% stacked bar chart: x-axis `dim_facility[facility_name]`, y-axis
  `[Total Discharges]` as a percentage, legend `dim_payer[payer_category]`,
  sorted by `[Government Share]` desc, so the most government/Medicaid-
  concentrated facilities read left to right. **Updated 2026-07-16:**
  `payer_category`'s Sort By Column (§2) makes the legend itself read
  Government → Commercial → Self-Pay → Other, instead of the previous
  plain-alphabetical Commercial/Government/Other/Self-Pay.
- Scatter chart, the financial-fragility view: x-axis `[Medicaid Share]`,
  y-axis `[Total Discharges]` (facility volume), color `dim_facility[sub_region]`,
  details `dim_facility[facility_name]`. The lower-right quadrant (high
  Medicaid share, low discharge volume) is the concrete visual answer to
  question 3's second half: which facilities are both Medicaid-concentrated
  and small enough to be exposed to a financial shock
- Page-specific filter: `dim_payer[payer_category]` (per §3)

**Updated 2026-07-10 (review Fix 1), Medicaid sensitivity band.** The
`[Medicaid Share]` card is a reported floor, not the full picture, because
of the `Managed Care, Unspecified` ambiguity documented in §4.12. Three
additions:

- The `[Medicaid Share]` KPI card's field was renamed for this visual
  (right-click the field pill in the Values well > "Rename for this
  visual") to **"Medicaid Share (reported floor)"**, then widened so the
  full label is not truncated.
- A new table visual, titled "Medicaid Share - Sensitivity Band," with
  `[Medicaid Share (Adjusted Midpoint)]` (renamed for this visual to
  "Central estimate (adjusted midpoint)") and
  `[Medicaid Share (Upper Bound)]` (renamed to "Ceiling (all-MCO)"),
  showing the 16.4%-27.1% range with 23.7% as the sourced-weight central
  estimate.
- A caption text box: `"Managed Care, Unspecified" (10.7% of discharges)
  may include Medicaid managed care; the band shows the range.`

Full validation, the sourced 0.68 weight, and the stress-test table are in
`docs/decisions.md`, "Fix 1 finished: Medicaid sensitivity band added to
Page 4."

### Page 5, Length of stay by facility and severity (Q4)

- KPI cards: `[Avg Length of Stay (Days)]`, `[Median Length of Stay (Days)]`,
  `[Pct Censored Stays]`, all portfolio-wide, so the censoring caveat is
  visible before anyone reads the detail chart
- Small multiples column chart (one small chart per `dim_facility[sub_region]`):
  x-axis `apr_severity_of_illness`, y-axis `[Avg Length of Stay (Days)]`. Small
  multiples let a reviewer compare the LOS-by-severity shape across all four
  sub-regions side by side, which is the actual comparison question 4 asks
  for (does LOS differ by location, holding severity constant), rather than
  one cluttered chart with every facility and severity combination overlaid
- Table: `dim_facility[facility_name]`, `apr_severity_of_illness`,
  `[Total Discharges]`, `[Avg Length of Stay (Days)]`,
  `[Median Length of Stay (Days)]`, `[Pct Censored Stays]`, for the detail
  view behind the small multiples
- **New, 2026-07-09:** patient-disposition cross-cut, see
  `docs/decisions.md`, "`patient_disposition` added as a supporting cross-cut
  on Page 5." Add a bar or 100% stacked bar of
  `fact_discharges[patient_disposition_group]` by `dim_facility[sub_region]`,
  so the "post-acute access" claim in Q4 is shown directly (where patients
  actually go after discharge) rather than only inferred from LOS.
  **Grouping finalized 2026-07-10** (previously an open item): the 19 raw
  `patient_disposition` values are grouped into 5 categories via a Power
  Query conditional column, `patient_disposition_group`, on
  `fact_discharges`: Home, Post-Acute Facility, Hospice/Expired, Transfer to
  Another Hospital, Other/Unplanned. Full value-to-group mapping and
  rationale: `docs/decisions.md`, "`patient_disposition` grouping resolved
  (2026-07-10, ahead of the Page 5 build)." Chart the grouped column, not the
  19 raw values

### Page 6, Urban vs. rural utilization (Q5)

- KPI cards: `[ED Utilization Pct]`, `[High Severity Pct]`, both portfolio-wide
- Matrix (utilization scorecard): rows `dim_facility[sub_region]`, columns
  `[Total Discharges]`, `[Pct of Total Volume]`, `[ED Utilization Pct]`,
  `[High Severity Pct]`, `[Avg Length of Stay (Days)]`,
  `[Avg Cost per Discharge]`, with data bars (conditional formatting) turned
  on for every numeric column. This single matrix is the direct answer to
  question 5: how utilization differs between the urban core and the rural
  periphery, all six comparison metrics side by side by region
- **New, 2026-07-09:** add `[Discharges per 10k Population]` (§4.9) as a
  seventh matrix column. Label it "Discharges per 10,000 population, by
  hospital location" on the visual itself, not "utilization by residents
  of," per the caveat in `docs/decisions.md` (hospital county is where the
  facility sits, not where patients live, so Capital District's rate likely
  overstates its own residents' true utilization due to referral inflow to
  the academic medical center). This is what upgrades the page from a raw-
  volume comparison to an actual rate comparison, and it's also what surfaces
  the Mohawk Valley finding: lowest per-capita utilization of any sub-region,
  yet the highest ED-utilization share, worth a callout text box on this page
  once built
- Page-specific filters: `fact_discharges[emergency_department_indicator]`,
  `fact_discharges[type_of_admission]` (per §3)

**Updated 2026-07-10 (review Fix 4), callout reworded and footnote added.**
The Mohawk Valley callout text box's body was reworded from a stated fact to
an explicit hypothesis (heading unchanged): *"Mohawk Valley shows the lowest
discharges-per-resident and the highest ED share. Because this counts
discharges where the hospital sits, not where the patient lives, this
pattern is consistent with residents leaving the region for planned care
and/or constrained non-emergency access — it is a signal to investigate, not
a settled utilization rate."* A footnote text box was added below the
Matrix: *"Per-capita = discharges at in-region hospitals ÷ in-region
residents; the two populations are not identical (patients travel).
Directional only."* No measure or number changes. Full writeup:
`docs/decisions.md`, "Fix 4 finished: Page 6 per-capita callout reworded
from fact to hypothesis."

---

## 6. Save and publish

- Save the `.pbix` into the `powerbi/` folder.
- Export a screenshot of each of the six pages to `outputs/`.
- Embed the screenshots (and a one-paragraph summary each) on
  neydalarson.com, and link the repo from the resume's Portfolio Projects
  section.
- Do the resume's healthcare-bullet final pass only after this step, per
  `PORTFOLIO_LOG.md`.

---

## 7. Validation against the marts

Cross-check the DAX against numbers already known to be correct before
trusting the dashboard:

| Check | Compare to |
|---|---|
| `[Total Costs]` filtered to `apr_severity_of_illness = "Extreme"`, and `[Pct of Total Cost (Severity)]` for the same filter | `mart_severity_cost_concentration.total_costs` / `.pct_of_total_cost` for the `Extreme` row |
| `[Total Costs]` and `[Avg Cost per Discharge]` filtered to one `dim_drg[apr_drg_description]` value | the matching row in `mart_drg_cost_concentration` |
| `[Charge to Cost Ratio]` filtered to one facility | `mart_facility_financials.charge_to_cost_ratio` for that facility |
| `[Medicaid Share]` (recomputed as a share of facility discharges) filtered to one facility | `mart_payer_mix_by_facility.pct_of_facility_discharges` for that facility's `Government`/`Medicaid` rows |
| `[Avg Length of Stay (Days)]` filtered to one facility and one severity tier | `mart_los_by_facility_severity.avg_length_of_stay_days` for that combination |
| `[ED Utilization Pct]` and `[High Severity Pct]` filtered to one sub-region | `mart_regional_utilization.ed_utilization_pct` / `.high_severity_pct` for that region |

If any of these disagree, trust the mart (it was built and spot-checked
first, see `docs/decisions.md`) and debug the DAX, not the other way around.

### 7a. Reference values (computed independently, 2026-07-09)

Actual target numbers, computed directly from `fact_discharges.csv` and the
`mart_*.csv` files (not from the running dashboard), so each page can be
checked against a known-correct value as it's built, not just at the end.

**Portfolio-wide (checks `[Total Discharges]`, `[Total Charges]`,
`[Total Costs]`, `[Charge to Cost Ratio]`, and related measures used across
every page):**

| Measure | Expected |
|---|---|
| Total Discharges | 143,613 |
| Facility Count | 24 |
| County Count | 14 |
| Total Charges | $6,694,244,423.54 |
| Total Costs | $2,265,824,365.27 |
| Charge to Cost Ratio | 2.9544 |
| Extreme Tier Cost Share | 24.68% (mart's rounded value: 24.7%) |
| Avg Length of Stay (Days) | 5.45 |
| Median Length of Stay (Days) | 3.0 |
| Pct Censored Stays | 0.04% (57 of 143,613) |
| ED Utilization Pct | 61.85% |
| High Severity Pct | 37.22% |
| Government Share | 64.83% |
| Medicaid Share | 16.38% |

**Page 2, severity Pareto** (source: `mart_severity_cost_concentration`,
ranked by cost; Extreme is rank 3, not 1, Major carries the largest share):

| Rank | Severity | Total Costs | % of Total | Cumulative % |
|---|---|---|---|---|
| 1 | Major | $721,948,240.88 | 31.9% | 31.9% |
| 2 | Moderate | $642,240,392.59 | 28.3% | 60.2% |
| 3 | Extreme | $559,246,582.62 | 24.7% | 84.9% |
| 4 | Minor | $342,273,826.55 | 15.1% | 100.0% |
| 5 | Undetermined | $115,322.63 | 0.0% | 100.0% |

**Page 2, Top 15 DRGs** (source: `mart_drg_cost_concentration`): rank 1 is
Septicemia and disseminated infections (11,830 discharges, $220,967,976
total, $18,678.61 avg, 9.8% of total cost); rank 15 is Other pneumonia
(2,420 discharges, $26,540,360 total, cumulative 33.8% through rank 15).
Full 15-row detail available on request or by reading the mart directly.

**Page 3, charge-to-cost ratio** (source: `mart_facility_financials`):
portfolio ratio 2.9544. Highest: Saratoga Hospital, 4.78 (rank 1). Lowest:
O'Connor Hospital, 1.03 (rank 24).

**Page 4, payer mix**: portfolio Government Share 64.83%, Medicaid Share
16.38%. Highest Medicaid-share facilities: St. Peter's - SPARC 78.9% (266
discharges), St. Peter's Addiction Recovery 73.3% (397), Ellis - Bellevue
Woman's 38.0% (3,548). Lowest: Margaretville Hospital 1.0%, Albany Medical
Center 4.8%.

**Page 5, length of stay by sub-region and severity** (computed from
`fact_discharges.csv`, matches what the small-multiples chart should show):

| Sub-region | Minor | Moderate | Major | Extreme |
|---|---|---|---|---|
| Capital District | 2.87 | 4.49 | 6.74 | 12.64 |
| North Country/Adirondack | 2.84 | 4.65 | 6.86 | 12.13 |
| Central NY/Catskill Foothills | 3.37 | 4.39 | 6.29 | 11.69 |
| Mohawk Valley | 3.80 | 4.90 | 5.40 | 7.64 |

**Page 6, regional utilization matrix** (source: `mart_regional_utilization`,
all 4 rows, this is the entire matrix):

| Sub-region | Discharges | % of Volume | ED % | High-Sev % | Avg LOS | Total Costs | Avg Cost |
|---|---|---|---|---|---|---|---|
| Capital District | 97,911 | 68.2% | 59.4% | 38.5% | 5.56 | $1,511,164,022.05 | $15,434.06 |
| North Country/Adirondack | 24,080 | 16.8% | 69.2% | 33.2% | 5.26 | $367,969,032.69 | $15,281.11 |
| Central NY/Catskill Foothills | 15,275 | 10.6% | 61.9% | 37.5% | 5.28 | $314,923,668.66 | $20,616.93 |
| Mohawk Valley | 6,347 | 4.4% | 71.5% | 32.9% | 4.90 | $71,767,641.87 | $11,307.33 |

Notable finding worth calling out in the eventual write-up: Mohawk Valley
(smallest, most rural sub-region) has the highest ED utilization (71.5%),
and Capital District (largest, most urban) has the lowest (59.4%), the
opposite of what "urban core vs. rural periphery" might suggest before
looking at the actual numbers.

### 7b. Reference values for the 2026-07-09 scope upgrade

Computed the same way as §7a, independently of the dashboard, so the new
measures have a known-correct target as they're built. Full source detail
and every caveat: `docs/decisions.md`, "Dashboard scope upgrade: synthesis
over sprawl."

**Facility Risk Score, top 8 of 19 general-acute facilities** (source:
`fact_discharges.csv` + `dim_facility.csv`, equal-weighted percentile
composite of Medicaid dependency, size fragility, and cost complexity;
**recomputed 2026-07-10 after the Fix 3 general-acute rescoping** — see the
2026-07-10 note in §4.8. The original table below this one, computed
2026-07-09 across all 24 facilities including the 5 Specialty/Satellite
units, is superseded and removed; that ranking's three-way tie at 63.8
included two Specialty/Satellite units — St. Mary's - Amsterdam Memorial
Campus and St. Peter's - SPARC — that are no longer compared against
general-acute hospitals):

| Facility | Sub-region | Discharges | Medicaid Share | Extreme-Tier Cost Share | Risk Score |
|---|---|---:|---:|---:|---:|
| Ellis Hospital | Capital District | 9,552 | 19.2% | 33.2% | 68.5 |
| Nathan Littauer Hospital | Mohawk Valley | 2,282 | 30.2% | 17.0% | 68.5 |
| Samaritan Hospital | Capital District | 9,912 | 27.0% | 26.3% | 66.7 |
| UVM Health Network - Champlain Valley Physicians Hospital | North Country/Adirondack | 8,072 | 18.6% | 25.1% | 61.1 |
| St. Mary's Healthcare | Mohawk Valley | 3,806 | 28.3% | 15.3% | 61.1 |
| Columbia Memorial Hospital | Central NY/Catskill Foothills | 3,051 | 15.4% | 21.9% | 57.4 |
| St. Peter's Hospital | Capital District | 24,768 | 20.8% | 26.0% | 57.4 |
| Mary Imogene Bassett Hospital | Central NY/Catskill Foothills | 9,910 | 16.2% | 23.9% | 53.7 |

Lowest of 19, for contrast: UVM Elizabethtown Community Hospital (31.5),
Margaretville Hospital (33.3), Albany Medical Center Hospital (33.3, the
region's largest facility by volume, so simply too large to score as
fragile despite a high Extreme-tier cost share). None of the top 8 above are
flagged low-volume (all exceed the 1,000-discharge threshold, §4.11),
unlike the pre-Fix-3 ranking where 2 of the top 3 were sub-300-discharge
specialty units.

**Discharges per 10,000 population** (source: `mart_regional_utilization` +
Census Bureau/ACS county estimates, §1):

| Sub-region | Population | Discharges | Rate per 10k |
|---|---:|---:|---:|
| Capital District | 906,000 | 97,911 | 1,080.8 |
| North Country/Adirondack | 227,450 | 24,080 | 1,058.9 |
| Central NY/Catskill Foothills | 194,914 | 15,275 | 783.6 |
| Mohawk Valley | 101,721 | 6,347 | 624.1 |

**External benchmark comparison:** this project's portfolio-wide Charge to
Cost Ratio is 2.9544, versus a national average near 3.1 (CMS-based
cost-to-charge ratio trend data, ~2020) and 3.4 (Bai and Anderson, *Health
Affairs*, 2015, 2012 Medicare data). This region's markup sits below both.

**Small-n facilities (under 1,000 annual discharges), 9 of 24:** Margaretville
Hospital (100), O'Connor Hospital (180), Delaware Valley Hospital (180),
St. Mary's Healthcare - Amsterdam Memorial Campus (259), St. Peter's Hospital
- SPARC (266), St. Peter's Addiction Recovery Center (397), Cobleskill
Regional Hospital (455), UVM Elizabethtown Community Hospital (736), UVM
Alice Hyde Medical Center (835).
