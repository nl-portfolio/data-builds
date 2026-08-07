# QA and Self-Check Notes (2026-07-10)

> **Purpose of this file:** my own QA pass over the project's data, model,
> DAX, and stated conclusions, with a concrete fix for each issue I found and
> the reasoning behind it. Every finding below was checked by recomputing from
> `data/raw/sparcs_inpatient_discharges_2024.csv` and `data/processed/*.csv`
> directly, not read off the existing docs. Where a fix touches an existing
> document (`decisions.md`, `powerbi_guide.md`, `data_dictionary.md`,
> `project_context.md`, `README.md`, `sources.md`), the exact place to log it
> is named so the project's "no undocumented change" rule is preserved.
>
> **Status: all five fixes below are now applied and logged** (see the status
> board at the end). Each has its own dated entry in `decisions.md`, the same
> way every prior decision in this project was.

---

## 0. What was verified, and what held

Recomputed independently and **matched the existing docs exactly** (no action
needed, recorded here so the review is reproducible):

| Metric | Recomputed value | Matches |
|---|---|---|
| Discharges | 143,613 | ✓ |
| Total charges | $6,694,244,423.54 | ✓ |
| Total costs | $2,265,824,365.27 | ✓ |
| Charge-to-cost ratio | 2.9544 | ✓ |
| Extreme-tier cost share | 24.68% | ✓ |
| Government payer share | 64.83% | ✓ |
| Avg / median LOS | 5.45 / 3.00 | ✓ |
| Censored (`120+`) LOS rows | 57 | ✓ |
| Code→description 1:1 (DRG/MDC/Diag/Proc) | no fan-out possible | ✓ |
| Six pages / visual inventory in `.pbix` | matches build log | ✓ |

The star schema, the pipeline, and the KPI layer are sound. The fixes below
are about **conclusions and framing**, plus a small amount of doc hygiene, not
about broken numbers.

---

## Fix 1: Medicaid exposure is understated, add a sensitivity band

### The problem
`Managed Care, Unspecified` is **15,382 discharges, 10.71% of the file**, and
`dim_payer` currently rolls all of it into `Commercial`. In New York a large
share of Medicaid is delivered through Medicaid *managed care*, which is
exactly what lands in this catch-all label. The dashboard's headline
**Medicaid Share of 16.4%** therefore almost certainly undercounts, and the
`Government Share` of 64.83% is a floor, not a point estimate.

Sensitivity (recomputed):

| Assumption: share of "Managed Care, Unspecified" that is really Medicaid | Resulting Medicaid share |
|---|---:|
| 0% (current model) | 16.36% |
| 30% | 19.57% |
| 50% | 21.71% |
| 70% | 23.86% |

