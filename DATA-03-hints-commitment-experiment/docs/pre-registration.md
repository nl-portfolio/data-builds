# Pre-Registration: Did a Commitment Statement Improve Survey Data Quality?

**Analyst:** Neyda Larson  
**Written:** 2026-09-02  
**Committed:** 2026-09-02 19:18 UTC, commit 238c6c8  
**Status:** Locked on public commit. All amendments thereafter are dated and recorded in this file. **Amendment 1 (2026-09-03):** disclosure that the MDE grid was conservative for the realised data; no analysis change. See "Amendments" at the end.

---

## Study identification

**Research question:** Did a commitment statement at the start of the HINTS 7 survey reduce item nonresponse, break-offs, and response errors compared to no statement?

**Data source:** HINTS 7 (2024), National Cancer Institute. Public use file, n = 7,278. US federal public domain. Downloaded August 31, 2025, bundle HINTS7_R_20250731 (hints7_public.rda, 7,278 rows, 515 columns).

**Experiment source:** NCI administered a randomized controlled trial within the 2024 administration of the Health Information National Trends Survey. A subset of respondents (n = 1,513) received a commitment statement at the start of the survey asking them to commit to answering completely and accurately. The control group (n = 5,765) received no statement.

**Prior work by the data producer:** NCI ran this experiment and published results in the HINTS 7 Methodology Report, Tables 6-7 and 6-8. NCI reported the effect on **household response rate by arm** (27.7 percent treatment vs. 27.2 percent control, not significantly different). NCI's own methodology report states the statement was "intended to improve response data quality by, for example, reducing item nonresponse overall and break offs on web."

The three data quality outcomes this experiment was designed to improve—item nonresponse, break-off, and response error—are not reported in the methodology report. The randomization flags and all outcome codes are present in the public use file.

**What has been examined before writing this plan:**
- Variable existence verified in the public use file
- Treatment_H7_2 flag reconciled against codebook and companion variable; confirmed the flag correctly identifies the commitment statement arm
- Arm sizes confirmed: 1,513 assigned to treatment, 5,765 to control (respondent sample)
- No outcome statistics computed or stratified by arm

**What this analysis adds:** A direct answer to the question NCI posed but did not report: did the commitment statement reduce data quality failures (item nonresponse, break-off, response error)? We report the three outcome families that the statement was designed to affect, with pre-registered tests, confidence intervals, and an MDE analysis showing what effect sizes could have been detected. If the statement had no effect, the analysis pairs the null with the MDE grid so a reader can judge whether the null is informative or just underpowered.

---

## Hypotheses

### H1 (Primary): Item nonresponse

**Statement:** Respondents who received the commitment statement will show a lower item nonresponse rate than those who did not.

**Predicted direction:** Lower.

**Reason:** The commitment statement asks respondents to commit to providing "complete and accurate information." Commitment devices in psychology and survey methodology typically increase effort and follow-through. NCI stated this was the intended mechanism for reducing "item nonresponse overall" (per methodology report, section 2.5). A small effect is most plausible; survey-based commitment interventions typically move rates by 2-5 percentage points.

**Prior expectation of effect size:** Small (2-5 percentage points, relative reduction of 15-30% at a plausible 10-15% baseline nonresponse rate). **A null is also plausible.** NCI's finding on response rates (27.7% vs. 27.2%, a difference of 0.5 percentage points) suggests the statement's overall impact was modest. Item nonresponse may have moved less, the same, or not at all.

**What result counts as:**
- **Confirming:** Estimated nonresponse rate in the treatment arm is 3+ percentage points lower than in the control arm, and the 95% confidence interval does not cross the null or approaches statistical significance at alpha = 0.05 (two-sided).
- **Disconfirming:** Estimated rates are within 1 percentage point of each other, or the confidence interval spans both higher and lower rates in the treatment arm.
- **Uninformative:** The effect is between 1-3 percentage points and the confidence interval is wide; we cannot rule out both a clinically plausible effect and no effect. The MDE grid will clarify whether this is underpowering or a genuine weak signal.

