# Data Dictionary: analysis_frame.parquet

Complete documentation of every constructed variable and denominator rule.

**Frame:** One row per respondent (n = 7,278)
**Columns:** 72 (outcomes, weights, design variables, strata, mode, sensitivity variants)
**Created by:** Phase 3 (Data Preparation). Extended by Phase 3b (repair) 2026-09-03: mode variable, Family B, Filter Missing sensitivity variant.
**Status:** Arm-blind construction and extension. No treatment-arm statistics computed during build (Phase 3) or extension (Phase 3b).

**Correction (Phase 3b, 2026-09-03):** Phase 3's original self-report claimed
pooled Family A rate 10.2%, Family C rate 0.028%, denominator min 85 / median
327. Those figures do not match this file and were never true of it. The
figures the file actually produces, confirmed by independent recomputation
directly from the parquet on disk, are Family A 1.98%, Family C 0.52%
**(unweighted ratio-of-sums; see below for the weighted analysis quantities)**,
denominator min 223 / median 283 / max 368. See `docs/decisions.md`, Phase 3b
entry, and the 2026-09-03 incident entry, for the full reconciliation. The
frame itself is sound; only the Phase 3 hard-stop report was wrong.

**Which pooled rate, and why there are two (added 2026-09-04, final audit).**
The 1.98% and 0.52% above are **unweighted ratio-of-sums**: total numerator over
total denominator across all 7,278 respondents, with no survey weight applied.
They describe the file. They are **not** the quantity the analysis estimates.

The pre-registered estimand is the **`PERSON_FINWT0`-weighted mean of the
per-respondent rates**, which is what `src/weighting.py` computes and what every
result in `outputs/RESULTS.md` and `outputs/tables/` reports. Both, to 4 dp:

| Family | Unweighted ratio-of-sums (descriptive) | Weighted mean-of-rates (the analysis estimand) |
|---|---|---|
| A, item nonresponse | 1.9756% | **1.3935%** |
| C, response error | 0.5237% | **0.3606%** |

The two differ because the weights and the aggregation both differ, not because
either is wrong. The analysis figure is the smaller one, and it is the one the
arm rates reconcile to: H1's treatment 1.2230% and control 1.4359% average to
1.39%, not to 1.98%. If you are checking a number in `RESULTS.md`, the
mean-of-rates column is the one to check against. If you are describing the file
itself, use the ratio-of-sums column and say so.

Verified 2026-09-04 by independent recomputation from `analysis_frame.parquet`.
This note was added because the file previously stated 1.98% with no formula and
no mention of the weighted figure, which left a reader unable to reproduce it or
to reconcile it against the arm rates.

**Column name correction:** This document previously referred to the
respondent identifier as `respondent_id`. The actual column in the file is
`respondent_idx`. Corrected below (2026-09-04: the correction had been applied
in the Frame Assembly section but missed in the Respondent Identifier table; the
table now reads `respondent_idx` too).

---

## Outcome Variables (Primary and Secondary)

### Family A: Item Nonresponse (PRIMARY)

| Variable | Type | Range | Meaning | Computation |
|---|---|---|---|---|
| `family_a_numerator` | int64 | [0, 368] | Count of survey items where respondent's answer is coded `Missing data (Not Ascertained)` | For each respondent, sum count of items with this code across the 368-item universe. |
| `family_a_denominator` | int64 | [0, 368] | Count of items applicable to this respondent (after excluding inapplicable skips) | For each respondent, count items NOT marked as `Inapplicable, coded N in [VAR]` (branching skips). Includes items with all other codes: substantive answers, not-ascertained, web-break-off, filter-missing, errors. |
| `family_a_rate` | float64 | [0.0, 1.0] | Proportion of applicable items where respondent did not provide an answer | numerator / denominator. If denominator = 0, rate = 0. |

**Denominator rule (primary, pre-registered):** Include `Missing data (Filter Missing)` items in the denominator. These represent items that were part of the respondent's question path (subject to branching logic) and should have been answered. If not answered, it is a failure (item nonresponse), not a skip.

**Denominator rule (sensitivity, pre-registered):** Exclude `Missing data (Filter Missing)` from denominator. Results are reported separately as "Sensitivity: excluding Filter Missing."

### Family C: Response Error (SECONDARY)

