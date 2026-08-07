# Project Context: Healthcare Operations & Finance (Payer Perspective)

> **Purpose of this file:** this is the working scratchpad for the project's
> reasoning: region, data, and question selection, kept as detailed as it
> needs to be. The project's actual `README.md` stays concise and reader-facing;
> this file is where the "why" lives in full.

---

## 1. Why this project, and why this data

The project analyzes real 2024 hospital discharge data from a specific region
of New York State, read the way a **health insurer's medical-economics /
network-analytics team** would read it, not the way a hospital's own finance
team would. A payer cares about where cost concentrates, how much of a
region's care is tied to Medicaid, whether small rural facilities are at
financial risk (a network-continuity problem for the payer, not just a
provider problem), and whether utilization patterns (length of stay, ED use)
suggest opportunities for utilization management.

This region was chosen deliberately, not just because the file was a
convenient size: it contains one large academic medical center, several
mid-size community hospitals, and multiple small rural hospitals, inside a
single, real, live policy environment where Medicaid funding cuts are
projected to materially affect coverage starting in 2026. That combination
makes the analysis genuinely load-bearing rather than a generic BI exercise.

## 2. The region we're studying

**Data source:** NY State SPARCS (Statewide Planning and Research Cooperative
System), de-identified hospital inpatient discharge records, pulled directly
from the state's public Socrata API for `health_service_area = 'Capital/Adirondacks'`,
discharge year 2024. Source dataset: [Hospital Inpatient Discharges (SPARCS
De-Identified): 2024](https://health.data.ny.gov/Health/Hospital-Inpatient-Discharges-SPARCS-De-Identified/sf4k-39ay/about_data).
`Capital/Adirondacks` is the state's own administrative label for this
region (a NYS DOH-defined Health Service Area); it is **not** a single
natural, contiguous geography, and that matters for how we interpret it (see
below).

**Important field note:** `hospital_county` in this data is the county
**where the hospital is located**, not where the patient lives. Patients from
counties with no hospital of their own (e.g. Hamilton, Washington, Greene,
part of the broader Health Service Area but absent from our facility list)
are presumably traveling to a hospital in one of the 14 counties below.

**The 14 counties actually present in our extract**, grouped into the
sub-regions they naturally fall into (all counts below are computed directly
from the downloaded file, not estimated):

| Sub-region | Counties | Discharge rows | Share |
|---|---|---:|---:|
| Capital District (urban/suburban core) | Albany, Schenectady, Rensselaer, Saratoga | 97,911 | 68.2% |
| North Country / Adirondack (rural, borders Canada/VT, Adirondack Park) | Warren, Clinton, Essex, Franklin | 24,080 | 16.8% |
| Central NY / Catskill foothills (rural, agricultural, "Leatherstocking" region) | Otsego, Delaware, Schoharie, Columbia | 15,275 | 10.6% |
| Mohawk Valley (rural/small-town, historically industrial) | Montgomery, Fulton | 6,347 | 4.4% |

Total: 143,613 rows. Matches the API row count exactly, confirmed on
download.

**Facility-to-county detail** (every facility in the file, grounded in the
actual data):

| County | Facility | Rows |
|---|---|---:|
| Albany | Albany Medical Center Hospital | 36,882 |
| Albany | St. Peter's Hospital | 24,768 |
| Albany | St. Peter's Addiction Recovery Center | 397 |
| Schenectady | Ellis Hospital | 9,552 |
| Schenectady | Ellis Hospital – Bellevue Woman's Care Center Division | 3,548 |
| Schenectady | Sunnyview Hospital and Rehabilitation Center | 2,245 |
| Rensselaer | Samaritan Hospital | 9,912 |
| Rensselaer | St. Peter's Hospital – SPARC | 266 |
| Saratoga | Saratoga Hospital | 10,341 |
| Warren | Glens Falls Hospital | 12,271 |
| Clinton | UVM Health Network – Champlain Valley Physicians Hospital | 8,072 |
| Essex | UVM Health Network – Elizabethtown Community Hospital | 736 |
| Franklin | Adirondack Medical Center – Saranac Lake Site | 2,166 |
| Franklin | UVM Health Network – Alice Hyde Medical Center | 835 |
| Otsego | Mary Imogene Bassett Hospital | 9,910 |
| Otsego | A.O. Fox Memorial Hospital | 1,399 |
| Delaware | Delaware Valley Hospital Inc | 180 |
| Delaware | O'Connor Hospital | 180 |
| Delaware | Margaretville Hospital | 100 |
| Schoharie | Cobleskill Regional Hospital | 455 |
| Columbia | Columbia Memorial Hospital | 3,051 |
| Montgomery | St. Mary's Healthcare | 3,806 |
| Montgomery | St. Mary's Healthcare – Amsterdam Memorial Campus | 259 |
| Fulton | Nathan Littauer Hospital | 2,282 |

**Is Franklin County in our area? Yes, directly, not adjacently.**
Franklin County sits in the far north of New York, bordering Quebec, Canada,
and lies partly within the Adirondack Park. It is one of the 14 counties in
our downloaded extract (North Country / Adirondack sub-region), represented
by two facilities: Adirondack Medical Center's Saranac Lake site and Alice
Hyde Medical Center in Malone: 3,001 discharge rows, 2.1% of our dataset.
Its relevance isn't secondhand: the poverty and rural-access dynamics
described in secondary research (Franklin among the highest-poverty rural
counties in NY) describe a population that literally shows up in our fact
table, not a neighboring area we're inferring about by proximity.

**Regional profile** (condensed from research done earlier in this project;
full citations in the chat record / can be added here on request):

- Capital District core (Albany-Schenectady-Troy metro): ~906,000 people,
  median age 40.5, median household income ~$86,000 (ACS 5-year estimate),
  a stable, government/healthcare/education-anchored economy.
- Rural periphery (North Country, Mohawk Valley, Catskill foothills): losing
  population while the state grows, aging faster than the state average
  (Hamilton County: ~34-36% of residents 65+, Census Bureau QuickFacts 2024
  vintage; a prior "25%" figure here was stale, corrected 2026-07-10, see
  `docs/decisions.md` and `docs/sources.md` §5), and home to some of NY's highest
  rural poverty rates (Franklin County notably).
- Statewide rural hospital finance: 62% of NY's rural hospitals reported
  financial losses in 2023–2024; roughly 1 in 3 rural inpatient hospitals is
  considered at imminent risk of closure.
- Medicaid exposure: 27% of the rural NY population (~205,000 people) was on
  Medicaid as of May 2025; NYS DOH has warned that federal funding changes
  taking effect in 2026 could add ~450,000 uninsured New Yorkers this year,
  with a larger Medicaid coverage-loss wave to follow.

**Sub-region population (added 2026-07-09, Census Bureau / ACS estimates,
2023-2024 vintage), needed to normalize utilization by population rather than
raw volume; full rationale in `docs/decisions.md`, "Per-capita utilization
measure added to Page 6":**

| Sub-region | Population | Source counties |
|---|---:|---|
| Capital District | ~906,000 | Albany, Schenectady, Rensselaer, Saratoga |
| North Country/Adirondack | ~227,450 | Warren 65,288 + Clinton 78,493 + Essex 36,973 + Franklin 46,696 |
| Central NY/Catskill Foothills | ~194,914 | Otsego 60,100 + Delaware 44,410 + Schoharie 30,105 + Columbia 60,299 |
| Mohawk Valley | ~101,721 | Montgomery 49,648 + Fulton 52,073 |

Discharges per 10,000 population, by hospital location, not by patient
residence (see the `hospital_county` field note above): Capital District
1,080.8; North Country/Adirondack 1,058.9; Central NY/Catskill Foothills
783.6; Mohawk Valley 624.1. Mohawk Valley has the lowest per-capita inpatient
utilization of any sub-region and, per `mart_regional_utilization`, the
highest ED-utilization share (71.5%), a combination consistent with
constrained non-emergency access rather than simply higher overall
utilization.

This is why several of the smaller facilities in our own data (Adirondack
Medical Center, Alice Hyde, Nathan Littauer, Cobleskill Regional, Delaware
Valley, Margaretville, Elizabethtown Community) aren't just "small hospitals"
in the abstract; they're the concrete instances of the exact rural-hospital
fragility described in current NY health-policy reporting.

## 3. First look at the data

- **Extracted:** 2026-07-07, via `https://health.data.ny.gov/resource/sf4k-39ay.csv?$where=health_service_area='Capital/Adirondacks'&$limit=200000`
- **Saved to:** `data/raw/sparcs_inpatient_discharges_2024.csv`
- **Size:** 143,613 rows (confirmed against the API's own count), 33 columns, ~61MB
- **Grain:** one row per hospital discharge (inpatient stay)

**Columns as published** (plain-English pass, not yet a formal data
dictionary; that comes after full profiling):

| Column | What it is |
|---|---|
| `health_service_area`, `hospital_county` | Facility's region/county (constant region here) |
| `operating_certificate_number`, `permanent_facility_id`, `facility_name` | Facility identifiers; IDs are zero-padded, must stay text |
| `age_group`, `zip_code`, `gender`, `race`, `ethnicity` | Patient demographics (banded/masked for privacy, no direct identifiers) |
| `length_of_stay` | Days in the hospital; needs validation (SPARCS sometimes buckets very long stays as text) |
| `type_of_admission`, `patient_disposition` | How the patient was admitted / where they went after discharge |
| `discharge_year` | Constant (2024) in this extract; no year-over-year trend possible from this file alone |
| `ccsr_diagnosis_code/description`, `ccsr_procedure_code/description` | Diagnosis and (if applicable) procedure classification; procedure fields blank when none performed |
| `apr_drg_code/description`, `apr_mdc_code/description` | All Patient Refined DRG, the primary case-grouping/severity classification |
| `apr_severity_of_illness_code/description`, `apr_risk_of_mortality` | Clinical severity tiers; central to the payer/risk-adjustment lens |
| `apr_medical_surgical` | Medical vs. surgical case flag |
| `payment_typology_1/2/3` | Payer(s) for the stay: primary/secondary/tertiary, blank when not applicable |
| `birth_weight` | Populated only for newborn cases |
| `emergency_department_indicator` | Whether the stay originated in the ED |
| `total_charges`, `total_costs` | Billed amount vs. actual cost of care; stored as quoted text in the CSV, need numeric casting |

**Known/likely data-quality issues to confirm during full profiling** (carried
over from initial inspection, not yet exhaustively verified):

- Zero-padded facility/certificate IDs must be kept as text end-to-end.
- `zip_code` mixes 3-digit truncated codes with the literal string `"OOS"`
  (out of state), categorical/text, not numeric.
- Blanks in `ccsr_procedure_*` and `payment_typology_2/3` are expected
  (no procedure / single payer), not missing data in the problematic sense;
  needs explicit documentation so it isn't "cleaned" incorrectly.
- `total_charges`/`total_costs` need casting from text to numeric; watch for
  stray characters before a blanket cast.
- `length_of_stay` needs a check for non-numeric long-stay codes.
- No unique row or patient identifier exists in this file; duplicate rows
  are genuinely ambiguous (could be two different real patients with
  identical recorded characteristics) and need a documented, honest handling
  decision rather than a mechanical dedupe.
- `facility_name` is all-caps and inconsistent in punctuation, cosmetic,
  low priority.

A full profiling pass (null rates, distinct-value counts, ranges, duplicate
check) is the next step before any cleaning code is written.

## 4. Perspective & locked business questions

**Framing:** the project is written from the perspective of a health
insurer's medical-economics / network-analytics function, not a hospital's
internal finance team. That reframes the same columns around cost
concentration, risk exposure, and network adequacy rather than hospital
revenue.

**Locked business questions:**

1. Where is cost concentrated? What share of total spend comes from the
   highest-severity tier of cases, and which DRGs/conditions drive it?
2. What does the charge-to-cost ratio look like by facility, and does it vary
   systematically between the academic center, mid-size community hospitals,
   and small rural facilities?
3. What's the payer-mix exposure by facility and county, specifically,
   which facilities are most Medicaid-concentrated, and how does that overlap
   with the facilities most likely to be financially distressed?
4. Does length of stay differ by facility size/location for comparable
   severity, and what would that imply about post-acute access in rural
   counties?
5. How does utilization (volume, severity mix, ED share) differ between the
   urban core and the rural periphery, and what would that mean for network
   design if this were an actual payer's coverage area?

**Extended 2026-07-09** (portfolio-value review, not a change to the five
questions above): each question now carries a second-order cut using data
already in the model, plus a synthesis layer on Page 1 that ranks all 24
facilities on a combined risk signal instead of leaving five findings
separate. Full detail in `docs/decisions.md`, "Dashboard scope upgrade:
synthesis over sprawl."

## 5. Current status & what's left

Everything through the SQL layer is done and validated: raw data sourced,
profiled, modeled into a star schema, and built/exported via
`src/run_pipeline.py` (143,613-row `fact_discharges`, zero orphan foreign
keys, all six marts spot-checked). `README.md`'s architecture/reproduction
sections are current. `docs/powerbi_guide.md` is rewritten against the real
schema and is now being built from directly in Power BI Desktop.

**In progress: the Power BI dashboard build.** Data is loaded (all 13
tables: six dimensions, `fact_discharges`, six marts), the six star-schema
relationships are built, and every DAX measure in `docs/powerbi_guide.md`
§4 exists in the `_Measures` table, spot-checked against `fact_discharges.csv`
directly (Total Discharges, Total Charges, Total Costs, and Charge to Cost
Ratio all matched exactly). Pages 1 (Overview) and 2 (Cost concentration,
Q1) are the furthest along; pages 3 through 6 are not yet built. One real
DAX bug was found and fixed along the way (`ALLSELECTED` interacting badly
with a visual-level filter on the Page 2 "Extreme-tier cost share" card);
full detail in `docs/decisions.md` under "Power BI dashboard build: findings
from the actual build session." A full expected-value reference (portfolio-
wide KPIs plus per-page breakdowns, computed independently from the mart
files and `fact_discharges.csv`) now exists to validate each remaining page
against as it's built; see `docs/powerbi_guide.md` §7.

**Also as of 2026-07-09:** a portfolio-value review upgraded the dashboard
plan itself, before pages 3-6 were built. Pages 2, 3, 5, and 6 each gained a
second-order cut (discharge-level cost percentiles and a mortality-risk
cross-cut on Page 2; an external benchmark and a low-volume flag on Page 3;
a patient-disposition cross-cut on Page 5; a per-capita utilization rate on
Page 6), none of which are built in the `.pbix` yet. Full detail, including
the new measures' methodology and every caveat, in `docs/decisions.md`,
"Dashboard scope upgrade: synthesis over sprawl," and the corresponding
sections of `docs/powerbi_guide.md`.

**Update, later on 2026-07-09:** Page 1 has now been reworked into the
Executive Summary. The `_SubRegionPopulation` table and relationship are
built, all 11 remaining measures from `docs/powerbi_guide.md` §4.8-4.11 exist
in `_Measures`, and the Facility Risk Score table (top 8 by risk score) plus
a data-grounded recommendations text box are on the page. Two real DAX bugs
were found and fixed in the Facility Risk Score composite along the way, both
insufficient `ALL()` scope; full root-cause writeup in `docs/decisions.md`
("Page 1 Executive Summary build" section), including a note that
`docs/powerbi_guide.md` §4.8 itself needs correcting, not just the built
model. Validated against the documented reference ranking: top three tied at
63.8 (Nathan Littauer Hospital, St. Mary's Healthcare - Amsterdam Memorial
Campus, St. Peter's Hospital - SPARC), low end at 33.3/37.7 (Albany Medical
Center Hospital, Saratoga Hospital), matching exactly.

**Update, later still on 2026-07-09:** stress-testing Page 1 against the
global severity slicer surfaced a third real DAX bug (the same class as the
two above, an unlocked filter letting the severity slicer distort the
Facility Risk Score composite, in this case producing Extreme Cost Share
values over 1,000,000%) plus a mis-bound table field (the "Medicaid %" column
was reading the wrong measure). Both fixed and validated: every input to
Facility Risk Score now stays fixed regardless of what's selected on the
severity slicer. Full writeup in `docs/decisions.md`, "A third real bug:
Facility Risk Score under the global severity slicer." Page 1 (the Executive
Summary) is now complete, including the layout fix. **Not yet done:** pages 3
through 6.

