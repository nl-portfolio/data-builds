# Phase 6 — Validation Reference Sheet

Generated from `outputs/tables/*.csv` (the same locked tables the Power BI
model reads). Use this next to the built scorecard: every value below should
appear on the page in exactly this rounded form. A mismatch is a build bug,
not a data bug — the CSVs are the source of truth, and they trace to
`src/analysis.py` / `notebooks/03_analysis.ipynb`.

Formatting mirrors the guide's DAX: pp columns as `+0.00`/`-0.00`, p-values as
`0.000`, rates as `0.00%`, counts as `#,0`.

---

## Panel 1A — Headline (per hypothesis_id, via slicer)

### H1 — H1 item nonresponse

- Effect Label: `-0.21 pp   [-0.437, 0.012] pp`
- Rates Label: `Treatment 1.22%   vs   Control 1.44%`
- Arms Label: `Treatment n = 1,513   |   Control n = 5,765`
- p Label: `p = 0.063 uncorrected   |   p = 0.190 Holm (family of 3)`
- Verdict Class: `INFORMATIVE_NULL`
- Verdict (full text): DISCONFIRMING (rates within 1 pp, or CI spans both directions) -> NULL; INFORMATIVE NULL (observed effect < MDE, MDE < 3 pp)

### H2 — H2 break-off (web only)

- Effect Label: `+1.81 pp   [-1.172, 4.802] pp`
- Rates Label: `Treatment 6.94%   vs   Control 5.12%`
- Arms Label: `Treatment n = 1,061   |   Control n = 3,800`
- p Label: `p = 0.234 uncorrected   |   p = 0.467 Holm (family of 3)`
- Verdict Class: `UNDERPOWERED_NULL`
- Verdict (full text): H2 break-off: NULL (CI includes 0); observed effect (1.815 pp) < MDE (4.270 pp): experiment could not have detected it

### H3 — H3 response error

- Effect Label: `-0.02 pp   [-0.104, 0.062] pp`
- Rates Label: `Treatment 0.34%   vs   Control 0.36%`
- Arms Label: `Treatment n = 1,513   |   Control n = 5,765`
- p Label: `p = 0.617 uncorrected   |   p = 0.617 Holm (family of 3)`
- Verdict Class: `UNDERPOWERED_NULL`
- Verdict (full text): H3 response error: NULL (CI includes 0); observed effect (0.021 pp) < MDE (0.118 pp): experiment could not have detected it

---

## Panel 1B — Effect vs. MDE (all three rows shown at once)

| H | dot (difference_pp) | CI low | CI high | MDE empirical (±) | MDE grid formula (±) |
|---|---|---|---|---|---|
| H1 | -0.21 | -0.44 | +0.01 | ±0.32 | ±1.20 |
| H2 | +1.81 | -1.17 | +4.80 | ±4.27 | ±3.67 |
| H3 | -0.02 | -0.10 | +0.06 | ±0.12 | ±0.59 |

Sanity: for H1, |difference_pp| (0.21) < mde_empirical_pp (0.32) — dot and whole CI should sit inside the shaded band.

---

## Panel 3A — Multiplicity strip (Holm, family of 3)

| hypothesis | p_uncorrected | holm_threshold | p_holm | reject_at_familywise_0.05 |
|---|---|---|---|---|
| H1 item nonresponse | 0.063 | 0.017 | 0.190 | False |
| H2 break-off (web only) | 0.234 | 0.025 | 0.467 | False |
| H3 response error | 0.617 | 0.050 | 0.617 | False |

Footnote check — family of 5 (should also all be FALSE):

| row | p_uncorrected | p_holm | reject |
|---|---|---|---|
| mode interaction: A item nonresponse | 0.057 | 0.284 | False |
| H1 item nonresponse | 0.063 | 0.284 | False |
| H2 break-off (web only) | 0.234 | 0.701 | False |
| mode interaction: C response error | 0.596 | 1.000 | False |
| H3 response error | 0.617 | 1.000 | False |

---

## Panel 2A — Pre-registered mode subgroup

| family | mode | diff_pp | ci_lo | ci_hi | p_value |
|---|---|---|---|---|---|
| A item nonresponse | web | -0.05 | -0.26 | +0.16 | 0.645 |
| A item nonresponse | paper | -0.67 | -1.28 | -0.07 | 0.029 |
| C response error | web | -0.01 | -0.03 | +0.02 | 0.634 |
| C response error | paper | -0.09 | -0.39 | +0.22 | 0.572 |
| B break-off | web | +1.81 | -1.17 | +4.80 | 0.234 |
| A item nonresponse | web - paper (interaction) | +0.62 | -0.02 | +1.26 | 0.057 |
| C response error | web - paper (interaction) | +0.08 | -0.22 | +0.39 | 0.596 |