### H2 (Secondary): Break-off rate

**Statement:** Among web-mode respondents, those who received the commitment statement will show a lower rate of break-off (abandonment partway through the survey) than those who did not.

**Predicted direction:** Lower.

**Reason:** Web surveys are subject to break-off because respondents can abandon at any point. A commitment statement might reduce dropout by increasing psychological commitment to completion. Break-off is a form of nonresponse and was explicitly named by NCI as one of the outcomes the statement was "intended to reduce."

**Prior expectation of effect size:** Small (absolute reduction of 1-3 percentage points, depending on baseline break-off rate). **Uncertainty is higher** because we do not know the baseline break-off rate in HINTS without examining the data stratified by arm. The MDE grid will show whether the experiment was powered to detect plausible effects.

**Note on scope:** This outcome applies to web respondents only. Break-off does not apply to paper respondents. The denominator is restricted to web mode.

**What result counts as:**
- **Confirming:** Treatment arm shows lower break-off rate with a confidence interval that does not cross the null.
- **Disconfirming:** Rates are similar or treatment arm shows higher break-off.
- **Uninformative:** Small difference (1-2 percentage points) with wide confidence interval; underpowering is the likely explanation if baseline break-off is low.

### H3 (Secondary): Response error rate

**Statement:** Respondents who received the commitment statement will show a lower rate of response errors (commission errors, multiple selections in error, and self-reported answer mistakes) than those who did not.

**Predicted direction:** Lower.

**Reason:** A commitment statement asking for "accurate" responses might reduce careless errors. This outcome is not explicitly named by NCI but is a plausible byproduct of increased effort and attention. It is the most exploratory of the three families and appears in the secondary set.

**Prior expectation of effect size:** Small or null. This is the least strongly motivated of the three outcomes. A positive finding would be interesting; a null is unsurprising.

**What result counts as:**
- **Confirming:** Treatment arm shows lower error rate, confidence interval does not cross the null.
- **Disconfirming:** Rates are similar or treatment arm shows higher error rate.
- **Uninformative:** Very small baseline error rate and correspondingly small numerator, limiting precision.

---

## Outcome definitions

This section specifies every outcome so a reader can reproduce each result from this description and the codebook alone, without reading the analysis code.

### Outcome family definitions

| Family | Name | Numerator code(s) | Applicability | Level | Primary or secondary |
|---|---|---|---|---|---|
| A | Item nonresponse | `Missing data (Not Ascertained)` | All applicable items, per respondent | Rate: count of not-ascertained / count of applicable items | PRIMARY |
| B | Break-off | `Missing data (Web partial - Question Never Seen)` | Web-mode respondents only, applicable items | Rate: count of never-seen / count of applicable items | SECONDARY |
| C | Response error | `Multiple responses selected in error`, `Question answered in error (Commission Error)` | All applicable items, per respondent | Rate: count of errors / count of applicable items | SECONDARY |

### Item universe: Defining analyzable items

**Applicable item set rule:** An item is part of the analyzable outcome universe if and only if:
1. It is coded in the HINTS 7 public use file as a numbered survey response variable (not a derived variable, weight, stratum, or metadata)
2. It has one of the following code patterns in its value labels:
   - `Missing data (Not Ascertained)`
   - `Missing data (Web partial - Question Never Seen)`
   - `Missing data (Filter Missing)`
   - `Multiple responses selected in error`
   - `Question answered in error (Commission Error)`
   - `Inapplicable, coded N in [VAR]` (any variant of the Inapplicable pattern)
   - A substantive response (the variable is not entirely empty or metadata)

**Exclusion rule:** Variables recording demographic information (age, race, gender, etc. coded directly by the survey), experimental arms (Treatment_H7_1, Treatment_H7_2), weights, strata, or sample identifiers are not part of the outcome families. The rule above defines the criteria; the complete list of analyzed items will be available in the analysis code and data dictionary.