**Update, 2026-07-09 (later session): Page 2 (Cost concentration, Q1) is now
complete**, including the two 2026-07-09 scope-upgrade additions (discharge-
level cost concentration cards and the risk-of-mortality cross-cut). Final
page holds 8 visuals: the two header KPI cards, the severity Pareto combo
chart, the Top 15 DRG table (Top N = 15 filter), the full 324-DRG cumulative
curve, three new discharge-level percentile cards (Top 1/5/10% Discharge Cost
Share: 10.88% / 27.53% / 40.03%), and a new clustered column chart crossing
`apr_severity_of_illness` by `apr_risk_of_mortality` on `Total Costs` (built
as a clustered column chart rather than a matrix, since the Matrix icon
couldn't be reliably located in the Visualizations pane during this session;
functionally equivalent to what the guide asked for). All values validated
against `docs/powerbi_guide.md` §7a and matched (within a $1 display-rounding
difference on one DRG total). Full detail, including the Table/Card
visual-type icon workaround used throughout this page's build, in
`docs/decisions.md`, "Page 2 (Cost concentration, Q1) build completed."

**Update, 2026-07-09 (same session): Page 3 (Hospital pricing behavior,
charge-to-cost markup, Q2) is now complete.** Built by duplicating the Page 2
tab, stripping it down to the three shared slicers, then adding the
Page 3-specific content: five KPI cards (portfolio `Charge to Cost Ratio`
2.95, highest facility ratio 4.78, lowest facility ratio 1.03, and the two
national benchmark measures 3.10 and 3.40), a scatter/bubble chart (x-axis
`Charge to Cost Ratio`, size `Total Discharges`, color `sub_region`, tooltip
`Is Low Volume Facility`), and a bar chart (`Charge to Cost Ratio` by
`facility_name`, sorted descending). The highest/lowest cards use two new
DAX measures (`Highest Facility Ratio`, `Lowest Facility Ratio`) instead of
the guide's originally-specified visual-level filter, after that Filters-pane
control proved unresponsive in this session; full root-cause detail and the
DAX in `docs/decisions.md`. All values validated against
`docs/powerbi_guide.md` §7a and matched exactly, including the bar chart's
rank order (Saratoga Hospital highest, O'Connor Hospital lowest, confirmed by
scrolling the full sorted list).