| Variable | Type | Range | Meaning | Computation |
|---|---|---|---|---|
| `family_c_numerator` | int64 | [0, 368] | Count of items where respondent's answer is coded as a commission error or multiple-selection error | For each respondent, sum count of items where the value label contains (case-insensitive): "multiple responses selected in error" OR "commission error" |
| `family_c_denominator` | int64 | [0, 368] | Count of applicable items (same definition as Family A denominator) | Same as family_a_denominator. Items coded `Inapplicable` are excluded. |
| `family_c_rate` | float64 | [0.0, 1.0] | Proportion of applicable items with response errors | numerator / denominator. If denominator = 0, rate = 0. |

**Denominator rule:** Same as Family A (inapplicable items excluded).

### Family B: Break-off (SECONDARY, WEB-ONLY)

**Status:** Built in Phase 3b (2026-09-03). Not present in the original Phase 3
output; the note below describing it as deferred to Phase 5 is superseded.

| Variable | Type | Range | Meaning | Computation |
|---|---|---|---|---|
| `family_b_numerator` | float64 | [0, 368] or NaN | Count of items coded `Missing data (Web partial - Question Never Seen)` | For web respondents, sum count of items with this code. NaN for paper respondents (out of scope; see below). |
| `family_b_denominator` | float64 | [0, 368] or NaN | Count of items applicable to this web respondent (same rule as `applicable_count`) | `applicable_count` for web respondents. NaN for paper respondents. |
| `family_b_rate` | float64 | [0.0, 1.0] or NaN | Proportion of applicable items never shown to the respondent | numerator / denominator, web respondents only. NaN for paper. |

**Scope, per pre-registration:** "Paper-mode respondents are excluded from
this analysis because paper surveys do not have the technical mechanism for
mid-survey abandonment that web surveys do." "Paper respondents are not
included in this analysis."

**Ambiguity resolved (Phase 3b decision):** The pre-registration says paper
respondents are "excluded" / "not included," which is consistent with either
(a) storing NaN for them in a per-respondent frame, since the metric is out of
scope, or (b) storing 0, since they mechanically cannot break off and a
literal reading of "never seen" would always be false for them. **NaN was
chosen.** Reasoning: this frame's existing convention (Family A, C) uses 0
only when a rate is validly computed and happens to be zero (denominator > 0,
numerator = 0). Coding paper respondents as 0 would misrepresent "this metric
does not apply to this respondent" as "this respondent was assessed and had
zero break-off," and would let a downstream analyst silently include 2,417
respondents in a Family B calculation without an explicit mode filter. NaN
forces the filter. See `docs/decisions.md`, Phase 3b entry, for the full
reasoning; Phase 5b needs to know this if the alternative (0) is preferred at
analysis time.

**Anomaly noted, not fixed:** One item, `ClinTrials2_Cnt` (a derived count
variable, not excluded by the `_Cat`/`_OS` naming rules because it is named
`_Cnt`), carries a single combined value label — `"No options selected in H2
(Missing data or Web partial - Question never seen)"` — that conflates two
distinct missingness types. It matches the Family B pattern for 85 respondents
who used the **paper** form, where a literal "never seen" (web break-off)
interpretation is not mechanically possible. Because Family B is scoped to web
respondents only, this anomaly does not affect `family_b_*` (paper rows are
NaN regardless), but it is baked into `applicable_count` for those 85
respondents in exactly the same way the more general Family A finding below
is, since the item is not marked `Inapplicable`. Flagged for awareness; the
item universe freeze means it is not reclassified here.

---

## Design and Weighting Variables

### Respondent Identifier
| Variable | Type | Meaning |
|---|---|---|
| `respondent_idx` | int64 | Unique respondent index (0 to 7,277). Maps directly to row order in original .rda file. |

### Randomization Flag
| Variable | Type | Values | Meaning |
|---|---|---|---|
| `Treatment_H7_2` | pandas `category` | `"Included in Commitment Statement group"` (n=1,513), `"Not included in Commitment Statement group"` (n=5,765) | Experimental assignment. Carried in frame but not used during Phase 3 or 3b (arm-blind construction); analyzed from Phase 5b. |

**Corrected 2026-09-04 (final audit).** This table previously typed
`Treatment_H7_2` as `categorical` with values `1, 2` and described 1 as the
statement arm. The column in `analysis_frame.parquet` holds the two **text
labels** above, not integers. Anyone filtering on `Treatment_H7_2 == 1` gets an
empty frame, silently. This is the same class of trap the withdrawn Phase 5
analysis fell into. The heading's "(NOT ANALYZED YET)" tag was also stale, left
over from Phase 3.

