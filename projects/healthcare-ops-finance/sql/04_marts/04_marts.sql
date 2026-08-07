-- Marts: pre-aggregated, analysis-ready tables mapped directly onto the
-- five locked business questions in README.md / docs/project_context.md.
-- Deliberately uses CTEs, window functions (RANK, running-total SUM OVER,
-- PARTITION BY shares), and safe division (NULLIF) throughout.

-- Q1a: cost concentration by clinical severity tier (Pareto-style)
CREATE OR REPLACE TABLE mart_severity_cost_concentration AS
WITH by_severity AS (
    SELECT
        apr_severity_of_illness,
        COUNT(*)           AS discharge_count,
        SUM(total_charges) AS total_charges,
        SUM(total_costs)   AS total_costs
    FROM fact_discharges
    GROUP BY apr_severity_of_illness
),
ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY total_costs DESC) AS cost_rank,
        SUM(total_costs) OVER (ORDER BY total_costs DESC
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_cost,
        SUM(total_costs) OVER () AS grand_total_cost
    FROM by_severity
)
SELECT
    apr_severity_of_illness, discharge_count, total_charges, total_costs, cost_rank,
    ROUND(100.0 * total_costs   / NULLIF(grand_total_cost,0), 1) AS pct_of_total_cost,
    ROUND(100.0 * running_cost  / NULLIF(grand_total_cost,0), 1) AS cumulative_pct_of_total_cost
FROM ranked
ORDER BY cost_rank;

-- Q1b: cost concentration by DRG (which specific conditions drive spend)
-- 2026-07-15 fix: 6 DRGs (tracheostomy x2, ECMO, and the three "O.R. procedure
-- unrelated to principal diagnosis" DRGs) don't have one fixed mdc_key --
-- individual discharges for these DRGs carry different mdc_key values, since
-- an unrelated-to-principal-diagnosis procedure can occur under any MDC.
-- Grouping directly by fact_discharges.mdc_key (as this mart used to) split
-- those DRGs' costs across up to 15 rows each, fragmenting their true total
-- cost and silently dropping them out of rank-ordered views like the top-15-
-- DRGs table (confirmed live in the .pbix: Tracheostomy w/ Extensive
-- Procedure, true total $27.64M / rank 13, was showing as a single $8.57M
-- fragment). Fix: pick one representative ("primary") MDC per DRG -- the
-- MDC its discharges most often fall under -- for display only, and group
-- the actual cost/rank calculation by DRG alone so no DRG's cost is ever
-- split across rows.
CREATE OR REPLACE TABLE mart_drg_cost_concentration AS
WITH drg_mdc_counts AS (
    SELECT
        f.drg_key, f.mdc_key, COUNT(*) AS n,
        ROW_NUMBER() OVER (PARTITION BY f.drg_key ORDER BY COUNT(*) DESC) AS rn
    FROM fact_discharges f
    GROUP BY f.drg_key, f.mdc_key
),
primary_mdc AS (
    SELECT drg_key, mdc_key FROM drg_mdc_counts WHERE rn = 1
),
by_drg AS (
    SELECT
        d.apr_drg_description, m.apr_mdc_description,
        COUNT(*)              AS discharge_count,
        SUM(f.total_charges)  AS total_charges,
        SUM(f.total_costs)    AS total_costs,
        ROUND(AVG(f.total_costs), 2) AS avg_cost_per_discharge
    FROM fact_discharges f
    JOIN dim_drg d ON d.drg_key = f.drg_key
    JOIN primary_mdc pm ON pm.drg_key = f.drg_key
    JOIN dim_mdc m ON m.mdc_key = pm.mdc_key
    GROUP BY d.apr_drg_description, m.apr_mdc_description
),
ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY total_costs DESC) AS cost_rank,
        SUM(total_costs) OVER (ORDER BY total_costs DESC
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_cost,
        SUM(total_costs) OVER () AS grand_total_cost
    FROM by_drg
)
SELECT
    apr_drg_description, apr_mdc_description, discharge_count,
    total_charges, total_costs, avg_cost_per_discharge, cost_rank,
    ROUND(100.0 * total_costs  / NULLIF(grand_total_cost,0), 1) AS pct_of_total_cost,
    ROUND(100.0 * running_cost / NULLIF(grand_total_cost,0), 1) AS cumulative_pct_of_total_cost