**Update, 2026-07-09 (later session): Page 4 (Payer mix and Medicaid
exposure, Q3) is now complete.** Before building, a page-numbering
discrepancy surfaced and was resolved: the build request's own
description of "Page 4" matched `docs/powerbi_guide.md`'s Page 5 (length of
stay, Q4) rather than its actual Page 4 (payer mix, Q3); confirmed to build
the guide's real Page 4 instead, leaving Page 5 and its unresolved
`patient_disposition` grouping item for a future session. Page created by
duplicating the Page 3 tab, stripped to the three shared slicers, then built
with two KPI cards (`Government Share` 64.83%, `Medicaid Share` 16.38%, both
portfolio-wide), a 100% stacked bar chart (`facility_name` by
`payer_category`, sorted descending by `Government Share`), and a scatter
chart (`Medicaid Share` by `Total Discharges`, colored by `sub_region`,
detailed by `facility_name`), plus the page-specific `payer_category` filter.
All values validated against `docs/powerbi_guide.md` §7a, including two
spot-checked scatter points (St. Peter's Hospital - SPARC and Albany Medical
Center Hospital) that matched the documented per-facility reference exactly.
One new Power BI gotcha found and worked around: the bar chart's "sort by
`Government Share`" requirement needed that field added to the visual's
Tooltips well first, since Power BI's Sort by menu only offers fields already
bound to the visual. Full detail in `docs/decisions.md`, "Page 4 (Payer mix
and Medicaid exposure, Q3) build completed." **Not yet done:** pages 5 and 6.