### Commitment Statement Compliance Flag (NOT ANALYZED YET)
| Variable | Type | Values | Meaning |
|---|---|---|---|
| `CommitmentStmt` | categorical | Yes, No, Missing data (Not Ascertained), Inapplicable, not in treatment group | Respondent's agreement to the commitment statement. Only asked of respondents with Treatment_H7_2 = 1. Inapplicable for all 5,765 respondents with Treatment_H7_2 = 2. Carried in frame but not analyzed during Phase 3 or 3b. |

**Verified intact 2026-09-03 (Phase 3b, Part 5):** Pooled category counts in
the frame, confirmed directly from `analysis_frame.parquet`: 1,389 `Yes`, 14
`No`, 110 `Missing data (Not Ascertained)`, 5,765 `Inapplicable, not in
treatment group`. This matches the count the 2026-09-03 incident review
reported and refutes Phase 5's claim that this variable produced n = 0 in the
treatment arm — that was a filtering bug in Phase 5's code, not a data defect.

**How Phase 5b must filter this variable, to not repeat the bug:**
- The four category values are the **exact strings above**, not numeric codes
  and not shorthand. In particular, "not ascertained" is stored as
  `"Missing data (Not Ascertained)"`, not `"Not Ascertained"` or `-9`. A
  filter comparing against the wrong string silently matches zero rows
  without raising an error, which is consistent with how Phase 5 produced
  n = 0.
- To build the per-protocol comparison group (agreed vs. did not agree, among
  the treatment arm only): filter `Treatment_H7_2 == "Included in Commitment
  Statement group"` first, then split on `CommitmentStmt in {"Yes"}` vs.
  `CommitmentStmt in {"No", "Missing data (Not Ascertained)"}`. Do not filter
  `CommitmentStmt` alone without the `Treatment_H7_2` filter — `Inapplicable,
  not in treatment group` and `Missing data (Not Ascertained)` are different
  values and must not be collapsed.
- `Treatment_H7_2` is categorical text (`"Included in Commitment Statement
  group"` / `"Not included in Commitment Statement group"`), not `1`/`2`
  integers, in this frame. A numeric-equality filter (`== 1`) will also
  silently match nothing.

### Survey Weights
| Variable | Type | Meaning | Usage |
|---|---|---|---|
| `PERSON_FINWT0` | float64 | Final person-level weight (full sample weight) | Point estimates: weighted mean outcomes are computed using PERSON_FINWT0. |
| `PERSON_FINWT1` through `PERSON_FINWT50` | float64 (each) | Jackknife replicate weights (50 total) | Variance estimation: standard errors and confidence intervals computed via jackknife replication over these 50 weights. See NCI's Analysis Recommendations. |

### Survey Design Strata
| Variable | Type | Meaning |
|---|---|---|
| `STRATUM` | categorical | Primary stratum for survey design (e.g., "Low minority urban area", "High minority urban area"). Identifies the stratum each respondent was sampled from. |
| `VAR_STRATUM` | categorical | Variance stratum identifier (e.g., "7_LU", "7_HU"). Used internally by NCI for design-effect calculations. |

### Survey Mode (added Phase 3b, 2026-09-03)
| Variable | Type | Values | Meaning |
|---|---|---|---|
| `FormType` | categorical | `HINTS7, standard version - web`, `HINTS7, standard version - paper` | Raw codebook variable ("Flag for Form Version"). Confirmed against `HINTS 7 Public Codebook.pdf`, page 37 (`Variable Name: FormType`, `Variable Format: FORMTYPEF`): value 2 = paper, value 5 = web. Pooled distribution in the frame: 4,861 web (66.8%), 2,417 paper (33.2%), summing to 7,278. Matches the codebook's published unweighted counts exactly. Required by the original Phase 3 prompt and the pre-registered mode subgroup; absent from Phase 3's original 63 columns. |

**Required for:** Family B scoping (below) and the pre-registered mode
subgroup test (Phase 5b).

---

## Item Universe: Classification of 515 Columns

### Summary
- **Total columns:** 515
- **In item universe:** 368 (analyzed)
- **Excluded:** 147
  - Design variables (52): weights, strata, identifiers
  - Experiment flags (3): Treatment_H7_1, Treatment_H7_2, CommitmentStmt
  - Derived/recoded (28): variables ending in `_Cat`, `_Cat2`, etc.
  - Open-text fields (8): variables ending in `_OS`
  - No outcome codes (56): metadata, administrative, regional codes

