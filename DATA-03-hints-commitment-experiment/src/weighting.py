"""
Survey-weighted estimation using HINTS 7 jackknife replicate weights.

Per NCI's "HINTS 7 Survey Overview Data Analysis Recommendations":
- Point estimates: Weighted proportions using PERSON_FINWT0
- Variance: Jackknife over PERSON_FINWT1 through PERSON_FINWT50 (50 replicates)
- Jackknife adjustment factor: 0.98, applied per replicate and summed
- Denominator degrees of freedom: 49

JK1/JKn variance estimator (derived from NCI's own R and SAS specifications;
see docs/validation.md, Phase 4b CORRECTION section):

    Var(theta_hat) = 0.98 * sum_{i=1}^{50} (theta_hat_i - theta_hat_0)^2
    SE(theta_hat)  = sqrt(Var)

There is NO division by the replicate count. The 0.98 (`scale` / `jkcoefs`)
multiplies each squared deviation; the products are summed.

References in NCI's document:
- "R Replicate Weights Variance Estimation Method" (R section):
      as_survey_rep(..., type = "JKn", scale = 0.98, rscales = rep(1, times = 50))
- "SAS Replicate Weights Variance Estimation Method":
      repweights person_FINWT1-person_FINWT50 / df = 49 jkcoefs = 0.98;
- Prose: "The jackknife adjustment factor for each replicate weight is 0.98."

History: an earlier version of jackknife_se() divided the summed squared
deviations by 50 (N_REPLICATES). That understated every variance 50-fold and
every standard error by sqrt(50) = 7.07x. Corrected in Phase 4b (2026-09-03);
see risk R15 and docs/decisions.md Failure 5.

This module provides functions to compute:
1. Point estimates (weighted proportions)
2. Jackknife standard errors
3. 95% confidence intervals
4. Design effect (ratio of complex-design variance to SRS variance)
5. A sanity guard: SE must not imply more observations than there are respondents
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict


# NCI-specified constants
JACKKNIFE_MULTIPLIER = 0.98  # Per NCI SAS code (jkcoefs) and R (scale); applied per replicate, summed
N_REPLICATES = 50
REPLICATE_WEIGHT_COLS = [f"PERSON_FINWT{i}" for i in range(1, N_REPLICATES + 1)]
POINT_ESTIMATE_WEIGHT = "PERSON_FINWT0"

# Sanity guard tolerance. The jackknife SE of a weighted mean should imply an
# effective n at or below the respondent count (design effect >= ~1). A small
# cushion absorbs jackknife noise when the design effect sits just under 1.
# Phase 5's failure had implied_n / n_respondents in the tens to hundreds, so
# this still catches it with wide margin.
SANITY_N_TOLERANCE = 1.10


def weighted_variance(values: np.ndarray, weights: np.ndarray) -> float:
    """Population (weighted) variance of `values`. NaNs excluded pairwise."""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    m = np.isfinite(values) & np.isfinite(weights)
    values, weights = values[m], weights[m]
    if weights.sum() == 0:
        return np.nan
    mu = np.sum(values * weights) / np.sum(weights)
    return np.sum(weights * (values - mu) ** 2) / np.sum(weights)


def assert_variance_plausible(
    point_estimate: float,
    se: float,
    n_respondents: int,
    dispersion: float = None,
    label: str = "estimate",
) -> None:
    """
    Fail loudly if the standard error implies more independent observations than
    there are respondents.

    A weighted mean estimated on n respondents cannot carry a standard error
    smaller than sqrt(dispersion / n) by more than the survey design allows
    (design effect >= ~1 for weighted survey estimates). implied_n =
    dispersion / se^2 must not exceed n_respondents.

    `dispersion` is the variance of the per-respondent quantity being averaged:
      - for a genuine 0/1 proportion it is p*(1-p) (the default when dispersion
        is None), which reproduces the assertion named in the Phase 4b prompt;
      - for a per-respondent RATE it is the weighted sample variance of that
        rate, which is far below p*(1-p) for a stable low rate. Using p*(1-p)
        for a rate produces false positives on correct estimates (real Family A:
        implied_n/n = 6.0 with the corrected harness), so estimate_rate() passes
        the actual weighted variance of the per-respondent rate instead.

    Either way the guard catches the Phase 5 failure mode: computing variance by
    pooling items across respondents drives implied_n to many times n (real
    Family A item-pooling: implied_n/n = 21.8; the synthetic negative control:
    5,000 against 50). See docs/decisions.md Failure 1, docs/validation.md
    (Phase 4b), and risk R12.

    Wired into estimate_rate() so it runs on every estimate the analysis makes.
    No-ops for degenerate inputs (se <= 0, p at a boundary, dispersion <= 0)
    rather than raising.
    """
    p = point_estimate
    if se is None or not np.isfinite(se) or se <= 0:
        return
    if not np.isfinite(p) or p <= 0 or p >= 1:
        return
    if dispersion is None:
        dispersion = p * (1.0 - p)
    if not np.isfinite(dispersion) or dispersion <= 0:
        return
    implied_n = dispersion / se ** 2
    assert implied_n <= n_respondents * SANITY_N_TOLERANCE, (
        f"{label}: variance implies {implied_n:,.0f} independent observations "
        f"against {n_respondents:,} respondents "
        f"(p={p:.6g}, se={se:.6g}, dispersion={dispersion:.6g}). "
        f"Standard error computed on the wrong unit of analysis?"
    )


def weighted_proportion(
    data: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    weight_col: str = POINT_ESTIMATE_WEIGHT
) -> float:
    """
    Compute a weighted proportion (mean of outcome rates).

    Args:
        data: DataFrame with outcome variables
        numerator_col: Column name (count of failures per respondent)
        denominator_col: Column name (applicable items per respondent)
        weight_col: Weight column name (default: PERSON_FINWT0)

    Returns:
        Weighted mean rate as a float in [0, 1]
    """
    # Compute rate for each respondent (avoid division by zero)
    rates = np.zeros(len(data))
    valid = data[denominator_col] > 0
    rates[valid] = data.loc[valid, numerator_col] / data.loc[valid, denominator_col]

    # Weighted mean
    weights = data[weight_col].values
    total_weight = weights.sum()
    if total_weight == 0:
        return 0.0

    weighted_sum = (rates * weights).sum()
    return weighted_sum / total_weight


def jackknife_se(
    data: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    point_estimate: float
) -> float:
    """
    Compute jackknife standard error using 50 replicate weights.

    Formula (per NCI jkcoefs / scale = 0.98, applied per replicate and summed):
        SE = sqrt(0.98 * sum((estimate_i - point_estimate)^2))

    There is no division by the replicate count. See module docstring and
    docs/validation.md (Phase 4b CORRECTION) for the derivation and the history
    of the earlier "/ 50" error (risk R15).

    Args:
        data: DataFrame with outcome and weight variables
        numerator_col: Column name (count of failures)
        denominator_col: Column name (applicable items)
        point_estimate: The point estimate (computed with PERSON_FINWT0)

    Returns:
        Standard error as a float
    """
    # Compute replicate estimates
    replicate_estimates = np.zeros(N_REPLICATES)
    for i, weight_col in enumerate(REPLICATE_WEIGHT_COLS):
        replicate_estimates[i] = weighted_proportion(
            data, numerator_col, denominator_col, weight_col
        )

    # Jackknife variance: 0.98 * sum of squared deviations. NOT divided by the
    # replicate count -- the 0.98 multiplies each squared deviation and the
    # products are summed (NCI SAS jkcoefs / R survey scale).
    squared_deviations = (replicate_estimates - point_estimate) ** 2
    variance = JACKKNIFE_MULTIPLIER * squared_deviations.sum()

    return np.sqrt(variance)


def confidence_interval(
    point_estimate: float,
    se: float,
    confidence_level: float = 0.95
) -> Tuple[float, float]:
    """
    Compute confidence interval using normal approximation.

    Args:
        point_estimate: The point estimate
        se: Standard error
        confidence_level: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_ci, upper_ci)
    """
    z_critical = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576
    }.get(confidence_level, 1.96)

    margin = z_critical * se
    return (point_estimate - margin, point_estimate + margin)


def design_effect(
    se_jackknife: float,
    point_estimate: float,
    n: int,
    dispersion: float = None,
) -> float:
    """
    Compute design effect (DEFF) as ratio of complex-design variance to SRS variance.

        DEFF = Var_complex / Var_SRS = se_jackknife^2 / (dispersion / n)

    `dispersion` is the variance of the per-respondent quantity being averaged:
      - None (default): p*(1-p), correct for a genuine 0/1 proportion.
      - For a per-respondent RATE: pass the weighted sample variance of that
        rate. p*(1-p) is the wrong SRS reference for a rate -- for the real
        Family A rate it gives DEFF = 0.17 (nonsense), because a stable ~1.4%
        rate has variance ~9x below p*(1-p). With the rate's own variance the
        DEFF is 1.56 (Family A) / 1.44 (Family C), matching survey::svymean's
        deff=TRUE. This is the design effect the Phase 4b prompt asks for --
        "the design effect for that estimator specifically, which is not the
        same as the design effect for a simple proportion".

    Args:
        se_jackknife: Standard error from jackknife (complex design)
        point_estimate: The estimate p (used only for the default dispersion)
        n: Respondent count
        dispersion: Variance of the per-respondent quantity; default p*(1-p)

    Returns:
        Design effect as a float, or NaN for degenerate inputs.
    """
    if dispersion is None:
        if point_estimate <= 0 or point_estimate >= 1:
            return np.nan
        dispersion = point_estimate * (1 - point_estimate)

    if not np.isfinite(dispersion) or dispersion <= 0 or n <= 0:
        return np.nan

    var_srs = dispersion / n
    if var_srs == 0:
        return np.nan

    return se_jackknife ** 2 / var_srs


def estimate_rate(
    data: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    outcome_name: str = "Outcome"
) -> Dict[str, float]:
    """
    Complete estimation pipeline for a single rate.

    Args:
        data: DataFrame with outcomes and weights
        numerator_col: Column name (count of failures)
        denominator_col: Column name (applicable items)
        outcome_name: Human-readable name for the outcome

    Returns:
        Dictionary with point estimate, SE, CI, DEFF, and weighted n
    """
    # Point estimate
    point_est = weighted_proportion(data, numerator_col, denominator_col)

    # Standard error
    se = jackknife_se(data, numerator_col, denominator_col, point_est)

    # Weighted variance of the per-respondent rate -- the correct SRS reference
    # for both the design effect and the sanity guard of a rate estimator.
    n_respondents = len(data)
    valid = (data[denominator_col].values > 0)
    rates = np.zeros(len(data))
    rates[valid] = (
        data.loc[valid, numerator_col].values
        / data.loc[valid, denominator_col].values
    )
    rate_dispersion = weighted_variance(rates, data[POINT_ESTIMATE_WEIGHT].values)

    # Sanity guard: SE must not imply more observations than respondents exist.
    # Fires automatically on every estimate the analysis makes. Had this been in
    # place, the Phase 5 item-level variance error could not have shipped.
    assert_variance_plausible(
        point_est, se, n_respondents,
        dispersion=rate_dispersion, label=outcome_name,
    )

    # Confidence interval
    ci_lower, ci_upper = confidence_interval(point_est, se)

    # Design effect for THIS estimator (rate), not for a simple proportion
    deff = design_effect(se, point_est, n_respondents, dispersion=rate_dispersion)

    # Weighted sample size (sum of weights)
    weighted_n = data[POINT_ESTIMATE_WEIGHT].sum()

    # Effective sample size and the proportion-style DEFF (what the
    # pre-registration's MDE grid implicitly assumed). Kept for Phase 5b.
    deff_proportion = design_effect(se, point_est, n_respondents)
    n_effective = n_respondents / deff if (deff and np.isfinite(deff) and deff > 0) else np.nan
    implied_n = (rate_dispersion / se ** 2) if (se and se > 0 and np.isfinite(rate_dispersion)) else np.nan

    return {
        "outcome": outcome_name,
        "point_estimate": point_est,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "design_effect": deff,                 # rate estimator, vs var(rate)/n
        "design_effect_proportion": deff_proportion,  # vs p(1-p)/n; MDE-grid basis
        "rate_dispersion": rate_dispersion,    # weighted var of per-respondent rate
        "n_respondents": n_respondents,
        "n_effective": n_effective,
        "implied_n": implied_n,
        "weighted_n": weighted_n,
    }


def estimate_treatment_effect(
    data: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    treatment_col: str = "Treatment_H7_2",
    treatment_value: int = 1
) -> Dict[str, any]:
    """
    Compute intention-to-treat effect (treatment vs. control arm comparison).

    Args:
        data: Full analysis frame
        numerator_col: Outcome numerator column
        denominator_col: Outcome denominator column
        treatment_col: Treatment assignment column (default: Treatment_H7_2)
        treatment_value: Value in treatment_col that marks treatment arm (default: 1)

    Returns:
        Dictionary with treatment and control estimates, difference, and test results
    """
    # Split by arm
    treatment_data = data[data[treatment_col] == treatment_value]
    control_data = data[data[treatment_col] != treatment_value]

    # Estimates for each arm
    tx_result = estimate_rate(treatment_data, numerator_col, denominator_col, "Treatment")
    ctrl_result = estimate_rate(control_data, numerator_col, denominator_col, "Control")

    # Difference
    difference = tx_result["point_estimate"] - ctrl_result["point_estimate"]

    # SE of difference
    se_diff = np.sqrt(tx_result["se"] ** 2 + ctrl_result["se"] ** 2)

    # Confidence interval on difference
    ci_diff_lower, ci_diff_upper = confidence_interval(difference, se_diff)

    # Test statistic (z-score)
    z_stat = difference / se_diff if se_diff > 0 else np.nan

    # Two-tailed p-value (using normal approximation)
    from scipy.stats import norm
    p_value = 2 * (1 - norm.cdf(abs(z_stat))) if not np.isnan(z_stat) else np.nan

    return {
        "treatment": tx_result,
        "control": ctrl_result,
        "difference": difference,
        "se_difference": se_diff,
        "ci_diff_lower": ci_diff_lower,
        "ci_diff_upper": ci_diff_upper,
        "z_statistic": z_stat,
        "p_value_two_sided": p_value,
    }


def percentage_format(value: float, decimals: int = 1) -> str:
    """Format a proportion as percentage with specified decimal places."""
    if np.isnan(value) or value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


if __name__ == "__main__":
    # Example usage
    print("Module loaded. See estimate_rate() and estimate_treatment_effect() functions.")