**Update, 2026-07-10: Page 5 (Length of stay by facility and severity, Q4)
is now complete**, including resolving the `patient_disposition` grouping
open item carried over from the 2026-07-09 scope upgrade. The 19 raw
`patient_disposition` values were pulled directly from `fact_discharges.csv`,
two grouping options were considered, and the 5-category version was
confirmed and built as a Power Query conditional column
(`patient_disposition_group`) on `fact_discharges`. Full distribution,
rationale, and the finalized mapping are in `docs/decisions.md`,
"`patient_disposition` grouping resolved (2026-07-10, ahead of the Page 5
build)."

Page created by duplicating the Page 4 tab and stripping it to the three
shared slicers. This build hit one data-loss incident (a stray click closed
the file without a save prompt, discarding in-progress work); the stripped stub was manually
recreated and saved, and the build resumed from there. The
final page holds three KPI cards (`Avg Length of Stay (Days)` 5.45,
`Median Length of Stay (Days)` 3.00, `Pct Censored Stays` 0.04%), a small
multiples clustered column chart (`apr_severity_of_illness` by
`[Avg Length of Stay (Days)]`, small multiples by `sub_region`), a Matrix
visual standing in for the guide's suggested Table (same icon-grid
limitation already documented on Page 2), and a 100% stacked bar chart
crossing `sub_region` by the new `patient_disposition_group` column. All
values validated against `docs/powerbi_guide.md` §7a and
`mart_los_by_facility_severity.csv` directly: two small-multiples spot
checks (Capital District/Extreme 12.64, Mohawk Valley/Extreme 7.64) and one
Matrix facility+severity spot check (Albany Medical Center Hospital/Extreme:
4,227 discharges, 16.07 avg days, 11.00 median days, 0.35% censored) all
matched exactly. Confirmed non-overlapping via a full-page screenshot with
the side panes collapsed, then saved with Ctrl+S and the title-bar timestamp
confirmed. Afterward, the page was stress-tested under all three global
slicers, individually and combined, specifically because every real DAX bug
found earlier in this project only surfaced under slicer interaction; every
KPI, chart, and table value was independently recomputed from the raw CSVs
under four different filter combinations and matched exactly each time, with
no `ALL()`/`ALLSELECTED` override bugs found. Full detail in
`docs/decisions.md`, "Page 5 (Length of stay by facility and severity, Q4)
built (2026-07-10)" and "Page 5 stress-tested under the global slicers, no
bugs found." **Not yet done:** Page 6.

