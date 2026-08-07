# Case Study Draft: Healthcare Operations & Finance (Project 1)

*Published-copy draft, ready to paste into Elementor. Built from
`case_study_brief.md` and `case_study_outline_template.md`. Target ~500-650
words; keeps 4 of the 5 findings (dropped the urban/rural ER-routing
finding, since the length-of-stay finding below already carries the
"read past the obvious interpretation" point without repeating it). Word
count noted at the end.*

---

**Eyebrow:** Data Analytics — Project 1 of 3

## Healthcare Operations & Finance Dashboard

A six-page Power BI dashboard built on 143,613 real 2024 hospital discharge
records for one New York region, read the way a health insurer's
medical-economics team would read it, not a hospital's own finance view.

**Data:** Real, de-identified NY State SPARCS inpatient discharge records
(no PHI), Capital/Adirondacks region, 2024. 143,613 rows, 24 facilities, 14
counties, $2.27B in inpatient cost, pulled directly from the state's public
API.

**Stack:** DuckDB, SQL, Power BI, DAX, Python for independent validation.

### The questions

Framed from a payer's perspective, not a hospital's: where does cost
concentrate, how do charges compare to estimated cost, who pays and where is
Medicaid exposure highest, does length of stay differ by location, and how
does urban utilization compare to rural.

### The approach

Build a real star schema from messy government data, validated end to end
(the fact table's row count reconciles exactly to the raw source, 143,613 to
143,613, zero orphan foreign keys), then compute every measure as live DAX
over that shared model rather than importing six pre-built tables. That
choice matters more than it sounds: it means every slicer on the dashboard,
facility, sub-region, severity, filters all six pages at once, so a reviewer
can actually interrogate the data instead of clicking through six static
charts.

### What the data says

**Cost is sharply concentrated, and two independent cuts agree.** The
highest severity tier is under 10% of admissions but drives 24.7% of cost. A
sharper cut, ranking all 143,613 individual discharges, says it harder: the
top 10% of admissions account for 40% of spend, the top 1% for 11%. Two
different lenses landing on the same conclusion is what makes it load-bearing.
**So what:** care-management effort belongs on a narrow high-cost band, not
spread evenly.

**One condition is a $221M line item.** Septicemia and serious infections is
the single largest cost driver in the region, $221M, 11,830 discharges,
9.8% of all regional spend. **So what:** if a payer had to pick one
condition to build an early-intervention program around first, the data
names it.

**Length of stay tells an access story, not an efficiency one.** Rural
Mohawk Valley shows *shorter* stays than the urban Capital District for the
sickest patients (7.6 vs. 12.6 days). Read alone, that looks like a rural
efficiency win; cross-referenced with where patients go after discharge, it
more likely reflects limited on-site capacity and transfers out. **So
what:** read it as a capacity and post-acute access gap when planning
network adequacy, not a quality signal.

**A composite risk score caught its own methodology bug.** Combining
Medicaid dependency, size fragility, and cost complexity into one ranked
score first put two tiny specialty campuses at the top, an artifact of the
size measure rewarding smallness. Rescoped to actual CMS facility
designation (19 general-acute facilities, not 24), the corrected top is
Ellis Hospital and Nathan Littauer Hospital, tied at 68.5. **So what:**
Nathan Littauer, a real rural hospital with real volume and a 30% Medicaid
share, is the facility a payer should watch first for network-adequacy
risk, not a false positive from a specialty-campus edge case.

### Design decisions worth noting

- **Real data got real judgment calls, logged, not hidden.** 57 top-coded
  "120+" length-of-stay rows were floored and flagged rather than dropped;
  70 rows sitting in exact-duplicate groups were kept, not deduped, because
  the file has no patient or row identifier and can't safely distinguish
  two real patients from one duplicated record.
- **Two headline metrics are reported as ranges, not single numbers.** The
  charge-to-cost ratio (2.95x) is disclosed as a derived figure, since
  SPARCS costs are themselves estimated from charges, and Medicaid share is
  reported as a floor-to-ceiling band (16.4% to 27.1%) because a large
  "unspecified managed care" bucket can't be split at the row level.
  Disclosing an estimate's limit is part of the finding, not a footnote.

### What this demonstrates

Dimensional modeling against a real, non-trivial grain with no natural key,
live DAX measures built to survive slicer interaction rather than just look
right once, and the habit of checking a plausible alternative explanation
before publishing a conclusion, most visibly in catching a facility-ranking
artifact before it became a wrong headline. That same QA discipline (state
the finding, then state what would make it wrong) is what makes the honest
parts of this dashboard, the ranges instead of single numbers, credible
rather than hedging.

*Project 2 (catering) and Project 3 (bakery) link here once built. Full
repo: [link]. Resume Portfolio Projects section links back to this page.*

---

**Word count (body copy, Eyebrow through What this demonstrates):** ~560
words.
