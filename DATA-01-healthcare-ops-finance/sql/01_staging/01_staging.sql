-- Staging: type-cast and clean the raw SPARCS extract.
-- raw_discharges is loaded as ALL_VARCHAR by src/run_pipeline.py; every cast
-- happens explicitly here. See docs/decisions.md and docs/data_dictionary.md
-- for the reasoning behind each rule below.

CREATE OR REPLACE VIEW stg_discharges AS
WITH base AS (
    SELECT
        ROW_NUMBER() OVER () AS staging_row_id,

        TRIM(facility_name)   AS facility_name,
        TRIM(hospital_county)  AS hospital_county,
        permanent_facility_id,
        operating_certificate_number,

        age_group,
        gender,
        race,
        ethnicity,
        NULLIF(zip_code, '') AS zip_code,

        type_of_admission,
        patient_disposition,
        emergency_department_indicator,
        apr_severity_of_illness,
        apr_risk_of_mortality,
        apr_medical_surgical,

        ccsr_diagnosis_code,
        ccsr_diagnosis_description,
        NULLIF(ccsr_procedure_code, '')        AS ccsr_procedure_code,
        NULLIF(ccsr_procedure_description, '') AS ccsr_procedure_description,
        apr_drg_code,
        apr_drg_description,
        apr_mdc_code,
        apr_mdc_description,

        -- length of stay: "120+" (57 rows) cast to a floor of 120, flagged
        CASE WHEN length_of_stay = '120+' THEN 120
             ELSE TRY_CAST(length_of_stay AS INTEGER)
        END AS length_of_stay_days,
        (length_of_stay = '120+') AS is_los_censored,

        TRY_CAST(NULLIF(birth_weight, '') AS INTEGER) AS birth_weight,

        -- payer: coalesce first non-null across the three slots (33 rows recovered)
        COALESCE(NULLIF(payment_typology_1, ''), NULLIF(payment_typology_2, ''), NULLIF(payment_typology_3, ''))
            AS primary_payer,
        NULLIF(payment_typology_2, '') AS payment_typology_2_raw,
        NULLIF(payment_typology_3, '') AS payment_typology_3_raw,

        TRY_CAST(total_charges AS DECIMAL(12,2)) AS total_charges,
        TRY_CAST(total_costs   AS DECIMAL(12,2)) AS total_costs
    FROM raw_discharges
)
SELECT
    staging_row_id,
    facility_name,
    hospital_county,
    permanent_facility_id,
    operating_certificate_number,
    age_group, gender, race, ethnicity, zip_code,
    type_of_admission, patient_disposition, emergency_department_indicator,
    apr_severity_of_illness, apr_risk_of_mortality, apr_medical_surgical,
    ccsr_diagnosis_code, ccsr_diagnosis_description,
    COALESCE(ccsr_procedure_code, 'NONE')                        AS ccsr_procedure_code,
    COALESCE(ccsr_procedure_description, 'No Procedure Performed') AS ccsr_procedure_description,
    apr_drg_code, apr_drg_description, apr_mdc_code, apr_mdc_description,
    length_of_stay_days, is_los_censored,
    birth_weight,
    COALESCE(primary_payer, 'Unknown') AS primary_payer,
    payment_typology_2_raw, payment_typology_3_raw,
    total_charges, total_costs
FROM base;
