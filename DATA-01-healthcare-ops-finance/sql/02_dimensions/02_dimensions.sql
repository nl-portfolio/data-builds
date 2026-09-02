-- Dimensions built from the cleaned staging view.
-- Surrogate keys are generated here (ROW_NUMBER over a stable ORDER BY)
-- since none of these entities have a natural key in the source data.

-- dim_facility: Alice Hyde's two source facility IDs collapse onto one
-- facility_name automatically (confirmed identical in the source data);
-- both source IDs are retained as a traceability note.
CREATE OR REPLACE TABLE dim_facility AS
WITH facility_ids AS (
    SELECT DISTINCT facility_name, hospital_county, permanent_facility_id, operating_certificate_number
    FROM stg_discharges
)
SELECT
    ROW_NUMBER() OVER (ORDER BY facility_name) AS facility_key,
    facility_name,
    hospital_county,
    CASE hospital_county
        WHEN 'Albany'      THEN 'Capital District'
        WHEN 'Schenectady' THEN 'Capital District'
        WHEN 'Rensselaer'  THEN 'Capital District'
        WHEN 'Saratoga'    THEN 'Capital District'
        WHEN 'Warren'      THEN 'North Country / Adirondack'
        WHEN 'Clinton'     THEN 'North Country / Adirondack'
        WHEN 'Essex'       THEN 'North Country / Adirondack'
        WHEN 'Franklin'    THEN 'North Country / Adirondack'
        WHEN 'Otsego'      THEN 'Central NY / Catskill Foothills'
        WHEN 'Delaware'    THEN 'Central NY / Catskill Foothills'
        WHEN 'Schoharie'   THEN 'Central NY / Catskill Foothills'
        WHEN 'Columbia'    THEN 'Central NY / Catskill Foothills'
        WHEN 'Montgomery'  THEN 'Mohawk Valley'
        WHEN 'Fulton'      THEN 'Mohawk Valley'
        ELSE 'Unclassified'
    END AS sub_region,
    -- facility_role: added 2026-07-10 for the Facility Risk Score fix (see
    -- docs/review_findings_and_fixes.md Fix 3 and docs/decisions.md 2026-07-10).
    -- Separates non-general-acute units (rehab, addiction, standalone women's/OB,
    -- named satellite campuses) and the academic center from general acute
    -- hospitals, so the Page 1 risk ranking compares like with like instead of
    -- letting sub-300-discharge specialty campuses top it.
    --
    -- The general-acute facilities are labeled by their ACTUAL CMS designation
    -- (Critical Access Hospital vs. Sole Community Hospital vs. standard PPS),
    -- not by size, so "rural / sole-community" is a checkable federal status
    -- rather than a judgment call. Sources (both retrieved 2026-07-10, added to
    -- docs/sources.md): NY State DOH "Critical Access Hospital and Sole Community
    -- Hospital Outpatient Rate Add-ons, 4/1/2024-3/31/2025" (lists every NY CAH
    -- and SCH by name); cross-checked against the Flex Monitoring Team CAH
    -- Locations List. Note: the SCH list's "Samaritan Medical Center" is the
    -- Watertown (Jefferson County) hospital, NOT this dataset's Samaritan
    -- Hospital in Troy (Rensselaer) -- the Troy facility is standard PPS.
    -- Names matched exactly as stored (all-caps, single quotes doubled).
    CASE
        WHEN facility_name = 'ALBANY MEDICAL CENTER HOSPITAL'
            THEN 'Academic Medical Center'
        -- Not general acute: excluded from the Page 1 risk ranking, shown separately.
        WHEN facility_name IN (
            'ST. PETER''S ADDICTION RECOVERY CENTER',
            'ST. PETER''S HOSPITAL - SPARC',
            'SUNNYVIEW HOSPITAL AND REHABILITATION CENTER',
            'ELLIS HOSPITAL - BELLEVUE WOMAN''S CARE CENTER DIVISION',
            'ST. MARY''S HEALTHCARE - AMSTERDAM MEMORIAL CAMPUS'
        ) THEN 'Specialty / Satellite'
        -- CMS-designated Critical Access Hospitals (per NY DOH CAH list).
        WHEN facility_name IN (
            'COBLESKILL REGIONAL HOSPITAL',
            'DELAWARE VALLEY HOSPITAL INC',
            'MARGARETVILLE HOSPITAL',
            'O''CONNOR HOSPITAL',
            'THE UNIVERSITY OF VERMONT HEALTH NETWORK - ALICE HYDE MEDICAL CENTER',
            'THE UNIVERSITY OF VERMONT HEALTH NETWORK - ELIZABETHTOWN COMMUNITY HOSPITAL'
        ) THEN 'Critical Access Hospital'
        -- CMS-designated Sole Community Hospitals (per NY DOH SCH list). Bassett
        -- and Champlain Valley are large but federally SCH (distance-based).
        WHEN facility_name IN (
            'ADIRONDACK MEDICAL CENTER-SARANAC LAKE SITE',
            'A.O. FOX MEMORIAL HOSPITAL',
            'MARY IMOGENE BASSETT HOSPITAL',
            'THE UNIVERSITY OF VERMONT HEALTH NETWORK - CHAMPLAIN VALLEY PHYSICIANS HOSPITAL'
        ) THEN 'Sole Community Hospital'
        -- Everything else: general acute with no federal rural designation.
        -- Includes Nathan Littauer (small/independent but neither CAH nor SCH)
        -- and Samaritan Hospital, Troy (not the Watertown SCH of the same name).
        ELSE 'Community Acute (PPS)'
    END AS facility_role,
    STRING_AGG(permanent_facility_id, ', ')        AS source_facility_ids,
    STRING_AGG(operating_certificate_number, ', ') AS source_operating_certificates