This is not a new risk — `docs/decisions.md` (2026-07-07, "Added
`payer_category` to `dim_payer`") already says the category is Commercial "by
default but can sometimes represent Medicaid managed-care… **worth revisiting
if that category turns out to carry a lot of volume.**" It carries 10.7% of
volume. The caveat's own trigger condition fired; the revisit is this fix.
Because Q3 (payer-mix / Medicaid exposure) is the question the entire payer
framing leans on, a reviewer will find this, so the honest move is to surface
the uncertainty on the dashboard rather than present 16.4% as a clean fact.

### The fix
Do **not** silently reclassify `Managed Care, Unspecified` to Government — that
would replace one unverifiable assumption with another. Instead present a
**band** and label the assumption explicitly. Add three measures to
`_Measures`:

```DAX
-- Volume share of the ambiguous bucket, so the band is auditable on the page.
Managed Care Unspecified Share =
DIVIDE (
    CALCULATE ( [Total Discharges], dim_payer[payer_name] = "Managed Care, Unspecified" ),
    [Total Discharges]
)

-- Upper bound: assume ALL "Managed Care, Unspecified" is Medicaid managed care.
Medicaid Share (Upper Bound) =
[Medicaid Share] + [Managed Care Unspecified Share]

-- Labeled midpoint. 0.5 is an explicit, documented placeholder, NOT a
-- measured value. Replace the 0.5 with a sourced NY Medicaid managed-care
-- penetration rate once cited in docs/sources.md (see "sourcing" below).
Medicaid Share (Adjusted Midpoint) =
[Medicaid Share] + 0.5 * [Managed Care Unspecified Share]
```

On **Page 4 (Payer Mix, Q3)**: keep the existing `Medicaid Share` card as
"Medicaid Share (reported floor)" and add a companion card or a labeled
min–max band reading **"16.4% – 27.1% (floor → all-MCO ceiling)"**, with the
adjusted midpoint shown as the central estimate. A small caption:
*"'Managed Care, Unspecified' (10.7% of discharges) may include Medicaid
managed care; the band shows the range."*

The Facility Risk Score's `Medicaid Dependency Percentile` (Fix 3) should be
re-checked under the adjusted midpoint too — a facility heavy in
`Managed Care, Unspecified` could rank differently.

### Sourcing note (do this before picking the 0.5)
The 0.5 midpoint is a placeholder. The defensible version cites the actual NY
statewide **Medicaid managed-care penetration rate** (the share of Medicaid
enrollees in managed care vs. fee-for-service) and uses that as the split, or
states plainly that the true split is unknown for this de-identified extract
and the band is bounded rather than pointed. Add whatever figure is used to
`docs/sources.md` §2-style, with the link, exactly as the population and
benchmark numbers were sourced.

### Where to log it
- New dated entry in `docs/decisions.md`: *"Medicaid share sensitivity band
  added (2026-07-10): 'Managed Care, Unspecified' revisited after it proved to
  be 10.7% of volume."* Include the sensitivity table above and the explicit
  statement that the midpoint assumption is a placeholder pending sourcing.
- `docs/data_dictionary.md`: update the existing `Managed Care, Unspecified`
  caveat on `dim_payer` from "worth revisiting" to "revisited; see decisions
  2026-07-10 and the Page 4 band."
- `docs/powerbi_guide.md` §4 (measures) and §5 Page 4 layout: add the three
  measures and the band card.
- `docs/sources.md`: add the Medicaid managed-care penetration source if used.

---

## Fix 2: Charge-to-cost ratio is CCR-derived, not observed pricing, re-caveat Page 3

### The problem
Page 3 is titled "Hospital Pricing Behavior" and reads the charge-to-cost
ratio as markup. But SPARCS `total_costs` is **not** a hospital's accounting
cost — it is an estimate produced by applying cost-to-charge ratios (CCRs) to
charges. Tested directly: within each facility, log-charge explains a **median
R² of 0.92** of log-cost variance (per-facility range ≈ 0.77–0.95 across the
12 largest facilities). That means a facility's aggregate charge-to-cost ratio
is close to the **inverse of the CCR SPARCS assigned it**, not an independent
observation of how aggressively it prices. The signal is partly circular: high
ratio ⇔ low assigned CCR.

This does not make Page 3 worthless — cross-facility CCR differences are real
and the national-benchmark comparison (already cited in `docs/sources.md` §3)
is legitimate context. It makes the **"pricing behavior" label overclaim**
what a derived-cost figure can show.

### The fix
1. **Reframe the page title / subtitle** from "Hospital Pricing Behavior" to
   something honest about the metric, e.g. **"Charge-to-Cost Ratio (SPARCS
   derived-cost basis)"** with subtitle *"Ratio of billed charges to SPARCS
   estimated costs. SPARCS costs are derived from cost-to-charge ratios, so
   this reflects each facility's assigned CCR, not independently observed
   pricing."*
2. **Add a caveat text box** to Page 3 (mirror the Page 6 Mohawk Valley
   callout style):
   > *"SPARCS `total_costs` is estimated by applying cost-to-charge ratios to
   > charges, not measured from hospital accounting. Within a facility, ~92%
   > of cost variation is explained by charges, so this ratio largely restates
   > each facility's assigned CCR. Read cross-facility differences as
   > directional, and compare to the national benchmark rather than treating
   > any single facility's ratio as a pricing decision."*
