# Build Spec: Did a Commitment Statement Improve Survey Data Quality?

*Created 2026-09-02. DATA-03. Public repo name: `DATA-03-hints-commitment-experiment`.*

---

## What this is

A re-analysis of a real randomized experiment that the US National Cancer
Institute ran inside the 2024 Health Information National Trends Survey, and
then only partially reported.

NCI randomized a subset of households to receive a statement at the start of
the survey asking them to commit to answering completely and accurately. The
published methodology report states the purpose plainly: the statement was
"intended to improve response data quality by, for example, reducing item
nonresponse overall and break offs on web."

What NCI published about it is one table pair showing **response rates** by
arm, with no significant difference (27.7 percent versus 27.2 percent).
Response rate was never the point. The data quality outcomes the experiment
was built to move do not appear in the report, and the randomization flags
and the outcome codes are both in the public use file.

That is the project. One randomized experiment, one unanswered primary
question, answered properly.

**The statistics are the point. The experiment is the vehicle.** If a tradeoff
has to be made under time pressure, cut breadth of outcomes before cutting
statistical rigor.

## Data

**Source:** HINTS 7 (2024), National Cancer Institute. Public domain federal
survey data, no license restriction, no registration required.

**File verified 2026-09-02:** `hints7_public.rda`, 7,278 rows, 515 columns.
Bundle also contains the public codebook, annotated instrument, methodology
report, and analysis recommendations.

### Confirmed variables

| Variable | Distribution as read from the file |
|---|---|
| `Treatment_H7_2` | 1,513 "Included in Commitment Statement group" / 5,765 "Not included" |
| `CommitmentStmt` | 1,389 Yes, 14 No, 110 Not Ascertained, 5,765 Inapplicable |
| `Treatment_H7_1` | 1,035 in extra incentive group / 6,243 not (second experiment, out of scope) |
| `STRATUM`, `VAR_STRATUM` | Design strata |
| `PERSON_FINWT0` through `PERSON_FINWT50` | Full sample weight plus 50 replicate weights |

`CommitmentStmt` counts sum exactly to the 1,513 flagged in
`Treatment_H7_2`, which indicates the flag marks the arm that actually
received the statement.

### Open reconciliation, Phase 1 Task 1, blocking

The methodology report states 7,200 households were in the experiment, split
2,400 treatment and 4,800 control. At the survey's 27.3 percent response rate,
2,400 treatment households should yield roughly 665 respondents. The file
shows 1,513. The report's arm sizes and the file's flag distribution do not
reconcile on any obvious reading.

**Do not begin analysis until this is settled.** Resolve against the public
codebook's own definition of `Treatment_H7_2` and the History Document. If it
cannot be settled from the documentation, email `NCIhints@mail.nih.gov` and
record the answer. Either the report, the flag semantics, or the current
reading is wrong, and the whole design rests on knowing which.

Whatever the resolution, record it in `docs/decisions.md` with a date. If NCI
confirms a documentation error, that is itself a reportable finding and
belongs in the case study.

### A note on the comparison group

Respondents not flagged into the statement arm include both true controls and
households never selected into the experiment. This does not invalidate the
comparison. Selection into the experiment was random and nobody outside the
statement arm saw the statement, so treatment versus everyone else remains an
unbiased contrast of statement against no statement. **State this explicitly
in the pre-registration rather than leaving a reviewer to notice it.**

---

## Outcomes

Three families, defined from distinct codes the codebook already separates.
Family membership is fixed at pre-registration and does not change afterward.

| Family | Constructed from | What it measures |
|---|---|---|
| A. Item nonresponse | `Missing data (Not Ascertained)` | Questions seen and skipped. The primary outcome NCI named. |
| B. Break-off | `Missing data (Web partial - Question Never Seen)` | Abandonment partway through, web mode only. The second outcome NCI named. |
| C. Response error | `Multiple responses selected in error`, `Question answered in error (Commission Error)` | Careless or inattentive answering. Not named by NCI, and the most interesting if it moves. |

**Primary outcome:** Family A, item nonresponse rate per respondent across a
fixed denominator of applicable items. One number, designated in advance.