FROM ranked
ORDER BY cost_rank;

-- Q2: charge-to-cost ratio (markup) by facility
CREATE OR REPLACE TABLE mart_facility_financials AS
WITH by_facility AS (
    SELECT
        fac.facility_name, fac.hospital_county, fac.sub_region,
        COUNT(*)              AS discharge_count,
        SUM(f.total_charges)  AS total_charges,
        SUM(f.total_costs)    AS total_costs
    FROM fact_discharges f
    JOIN dim_facility fac ON fac.facility_key = f.facility_key
    GROUP BY fac.facility_name, fac.hospital_county, fac.sub_region
)
SELECT
    facility_name, hospital_county, sub_region, discharge_count, total_charges, total_costs,
    ROUND(total_charges / NULLIF(total_costs,0), 2) AS charge_to_cost_ratio,
    RANK() OVER (ORDER BY total_charges / NULLIF(total_costs,0) DESC) AS markup_rank
FROM by_facility
ORDER BY markup_rank;

-- Q3: payer-mix exposure by facility (government/Medicaid concentration)
CREATE OR REPLACE TABLE mart_payer_mix_by_facility AS
WITH by_facility_payer AS (
    SELECT
        fac.facility_name, fac.sub_region, pay.payer_category,
        COUNT(*)           AS discharge_count,
        SUM(f.total_costs) AS total_costs
    FROM fact_discharges f
    JOIN dim_facility fac ON fac.facility_key = f.facility_key
    JOIN dim_payer    pay ON pay.payer_key    = f.payer_key
    GROUP BY fac.facility_name, fac.sub_region, pay.payer_category
)
SELECT
    facility_name, sub_region, payer_category, discharge_count, total_costs,
    ROUND(100.0 * discharge_count / SUM(discharge_count) OVER (PARTITION BY facility_name), 1)
        AS pct_of_facility_discharges
FROM by_facility_payer
ORDER BY facility_name, pct_of_facility_discharges DESC;

-- Q4: length of stay by facility and severity (rural post-acute access proxy)
CREATE OR REPLACE TABLE mart_los_by_facility_severity AS
SELECT
    fac.facility_name, fac.sub_region, f.apr_severity_of_illness,
    COUNT(*)                                   AS discharge_count,
    ROUND(AVG(f.length_of_stay_days), 2)       AS avg_length_of_stay_days,
    MEDIAN(f.length_of_stay_days)               AS median_length_of_stay_days,
    SUM(CASE WHEN f.is_los_censored THEN 1 ELSE 0 END) AS censored_stay_count
FROM fact_discharges f
JOIN dim_facility fac ON fac.facility_key = f.facility_key
GROUP BY fac.facility_name, fac.sub_region, f.apr_severity_of_illness
ORDER BY fac.sub_region, fac.facility_name, f.apr_severity_of_illness;

-- Q5: urban core vs. rural periphery utilization comparison
CREATE OR REPLACE TABLE mart_regional_utilization AS
WITH by_region AS (
    SELECT
        fac.sub_region,
        COUNT(*) AS discharge_count,
        SUM(CASE WHEN f.emergency_department_indicator = 'Y' THEN 1 ELSE 0 END) AS ed_discharge_count,
        SUM(CASE WHEN f.apr_severity_of_illness IN ('Major','Extreme') THEN 1 ELSE 0 END) AS high_severity_count,
        ROUND(AVG(f.length_of_stay_days), 2) AS avg_length_of_stay_days,
        SUM(f.total_costs)                   AS total_costs,
        ROUND(AVG(f.total_costs), 2)         AS avg_cost_per_discharge
    FROM fact_discharges f
    JOIN dim_facility fac ON fac.facility_key = f.facility_key
    GROUP BY fac.sub_region
)
SELECT
    sub_region, discharge_count,
    ROUND(100.0 * discharge_count / SUM(discharge_count) OVER (), 1) AS pct_of_total_volume,
    ROUND(100.0 * ed_discharge_count    / discharge_count, 1) AS ed_utilization_pct,
    ROUND(100.0 * high_severity_count   / discharge_count, 1) AS high_severity_pct,
    avg_length_of_stay_days, total_costs, avg_cost_per_discharge
FROM by_region
ORDER BY discharge_count DESC;