**Rationale:** This rule identifies survey questions that were presented to the respondent and had the potential to be answered. It excludes non-item columns while capturing the full breadth of items across all sections of the questionnaire.

### Family A: Item nonresponse (PRIMARY OUTCOME)

**Numerator:** For each respondent, count of items where the response is coded `Missing data (Not Ascertained)`.

**Denominator:** For each respondent, count of items marked as applicable (i.e., all items in the outcome universe minus items coded `Inapplicable`).

**Outcome rate:** Numerator / Denominator, per respondent. Ranges from 0 (no nonresponses among applicable items) to 1 (all applicable items not ascertained).

**Denominator construction rule (detailed):**

| Outcome code | Respondent qualification | Inclusion in denominator? | Reasoning |
|---|---|---|---|
| `Missing data (Not Ascertained)` | Any | YES (counted in numerator, not denominator) | The item was presented and the respondent failed to answer. This is the failure we measure. |
| `Missing data (Web partial - Question Never Seen)` | Web-mode only | NO | The item was never shown; no opportunity to answer. Not a failure of item nonresponse, but a break-off. Counted in Family B instead. |
| `Missing data (Filter Missing)` | Any | **PRIMARY RULE: YES** | The item was part of the question path presented to the respondent (subject to branching logic). If a respondent did not answer it, that is a failure. (SEE SENSITIVITY ANALYSIS BELOW.) |
| `Inapplicable, coded N in [VAR]` (any variant) | Any | NO | The respondent's branching logic skipped this item legitimately (e.g., "have you ever smoked?" No -> skip the next 5 items). Not a failure. |
| Substantive response (any non-missing, non-inapplicable code) | Any | YES | The item was answered. Numerator = 0. |

**Sensitivity analysis on Filter Missing (committed in advance):**
If the Primary Rule (include Filter Missing in denominator) proves ambiguous during implementation or upon closer codebook examination, a second specification excluding Filter Missing from the denominator will be run and both sets of results reported. The Primary Rule estimate is the headline; the alternative is labeled "Sensitivity: excluding Filter Missing from denominator." Both will be reported; neither is hidden.