Families B and C are secondary and carry the multiplicity correction.

**Denominator construction is the hardest task in this build.** "Inapplicable"
codes are legitimate skips driven by branching logic, not quality failures,
and the codebook contains at least 30 distinct inapplicable variants. Building
the applicable-item denominator per respondent is Phase 1 work, must be done
blind to arm, and must be documented item by item in `docs/data_dictionary.md`.

---

## Estimands

| Estimand | Definition |
|---|---|
| Intention to treat | Assigned to the statement arm versus not, regardless of whether they agreed. The headline. |
| Per protocol | Among the statement arm, agreed versus did not agree. Reported as descriptive and explicitly flagged as no longer randomized. |
| Non-compliance | The 14 who declined and the 110 not ascertained. Too small for inference. Describe, do not test. |

ITT is the estimate that carries the claim. Per protocol is reported because
omitting it looks like hiding it, and labelled honestly because presenting it
as causal would be wrong.

---

## Statistical plan

Fixed before any arm-split computation. Written into
`docs/pre-registration.md` and committed publicly before analysis code exists.

1. **Minimum detectable effect.** The sample is fixed, so this is not a sample
   size calculation. Compute MDE across a grid of plausible baseline rates at
   80 percent power, alpha 0.05, two-sided, at the realized arm sizes.
   Answers the prior question: was this experiment powered to find what it
   was looking for? A well-powered null and an underpowered null are different
   findings and most write-ups conflate them.
2. **Weighting.** `PERSON_FINWT0` for point estimates, the 50 replicate
   weights for variance, jackknife per the bundle's analysis recommendations.
   No unweighted headline numbers.
3. **Tests.** Weighted two-sample comparison per outcome family, with
   confidence intervals reported alongside every p-value.
4. **Multiple comparisons.** Correction method and family definitions fixed in
   the pre-registration, applied across the three families and any
   pre-registered subgroups. No post hoc family redefinition.
5. **Sequential testing.** Demonstrated, not committed. Show what the p-value
   trajectory would have looked like under repeated peeking, as a worked
   illustration of why the plan was locked first.
6. **Subgroups.** Pre-registered only. Mode (paper versus web) is the
   defensible one, since break-off is structurally web-only. Any subgroup not
   named in the pre-registration is exploratory and labelled as such.

### Standing discipline

**No statistic split by treatment arm may be computed before
`docs/pre-registration.md` is committed to the public repo.** This includes
exploratory missingness checks. Phase 1 validation runs pooled or blind to
arm. Violating this destroys the only claim the project makes that other
portfolios do not.

---

## Phases

| Phase | Work | Hours | Gate |
|---|---|---|---|
| 0 | Reconcile the arm-size discrepancy. Write and publicly commit the pre-registration: hypotheses, outcome definitions, MDE grid, correction method, subgroups. | 6-8 | Pre-registration committed and timestamped. Nothing arm-split computed. |
| 1 | Load, validate against codebook, build the applicable-item denominator, construct all three outcome families. Pooled validation only. | 10-12 | Row count matches 7,278. Denominator logic documented per item. Weights verified against the analysis recommendations. |
| 2 | Run the pre-registered analysis. ITT, per protocol, corrections, subgroups. | 8-10 | Every number reproducible from committed code. |
| 3 | Scorecard page, case study, decisions log, README. | 8-10 | A stranger can reproduce from the README. |

**Total: 32-40 hours, target ship 3 to 4 weeks from 2026-09-02.**

Phase gates are real. Do not start Phase 2 with Phase 1's denominator
undocumented.

---

## Deliverables

- `docs/pre-registration.md`, committed publicly before Phase 1
- `docs/decisions.md`, dated entries, append only
- `docs/data_dictionary.md`, every constructed variable and the denominator
  rules item by item
- `src/`, importable Python: load, construct outcomes, weighted estimation
- `notebooks/`, numbered, the analysis narrative
- `powerbi/`, one experiment scorecard page: effect sizes with confidence
  intervals by outcome family, MDE reference line, arm sizes
- `case-study.md`, 800 to 1,200 words per the case-studies playbook
- `logs/project_log.md`