**Update, 2026-07-10 (same session): Page 6 (Urban vs. rural utilization,
Q5), the sixth and final dashboard page, is now complete.** Page created by
duplicating the Page 5 tab and stripping it to the three shared slicers,
including removing a leftover `payer_category` page filter carried over from
the Page 4 to Page 5 to Page 6 duplication chain. The final page holds two
portfolio-wide KPI cards (`ED Utilization Pct` 61.85%, `High Severity Pct`
37.22%), a seven-column Matrix (rows = `sub_region`; columns = Total
Discharges, Pct of Total Volume, ED Utilization Pct, High Severity Pct, Avg
Length of Stay, Avg Cost per Discharge, and `Discharges per 10,000
population, by hospital location`, all with data bars), the two page-specific
filters (`emergency_department_indicator`, `type_of_admission`), and a
callout text box on the Mohawk Valley finding (lowest per-capita utilization,
highest ED-utilization share of any sub-region). Two real DAX bugs were found
and fixed during the build and stress test, both the same root-cause pattern
already seen three times on Page 1: a `CALCULATE` filter silently overriding
an existing filter on the same column rather than intersecting with it. The
first (`Sub-Region Population` returning wrong per-capita values, caused by
the `_SubRegionPopulation` relationship's documented single-direction
cross-filter setting) was fixed at the measure level with `CROSSFILTER (...,
BOTH )`, deliberately leaving the locked relationship setting untouched. The
second (`High Severity Pct` reading an impossible 382.95% under an
Extreme-only severity slicer selection) was fixed by wrapping the measure's
boolean filter in `KEEPFILTERS`. Both fixes were verified against independent
Python recomputations from `fact_discharges.csv` joined to `dim_facility.csv`
and matched exactly. The finished page was then stress-tested under an
Extreme-only severity filter, a Mohawk Valley-only sub-region filter, and
with all filters cleared; every KPI card and Matrix value matched the
independent recomputation each time, and clearing all filters restored the
exact baseline (143,613 / 61.85% / 37.22% / 5.45 / $15,777.29). Confirmed
non-overlapping via a full-page screenshot with all four side panes
collapsed, then saved with Ctrl+S and the title-bar timestamp confirmed. Full
detail in `docs/decisions.md`, "Page 6 (Urban vs. rural utilization, Q5)
built (2026-07-10)."

**All six dashboard pages are now complete.** The next phase per
`docs/powerbi_guide.md` §6 is saving the `.pbix` into the project's
`powerbi/` folder and exporting page screenshots into `outputs/` (both
currently empty), followed by a final documentation pass across the whole
project. That phase has not been started yet and needs to be confirmed
before beginning.

**Update, 2026-07-10 (same session): a full six-page QA pass found one real
gap.** Page 1 (Executive Summary) was missing 4 of its 5 specified top-row
KPI cards (`Total Discharges`, `Facility Count`, `County Count`,
`Charge to Cost Ratio`; only `Total Costs` existed). Rebuilt all four and
verified all five against an independent Python recomputation (144K / 24 /
14 / 2.27bn / 2.95). Pages 2 through 6 were confirmed complete against
`docs/powerbi_guide.md` §5's spec, no other gaps found. Full detail in
`docs/decisions.md`, "Full six-page QA pass (2026-07-10, same session)."

**Update, 2026-07-16: current finished picture.** All five senior-review
fixes are complete (see `docs/review_findings_and_fixes.md` status board),
and the reference mockup `outputs/dashboard_six_page_mockup.html` was
regenerated 2026-07-16 to match that post-fix state — it previously still
showed the pre-fix dashboard for Fixes 1-4 (Page 1 "top 8 of 24" with the old
63.8 tie, Page 3 "Hospital pricing behavior," no Page 4 Medicaid band, Page 6
callout stated as fact). Every regenerated value was re-derived independently
from `data/processed/`; full writeup in `docs/decisions.md`, "Mockup
regenerated to the post-review state" (2026-07-16). The `.pbix` now sits in
`powerbi/` (the "both currently empty" note in the 2026-07-10 paragraph above
is superseded). **Still outstanding — the one remaining piece of Task E:**
exporting the six *live* page screenshots from the `.pbix` into `outputs/`
(the HTML mockup is a reference companion, not a substitute), then a final
confirmation pass across `README.md`, this section, and the status board.

Full phase-by-phase history of how the project got here: §6 below.

## 6. Development log

High-level record of how this project was actually built, phase by phase.
Every phase below has its full detail (reasoning, data, SQL) in
`docs/decisions.md` and `docs/data_dictionary.md`; this is the map, not the
territory.

**Phase 1: Source & scope (data pivot).** Reversed the original plan, a
seeded synthetic generator, in favor of a real, public, de-identified
dataset, specifically to demonstrate cleaning data whose messiness wasn't
engineered by us. Sourced NY SPARCS hospital discharge records for the
`Capital/Adirondacks` region, 2024 (143,613 rows), via the state's public
Socrata API. Reframed the project from a hospital's internal finance view to
a health insurer's (payer) medical-economics perspective. Researched the
region's demographics, economy, and rural-hospital-finance context (§1-2
above) to ground why the analysis matters, not just what it measures.

**Phase 2: Profiling & cleaning decisions.** Full profile of all 143,613
rows / 33 columns (nulls, cardinality, duplicates, categorical breakdowns).
Four cleaning decisions resolved and logged: coalescing the payer field
across its three slots, flooring/flagging censored `"120+"` length-of-stay
values, keeping (not deduping) the exact-duplicate rows (70 rows sit in
exact-duplicate groups; 36 would be removed by a keep-first dedupe) given no
patient ID exists to disambiguate them, and merging Alice Hyde Medical Center's two
source facility IDs into one after investigating and ruling out both an
ownership-change theory and a clinically-distinct-population theory.

**Phase 3: Star schema design.** Designed `fact_discharges` (grain: one
discharge) plus six dimensions. Three design forks resolved: demographics
kept flat on the fact table rather than a `dim_patient_profile` (no stable
patient entity exists), a `payer_category` rollup added to `dim_payer`
(Government/Commercial/Self-Pay/Other) to directly support the Medicaid-
exposure question, and no `dim_date` (the public file has no real dates,
only a constant `discharge_year`, which was dropped entirely).

**Phase 4: SQL layer build & validation.** Built `sql/01_staging` →
`02_dimensions` → `03_facts` → `04_marts` in DuckDB, plus
`src/fetch_data.py`, `src/profile_data.py`, and `src/run_pipeline.py`. Found
and fixed one real bug on first run: `dim_drg` initially carried MDC as a
DRG attribute, which fanned `fact_discharges` out past the raw row count.
Root cause was genuine APR-DRG grouper behavior (six DRG codes, tracheostomy/
ECMO/unrelated-O.R.-procedure, legitimately span multiple MDCs), not a data
error; fixed by making `dim_mdc` its own independent dimension. Re-validated
end to end: fact row count matches the raw extract exactly, zero orphan
foreign keys, all six marts (one per locked business question) spot-checked.