3. Keep the national-benchmark reference lines already specified in
   `docs/powerbi_guide.md` §4.9 — they are the correct mitigation and should
   stay.

No measure changes are required; this is a framing and disclosure fix.

### Where to log it
- New dated entry in `docs/decisions.md`: *"Page 3 reframed from 'pricing
  behavior' to derived-cost charge-to-cost ratio (2026-07-10)."* Include the
  median-R²-0.92 finding and the reasoning.
- `docs/powerbi_guide.md` §5 Page 3: update the page title, subtitle, and add
  the caveat box to the spec.
- `docs/data_dictionary.md`: on `total_costs`, add a one-line note that it is a
  CCR-derived estimate (if not already stated), since this underlies the
  caveat.

---

## Fix 3: Facility Risk Score is dominated by small specialty/satellite units

### The problem
Reconstructed the score from the DAX in `docs/powerbi_guide.md` §4.8. The top
of the ranking is driven by tiny units, not by the rural sole-community
hospitals the payer narrative is actually about:

| Rank | Facility | Discharges | Medicaid share | Extreme cost share |
|---|---|---:|---:|---:|
| 1 | St. Mary's Healthcare – Amsterdam Memorial Campus | 259 | 36.3% | 1.0% |
| 2 | St. Peter's Hospital – SPARC | 266 | 78.9% | 0.4% |
| 3 | Nathan Littauer Hospital | 2,282 | 30.1% | 17.0% |