### Repo handling

Build here in `data-builds-source/hints-commitment-experiment/` (private).
Publish the finished copy to `data-builds/DATA-03-hints-commitment-experiment/`.

`.gitignore` excludes `data/raw/` and the HINTS bundle PDFs. `src/fetch_data.py`
downloads the bundle from NCI so the build reproduces without a 20MB commit,
same pattern as DATA-01's SPARCS fetch.

**Move the existing download.** The bundle currently sits at
`data-builds/DATA-03/HINTS7_R_20250731/`, which is the public repo and against
convention. Move to `data-builds-source/hints-commitment-experiment/data/raw/`.

---

## Honesty requirements

Non-negotiable, and consistent with the honesty standard applied across this
portfolio's other builds.

- **A null is a result.** If the statement did nothing, report that as the
  finding. Pair it with the MDE so the reader knows whether the null is
  informative or just underpowered. Do not go hunting for a subgroup that
  moved.
- **Do not overclaim against NCI.** They ran a real randomized experiment and
  published their methodology in enough detail that this re-analysis is
  possible at all. The finding is "the primary outcome appears unreported and
  here it is," not "NCI got it wrong." If the reanalysis agrees with their
  null on response rate, say so.
- **Report the reconciliation.** Whatever Phase 1 Task 1 turns up goes in the
  case study, including if the answer is that the current reading was wrong.
- **Label per protocol as non-randomized** every place it appears.
- **Name the limitations:** single cycle, self-reported survey outcomes,
  comparison group includes non-experiment households, and item nonresponse is
  a proxy for data quality rather than data quality itself.

---

## Deliberately not in scope

- **The incentive experiment (`Treatment_H7_1`).** Its published outcome is
  response rate, which is not recomputable from a respondent-only file. Noted,
  set aside, available as a DATA-04 candidate.
- **The portal and scheduling engagement funnel.** `OfferedAccessHCP3`,
  `HCPEncourageOnlineRec2`, `AccessOnlineRecord3`, `Electronic2_MadeAppts` and
  the rest are all present and all interesting. They are a different project
  with a different claim. Keeping this one single-purpose is the decision.
- **Auditing the ONC data brief's encouragement contrast.** Strong project,
  fully verified as feasible, held as the fallback if Phase 1 Task 1 kills
  this one.
- **A synthetic validation arm.** Considered and cut for scope.

## Risks

| Risk | Mitigation |
|---|---|
| Arm-size discrepancy proves the flag means something else | Phase 0 gate. Fall back to the ONC encouragement audit, which reuses the same weighting machinery, so Phase 1 work is not wasted |
| Denominator construction sprawls past its budget | Fix the applicable-item list at the end of Phase 1 and freeze it. Document exclusions rather than resolving every edge case |
| Result is a null and reads as thin | The MDE grid is what makes a null publishable. This is why it is Phase 0 work, not an afterthought |
| Jackknife implementation is unfamiliar | The bundle ships analysis recommendations with worked code. Budget Phase 1 time to reproduce a published HINTS estimate first, as a harness check |

---

## Sources

- [HINTS 7 (2024) public use dataset](https://hints.cancer.gov/data/download-data.aspx), NCI, updated August 2025
- [HINTS 7 Methodology Report](https://hints.cancer.gov/docs/methodologyreports/HINTS_7_MethodologyReport.pdf), sections 2.5 and 6, embedded experiments and arm response rates
- [HINTS 7 Survey Materials](https://hints.cancer.gov/data/survey-instruments.aspx), annotated instrument including the commitment statement wording
- [ASTP/ONC Data Brief 77, July 2025](https://www.healthit.gov/wp-content/uploads/2025/07/2024-HINTS-Patient-Access-DB77_508.pdf), context for the fallback project
- Bundled with the dataset: HINTS 7 Public Codebook, History Document, Survey Overview and Data Analysis Recommendations

## Change log

- **2026-09-02:** Created. Scope, repo handling, pre-registration method, and
  timeline set by Neyda this session. Variable existence and distributions
  verified directly against `hints7_public.rda`, not inferred from published
  literature. No arm-split statistic computed.