**Phase 5: Power BI dashboard build. In progress, started 2026-07-09.**
First load attempt used `Get Data > Folder` pointed at `data/processed/`,
which returned a file-listing table instead of the actual CSV contents
(the Folder connector's "Combine" step needs every file to share one
schema, which doesn't hold across six dimensions, one fact table, and six
differently-shaped marts). Corrected by importing each of the 13 files
individually via `Get Data > Text/CSV`, per the guide. "Autodetect new
relationships after data is loaded" was turned off before this, since
several marts share column names with the star schema on purpose (they're
self-contained validation copies) and autodetect could otherwise wire up
unwanted relationships silently. All six dimension-to-fact relationships
were then built by hand and confirmed correct (1-side to dimension, many-side
to `fact_discharges`, single direction). Every measure in `docs/powerbi_guide.md`
§4 was created in `_Measures` and spot-checked against independently
computed values from the raw file: Total Discharges (143,613), Total
Charges ($6,694,244,423.54), Total Costs ($2,265,824,365.27), and Charge to
Cost Ratio (2.9544) all matched exactly.

One real DAX bug found and fixed while building Page 2's "Extreme-tier cost
share" KPI card: pairing the existing `[Pct of Total Cost (Severity)]`
measure with a visual-level filter pinned to `apr_severity_of_illness =
"Extreme"` always returned 1.00, because `ALLSELECTED` in that measure's
denominator does not strip out a visual-level filter (it treats it like an
externally selected context, the same as a slicer). Fixed by adding a new,
self-contained `Extreme Tier Cost Share` measure that hardcodes both sides
of the ratio in DAX instead of depending on a Filters-pane filter; verified
at 24.68% against the raw data. Full root-cause writeup, plus a related
gotcha about same-named columns repeating across `fact_discharges` and
several `mart_*` tables (a dragged field can silently filter nothing if
it's pulled from the wrong table), in `docs/decisions.md`.

Pages 1 and 2 are partially built; pages 3 through 6 remain. A complete
expected-value reference (portfolio-wide KPIs and per-page breakdowns,
independently computed from the mart CSVs and `fact_discharges.csv`) was
produced to validate every remaining page against, now folded into
`docs/powerbi_guide.md` §7.

**Phase 6: Portfolio-value review and scope upgrade (2026-07-09).** Before
building pages 3-6, ran a portfolio-value review of the five locked business
questions and their KPIs against what would actually read as senior-level
work to a hiring manager, rather than competent-but-junior work. Two rounds
of findings, both folded into the build plan rather than left as chat notes:
first, framing gaps in the existing questions (a discharge-level cost
percentile view was missing, the charge-to-cost-ratio narrative overstated
what a payer actually cares about, utilization was measured in raw volume
instead of per capita, and two already-collected columns, `patient_disposition`
and `apr_risk_of_mortality`, were unused); second, a set of "what would make
this senior, not just correct" additions (a composite Facility Risk Score
synthesizing multiple signals into one ranked, decision-ready output, a
recommendations layer, small-n confidence flagging, and an external
benchmark). Decision, made explicitly rather than by default: keep the
dashboard at six pages and fold every addition into an existing page,
upgrading Page 1 into a true executive-summary/synthesis page, rather than
letting the page count grow. Two items needed genuinely new external data
(sub-region population for per-capita rates, a national charge-to-cost
benchmark) and were researched and cited rather than estimated. Full
methodology, every new measure, every caveat, and the real computed reference
values (including the Facility Risk Score ranking) are in `docs/decisions.md`,
"Dashboard scope upgrade: synthesis over sprawl," with the corresponding
build instructions in `docs/powerbi_guide.md`. Not yet done: none of this is
built in the `.pbix` yet, including Page 1, which needs reworking to this new
spec even though it was already partially built under the old design.

**Phase 5 continued: Page 1 rebuilt as the Executive Summary (2026-07-09,
same day).** Built the `_SubRegionPopulation` reference table (4 rows,
manually entered) and its relationship to `dim_facility`, then added all 11
remaining measures from `docs/powerbi_guide.md` §4.8-4.11 to `_Measures`.
Found and fixed two real DAX bugs while building the Page 1 table, both in
the Facility Risk Score composite's three percentile measures, both
insufficient `ALL()` scope copied verbatim from the guide: first, the
facility-count denominator used a bare `DISTINCTCOUNT` with no `ALL()`
wrapper, so it evaluated to 1 in row context and produced a blank score on
every row but the grand total; second, after fixing that, `ALL()` was scoped
to a single column (`facility_name`) rather than the whole `dim_facility`
table, so once the table visual also carried `sub_region`, the row context's
sub-region filter survived and rankings were computed within one sub-region
instead of across all 24 facilities, producing impossible values above 100
and a false tie. Both fixed by using `ALL ( dim_facility )` (the whole table)
throughout. Re-validated against the reference ranking computed independently
in the prior phase, exact match within rounding. Full root-cause detail in
`docs/decisions.md`; the guide itself (§4.8) needs the same correction so it
isn't rediscovered on a future build.

**Phase 5 continued: Page 2 (Cost concentration, Q1) completed, including
the 2026-07-09 scope-upgrade additions (2026-07-09, later session).** Added
the three discharge-level cost-concentration KPI cards (`Top 1/5/10%
Discharge Cost Share`, the underlying measures already existed in
`_Measures` from an earlier session) and a new clustered column chart
crossing `apr_severity_of_illness` by `apr_risk_of_mortality` on `Total
Costs`, built as a clustered column chart rather than a matrix (the Matrix
icon could not be reliably located in the Visualizations pane this session;
functionally equivalent). Confirmed and worked around two Visualizations
pane quirks along the way: the Table and Card visual-type icons could not be
found reliably by position (icon layout reflows with pane width), so a Table
was built by checking a field's checkbox with nothing selected, and new
Cards were built by copying an existing correct Card and swapping its Value
field, always confirming via the Selection pane's entry count that a
genuinely new visual had been created before editing it. All Page 2 values
validated against `docs/powerbi_guide.md` §7a and matched (one DRG total off
by $1, a display-rounding difference, not a data error). Full detail in
`docs/decisions.md`, "Page 2 (Cost concentration, Q1) build completed."