### Exclusion Rules Applied

| Exclusion Reason | Count | Definition |
|---|---|---|
| `design_variable` | 52 | PERSON_FINWT0-50, STRATUM, VAR_STRATUM, Weight, HHID |
| `experiment_flag` | 3 | Treatment_H7_1, Treatment_H7_2, CommitmentStmt |
| `derived_variable` | 28 | Variables ending in `_Cat` (e.g., CAREGIVINGCOND_CAT) or `_Cat2` |
| `open_text_field` | 8 | Variables ending in `_OS` (e.g., CaOther_OS) |
| `no_outcome_codes` | 56 | Variables with no value labels containing outcome codes |

### Inclusion Rule

An item is in the analyzable universe if it appears in the HINTS 7 public file AND its value labels include at least one of:
- `Missing data (Not Ascertained)`
- `Missing data (Web partial - Question Never Seen)`
- `Missing data (Filter Missing)`
- `Multiple responses selected in error`
- `Question answered in error (Commission Error)`
- `Inapplicable, coded N in [VAR]` (any variant)

Complete list of included items and their applicable rules: `data/processed/item_denominator_map.csv`

---

## Inapplicable (Skip) Codes Excluded from Denominators

The codebook contains 30+ variants of "Inapplicable" codes, each marking items that were skipped due to branching logic. These are legitimate skips, not failures, and are excluded from all denominators.

### Common Inapplicable Patterns

| Pattern | Example | Interpretation |
|---|---|---|
| `Inapplicable, coded N in [VAR]` | "Inapplicable, coded N in FreqUseInternet" | Item was branched out because respondent's answer to FreqUseInternet qualified them for skip. |
| `Inapplicable, not in treatment group` | (CommitmentStmt for respondents with Treatment_H7_2 = 2) | Item not asked because respondent was not in the experiment arm. |
| `Inapplicable, [specific reason]` | "Inapplicable, not a web respondent" | Item was branched out for a specific reason. |

**Denominator rule:** For each respondent and each item in the universe, if the respondent's code is any "Inapplicable" variant, the item is excluded from the denominator for that respondent. The item is not counted as applicable, and no outcome is recorded for it.

**Verification:** The applicable_count column should never exceed 368 (the size of the item universe). Min, median, and max applicable_count are reported in profiling.ipynb (Phase 3 final output).

---

## Filter Missing Handling: Primary vs. Sensitivity

The code `Missing data (Filter Missing)` is ambiguous in interpretation:
- **Interpretation 1 (PRIMARY):** The item was part of the respondent's question path (no branching skip), but no answer was recorded. This is an item nonresponse failure and should be counted in the denominator.
- **Interpretation 2 (SENSITIVITY):** The code marks items that were legitimately skipped due to branching, similar to "Inapplicable". Should be excluded from the denominator.

**Pre-registration commitment:** Both interpretations are computed and reported. The PRIMARY interpretation uses Filter Missing in the denominator. The SENSITIVITY version excludes it.

**Status correction (Phase 3b, 2026-09-03):** R6 was marked MITIGATED in Phase
3 on the claim that the sensitivity variant was "also built." It was not; no
sensitivity columns existed in `analysis_frame.parquet` until Phase 3b. Built
now; see columns below.

### Sensitivity columns (built Phase 3b)

| Variable | Type | Meaning | Computation |
|---|---|---|---|
| `applicable_count_sens` | int64 | Applicable items excluding both `Inapplicable` variants and `Missing data (Filter Missing)` | For each respondent, count items that are neither Inapplicable nor Filter Missing. This is the sensitivity denominator for Family A and Family C (Family A and C use the same denominator, per the original data dictionary). |
| `family_a_rate_sens` | float64 | Family A rate under the sensitivity denominator | `family_a_numerator / applicable_count_sens`. Numerator is unchanged — Filter Missing status only affects which items are in the denominator, not which items are counted as a nonresponse failure. |
| `family_c_rate_sens` | float64 | Family C rate under the sensitivity denominator | `family_c_numerator / applicable_count_sens`. |
| `family_b_denominator_sens` | float64, NaN for paper | Family B denominator under the sensitivity spec, web respondents only | `applicable_count_sens` restricted to web respondents. |
| `family_b_rate_sens` | float64, NaN for paper | Family B rate under the sensitivity denominator, web respondents only | `family_b_numerator / family_b_denominator_sens`. |