---

## Panels 2B & 2C — Sensitivity strip

### Panel 2B — Filter-Missing (primary vs sensitivity)

| H | primary diff | primary p | sensitivity diff | sensitivity p | sign agrees |
|---|---|---|---|---|---|
| H1 | -0.21 | 0.063 | -0.27 | 0.025 | True |
| H2 | +1.81 | 0.234 | +1.81 | 0.235 | True |
| H3 | -0.02 | 0.617 | -0.02 | 0.584 | True |

### Panel 2C — Web-Never-Seen (footnote; spec NOT changed)

| H | primary diff | primary p | sensitivity diff | sensitivity p | sign agrees |
|---|---|---|---|---|---|
| H1 | -0.21 | 0.063 | -0.10 | 0.550 | True |
| H3 | -0.02 | 0.617 | -0.02 | 0.613 | True |

---

## Panel 3B — Balance

| covariate | p_value | max_arm_share_gap_pp | overrepresented_level | tx share % | ctl share % | flag |
|---|---|---|---|---|---|---|
| Age group (AgeGrpB) | 0.091 | 2.69 | 35-49 | 20.62 | 18.09 | balanced |
| Sex at birth (BirthSex) | 0.499 | 0.78 | (missing/not ascertained) | 8.46 | 7.68 | balanced |
| Race/ethnicity (RaceEthn5) | 0.107 | 1.98 | Non-Hispanic Black or African American | 14.87 | 12.89 | balanced |
| Education (EducA) | 0.585 | 1.63 | High School Graduate | 16.19 | 15.20 | balanced |
| Income (IncomeRanges) | 0.766 | 0.94 | $0 to $9,999 | 7.53 | 6.59 | balanced |
| Marital status (MaritalStatus) | 0.743 | 1.78 | Living as married or living with a romantic partner | 5.75 | 5.05 | balanced |
| Survey mode (FormType) | 0.002 | 4.21 | HINTS7, standard version - web | 70.13 | 65.92 | IMBALANCED (p<0.01) |
| Design stratum (STRATUM) | 0.433 | 1.04 | High minority urban area | 64.90 | 63.99 | balanced |

Caption number check: Survey mode row → 70.13% (tx) vs 65.92% (ctl), p = 0.002.
(The guide's caption prose rounds to 70.1% / 65.9% — one fewer decimal place; same value.)

---

## Panel 3C — Descriptive per-protocol (NON-RANDOMISED)

| group | n | rate_pct | ci_lo | ci_hi |
|---|---|---|---|---|
| Agreed (CommitmentStmt = Yes) [NON-RANDOMISED] | 1,389 | 1.17 | 0.98 | 1.35 |
| Did not agree (No or Not Ascertained) [NON-RANDOMISED] | 124 | 1.86 | 1.14 | 2.58 |
| Descriptive difference (agreed - did not agree) [NON-RANDOMISED, NOT CAUSAL] | 1,513 | -0.69 | -1.43 | 0.05 |
| Declined only (CommitmentStmt = No) -- DESCRIBED, NOT TESTED | 14 | — | — | — |

Caption number check: agreed 1.17% vs did not agree 1.86%.

---

## Footer — Build-integrity footnote

- Rows in `assertion_history.csv`: 31 (guide says 31) — matches
- All `guard` values 'passed': True
- implied_n/n range: 0.16–0.79 (guide says 0.15–0.79 — the min cell is
  0.1557, which rounds to 0.16 at 2dp; guide truncated instead of rounding.
  Not a discrepancy in the underlying data, just a presentation rounding
  choice — pick either 0.15 or 0.16 for the footnote text, they mean the
  same cell.)

---

## Guide gaps found (report these per the Phase 6 prompt, don't fill silently)

1. **Left-rail legend is named but not specified.** §5 says the left rail
   carries "a static legend for the pre-registered / exploratory colour
   key," but nothing in the guide defines what counts as "exploratory" on
   this page, or what the legend's entries/colors should be. Every panel on
   the page is either pre-registered (H1–H3, multiplicity, mode subgroup,
   balance) or carries its own explicit tag (NON-RANDOMISED, ILLUSTRATION) —
   none is labeled "exploratory" anywhere else in the guide. Recommend
   confirming with the Phase 5 agent's intent before building this legend,
   or dropping it if nothing on the page is actually exploratory by the
   guide's own panel definitions.
2. **Minor rounding inconsistency, not a bug:** the footer footnote's
   "0.15–0.79" implied_n/n range truncates the low end (actual 0.1557)
   rather than rounding it — cosmetic only, flagged above.

Everything else in the guide — data types, relationships, DAX, layout,
pitfalls, and prohibitions — is fully specified and traces cleanly to these
tables. No other gaps found.