Renamed the Page 1 tab "Overview" to "Executive Summary," dropped the
optional treemap in favor of the Facility Risk Score table (top 8 by risk
score, via a Top N visual filter, columns formatted and ordered per the
guide), and added a "Recommended focus areas" text box with three lines
written from the real validated numbers rather than a template. Not yet done:
the text box was left overlapping the existing bar chart at the end of this
session and needs to be resized into the empty space beside it, with a final
crowding check, before moving to pages 3-6.

**Phase 5 continued: Page 3 (Hospital pricing behavior, charge-to-cost
markup, Q2) completed (2026-07-09, same session).** Page created by manually
duplicating the Page 2 tab (Power BI has no blank-page duplication shortcut
that skips this), then stripped down to the three shared slicers and rebuilt
from `docs/powerbi_guide.md` §5's Page 3 spec: five KPI cards, a scatter/
bubble chart, and a ranked bar chart. Hit and worked around one real UI
blocker: the Filters pane's advanced numeric filter (needed for the
guide's originally-specified `[Facility Markup Rank] = 1` / `= [Facility
Count]` card filters) would not accept typed input in this session after
15+ varied attempts; substituted two new DAX measures (`Highest Facility
Ratio`, `Lowest Facility Ratio`, both `MAXX`/`MINX` over `ALL (
dim_facility[facility_name] )`) bound directly to the cards' Value fields
instead, verified to produce the identical documented values (4.78, 1.03).
Also re-confirmed the Visualizations pane's icon-grid instability first
seen on Page 2: a remembered coordinate for "Clustered bar chart" pointed to
"Stacked column chart" instead after the Filters/Selection panes were
resized; used "Stacked bar chart" instead, which renders identically here
since the visual has only one value series and nothing to stack against.
All Page 3 values validated against `docs/powerbi_guide.md` §7a and matched
exactly: portfolio ratio 2.95, highest Saratoga Hospital 4.78, lowest
O'Connor Hospital 1.03, both confirmed at the correct ends of the sorted bar
chart by scrolling through the full facility list. Full detail in
`docs/decisions.md`, "Page 3 (Hospital pricing behavior, charge-to-cost
markup, Q2) build completed."

**Phase 5 continued: Page 4 (Payer mix and Medicaid exposure, Q3) completed
(2026-07-09, later session).** Before this phase started, resolved a
page-numbering ambiguity: the session's own build request described "Page 4"
in terms that actually matched `docs/powerbi_guide.md`'s Page 5 (length of
stay, Q4), not its real Page 4 (payer mix, Q3); confirmed to build
the guide's actual Page 4, deferring the length-of-stay page and its
unresolved `patient_disposition` grouping open item to a future session.
Page created by duplicating the Page 3 tab (same approach as Page 3's own
creation from Page 2), stripped to the three shared slicers, then built from
`docs/powerbi_guide.md` §5's Page 4 spec: two KPI cards (`Government Share`,
`Medicaid Share`), a 100% stacked bar chart, and a scatter chart, plus the
page-specific `payer_category` filter. The two KPI cards used the established
copy-paste Card workaround (no Card existed yet on the fresh page); the
scatter chart was built by copying Page 3's scatter/bubble visual and
remapping its fields, rather than searching the Visualizations pane's icon
grid, avoiding the icon-instability gotcha already seen on Pages 2 and 3.
One new gotcha found this session: sorting the bar chart by `Government
Share` required first adding that field to the visual's Tooltips well, since
Power BI's Sort by menu only lists fields already bound to the visual.
All Page 4 values validated against `docs/powerbi_guide.md` §7a and matched
exactly: portfolio `Government Share` 64.83%, `Medicaid Share` 16.38%, and
two spot-checked scatter points (St. Peter's Hospital - SPARC, Albany Medical
Center Hospital) matching the documented per-facility figures. Full detail in
`docs/decisions.md`, "Page 4 (Payer mix and Medicaid exposure, Q3) build
completed." Not yet done: pages 5 and 6.

**Phase 5 continued: Page 5 (Length of stay by facility and severity, Q4)
completed, including the `patient_disposition` grouping resolution
(2026-07-10).** Before building, pulled all 19 raw `patient_disposition`
values from `fact_discharges.csv` (143,613 rows, matching the fact table row
count exactly), considered a 4-category and a 5-category grouping, and
built the confirmed 5-category version (Home, Post-Acute Facility,
Hospice/Expired, Transfer to Another Hospital, Other/Unplanned) as a Power
Query conditional column, `patient_disposition_group`, on `fact_discharges`.
Page created by duplicating the Page 4 tab and stripping it to the three
shared slicers, the same pattern used for Pages 3 and 4. One data-loss
incident occurred mid-build (a stray click closed the file without a visible
save prompt, discarding the in-progress stripped-down stub); the correct
stub was manually recreated and saved, and the build resumed from that
confirmed state, with a Ctrl+S save and timestamp check after every
subsequent visual. Built three KPI cards, a small multiples clustered column
chart (severity by sub-region), a Matrix visual in place of the guide's
suggested Table (the same icon-grid limitation already hit on Page 2), and a
100% stacked bar chart crossing `sub_region` by `patient_disposition_group`
(built by copying Page 4's payer-mix stacked bar and remapping its fields).
All values validated against `docs/powerbi_guide.md` §7a and
`mart_los_by_facility_severity.csv`: small-multiples tooltips matched at
Capital District/Extreme (12.64) and Mohawk Valley/Extreme (7.64); the
Matrix's Albany Medical Center Hospital/Extreme row matched the mart file
exactly on all four measures (4,227 discharges, 16.07 avg days, 11.00 median
days, 0.35% censored); the Total row (143,613 / 5.45 / 3.00 / 0.04%) matched
the page's own KPI cards. Confirmed non-overlapping via a full-page
screenshot with the Filters, Selection, and Data panes collapsed. Then
stress-tested the finished page under all three global slicers (severity
alone, sub-region alone, facility alone, and facility+severity combined),
independently recomputing every KPI and table value from the raw CSVs each
time; all four combinations matched exactly, with no `ALL()`/`ALLSELECTED`
override bugs, unlike the three such bugs found earlier on Page 1's Facility
Risk Score composite. Full detail in `docs/decisions.md`, "Page 5 (Length of
stay by facility and severity, Q4) built (2026-07-10)" and "Page 5
stress-tested under the global slicers, no bugs found." **Not yet done:**
Page 6.

**Phase 5 continued: Page 6 (Urban vs. rural utilization, Q5) completed,
the sixth and final dashboard page (2026-07-10, same session).** Page
created by duplicating the Page 5 tab and stripping it to the three shared
slicers, the same pattern used for Pages 3 through 5, including removing a
leftover `payer_category` page filter inherited from the duplication chain.
Built two portfolio-wide KPI cards, a seven-column Matrix (in place of the
guide's suggested Table, the same icon-grid limitation already hit on Pages
2 and 5) with data bars on every numeric column and the per-capita column
labeled exactly per the locked "Discharges per 10,000 population, by
hospital location" decision, the two page-specific filters, and a callout
text box on the Mohawk Valley finding. Two real DAX bugs were found and
fixed, both the same root-cause pattern as the three earlier Facility Risk
Score bugs on Page 1 (a `CALCULATE` filter argument replacing rather than
intersecting with existing filter context): `Sub-Region Population` fixed
with `CROSSFILTER (dim_facility[sub_region], _SubRegionPopulation[sub_region],
BOTH )` inside `CALCULATE`, deliberately without touching the underlying
relationship's locked single-direction setting; `High Severity Discharges`
fixed by wrapping its boolean filter in `KEEPFILTERS`. Both verified against
independent Python recomputations from the raw CSVs. The finished page was
stress-tested under an Extreme-only severity filter, a Mohawk Valley-only
sub-region filter, and with all filters cleared; every value matched the
independent recomputation each time, including the per-sub-region breakdown
reconciling arithmetically against the Total row, and clearing all filters
restored the exact unfiltered baseline. Confirmed non-overlapping via a
full-page screenshot with all four side panes collapsed, then saved with
Ctrl+S and the title-bar timestamp confirmed. Full detail in
`docs/decisions.md`, "Page 6 (Urban vs. rural utilization, Q5) built
(2026-07-10)."

**All six dashboard pages are now complete.** The next phase per
`docs/powerbi_guide.md` §6, not yet started, is saving the `.pbix` into
`powerbi/` and exporting page screenshots into `outputs/`, followed by a
final documentation pass across the whole project.

**Update, 2026-07-10 (same session): full six-page QA pass, one real gap
found and fixed.** Checked every page's Selection-pane visual inventory and
Filters-pane page filters against `docs/powerbi_guide.md` §5's spec.
Page 1 (Executive Summary) was missing 4 of its 5 specified top-row KPI
cards (only `Total Costs` existed; `Total Discharges`, `Facility Count`,
`County Count`, and `Charge to Cost Ratio` were absent, with no documented
decision to have dropped them). Rebuilt all four, positioned as a clean
five-card row (144K / 24 / 14 / 2.27bn / 2.95), each value independently
verified against Python and matching the guide's own §7a reference exactly.
Pages 2 through 6 were all confirmed complete against spec, no other
missing visuals found. Also re-confirmed Page 1's severity-slicer fix still
holds (no regression) and investigated Page 2's `Extreme Tier Cost Share`
card staying fixed under a severity filter, confirmed by design (explicit
`ALL()` in the DAX, not a bug). Full detail in `docs/decisions.md`, "Full
six-page QA pass (2026-07-10, same session)."

**Update, 2026-07-10: a QA and self-check pass conducted; findings and a
prioritized fix plan added.** Every headline KPI was re-derived from the raw
file and matched exactly (143,613 / $6.694B / $2.266B / 2.9544 / Extreme cost
share 24.68% / Government share 64.83%), and the star schema was confirmed
fan-out-free. The review also surfaced issues in framing and conclusions, now
written up with concrete fixes in `docs/review_findings_and_fixes.md` (which
carries a live status board). Summary of what's left after this review:

- **Fix 5 (documentation hygiene): DONE.** README `powerbi_guide` status
  corrected; the "70 exact-duplicate rows" wording aligned to "70 rows in
  exact-duplicate groups; 36 removable by a keep-first dedupe" in this file and
  `docs/data_dictionary.md`; Hamilton County 65+ figure updated from a stale
  25% to ~34-36% (2024 Census vintage). Logged in `docs/decisions.md`
  ("Documentation hygiene pass, 2026-07-10").
- **Fix 3 (Facility Risk Score / `facility_role`): SQL DONE, model wiring
  PENDING.** A `facility_role` column was added to `dim_facility`
  (`sql/02_dimensions/02_dimensions.sql`), grounded in each facility's actual
  CMS designation (CAH/SCH/PPS; sources in `docs/sources.md` §6), so the Page 1
  risk ranking can exclude the five specialty/satellite units. Still to do:
  re-run `src/run_pipeline.py`, wire the column into Power BI, filter the Page 1
  risk table, and rescope its three percentile measures.
- **Fixes 1, 2, 4: PENDING (Power BI).** Medicaid sensitivity band (Page 4,
  because `Managed Care, Unspecified` = 10.7% of volume makes the 16.4%
  Medicaid share a floor), charge-to-cost reframing (Page 3, SPARCS costs are
  CCR-derived, not observed pricing), and a per-capita caveat (Page 6).

A self-contained prompt to execute all remaining work is in
`docs/agent_handoff_prompt.md`. The previously-noted close-out phase (save the
`.pbix` into `powerbi/`, export screenshots into `outputs/`, final doc pass)
still stands and now follows the fixes above.