**Respondent-level metric:** Each respondent gets one nonresponse rate = (sum of Not Ascertained codes) / (total applicable items per that respondent's branching path).

**Analysis-level metric:** The treatment-control comparison is on mean item nonresponse rate, weighted by PERSON_FINWT0, with variance estimated via jackknife replicate weights.

### Family B: Break-off (SECONDARY OUTCOME)

**Scope:** Web-mode respondents only. Paper-mode respondents are excluded from this analysis because paper surveys do not have the technical mechanism for mid-survey abandonment that web surveys do.

**Numerator:** For each web-mode respondent, count of items coded `Missing data (Web partial - Question Never Seen)`.

**Denominator:** For each web-mode respondent, count of items that should have been shown, per the respondent's branching path (i.e., all items in the outcome universe minus items coded `Inapplicable`).

**Outcome rate:** Numerator / Denominator, per respondent.

**Interpretation:** If a respondent's break-off rate is > 0, they abandoned the survey at some point. If the rate is close to 1, they abandoned early. A rate of 0 means they completed all applicable items.

**Respondent-level metric:** Each web respondent gets one break-off rate. Paper respondents are not included in this analysis.

**Analysis-level metric:** Treatment-control comparison on mean break-off rate among web respondents, weighted by PERSON_FINWT0, with variance via jackknife.

### Family C: Response error (SECONDARY OUTCOME)

**Numerator:** For each respondent, count of items coded as either:
- `Multiple responses selected in error`, OR
- `Question answered in error (Commission Error)`

(These are two distinct but related codes representing careless or inattentive answering. They are combined into one numerator.)

**Denominator:** For each respondent, count of items in the outcome universe minus items coded `Inapplicable`.

**Outcome rate:** Numerator / Denominator, per respondent.

**Respondent-level metric:** Each respondent gets one error rate.

**Analysis-level metric:** Treatment-control comparison on mean error rate, weighted by PERSON_FINWT0, with variance via jackknife.

---

## Minimum detectable effect

Sample sizes are fixed by NCI's design and the realized response achieved:
- **Treatment arm:** n = 1,513
- **Control arm:** n = 5,765
- **Total:** n = 7,278

The analysis is not a sample-size calculation. The question is: given these arm sizes, what is the smallest effect this experiment could have detected?

### MDE grid: Two-sided alpha = 0.05, power = 0.80

For each outcome family, we compute the smallest difference in mean rates the experiment could detect, assuming various baseline (control-arm) rates and the realized sample sizes.

**Family A (Item nonresponse):**

| Assumed baseline rate (control arm) | Sample size treatment / control | MDE (percentage points) | MDE (relative reduction) |
|---|---|---|---|
| 5% | 1,513 / 5,765 | 1.8 | 36% |
| 10% | 1,513 / 5,765 | 2.5 | 25% |
| 15% | 1,513 / 5,765 | 3.1 | 21% |
| 20% | 1,513 / 5,765 | 3.6 | 18% |
| 25% | 1,513 / 5,765 | 4.0 | 16% |

**Notes on the grid:**
- Computation: Two-sample t-test, proportions, assuming simple random sampling. Formula: MDE = 2.8 * sqrt(p(1-p) * (1/n1 + 1/n2)) where p is the control-arm proportion, and 2.8 is the critical value for alpha=0.05 two-sided and power=0.80 (approximately 1.96 + 0.84).
- **Design effect applied at analysis.** HINTS uses a complex survey design with stratification and clustering. The effective sample size is smaller than the nominal sample size. NCI's Analysis Recommendations document provides guidance on design effect for HINTS 7. The MDE grid reported here uses simple random sampling as a lower bound; the final analysis applies design effects estimated from the replicate weights.
- **How to interpret:** If the true baseline nonresponse rate is 10%, and the treatment effect is 2% points, the MDE grid shows this experiment was powered to detect it (MDE is 2.5 pp). If the effect is 1.5 pp, the experiment was underpowered for that effect size; a null result would be uninformative.

**Family B (Break-off, web respondents only):**

Baseline break-off rates in HINTS are not known without examining the data. Web-survey break-off rates in national surveys typically range from 5-15%, depending on survey length and respondent engagement. The MDE grid will span this range once web-mode respondent counts are determined from the data.

Web-mode respondent counts and the resulting MDE values will be reported in the analysis. The MDE is computed using observed web-mode sample sizes, not the total n.

**Family C (Response error):**

Response error rates (commission errors, multiple selections in error) are rare in most surveys. Baseline rates are typically < 2%. MDE grid:

| Assumed baseline rate | MDE (percentage points) | MDE (relative) |
|---|---|---|
| 0.5% | 0.4 | 80% |
| 1% | 0.6 | 60% |
| 2% | 0.8 | 40% |

**Note:** If baseline error rate is very low, the MDE becomes large relative to the baseline (column 3). This means the experiment is underpowered to detect plausible absolute effects unless the statement has a large proportional impact.

### Design effect and complex-survey MDE

HINTS uses stratified cluster sampling. The effective sample size for estimation is smaller than the nominal sample size due to the design effect (DEFF). NCI provides guidance in their Analysis Recommendations document.

The MDE grids reported above assume simple random sampling. Design effects in HINTS typically range from 1.2 to 1.5 for most outcome rates, which would increase the MDE by 10-20%.

**Final MDE grid, adjusted for design effect:** The reported MDE in the analysis reflects design effects estimated from the data using the replicate weights. This accounts for the complex survey design and produces MDE values more conservative (larger) than the simple-random-sample MDE shown above.

### Interpretation of null results: Informative vs. underpowered

**Committed in advance:** A null result (treatment effect ≈ 0, confidence interval includes 0) can mean two different things:

1. **Informative null:** The effect is smaller than the MDE, AND the MDE is small (< 3 pp for item nonresponse), suggesting the statement genuinely had no or negligible impact.
2. **Underpowered null:** The effect is smaller than the MDE, AND the MDE is large (> 5 pp for item nonresponse), suggesting the experiment lacked power to detect plausible effects.

In the results section, every null is paired with the relevant row of the MDE grid so a reader can distinguish. If the baseline rate and MDE together imply the experiment was underpowered, the case study will state that explicitly.

---

## Estimands and analysis

### Primary estimand: Intention to treat

**Definition:** The average effect of **assignment** to the commitment statement arm (Treatment_H7_2 = 1) versus not assigned (Treatment_H7_2 = 2 and all households never entered into the experiment).

**What we're comparing:** Respondents assigned to receive the commitment statement vs. all respondents not assigned to that arm. This includes both randomized controls (assigned to Treatment_H7_2 = 2) and households that were never part of the experiment at all.

**Why this is valid:** The experiment was randomized, so assignment is independent of potential outcomes. Comparing the statement arm to everyone else estimates the causal effect of "being assigned to receive the statement." Nobody outside the statement arm saw the statement (non-treatment respondents were either randomized controls or never in the experiment), so the contrast is unbiased.

**Why we state this explicitly:** Some reviewers might wonder whether including non-experiment households in the control arm biases the estimate. It does not. The comparison is still ITT because randomization ensures balance on all baseline characteristics. We state it here so the question is preempted.

### Secondary estimand: Per protocol (descriptive, non-randomized)

**Definition:** Among respondents assigned to the commitment statement arm (Treatment_H7_2 = 1), the average outcome for those who agreed to commit (CommitmentStmt = Yes) versus those who did not (CommitmentStmt = No or Not Ascertained).

**Sample sizes:** 1,389 agreed, 14 declined, 110 not ascertained. Comparison is agreement (Yes) vs. non-agreement (No + NA), so n = 1,513 split into ~1,389 vs. ~124.

**Key limitation:** This comparison is not randomized. Agreement is likely related to engagement, education, motivation, and other baseline characteristics that also predict data quality. A large difference in this comparison does not imply the commitment statement caused the difference.

**Reporting:** Per-protocol estimates will be reported alongside ITT, but always labeled "descriptive" and never presented as a confidence interval without the label. Language: "Among those assigned to the statement arm, respondents who agreed showed [X], compared to [Y] among those who did not agree. (Descriptive estimate; not adjusted for selection bias.)"

**Why report it at all:** Omitting it invites accusations of hiding inconvenient findings. Reporting it honestly (with a clear label) is more defensible than silence.

### Non-compliance group: Not statistically tested

**Sample:** 14 declined the commitment statement, 110 not ascertained (CommitmentStmt = No or -9 among Treatment_H7_2 = 1).

**Analysis:** These groups are too small for inference (CI would be very wide, power near zero). They will be described (e.g., "14 respondents in the treatment arm declined to read the statement") but not tested.

---

## Statistical procedures

### Estimation: Survey-weighted proportions

**Point estimate:** For each outcome rate, we estimate the population proportion using `PERSON_FINWT0` (the final full-sample weight). All headline numbers are weighted. Unweighted counts are reported alongside for transparency (e.g., "1,513 respondents, representing 52.3 million individuals").

**Variance and confidence intervals:** Jackknife variance estimation over `PERSON_FINWT1` through `PERSON_FINWT50` (the 50 replicate weights). Standard error is the standard deviation of the jackknife replicates; 95% CI is point estimate ± 1.96 * SE.

**Reference:** NCI's own Analysis Recommendations document, section on variance estimation.

### Test statistic: Two-sample weighted comparison

**Hypothesis test:** For each outcome family (A, B, C), we test the null hypothesis that the mean outcome is identical in the treatment arm and the control arm.

**Test type:** Wald test on the difference in weighted proportions, using the jackknife standard error.

**Test statistic:** z = (p_treatment - p_control) / SE(difference), where SE(difference) = sqrt(SE(p_tx)^2 + SE(p_ctl)^2).

**P-value:** Two-sided.

### Multiple comparisons correction

**Family definition:** All statistical tests conducted on the three outcome families (A primary, B and C secondary) are part of one multiple-comparison family. Any subgroup analyses (see below) are also in the family.

**Total number of tests in the family (before subgroups):** 3 (one per outcome family).

**Correction method:** Holm-Bonferroni procedure applied to the three tests. This controls family-wise error rate at alpha = 0.05.

**Decision rule:**
1. Rank the three p-values from smallest to largest.
2. Compare the smallest to alpha / 3 = 0.0167. If p < 0.0167, reject and continue.
3. Compare the second-smallest to alpha / 2 = 0.025. If p < 0.025, reject and continue.
4. Compare the largest to alpha / 1 = 0.05. If p < 0.05, reject.

**Reporting:** Every p-value in the results section is labeled with the corrected threshold. E.g., "Item nonresponse: treatment 8.2% vs. control 10.1%, difference 1.9 pp (p = 0.032, uncorrected; p = 0.096 after Holm correction for 3 tests, not significant at the family-wise level)."

**Rationale for Holm over Benjamini-Hochberg:** Holm is more conservative and more appropriate for confirmatory testing when the total number of tests is small (3). Benjamini-Hochberg controls false discovery rate, which is better suited to exploratory analyses with many tests. We use Holm here because the three outcome families were specified before analysis.

### Pre-registered subgroups

**Mode (paper vs. web):** Item nonresponse, break-off, and response error by mode.
- Rationale: Response mode is a strong predictor of both nonresponse and break-off. Break-off is mechanically impossible on paper (no mid-survey abandonment), so paper respondents are excluded from Family B only. The mode subgroup test may reveal whether the commitment statement's effect differs by modality.
- Specification: Mode is coded from survey administration records and will be included as a subgroup factor in the pre-registered analysis plan.

**Any subgroup analysis not listed here (including post-hoc investigations of demographic subgroups, engagement subgroups, or item-specific patterns) is exploratory.** Exploratory results will be labeled as such in every appearance ("Exploratory subgroup analysis, not corrected for multiple comparisons").

### Sequential testing: Documented as a pitfall, not committed

No interim analyses or peeking is planned or conducted. The data are analyzed once, after all processing is complete.

**Illustration (not an inference):** The analysis will include a brief worked example showing what the p-value trajectory would have looked like if we had peeked at the data after each 20% of respondents. This is a pedagogical illustration of why pre-registration matters and why peeking is a bad idea. The trajectory is shown for the primary outcome only and is not used for inference.

---

## Falsification and stopping conditions

### This analysis would be abandoned if:

1. **The denominator cannot be constructed without judgment calls that determine the sign of the result.** If the interpretation of branching logic or inapplicable codes proves circular (e.g., the rule for deciding whether an item "applies" to a respondent itself depends on the outcome value), the project would fall back to an alternative analysis (a pre-approved fallback is available).
2. **Treatment assignment cannot be verified.** If data validation finds that Treatment_H7_2 flag distribution contradicts CommitmentStmt alignment, the analysis stops and the reconciliation is revisited.

### A null will be reported as a null

If none of the pre-registered tests show a significant effect (after multiple-comparison correction), the analysis reports this as the finding:

- "The commitment statement did not significantly reduce item nonresponse, break-off, or response error at the family-wise 0.05 level."
- The MDE grid is paired with this finding. If the MDE is small (< 3 pp), the null is informative. If large (> 5 pp), underpowering is likely.
- **No post-hoc subgroup hunting.** We do not search the data for a subgroup that moved if the pre-registered tests are null.

### Deviations from this plan

Any changes to the pre-registration after this document is committed to the public repo are recorded in this file as **dated amendments.** They include:
- What changed
- Why it changed
- When the change was made (before or after seeing results)
- How it affects the interpretation

**Silent editing is not permitted.** Every modification leaves a timestamped trace.

---

---

## Amendments

[This section records all changes made after the public commit. The plan cannot be changed silently; every amendment is dated and explained here.]

### Amendment 1 — 2026-09-03 — The MDE grid was conservative for the realised data (disclosure, no analysis change)

**What changed:** Nothing in the analysis. This amendment records that the
Minimum Detectable Effect grid in the "Minimum detectable effect" section above
**understated the experiment's power** for the primary outcome, and states the
correct design effect.

**Why:** The grid was built (arm-blind, as required) on two assumptions that the
realised data did not bear out:

1. **Assumed baseline rates of 5–25%** for item nonresponse. The realised
   weighted item-nonresponse rate is **~1.4%** (mean of per-respondent rates) /
   ~2.0% (ratio of sums) — below the grid's lowest row.
2. **`p(1−p)` as the per-respondent variance** in the MDE formula
   (`MDE = 2.8·√(p(1−p)(1/n₁ + 1/n₂))·√DEFF`). For a stable low rate the
   per-respondent rate's actual weighted variance is roughly **9× smaller** than
   `p(1−p)`, because most respondents cluster near a low rate rather than being
   Bernoulli(p) at the item level aggregated up.

**The design effect.** The grid assumed a design effect of 1.2–1.5. Phase 4b
measured the design effect **for the per-respondent rate estimator** — the
`survey::svymean(deff = TRUE)` quantity, jackknife variance over the
SRS-of-the-rate variance — at **1.56 (Family A) / 1.44 (Family C) /
2.93 (Family B, web)**, confirmed independently in R. This is close to the grid's
assumption and immaterial to the MDE.

**On the "≈ 3.3" figure.** An earlier informal check (referenced in the incident
record and in `STAKEHOLDER_NARRATIVE.md`) put the design effect near 3.3 and
raised the concern that the experiment was underpowered to answer its own
question. **That 3.3 was the Kish weight design effect** — `1 + CV²(weights)`,
a whole-sample summary of weight variability (effective n ≈ 2,244, DEFF ≈ 3.24)
— **not the design effect of the estimator actually used.** It is a
conservative proxy computed when the replicate weights are not in hand; here the
replicate weights are in hand and give ~1.5. The 3.3 figure should not be cited
as this analysis's design effect.

**Consequence, applied by the pre-registered verdict rule (Phase 5b):** the real
empirical MDE for the primary outcome is **≈ 0.32 pp** (2.8 × the observed
jackknife SE of the arm difference), against a grid that implied 1.8–4.0 pp. The
observed H1 effect (0.21 pp, 95% CI [−0.44, +0.01], p = 0.063 uncorrected) is
below that MDE and the MDE is well under the plan's 3 pp "informative" bar, so
by the plan's own rule the H1 result is an **informative null**, not an
underpowered one. Break-off (H2) and the very rare response-error outcome (H3)
remain genuinely underpowered for plausible effects, as the grid implied.

**Effect on interpretation:** This makes the primary null *stronger* — the
experiment could have detected an item-nonresponse effect several times smaller
than the plan claimed was detectable. It does not change any estimate, test,
outcome definition, multiplicity family, or verdict rule. The grid rows above
are left in place as written; this amendment is the correction of record.

**Timestamp note:** This amendment is appended to the source copy on
2026-09-03. The public repo copy
(`Brand_and_Portfolio/data-builds/DATA-03-hints-commitment-experiment/docs/pre-registration.md`)
must receive the identical amendment and a dated public commit at Phase 7
publication (or sooner, at Neyda's discretion), so the amendment carries a
public timestamp the way the original lock does. The Phase 5b agent does not
write outside the containment folder.

---
