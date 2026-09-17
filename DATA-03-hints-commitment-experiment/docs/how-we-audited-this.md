# How We Audited This

Once the pre-registered analysis was complete, it went through an independent audit pass before publication. The goal was to try to break it, not to confirm it.

## What "independent" means here

Every headline result (H1, H2, H3) was recomputed from a jackknife variance estimator built directly from NCI's own published specification for HINTS 7 — not by reusing this project's `weighting.py` code. If a bug in the original implementation had produced the headline numbers, a second, differently-written implementation would not have reproduced them. It did, to four decimal places on every metric.

| | Difference (pp) | 95% CI (pp) | SE (pp) | z | p |
|---|---|---|---|---|---|
| H1 (primary) | -0.2129 | [-0.4375, +0.0117] | 0.1146 | -1.858 | 0.0632 |
| H2 | +1.8150 | [-1.1724, +4.8023] | 1.5241 | 1.191 | 0.2337 |
| H3 | -0.0211 | [-0.1040, +0.0617] | 0.0423 | -0.500 | 0.6172 |

## What the audit specifically checked for

This project had two earlier statistical bugs, caught and fixed during the build itself (see the decisions log). The audit re-checked for both, from scratch, rather than trusting that the fixes held:

1. **Item-cell variance inflation** — an earlier draft treated each survey item as its own independent observation instead of averaging per respondent, which artificially shrank the confidence intervals. Absent from the final analysis; design effects (1.44–2.93) are consistent with real survey-weighted variance, nowhere near the ~20x inflation the original bug produced.
2. **A misapplied jackknife scale factor** — an earlier draft's variance formula would have understated every standard error by a fixed proportional amount. Absent; the corrected formula is confirmed in sum form, not the erroneous mean form.

Beyond re-deriving the numbers, the audit also swept the entire project for **stale figures** — any result from an earlier, superseded pass of the analysis that might still be sitting unlabeled in a doc or notebook. Every superseded number found (including in the notebooks) carries an explicit "superseded" or "withdrawn" label at the point where it appears; none masquerade as current.

Finally, the audit confirmed the pre-registration was honored in full: every analysis specified in advance has a corresponding output, and the one amendment made after pre-registration was a disclosure of a conservative assumption, not a change to any decision rule.

## Verdict

**Green, with fixes.** No blockers. No number, table, or dashboard value changed as a result of the audit. What the audit did surface were six documentation inconsistencies — things like a stale status line, a formula that wasn't spelled out clearly enough in the data dictionary, and a couple of cross-references that had drifted out of sync as the project moved through revisions. All cosmetic, and all corrected before this build was published.

## What the audit didn't cover

Two things were out of scope for this pass and are noted rather than glossed over:
- The rendered dashboard exports (the build file existed; static exports were finalized afterward).
- A full re-run of the raw-to-processed data pipeline from the original source file, as a completely independent build-from-scratch check.

Full audit trail — including line-level findings, every fix applied, and the reasoning behind each — lives in the project's internal decision log, available on request.
