# ============================================================================
# QUARANTINED — WITHDRAWN PHASE 5 ANALYSIS. DO NOT RUN. DO NOT IMPORT.
# ============================================================================
#
# This is the original `src/analysis.py` as it stood when Phase 5 hard-stopped
# on 2026-09-03. It is retained UNMODIFIED (below this header) as case-study
# evidence for the incident write-up. It is NOT part of the analysis pipeline.
#
# Why it was withdrawn: it computed correct per-respondent point estimates and
# then computed variance as though every survey ITEM were an independent
# observation. Confidence intervals came out ~21x too narrow; two null results
# were reported as large, highly significant effects (H1 z = -13.14; H3
# z = -3.53, itself reported with an internally inconsistent p = 0.0071). It
# also misread H1's predicted direction as a "reversal" and mis-filtered
# `CommitmentStmt` (numeric `== 1` against categorical text) producing n = 0 in
# the treatment arm.
#
# The authoritative analysis is `src/analysis.py` (rewritten in Phase 5b, runs
# the full pre-registered set with respondent-level variance through the
# Phase 4b-validated `src/weighting.py`). Results: `outputs/RESULTS.md`,
# `notebooks/03_analysis.ipynb`. Full incident record: `logs/project_log.md`
# (INCIDENT and Phase 5b entries), `docs/decisions.md`, `STAKEHOLDER_NARRATIVE.md`.
#
# Original file MD5: 8fff5ccbfeaee2006d2b10d851b61107
# Declared in SITEMAP.md under Phase 5b (Neyda's ruling, 2026-09-03).
# ============================================================================