Two of the top three have **under 300 discharges**. The `Size Fragility
Percentile` is one-third of the composite by construction and
**deterministically rewards smallness** — but "small" here frequently means a
*specialty or satellite campus inside a solvent health system* (SPARC and the
Addiction Recovery Center are part of St. Peter's Health Partners; Amsterdam
Memorial is a St. Mary's campus), not an independent hospital at closure risk.
The score conflates "small unit of a big system" with "fragile sole-community
hospital," which is the exact distinction a payer's network-adequacy team
cares about. The `Is Low Volume Facility` flag *discloses* this but does not
*fix* the ranking.

Two secondary points:
- **Equal weighting** of the three axes is arbitrary (already disclosed in the
  §4.8 comment — kept honestly, but still a soft spot a reviewer may probe).
- I could **not exactly reproduce** the documented three-way tie at 63.8; my
  reconstruction gives 65.1 / 65.0 / 64.5 for the same three facilities. Same
  qualitative result, but the exact `Facility Medicaid Share` definition
  (count-based vs. cost-based, tie handling) is worth a spot-check against the
  built measure.

### The fix
Add a facility-role classification so the ranking compares like with like:

1. **Add a `facility_role` column to `dim_facility`** (Power Query conditional
   column or a `02_dimensions.sql` CASE), values along the lines of:
   `Academic Medical Center`, `Community Acute`, `Rural / Sole-Community
   Acute`, `Specialty / Satellite` (rehab, addiction, standalone women's/OB,
   named "campus" satellites). Starter mapping for the clearly non-general-acute
   units (confirm the rest with a dated decision, do not finalize unilaterally):

   | Facility | Proposed role |
   |---|---|
   | St. Peter's Addiction Recovery Center | Specialty / Satellite |
   | St. Peter's Hospital – SPARC | Specialty / Satellite |
   | Sunnyview Hospital and Rehabilitation Center | Specialty / Satellite |
   | Ellis Hospital – Bellevue Woman's Care Center Division | Specialty / Satellite |
   | St. Mary's Healthcare – Amsterdam Memorial Campus | Specialty / Satellite |
   | Albany Medical Center Hospital | Academic Medical Center |
   | (remaining 18) | Community Acute vs. Rural/Sole-Community — confirm |

2. **Filter the Page 1 Facility Risk Score table to general acute hospitals**
   (`facility_role IN ("Academic Medical Center","Community Acute","Rural /
   Sole-Community Acute")`), and show specialty/satellite units in a separate,
   clearly-labeled small table so they are not lost, just not ranked against
   full-service hospitals. This alone moves the genuine rural hospitals
   (Nathan Littauer, Glens Falls, the UVM North Country sites, Cobleskill,
   Delaware Valley) to the top of the risk list, which is the intended reading.

3. **Optionally replace raw `Size Fragility` with a truer fragility signal** —
   e.g. flag facilities that are the *only* hospital in their county and *not*
   part of a multi-hospital system, which captures sole-community risk directly
   instead of using size as a proxy. This is the more senior version; item 2
   is the minimum viable fix.

4. **Re-verify the 63.8 tie** against the built measure and, if the
   count-vs-cost definition of `Facility Medicaid Share` differs from §4.8's
   intent, correct the guide as well as the model (the same "fix the guide, not
   just the build" discipline used for the earlier `ALL()` bugs).

### Where to log it
- New dated entry in `docs/decisions.md`: *"Facility Risk Score: facility-role
  classification added; specialty/satellite units separated from general-acute
  ranking (2026-07-10)."* Include the top-3 table above, the small-n rationale,
  and the final agreed role mapping.
- `docs/data_dictionary.md`: document the new `facility_role` column on
  `dim_facility`.
- `docs/powerbi_guide.md` §4.8 and §5 Page 1: update the risk-score spec, the
  table filter, and (if the definition differs) the `Facility Medicaid Share`
  measure.
- If built in SQL, update `sql/02_dimensions/02_dimensions.sql` and re-run
  `src/run_pipeline.py`.

---

## Fix 4: Per-capita utilization mixes numerator and denominator populations

### The problem
On Page 6, `Discharges per 10,000 population, by hospital location` divides
discharges counted **by hospital location** by the population **resident in
that region**. Because patients travel (Albany Medical Center draws a regional
catchment; `hospital_county` is the facility's county, not the patient's), the
numerator and denominator describe *different* populations. Referral-center
regions are inflated and patient-exporting regions are deflated. The headline
"Mohawk Valley = lowest per-capita utilization, highest ED share" could partly
be residents leaving the region for planned inpatient care, not genuinely low
utilization.

This is already caveated as directional in `docs/project_context.md` §2, which
is good. The fix is to make that caveat *travel with the visual* and to soften
the conclusion.

### The fix
1. Keep the metric (it is still directionally useful) but **rename the callout
   conclusion** from a statement of fact to a hypothesis:
   *"Mohawk Valley shows the lowest discharges-per-resident and the highest ED
   share. Because this counts discharges where the hospital sits, not where the
   patient lives, this pattern is consistent with residents leaving the region
   for planned care and/or constrained non-emergency access — it is a signal to
   investigate, not a settled utilization rate."*
2. Add a one-line footnote on the Matrix: *"Per-capita = discharges at
   in-region hospitals ÷ in-region residents; the two populations are not
   identical (patients travel). Directional only."*

### Where to log it
- Dated note in `docs/decisions.md` under the existing "Per-capita utilization
  measure added to Page 6" entry: soften the conclusion, add the
  numerator/denominator-mismatch caveat.
- `docs/powerbi_guide.md` §5 Page 6: update the callout text and add the
  footnote to the spec.

---

## Fix 5: Documentation hygiene

Three small factual/consistency fixes. None affect any computed number; all
matter because this project's credibility rests partly on documentation
precision.

1. **`README.md`, "How to reproduce" step 4** still reads
   *"docs/powerbi_guide.md (pending update for the new schema; currently still
   describes the old synthetic model)."* The guide was rewritten against the
   real schema and the entire dashboard was built from it. **Fix:** delete the
   parenthetical; the guide is current.

2. **"70 exact-duplicate rows"** in `docs/project_context.md` §6 (Phase 2) and
   `docs/data_dictionary.md` (staging table) is imprecise. Verified: 70 rows
   sit *in* exact-duplicate groups, but only **36** rows would be removed by a
   keep-first dedupe. `docs/decisions.md` (2026-07-07, "Exact duplicate rows")
   already states this correctly. **Fix:** align the two front-facing docs with
   the decisions-log wording ("70 rows in exact-duplicate groups; 36 removable
   by a keep-first dedupe"). *(An earlier draft of this report listed `README.md`
   here; the README does not contain the phrasing — corrected.)*

3. **Hamilton County "25% of residents 65+"** in `docs/project_context.md` §2
   is stale; current Census (2024 vintage) is ~34–36%. This is already
   self-flagged in `docs/sources.md` §5. **Fix:** update the figure in
   `project_context.md` with a dated `decisions.md` entry recording the vintage
   chosen, so the correction is logged rather than silent (and note, as
   `sources.md` already does, that Hamilton has no facility in the dataset, so
   no computed number changes).

### Where to log it
- One combined dated entry in `docs/decisions.md`: *"Documentation hygiene pass
  (2026-07-10): README powerbi_guide status corrected, duplicate-row count
  wording aligned to 36/70, Hamilton County 65+ figure updated."*

---

## Status board (updated 2026-07-10)

| # | Fix | Status | What's left |
|---|---|---|---|
| 1 | Medicaid sensitivity band | ✅ Done | 3 measures added (`Managed Care Unspecified Share`, `Medicaid Share (Upper Bound)`, `Medicaid Share (Adjusted Midpoint)`, sourced 0.68 KFF/CMS weight); Page 4 card relabeled "Medicaid Share (reported floor)", new sensitivity-band table (23.66% / 27.09%) and caption added; validated against an independent Python recompute and stress-tested under all 3 slicers; full writeup in `docs/decisions.md`, "Fix 1 finished" (2026-07-10) |
| 2 | Re-caveat charge-to-cost / Page 3 | ✅ Done | Page tab renamed "Charge-to-Cost Ratio (Q2)"; title/subtitle text box added ("Charge-to-Cost Ratio (SPARCS derived-cost basis)"); caveat text box added (median R² 0.92 disclosure); national-benchmark reference cards kept unchanged; no measure changes; full writeup in `docs/decisions.md`, "Fix 2 finished" (2026-07-10) |
| 3 | Risk-score facility-role split | ✅ Done | Pipeline re-run (`facility_role` confirmed 1/8/6/4/5 in `dim_facility.csv`); a hardcoded `Columns=6` in the `dim_facility` Power Query step (stale from before `facility_role` existed) blocked refresh, found and fixed; Page 1 table filtered to 19 general-acute facilities; all 3 percentile measures rescoped to `GeneralAcute`; new ranking validated against an independent Python recompute (Ellis Hospital / Nathan Littauer Hospital tie at 68.5); stress-tested under all 3 slicers individually and combined; full writeup in `docs/decisions.md`, "Fix 3 finished" (2026-07-10) |
| 4 | Per-capita caveat / Page 6 | ✅ Done | Mohawk Valley callout body reworded from fact to hypothesis (heading unchanged); numerator/denominator footnote added below the Matrix; no measure changes; full writeup in `docs/decisions.md`, "Fix 4 finished" (2026-07-10) |
| 5 | Doc hygiene (3 items) | ✅ Done | — |

### Done this session (2026-07-10)

- **Fix 5.1** — `README.md` "How to reproduce" step 4 and the repository-layout
  note corrected: `powerbi_guide.md` now described as current (rewritten against
  the real schema, dashboard built from it), not "pending / old synthetic model."
- **Fix 5.2** — duplicate-row wording aligned in `docs/project_context.md` §6 and
  `docs/data_dictionary.md`: "70 rows in exact-duplicate groups; 36 removable by a
  keep-first dedupe."
- **Fix 5.3** — `docs/project_context.md` §2 Hamilton County figure updated from
  the stale "25%" to "~34–36% (Census QuickFacts 2024 vintage)," with an inline
  pointer to `decisions.md` / `sources.md` §5.
- **Fix 5 logging** — one combined dated entry added to `docs/decisions.md`
  ("Documentation hygiene pass (2026-07-10)").
- **Fix 3 (SQL finalized)** — `facility_role` CASE in
  `sql/02_dimensions/02_dimensions.sql`, escaped and validated (parses; yields
  Academic 1 / Community-PPS 8 / Critical Access Hospital 6 / Sole Community
  Hospital 4 / Specialty-Satellite 5 = 24). Per the 2026-07-10 sign-off, the
  18 general-acute facilities are labeled by their **actual CMS designation**
  (NY DOH CAH/SCH lists, cross-checked against Flex Monitoring), not by size.
  Corrections the CMS basis forced: Nathan Littauer → Community/PPS (no federal
  rural designation); Bassett and Champlain Valley → Sole Community Hospital
  (federally SCH). Sources added to `docs/sources.md` §6; full taxonomy and
  rationale in `docs/decisions.md` (2026-07-10). **Still pending:** pipeline
  re-run + Power BI wiring (see status board).

- **Fix 3 (finished)** — pipeline re-run, `facility_role` wired into the Power
  BI model and the Page 1 Facility Risk Score table/percentile measures, new
  19-facility ranking validated against an independent Python recompute and
  stress-tested under all 3 global slicers. A real Power Query bug (hardcoded
  `Columns=6` blocking refresh once `facility_role` added a 7th column) found
  and fixed along the way. Full writeup in `docs/decisions.md`, "Fix 3
  finished: `facility_role` wired into the Facility Risk Score."

- **Fix 1 (finished)** — sourced a real NY Medicaid MCO penetration rate
  (68%, KFF/CMS 2024) to replace the review spec's placeholder 0.5 midpoint
  weight; three DAX measures added and validated against an independent
  Python recompute (16.38% floor / 23.66% adjusted midpoint / 27.09%
  ceiling); Page 4 Medicaid card relabeled, sensitivity-band table and
  caption added; stress-tested under all 3 global slicers. Also flagged (not
  silently corrected) a discrepancy between the review spec's stated 16.36%
  floor and the independently-verified, four-source-corroborated 16.38%.
  Full writeup in `docs/decisions.md`, "Fix 1 finished: Medicaid sensitivity
  band added to Page 4."

- **Fix 2 (finished)** — Page 3 tab renamed "Charge-to-Cost Ratio (Q2)";
  title/subtitle and a separate caveat text box added disclosing that SPARCS
  `total_costs` is CCR-derived, not an accounting cost (median R² 0.92
  within-facility); national-benchmark reference cards kept unchanged as
  instructed; no DAX changed. `docs/data_dictionary.md`'s `total_costs`
  description also updated with the same disclosure. Full writeup in
  `docs/decisions.md`, "Fix 2 finished: Page 3 reframed from 'pricing
  behavior' to derived-cost charge-to-cost ratio."

- **Fix 4 (finished)** — the Page 6 Mohawk Valley callout's body paragraph
  reworded from a stated fact to an explicit hypothesis (bold heading left
  unchanged); a numerator/denominator footnote added below the Matrix
  clarifying that per-capita counts discharges by hospital location, not by
  patient residence. No measure or number changes. Full writeup in
  `docs/decisions.md`, "Fix 4 finished: Page 6 per-capita callout reworded
  from fact to hypothesis."

All five fixes from this review are now complete.

### Reference mockup realigned to the finished state (2026-07-16)

`outputs/dashboard_six_page_mockup.html` had drifted: it still showed the
*pre-fix* dashboard for Fixes 1-4 (Page 1 "top 8 of 24" with the old 63.8
three-way tie; Page 3 "Hospital pricing behavior"; no Page 4 Medicaid band;
Page 6 callout stated as fact). Regenerated 2026-07-16 to match this status
board — every regenerated number re-derived independently from
`data/processed/` (the Facility Risk Score recomputed from the star schema
reproduced the Ellis / Nathan Littauer 68.5 tie and Elizabethtown 31.5 floor;
the Page 4 band reproduced 16.38 / 23.66 / 27.09). Full writeup in
`docs/decisions.md`, "Mockup regenerated to the post-review state" (2026-07-16).

### Next up

Task E close-out (still outstanding): save the `.pbix` into `powerbi/`, export
all six page **screenshots from the live `.pbix`** into `outputs/` (the
HTML mockup is a reference companion, not a substitute for real exports), and
do a final documentation pass confirming `README.md`,
`docs/project_context.md` §5, and this status board all reflect the finished
state.
