# Sources and Citations

Every external number used anywhere in this project (the raw dataset, the
regional context in `docs/project_context.md`, and the population/benchmark
figures added in the 2026-07-09 dashboard scope upgrade) traced back to a
real, checkable source below. Numbers computed from the project's own data
(`fact_discharges.csv`, the `dim_*`/`mart_*` tables) are not repeated here;
those are documented in `docs/data_dictionary.md` and `docs/decisions.md`
instead. This file covers only facts that came from outside this project.

Where a number could not be verified, or where verification turned up a
different current figure than what is written elsewhere in this project,
that is stated plainly in §5 rather than papered over with a citation that
doesn't actually support the claim.

---

## 1. The core dataset

**What it's used for:** the entire raw extract, `data/raw/sparcs_inpatient_discharges_2024.csv`,
143,613 rows, 33 columns.

| Item | Source |
|---|---|
| Dataset | [Hospital Inpatient Discharges (SPARCS De-Identified): 2024](https://health.data.ny.gov/Health/Hospital-Inpatient-Discharges-SPARCS-De-Identified/sf4k-39ay/about_data), NY State Department of Health, via Health Data NY (Socrata) |
| Exact extraction query used | `https://health.data.ny.gov/resource/sf4k-39ay.csv?$where=health_service_area='Capital/Adirondacks'&$limit=200000`, built and run in `src/fetch_data.py` |
| Publisher | New York State Department of Health |
| Dataset identifier | `sf4k-39ay` (Socrata resource ID) |

The extraction link is reproducible: anyone can re-run `src/fetch_data.py`
(or paste the query URL into a browser) and get the same region/year slice
back. No API key or authentication is required; this is public,
de-identified data with no PHI.

---

## 2. County and sub-region population (added 2026-07-09, per-capita utilization measure)

**What it's used for:** `docs/decisions.md` "Per-capita utilization measure
added to Page 6," `docs/powerbi_guide.md` §4.9, and the `_SubRegionPopulation`
table to be built in Power BI. All figures are U.S. Census Bureau / American
Community Survey (ACS) estimates, most recent vintage available at the time
of this research (2023-2024).

| County | Population | Source |
|---|---:|---|
| Warren | 65,288 | [U.S. Census Bureau QuickFacts: Warren County, New York](https://www.census.gov/quickfacts/warrencountynewyork) |
| Clinton | 78,493 | [U.S. Census Bureau QuickFacts: Clinton County, New York](https://www.census.gov/quickfacts/clintoncountynewyork) |
| Essex | 36,973 | [U.S. Census Bureau QuickFacts: Essex County, New York](https://www.census.gov/quickfacts/fact/table/essexcountynewyork/PST045224) |
| Franklin | 46,696 | [U.S. Census Bureau QuickFacts: Franklin County, New York](https://www.census.gov/quickfacts/fact/table/franklincountynewyork/PST045224) |
| Otsego | 60,100 | [Otsego County, NY | Data USA](https://datausa.io/profile/geo/otsego-county-ny), cross-referenced against [Census Bureau QuickFacts](https://www.census.gov/quickfacts/otsegocountynewyork) |
| Delaware | 44,410 | [U.S. Census Bureau QuickFacts: Delaware County, New York](https://www.census.gov/quickfacts/fact/table/schohariecountynewyork,delawarecountynewyork,chenangocountynewyork,herkimercountynewyork,otsegocountynewyork/POP060210) |
| Schoharie | 30,105 | [U.S. Census Bureau QuickFacts: Schoharie County, New York](https://www.census.gov/quickfacts/fact/table/schohariecountynewyork,delawarecountynewyork,chenangocountynewyork,herkimercountynewyork,otsegocountynewyork/POP060210) |
| Columbia | 60,299 | [U.S. Census Bureau QuickFacts: Columbia County, New York](https://www.census.gov/quickfacts/fact/table/columbiacountynewyork/PST045224) |
| Montgomery | 49,648 | [U.S. Census Bureau QuickFacts: Montgomery County, New York](https://www.census.gov/quickfacts/fact/table/montgomerycountynewyork,fultoncountynewyork/PST045218) |
| Fulton | 52,073 | [U.S. Census Bureau QuickFacts: Fulton County, New York](https://www.census.gov/quickfacts/fact/table/fultoncountynewyork/PST045224) |

Sub-region totals (sums of the counties above, Capital District's ~906,000
was sourced separately, see §4) are in `docs/decisions.md` and
`docs/project_context.md` §2. Note these are point estimates from slightly
different QuickFacts vintages (2023-2024), not a single synchronized survey
wave; treat the per-capita rates built from them as directional, not
survey-precision statistics.

---

## 3. Hospital charge-to-cost ratio benchmark (added 2026-07-09, Page 3)

**What it's used for:** the two `National Avg Charge to Cost Ratio` reference
measures in `docs/powerbi_guide.md` §4.9, compared against this project's own
computed portfolio-wide ratio of 2.9544.

| Benchmark | Value | Source |
|---|---|---|
| National average cost-to-charge ratio, ~2020 | ~0.32 (equivalent to a charge-to-cost ratio near 3.1x) | [Cost-to-Charge Ratios: Trends Report](https://qualiabio.com/resources/inferences/cost-to-charge-ratios-trends-report), Qualia Bio, citing CMS cost-to-charge ratio (CCR) trend data |
| Typical US hospital markup, 2012 Medicare data | 3.4x Medicare-allowable cost (mode 2.4x) | Bai, G. and Anderson, G.F., ["Extreme Markup: The Fifty US Hospitals With The Highest Charge-To-Cost Ratios,"](https://www.healthaffairs.org/doi/10.1377/hlthaff.2014.1414) *Health Affairs*, 2015 ([PubMed record](https://pubmed.ncbi.nlm.nih.gov/26056196/)) |
| CMS's own published departmental cost-to-charge ratios, FY 2024 | range 0.033 (CT scans) to 0.417 (routine days) | [Understanding Cost-to-Charge Ratios and Their Role in Medicare Ratesetting](https://www.aabb.org/docs/default-source/default-document-library/resources/understanding-cost-to-charge-ratios.pdf), AABB, summarizing CMS data (referenced for context, not used as the headline benchmark since it's departmental, not hospital-wide) |

Caveat already logged in `docs/decisions.md`: these benchmarks use different
denominators (Medicare-allowable cost vs. a hospital's own reported
cost-to-charge ratio) and different vintages (2012, 2020, FY2024) than this
project's 2024 SPARCS-based figure. The comparison on the dashboard should be
presented as directional, not an exact one-to-one benchmark.

---

## 4. Regional demographic and policy context (`docs/project_context.md` §2)

These figures predate the 2026-07-09 session; they were researched earlier
in the project's history and written into `docs/project_context.md` without
their source links being carried into a file. This section retroactively
verifies and links each one.

| Claim | Verified value found | Source |
|---|---|---|
| Capital District (Albany-Schenectady-Troy metro) median age ~40.5 | 40.4 ± 0.4 (ACS 2024 1-year estimate) | [Albany-Schenectady-Troy, NY Metro Area, Census Reporter](http://censusreporter.org/profiles/31000US10580-albany-schenectady-troy-ny-metro-area/) |
| Capital District median household income ~$86,000 | $86,637 ± $2,732 (ACS 2024 1-year estimate) | [Albany-Schenectady-Troy, NY Metro Area, Census Reporter](http://censusreporter.org/profiles/31000US10580-albany-schenectady-troy-ny-metro-area/) |
| 62% of NY's rural hospitals reported financial losses in 2023-2024 | Confirmed | [DiNapoli: Rural Counties Face Shortage of Health Professionals](https://www.osc.ny.gov/press/releases/2025/08/dinapoli-rural-counties-face-shortage-health-professionals), Office of the NYS Comptroller, August 7, 2025 (audit of 16 rural NY counties) |
| Roughly 1 in 3 rural inpatient hospitals in NY at imminent risk of closure | Confirmed ("over a third... at risk of immediate closure") | Same OSC/DiNapoli press release above; also reported in [The Hill, "Rural New York's health care crisis deepens amid federal funding battle"](https://thehill.com/homenews/state-watch/5446974-rural-new-york-health-care-crisis/) |
| 27% of the rural NY population (~205,000 people) was on Medicaid as of May 2025 | Confirmed, same 16-county audit | Same OSC/DiNapoli press release above, cross-referenced with [Medicaid in New York, May 2025 fact sheet](https://files.kff.org/attachment/fact-sheet-medicaid-state-NY), KFF (Kaiser Family Foundation) |
| NYS DOH warning that federal funding changes could add ~450,000 uninsured New Yorkers in 2026 | Confirmed, though "uninsured" simplifies the actual mechanism | [New York State Department of Health Provides Update on Federal Approval to Preserve Health Coverage for 1.3 Million New Yorkers](https://www.health.ny.gov/press/releases/2026/2026-03-23_federal_approval_to_preserve_health_coverage.htm), NYS DOH, March 23, 2026; also [TIME, "Nearly 450,000 New Yorkers Are Losing Health Coverage"](https://time.com/article/2026/07/01/new-yorkers-lose-health-coverage-trump-cuts-health-care/), July 2026 |
| Hamilton County: 25% of residents 65+ | **Does not match current data, see §5** | See below |

**Important scope note:** the 62%/1-in-3/27%/205,000 figures come from a
16-county statewide rural-health audit (Allegany, Cattaraugus, Chenango,
Delaware, Essex, Franklin, Greene, Hamilton, Herkimer, Lewis, Schuyler,
Steuben, Sullivan, Washington, Wyoming, Yates). Only three of those 16
counties (Delaware, Essex, Franklin) actually overlap with this project's
four sub-regions and 14 counties. These statistics are legitimate, real, and
directly relevant as statewide rural-health context (the reason the payer
framing matters at all), but they are not statistics computed for this
project's own Capital/Adirondacks extract specifically. `docs/project_context.md`
should be read (and if it's ever revised, worded) as citing this as broader
context, not as a claim about our own 143,613 rows.

---

## 5. Numbers that need attention

Flagged rather than silently fixed, per this portfolio's own documentation
rule against unilateral changes to existing written content.

**Hamilton County: 25% of residents 65+ appears out of date.** Current
Census Bureau data (2024 vintage) puts Hamilton County's 65-and-over
population meaningfully higher, in the 34-36% range, not 25%:
[U.S. Census Bureau QuickFacts: Hamilton County, New York](https://www.census.gov/quickfacts/fact/table/hamiltoncountynewyork/PST045225).
25% may have been correct against an older data vintage at the time it was
originally researched, or may have been a transcription of a different
statistic. Recommend updating `docs/project_context.md` §2 with a dated
decisions.md entry once you confirm which vintage you want to cite, rather
than leaving the current 25% figure standing uncorrected. Note also that
Hamilton County itself has no hospital in this project's facility list (it's
mentioned only as regional context for counties with no hospital of their
own), so this doesn't affect any number computed from the actual dataset.

---

## 6. Facility CMS designations (added 2026-07-10, `facility_role` column)

**What it's used for:** the `facility_role` column on `dim_facility`
(`sql/02_dimensions/02_dimensions.sql`), which labels each general-acute
facility by its actual CMS designation (Critical Access Hospital, Sole
Community Hospital, or standard PPS) so the Page 1 Facility Risk Score compares
like with like. Full rationale in `docs/decisions.md` (2026-07-10,
"`facility_role` classification added") and `docs/review_findings_and_fixes.md`
Fix 3.

| Item | Source |
|---|---|
| NY Critical Access Hospitals and Sole Community Hospitals, by name | [Critical Access Hospital and Sole Community Hospital Outpatient Rate Add-ons, 4/1/2024–3/31/2025](https://www.health.state.ny.us/health_care/medicaid/rates/updates/2024/4-24_3-25_cah_sch_rate_add-ons.htm), NY State Department of Health ([PDF](https://www.health.state.ny.us/health_care/medicaid/rates/updates/2024/docs/4-24_3-25_cah_sch_rate_add-ons.pdf)) |
| CAH cross-check (national list, incl. Alice Hyde, Malone NY, CAH certified 10/1/23) | [Critical Access Hospital Locations List](https://www.flexmonitoring.org/critical-access-hospital-locations-list), Flex Monitoring Team (Univ. of Minnesota / UNC-Chapel Hill / Univ. of Southern Maine), last updated Jan 2026 |

Disambiguation logged so it isn't re-introduced: the SCH list's "Samaritan
Medical Center" is the **Watertown** (Jefferson County) hospital, **not** this
dataset's **Samaritan Hospital** in Troy (Rensselaer County). The Troy facility
holds no CAH/SCH designation and is classified `Community Acute (PPS)`.

---

## 7. NY Medicaid managed-care penetration rate (added 2026-07-10, Page 4 Fix 1)

**What it's used for:** the `Medicaid Share (Adjusted Midpoint)` measure's
0.68 weight, the central estimate in the Page 4 Medicaid sensitivity band.
`payer_category`'s `Managed Care, Unspecified` bucket (10.71% of discharges)
cannot be split into Medicaid-managed-care vs. commercial-managed-care at the
row level from the SPARCS extract itself, so a real, dated statewide
penetration rate was sourced to weight the ambiguous bucket rather than
guessing or using an arbitrary 50/50 split. Full rationale in
`docs/decisions.md` (2026-07-10, "Fix 1 finished: Medicaid sensitivity band
added to Page 4").

| Item | Source |
|---|---|
| NY comprehensive risk-based Medicaid MCO enrollment, 2024 | 4,751,430 enrollees, 68% of total NY Medicaid enrollment | [Total Medicaid MCO Enrollment](https://www.kff.org/medicaid/state-indicator/total-medicaid-mco-enrollment/), KFF State Health Facts (data as of July 1, 2024, sourced from CMS Medicaid Managed Care Enrollment and Program Characteristics reports) |

This is a statewide figure, not specific to the Capital District/Adirondacks
region this project covers, and it describes overall Medicaid managed-care
penetration, not the composition of SPARCS's specific `Managed Care,
Unspecified` payer code. It is used as the best available real-world proxy
for that split, not as a measured fact about this project's own 15,382
`Managed Care, Unspecified` discharges. The Page 4 band card and its caption
frame this as a sensitivity range (16.4%-27.1%) with the 0.68-weighted figure
as one central estimate among several plausible ones, not as a precise
Medicaid share.