"""
Phase 5: Pre-Registered Analysis
Did a commitment statement improve HINTS 7 data quality?

This module runs the complete pre-registered analysis plan:
1. Primary outcome: H1 Item nonresponse (Family A)
2. Secondary outcomes: H2 Break-off (Family B), H3 Response error (Family C)
3. Multiple comparison correction: Holm-Bonferroni
4. Per-protocol (non-randomized) comparison
5. Sensitivity analysis: Filter Missing rule (include vs. exclude)
6. Subgroup analysis: Mode (paper vs. web)

All analyses use the NCI-specified weighting harness from Phase 4.
All results reported with effect sizes, confidence intervals, and p-values.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, List
import sys
sys.path.insert(0, 'src')

from weighting import (
    estimate_rate, estimate_treatment_effect,
    percentage_format, POINT_ESTIMATE_WEIGHT, REPLICATE_WEIGHT_COLS,
    confidence_interval
)

# Lightweight normal CDF approximation (avoids scipy.stats DLL issues)
def norm_cdf(z):
    """Approximate normal CDF using error function."""
    return 0.5 * (1 + np.tanh(0.797885 * z))


class PreRegisteredAnalysis:
    """Run all pre-registered analyses in order."""

    def __init__(self, analysis_frame_path: str):
        """Load the arm-blind analysis frame from Phase 3."""
        self.data = pd.read_parquet(analysis_frame_path)
        self.results = {}

    def run_all(self) -> None:
        """Execute analyses in prescribed order: primary, secondary, corrections, per-protocol."""
        print("\n" + "="*80)
        print("PHASE 5: PRE-REGISTERED ANALYSIS")
        print("="*80)

        print("\n[STEP 1] Running primary outcome (H1): Item Nonresponse")
        self.h1_item_nonresponse()

        print("\n[STEP 2] Running secondary outcome (H3): Response Error")
        self.h3_response_error()

        print("\n[STEP 3] Running secondary outcome (H2): Break-off (web only)")
        self.h2_breakoff()

        print("\n[STEP 4] Applying Holm-Bonferroni multiplicity correction")
        self.apply_holm_correction()

        print("\n[STEP 5] Sensitivity analysis: Filter Missing (exclude from denominator)")
        self.sensitivity_filter_missing()

        print("\n[STEP 6] Per-protocol analysis (non-randomized)")
        self.per_protocol()

        print("\n[STEP 7] Subgroup analysis: Mode (paper vs. web)")
        self.subgroup_mode()

        print("\n[STEP 8] Peeking illustration (for case study)")
        self.peeking_illustration()

    def h1_item_nonresponse(self) -> None:
        """Primary outcome: Item nonresponse rate"""
        print("\n" + "-"*80)
        print("H1: ITEM NONRESPONSE (PRIMARY)")
        print("-"*80)

        # ITT effect: Need to map treatment_col appropriately for categorical values
        # Create numeric treatment indicator: 1 = treatment, 0 = control
        data_for_analysis = self.data.copy()
        data_for_analysis['treatment_numeric'] = (
            data_for_analysis['Treatment_H7_2'] == 'Included in Commitment Statement group'
        ).astype(int)

        # Use modified estimate_treatment_effect with numeric column
        treatment_arm = data_for_analysis[data_for_analysis['treatment_numeric'] == 1]
        control_arm = data_for_analysis[data_for_analysis['treatment_numeric'] == 0]

        tx_result = estimate_rate(treatment_arm, 'family_a_numerator', 'family_a_denominator', 'Treatment')
        ctrl_result = estimate_rate(control_arm, 'family_a_numerator', 'family_a_denominator', 'Control')

        # Build ITT result dict matching the expected structure
        itt_result = {
            'treatment': tx_result,
            'control': ctrl_result,
        }
        difference = tx_result['point_estimate'] - ctrl_result['point_estimate']
        se_diff = np.sqrt(tx_result['se']**2 + ctrl_result['se']**2)
        ci_diff_lower, ci_diff_upper = confidence_interval(difference, se_diff)
        z_stat = difference / se_diff if se_diff > 0 else np.nan
        # Simplified p-value using normal approximation (z-test)
        p_value = 2 * (1 - norm_cdf(abs(z_stat))) if not np.isnan(z_stat) else np.nan

        itt_result.update({
            'difference': difference,
            'se_difference': se_diff,
            'ci_diff_lower': ci_diff_lower,
            'ci_diff_upper': ci_diff_upper,
            'z_statistic': z_stat,
            'p_value_two_sided': p_value,
        })

        self.results['h1_itt'] = itt_result

        # Control-arm baseline for MDE grid
        ctrl_baseline = itt_result['control']['point_estimate']

        # Compute MDE at observed baseline (with observed design effect)
        deff = itt_result['control']['design_effect']
        if np.isnan(deff):
            deff = 1.28  # Pre-reg assumption if DEFF calculation failed

        mde = self._compute_mde(
            n_treatment=1513,
            n_control=5765,
            baseline_rate=ctrl_baseline,
            design_effect=deff
        )

        # Report
        print(f"\nControl arm (n={itt_result['control']['n_respondents']:,}):")
        print(f"  Point estimate: {percentage_format(itt_result['control']['point_estimate'], 2)}")
        print(f"  95% CI: [{percentage_format(itt_result['control']['ci_lower'], 2)}, {percentage_format(itt_result['control']['ci_upper'], 2)}]")

        print(f"\nTreatment arm (n={itt_result['treatment']['n_respondents']:,}):")
        print(f"  Point estimate: {percentage_format(itt_result['treatment']['point_estimate'], 2)}")
        print(f"  95% CI: [{percentage_format(itt_result['treatment']['ci_lower'], 2)}, {percentage_format(itt_result['treatment']['ci_upper'], 2)}]")

        print(f"\nTreatment effect (ITT):")
        print(f"  Difference: {percentage_format(itt_result['difference'], 2)} ({itt_result['difference']*100:.2f} pp)")
        print(f"  95% CI: [{percentage_format(itt_result['ci_diff_lower'], 2)}, {percentage_format(itt_result['ci_diff_upper'], 2)}]")
        print(f"  z-statistic: {itt_result['z_statistic']:.4f}")
        print(f"  p-value (two-tailed, UNCORRECTED): {itt_result['p_value_two_sided']:.4f}")

        rel_diff = (itt_result['treatment']['point_estimate'] - itt_result['control']['point_estimate']) / itt_result['control']['point_estimate']
        print(f"  Relative difference: {rel_diff:.2%}")

        print(f"\nMinimum Detectable Effect (MDE):")
        print(f"  Observed control baseline: {percentage_format(ctrl_baseline, 2)}")
        print(f"  Design effect: {deff:.2f}")
        print(f"  MDE (absolute): {percentage_format(mde, 2)} ({mde*100:.2f} pp)")
        print(f"  Observed effect: {percentage_format(abs(itt_result['difference']), 2)}")

        if abs(itt_result['difference']) < mde * 0.5:
            verdict = "UNINFORMATIVE NULL (effect < 0.5x MDE)"
        elif abs(itt_result['difference']) < mde:
            verdict = "UNINFORMATIVE NULL (effect < MDE; underpowered)"
        elif itt_result['p_value_two_sided'] < 0.05:
            verdict = "DETECTED EFFECT (p < 0.05, uncorrected)"
        else:
            verdict = "INFORMATIVE NULL (effect ≈ 0, well-powered)"

        print(f"  Verdict: {verdict}")
        self.results['h1_mde'] = mde
        self.results['h1_verdict'] = verdict

    def h3_response_error(self) -> None:
        """Secondary outcome (Family C): Response error rate"""
        print("\n" + "-"*80)
        print("H3: RESPONSE ERROR (SECONDARY)")
        print("-"*80)

        # Create numeric treatment indicator
        data_for_analysis = self.data.copy()
        data_for_analysis['treatment_numeric'] = (
            data_for_analysis['Treatment_H7_2'] == 'Included in Commitment Statement group'
        ).astype(int)

        # Split by arm
        treatment_arm = data_for_analysis[data_for_analysis['treatment_numeric'] == 1]
        control_arm = data_for_analysis[data_for_analysis['treatment_numeric'] == 0]

        tx_result = estimate_rate(treatment_arm, 'family_c_numerator', 'family_c_denominator', 'Treatment')
        ctrl_result = estimate_rate(control_arm, 'family_c_numerator', 'family_c_denominator', 'Control')

        # Build ITT result dict
        itt_result = {
            'treatment': tx_result,
            'control': ctrl_result,
        }
        difference = tx_result['point_estimate'] - ctrl_result['point_estimate']
        se_diff = np.sqrt(tx_result['se']**2 + ctrl_result['se']**2)
        ci_diff_lower, ci_diff_upper = confidence_interval(difference, se_diff)
        z_stat = difference / se_diff if se_diff > 0 else np.nan
        p_value = 2 * (1 - norm_cdf(abs(z_stat))) if not np.isnan(z_stat) else np.nan

        itt_result.update({
            'difference': difference,
            'se_difference': se_diff,
            'ci_diff_lower': ci_diff_lower,
            'ci_diff_upper': ci_diff_upper,
            'z_statistic': z_stat,
            'p_value_two_sided': p_value,
        })

        self.results['h3_itt'] = itt_result

        print(f"\nControl arm (n={itt_result['control']['n_respondents']:,}):")
        print(f"  Point estimate: {percentage_format(itt_result['control']['point_estimate'], 3)}")
        print(f"  95% CI: [{percentage_format(itt_result['control']['ci_lower'], 3)}, {percentage_format(itt_result['control']['ci_upper'], 3)}]")

        print(f"\nTreatment arm (n={itt_result['treatment']['n_respondents']:,}):")
        print(f"  Point estimate: {percentage_format(itt_result['treatment']['point_estimate'], 3)}")
        print(f"  95% CI: [{percentage_format(itt_result['treatment']['ci_lower'], 3)}, {percentage_format(itt_result['treatment']['ci_upper'], 3)}]")

        print(f"\nTreatment effect (ITT):")
        print(f"  Difference: {percentage_format(itt_result['difference'], 3)} ({itt_result['difference']*100:.3f} pp)")
        print(f"  95% CI: [{percentage_format(itt_result['ci_diff_lower'], 3)}, {percentage_format(itt_result['ci_diff_upper'], 3)}]")
        print(f"  z-statistic: {itt_result['z_statistic']:.4f}")
        print(f"  p-value (two-tailed, UNCORRECTED): {itt_result['p_value_two_sided']:.4f}")

    def h2_breakoff(self) -> None:
        """Secondary outcome (Family B): Break-off, web-mode only"""
        print("\n" + "-"*80)
        print("H2: BREAK-OFF (SECONDARY, WEB-MODE ONLY)")
        print("-"*80)

        print(f"\nSTATUS: Family B (break-off) was deferred to Phase 5.")
        print(f"Per data_dictionary.md: 'Requires mode-scoping, avoids arm-split'.")
        print(f"\nImplementation blockers:")
        print(f"  1. Mode variable not in analysis_frame.parquet")
        print(f"  2. Family B (break-off) outcomes not built in Phase 3")
        print(f"  3. Web-only filtering cannot be applied without Mode variable")
        print(f"\nAction: SKIP H2 analysis. Document as a pre-registration deviation.")
        print(f"This will be flagged in validation.md and decisions.md for Neyda review.")

        self.results['h2_itt'] = {
            'status': 'SKIPPED - Family B not available in Phase 3 analysis frame',
            'blocker': 'Mode variable and Family B outcomes not in analysis_frame.parquet'
        }

    def apply_holm_correction(self) -> None:
        """Apply Holm-Bonferroni correction to the analyses."""
        print("\n" + "-"*80)
        print("MULTIPLE COMPARISON CORRECTION: HOLM-BONFERRONI")
        print("-"*80)

        # Extract p-values (H2 is skipped)
        p_h1 = self.results['h1_itt']['p_value_two_sided']
        p_h3 = self.results['h3_itt']['p_value_two_sided']

        # Sort by p-value
        tests = [
            ('H1 (Item Nonresponse)', p_h1),
            ('H3 (Response Error)', p_h3),
        ]
        tests_sorted = sorted(tests, key=lambda x: x[1])

        print(f"\nTest family: 2 outcomes (H2 Break-off skipped - data not available)")
        print(f"Method: Holm-Bonferroni procedure")
        print(f"Significance level: alpha = 0.05")

        print(f"\nStep-down procedure (m=2 tests):")
        thresholds = [0.05/2, 0.05/1]

        for i, (test_name, p_val) in enumerate(tests_sorted):
            threshold = thresholds[i]
            rejected = p_val < threshold
            status = "REJECT" if rejected else "FAIL TO REJECT"
            print(f"\n  Step {i+1}: {test_name}")
            print(f"    Uncorrected p: {p_val:.4f}")
            print(f"    Holm threshold: {threshold:.4f}")
            print(f"    Decision: {status} (p {'' if rejected else '≥'} {threshold:.4f})")

        # Store corrected p-values
        holm_thresholds = {
            'H1 (Item Nonresponse)': 0.05/2,
            'H3 (Response Error)': 0.05/2,
        }

        print(f"\nResult: Both H1 and H3 rejected at family-wise level (after Holm correction)")
        self.results['holm_thresholds'] = holm_thresholds

    def sensitivity_filter_missing(self) -> None:
        """Sensitivity analysis: Exclude Filter Missing codes from denominator"""
        print("\n" + "-"*80)
        print("SENSITIVITY ANALYSIS: FILTER MISSING RULE")
        print("-"*80)

        print(f"\nPrimary rule: Include 'Filter Missing' in denominator")
        print(f"Sensitivity rule: Exclude 'Filter Missing' from denominator")
        print(f"\nNote: Both specifications are pre-registered. Results reported together.")

        # If Filter Missing variants are not already handled, note that
        print(f"\nCurrent status: Denominator built with 'Filter Missing' INCLUDED (primary rule).")
        print(f"Sensitivity specification not yet computed (requires separate denominator build).")
        print(f"\nFor Phase 5 full run: Build alternative denominator excluding Filter Missing")
        print(f"and compare results. If primary and sensitivity disagree significantly,")
        print(f"report it as a headline finding.")

        self.results['sensitivity_status'] = "Deferred - requires alternative denominator computation"

    def per_protocol(self) -> None:
        """Per-protocol analysis (non-randomized, for completeness)"""
        print("\n" + "-"*80)
        print("PER-PROTOCOL ANALYSIS (NON-RANDOMIZED, DESCRIPTIVE ONLY)")
        print("-"*80)

        treatment_arm = self.data[self.data['Treatment_H7_2'] == 1]

        agreed = treatment_arm[treatment_arm['CommitmentStmt'] == 'Yes']
        not_agreed = treatment_arm[treatment_arm['CommitmentStmt'].isin(['No', 'Missing data (Not Ascertained)'])]

        print(f"\nTreatment arm (n={len(treatment_arm):,}):")
        print(f"  Agreed to commitment: n={len(agreed):,}")
        print(f"  Did not agree or not ascertained: n={len(not_agreed):,}")

        if len(agreed) > 0:
            agreed_result = estimate_rate(agreed, 'family_a_numerator', 'family_a_denominator', 'Agreed')
            print(f"\n  Among those who agreed (n={len(agreed):,}):")
            print(f"    Item nonresponse: {percentage_format(agreed_result['point_estimate'], 2)}")
            print(f"    95% CI: [{percentage_format(agreed_result['ci_lower'], 2)}, {percentage_format(agreed_result['ci_upper'], 2)}]")

        if len(not_agreed) > 0:
            not_agreed_result = estimate_rate(not_agreed, 'family_a_numerator', 'family_a_denominator', 'Not Agreed')
            print(f"\n  Among those who did not agree (n={len(not_agreed):,}):")
            print(f"    Item nonresponse: {percentage_format(not_agreed_result['point_estimate'], 2)}")
            print(f"    95% CI: [{percentage_format(not_agreed_result['ci_lower'], 2)}, {percentage_format(not_agreed_result['ci_upper'], 2)}]")

        print(f"\nIMPORTANT: This comparison is NOT randomized and is NOT causal.")
        print(f"Agreement is correlated with engagement and motivation, both of which")
        print(f"predict data quality independently of the commitment statement itself.")
        print(f"No p-value or confidence interval interpretation without selection-bias adjustment.")

        self.results['per_protocol'] = {'agreed_n': len(agreed), 'not_agreed_n': len(not_agreed)}

    def subgroup_mode(self) -> None:
        """Subgroup analysis: Mode (paper vs. web)"""
        print("\n" + "-"*80)
        print("SUBGROUP ANALYSIS: MODE (PAPER VS. WEB)")
        print("-"*80)

        if 'Mode' not in self.data.columns:
            print("\nWARNING: Mode variable not found in analysis frame.")
            print("Subgroup analysis by mode cannot be performed.")
            print("This will be flagged as a data limitation.")
            self.results['mode_subgroup'] = "Mode variable not available"
            return

        paper = self.data[self.data['Mode'] == 'Paper']
        web = self.data[self.data['Mode'] == 'Web']

        print(f"\nSample composition:")
        print(f"  Paper respondents: n={len(paper):,} ({len(paper)/len(self.data)*100:.1f}%)")
        print(f"  Web respondents: n={len(web):,} ({len(web)/len(self.data)*100:.1f}%)")

        # Placeholder - full analysis would test mode × treatment interaction
        print(f"\nSubgroup analysis not yet run. When implemented, will test:")
        print(f"  - Treatment effect among paper respondents")
        print(f"  - Treatment effect among web respondents")
        print(f"  - Interaction term (mode × treatment)")

        self.results['mode_subgroup'] = "Placeholder - implementation pending"

    def peeking_illustration(self) -> None:
        """Peeking illustration for case study (not an inference)"""
        print("\n" + "-"*80)
        print("PEEKING ILLUSTRATION: Cumulative p-value trajectory")
        print("-"*80)

        print(f"\nThis is an ILLUSTRATION of why pre-registration matters.")
        print(f"It is NOT evidence about the hypothesis.")
        print(f"\nMethod: Sort respondents by plausible arrival order (random seed)")
        print(f"Compute p-value cumulatively as if we had peeked at each 10% of data")
        print(f"Plot trajectory against the alpha threshold to show multiple testing inflation")

        print(f"\nImplementation deferred - requires respondent ordering scheme")
        print(f"(survey mode + date fields, if available; random if not)")

        self.results['peeking'] = "Placeholder - requires date/order field"

    def _build_family_b(self, data: pd.DataFrame) -> None:
        """Build Family B (break-off) outcomes if not already present."""
        # Load original data to look for break-off codes
        # For now, placeholder
        pass

    def _compute_mde(self, n_treatment: int, n_control: int, baseline_rate: float, design_effect: float = 1.28) -> float:
        """
        Compute minimum detectable effect (MDE) at 80% power, two-sided α=0.05.

        Formula: MDE = z_α/2 + z_β × sqrt(p(1-p) * (1/n_tx + 1/n_ctl)) × sqrt(DEFF)

        For two-sided test with α=0.05, β=0.20 (80% power):
        z_α/2 = 1.96, z_β = 0.84, so multiplier ≈ 2.8
        """
        p = baseline_rate
        if p <= 0 or p >= 1:
            return np.nan

        var_pooled = p * (1 - p) * (1/n_treatment + 1/n_control)
        z_multiplier = 2.8  # 1.96 + 0.84 for α=0.05, power=0.80, two-sided

        mde = z_multiplier * np.sqrt(var_pooled * design_effect)
        return mde


if __name__ == "__main__":
    analysis = PreRegisteredAnalysis('data/processed/analysis_frame.parquet')
    analysis.run_all()

    # Save results
    print("\n" + "="*80)
    print("PHASE 5 ANALYSIS COMPLETE")
    print("="*80)
    print("\nResults saved to memory. Ready for notebook and reporting.")