FROM facility_ids
GROUP BY facility_name, hospital_county;

-- dim_drg: grain = one APR-DRG code. NOTE: does NOT carry MDC as an
-- attribute. Six DRG codes (004, 005, 009, 950, 951, 952 -- tracheostomy/
-- prolonged ventilation, ECMO, and "O.R. procedure unrelated to principal
-- diagnosis") are defined by the APR-DRG grouper methodology to span many
-- different MDCs depending on the patient's actual underlying diagnosis --
-- this is real grouper behavior, not a data error. Treating MDC as a
-- DRG-level attribute caused a join fan-out during development (324 DRGs
-- became 390 DRG/MDC combos). MDC is modeled as its own independent
-- dimension instead -- see docs/decisions.md.
CREATE OR REPLACE TABLE dim_drg AS
SELECT
    ROW_NUMBER() OVER (ORDER BY apr_drg_code) AS drg_key,
    apr_drg_code, apr_drg_description
FROM (SELECT DISTINCT apr_drg_code, apr_drg_description FROM stg_discharges);

-- dim_mdc: grain = one Major Diagnostic Category, independent of DRG (see note above)
CREATE OR REPLACE TABLE dim_mdc AS
SELECT
    ROW_NUMBER() OVER (ORDER BY apr_mdc_code) AS mdc_key,
    apr_mdc_code, apr_mdc_description
FROM (SELECT DISTINCT apr_mdc_code, apr_mdc_description FROM stg_discharges);

CREATE OR REPLACE TABLE dim_diagnosis AS
SELECT
    ROW_NUMBER() OVER (ORDER BY ccsr_diagnosis_code) AS diagnosis_key,
    ccsr_diagnosis_code, ccsr_diagnosis_description
FROM (SELECT DISTINCT ccsr_diagnosis_code, ccsr_diagnosis_description FROM stg_discharges);

-- includes the 'NONE' / 'No Procedure Performed' sentinel row so the fact
-- table's procedure_key is never null even for the 38.7% of stays with none
CREATE OR REPLACE TABLE dim_procedure AS
SELECT
    ROW_NUMBER() OVER (ORDER BY ccsr_procedure_code) AS procedure_key,
    ccsr_procedure_code, ccsr_procedure_description
FROM (SELECT DISTINCT ccsr_procedure_code, ccsr_procedure_description FROM stg_discharges);

-- payer_category rollup supports the Medicaid/government-exposure question;
-- 'Managed Care, Unspecified' -> Commercial by default, see docs/decisions.md caveat
CREATE OR REPLACE TABLE dim_payer AS
SELECT
    ROW_NUMBER() OVER (ORDER BY primary_payer) AS payer_key,
    primary_payer AS payer_name,
    CASE primary_payer
        WHEN 'Medicare'                      THEN 'Government'
        WHEN 'Medicaid'                       THEN 'Government'
        WHEN 'Federal/State/Local/VA'         THEN 'Government'
        WHEN 'Department of Corrections'      THEN 'Government'
        WHEN 'Blue Cross/Blue Shield'         THEN 'Commercial'
        WHEN 'Private Health Insurance'       THEN 'Commercial'
        WHEN 'Managed Care, Unspecified'      THEN 'Commercial'
        WHEN 'Self-Pay'                       THEN 'Self-Pay'
        WHEN 'Miscellaneous/Other'            THEN 'Other'
        WHEN 'Unknown'                        THEN 'Other'
        ELSE 'Other'
    END AS payer_category
FROM (SELECT DISTINCT primary_payer FROM stg_discharges);
