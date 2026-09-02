-- fact_discharges: grain = one row per hospital discharge (matches source grain).
-- No natural key in the source data, so discharge_key is a generated surrogate.
-- drg_key and mdc_key are resolved independently (NOT via a DRG->MDC chain --
-- see docs/decisions.md on why MDC isn't a stable DRG attribute for 6 codes).
-- All FKs resolve via inner join -- safe here because every dimension is
-- built from the distinct values actually present in stg_discharges, so no
-- orphans are possible (validated in run_pipeline.py).

CREATE OR REPLACE TABLE fact_discharges AS
SELECT
    ROW_NUMBER() OVER () AS discharge_key,
    fac.facility_key,
    d.drg_key,
    m.mdc_key,
    dx.diagnosis_key,
    p.procedure_key,
    pay.payer_key,

    s.age_group, s.gender, s.race, s.ethnicity, s.zip_code,
    s.type_of_admission, s.patient_disposition, s.emergency_department_indicator,
    s.apr_severity_of_illness, s.apr_risk_of_mortality, s.apr_medical_surgical,
    s.payment_typology_2_raw, s.payment_typology_3_raw,

    s.length_of_stay_days, s.is_los_censored,
    s.birth_weight,
    s.total_charges, s.total_costs
FROM stg_discharges s
JOIN dim_facility  fac ON fac.facility_name = s.facility_name AND fac.hospital_county = s.hospital_county
JOIN dim_drg       d   ON d.apr_drg_code = s.apr_drg_code
JOIN dim_mdc       m   ON m.apr_mdc_code = s.apr_mdc_code
JOIN dim_diagnosis dx  ON dx.ccsr_diagnosis_code = s.ccsr_diagnosis_code
JOIN dim_procedure p   ON p.ccsr_procedure_code = s.ccsr_procedure_code
JOIN dim_payer     pay ON pay.payer_name = s.primary_payer;