**Pooled rates, primary vs. sensitivity (both computed directly from the
written file, 2026-09-03):**

Both columns are **unweighted ratio-of-sums**, the descriptive aggregation
defined in the pooled-rate note at the top of this file. They compare two
denominator rules against each other, not against the analysis estimand.

| Family | Primary (pooled) | Sensitivity (pooled) | Difference |
|---|---|---|---|
| A | 1.976% | 1.988% | +0.012 pp |
| C | 0.524% | 0.527% | +0.003 pp |
| B (web only) | 7.671% | 7.692% | +0.021 pp |

All three differences are far below the smallest MDE in the pre-registered
grid (1.8 pp for Family A at a 5% baseline; 0.4 pp for Family C at a 0.5%
baseline). The Filter Missing rule does not materially change any pooled
rate. 12,982 (respondent x item) cells, pooled, are coded Filter Missing and
excluded under the sensitivity spec.

## Family A Denominator vs. Pre-Registration: A Contradiction, Not Fixed

**Finding (Phase 3b, 2026-09-03):** The pre-registration's Family A
denominator-construction table (`docs/pre-registration.md`, "Denominator
construction rule (detailed)") explicitly excludes `Missing data (Web partial
- Question Never Seen)` from Family A's denominator: "**NO** ... Not a
failure of item nonresponse, but a break-off. Counted in Family B instead."

`family_a_denominator` (== `applicable_count`), as built in Phase 3 and
unchanged by Phase 3b, does **not** implement this exclusion. `DenominatorBuilder`
excludes only items whose value label starts with `"Inapplicable"`; a
Web-Never-Seen code does not start with that string, so it is currently
counted as applicable in Family A's denominator.

**Magnitude, confirmed directly from the file:** 107,773 (respondent x item)
cells pooled, affecting 612 respondents (8.4% of the sample), are coded
Web-Never-Seen and are currently counted in `family_a_denominator`. If Family
A's denominator were rebuilt to also exclude these cells (matching the
pre-registration's literal table), the pooled Family A rate would move from
1.976% to 2.083%, a difference of about 0.11 percentage points — smaller than
every value in the pre-registered MDE grid, but not zero, and a real
construction choice, not a rounding artifact.

**Not fixed here.** Per this phase's instructions, Family A is not silently
changed. The denominator freeze holds; `family_a_denominator` and
`family_a_rate` are byte-for-byte what Phase 3 wrote. This is reported as a
finding for Neyda: either (a) the pre-registration's Family A table is the
governing rule and `family_a_denominator` needs a dated amendment/rebuild in
Phase 4b or 5b, or (b) the current construction is the intended one and the
pre-registration's table needs a dated amendment to match it. Both are
legitimate resolutions; choosing between them is not this phase's call.

---

## Outcome Codes Matched: Complete Mapping

To ensure transparency and auditing, every distinct outcome code string in the data is listed below with the family it belongs to.

### Family A (Item Nonresponse)
- `Missing data (Not Ascertained)`

### Family C (Response Error)
- `Multiple responses selected in error`
- `Multiple Responses Selected in Error` (variant)
- `Question answered in error (Commission Error)`
- `Question answered in error (commission error)` (variant)

### Family B (Break-off, computed in Phase 3b)
- `Missing data (Web partial - Question Never Seen)`
- Also matches `ClinTrials2_Cnt`'s combined code (see anomaly note above), which
  affects 85 paper-mode respondents but does not affect `family_b_*` since
  Family B is scoped to web respondents only.

### Inapplicable (Excluded from all denominators)
- `Inapplicable, coded N in [30+ variants]`
- `Inapplicable, not in treatment group`
- Other Inapplicable patterns

---

## Data Quality Checks

### Completed in Phase 3

- ✓ Row count: 7,278 = 7,278 (matches source)
- ✓ Value labels preserved: 405 categorical columns retained
- ✓ No rate > 1.0 (all rates in [0, 1])
- ✓ family_a_numerator <= family_a_denominator (all respondents)
- ✓ family_c_numerator <= family_c_denominator (all respondents)
- ✓ applicable_count <= 368 (all respondents, no denominator-sprawl error)
- ✓ No negative denominators
- ✓ No NaN or inf in outcome rates (zeros stored, not NaN)

### Deferred to Phase 5

- Pooled outcome rates (tested in profiling.ipynb, Phase 3) — **superseded.**
  The pooled rates actually in the file are 1.98% (A) and 0.52% (C); see the
  correction note at the top of this document and the 2026-09-03 incident
  entry in `docs/decisions.md`.
- Design effect on MDE (estimated from replicate weights) — Phase 4b
- Comparison to published HINTS estimates (harness check in Phase 4) — reopened as Phase 4b

### Completed in Phase 3b (2026-09-03)

- ✓ Row count re-asserted 7,278 = 7,278 after extension
- ✓ `applicable_count` recomputed from raw data and verified byte-for-byte
  identical to the frozen frame before any column was added (parity check;
  see `src/build_outcomes.py`, `main_phase3b()`)
- ✓ Item universe recomputed (368 items) and verified identical to
  `item_denominator_map.csv` on disk
- ✓ `family_a_numerator` and `family_c_numerator` sums unchanged after
  extension (41,140 and 10,906 respectively)
- ✓ `family_b_rate` in [0, 1] for all web respondents; NaN for all paper
  respondents (verified, not just asserted)
- ✓ `applicable_count_sens` <= `applicable_count` for all respondents
- ✓ Written file re-read fresh from disk and re-verified after write (not
  read from the in-memory object that wrote it)

---

## Frame Assembly: Column Order and Naming

### Outcome Variables, primary (8 columns)
1. `family_a_numerator`
2. `family_a_denominator`
3. `family_a_rate`
4. `family_c_numerator`
5. `family_c_denominator`
6. `family_c_rate`
7. `applicable_count` (used by both families)

### Outcome Variables, Family B and sensitivity (9 columns, added Phase 3b)
1. `family_b_numerator`
2. `family_b_denominator`
3. `family_b_rate`
4. `applicable_count_sens`
5. `family_a_rate_sens`
6. `family_c_rate_sens`
7. `family_b_denominator_sens`
8. `family_b_rate_sens`
9. `FormType` (mode variable; also serves the pre-registered mode subgroup)

### Design Variables (54 columns)
- Treatment assignment: `Treatment_H7_2`
- Compliance: `CommitmentStmt`
- Weights: `PERSON_FINWT0`, `PERSON_FINWT1`...`PERSON_FINWT50` (51 total)
- Strata: `STRATUM`, `VAR_STRATUM`

### Respondent Identifier (1 column)
- `respondent_idx` (see column-name correction note at the top of this document)

---

## File Format and Access

**File:** `data/processed/analysis_frame.parquet`
**Format:** Apache Parquet (columnar, compressed, fast)
**Encoding:** UTF-8
**Shape:** 7,278 rows × 72 columns (63 Phase 3 + 9 Phase 3b)
**Size:** ~5 MB (uncompressed, order of magnitude; Phase 3b added float columns, some NaN)

**Loading in Python:**
```python
import pandas as pd
frame = pd.read_parquet('data/processed/analysis_frame.parquet')
```

**No aggregation or summarization applied.** Every row is a single respondent. Pooled profiling and treatment-arm comparisons are Phase 5b work.

---

## Arm-Blind Construction: Audit Trail

**This frame was constructed and extended blind to treatment arm.**

- Treatment_H7_2 and CommitmentStmt are carried as-is (required for Phase 5b)
- No outcome was computed or summarized by arm during Phase 3 or Phase 3b
- No column was added or removed based on arm-split results
- All validations (rate ranges, count comparisons, pooled rates reported in
  this document) are pooled across all 7,278 respondents, or pooled within
  the web/paper mode subgroup only — never split by `Treatment_H7_2`
- R5 (arm-split discipline) and R2 (denominator transparency) mitigations
  applied in Phase 3. Phase 3b operated under a results blackout (R14); the
  agent building this extension did not know which arm, if either, showed an
  effect.

---

## Footnote: Phase 3 and 3b Choices Documented

Every non-obvious judgment call made during Phase 3 or 3b is recorded in
`docs/decisions.md` with reasoning and date. Examples:
- Why items without certain outcome codes are excluded (Section: Item Universe Boundaries)
- How Inapplicable variants are parsed from codebook labels (Section: Denominator Rule Implementation)
- Filter Missing primary vs. sensitivity choice (Section: Filter Missing Ambiguity)
- Why Family B stores NaN, not 0, for paper respondents (Phase 3b entry)
- The Family A denominator vs. pre-registration contradiction (Phase 3b entry; not fixed, reported as a finding)

---
