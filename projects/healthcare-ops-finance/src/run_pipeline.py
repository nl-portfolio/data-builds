"""
Runs the full SQL layer against the raw SPARCS extract and exports
analysis-ready tables to data/processed/.

Order: raw CSV -> stg_discharges (view) -> dim_* -> fact_discharges -> mart_*
Engine: DuckDB (single-file, zero setup, PostgreSQL-style SQL).
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "sparcs_inpatient_discharges_2024.csv"
DB_PATH = ROOT / "data" / "interim" / "warehouse.duckdb"
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"

DIMS = ["dim_facility", "dim_drg", "dim_mdc", "dim_diagnosis", "dim_procedure", "dim_payer"]
MARTS = [
    "mart_severity_cost_concentration",
    "mart_drg_cost_concentration",
    "mart_facility_financials",
    "mart_payer_mix_by_facility",
    "mart_los_by_facility_severity",
    "mart_regional_utilization",
]


def run_sql_file(con, path: Path):
    con.execute(path.read_text())


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))

    print(f"Loading raw CSV from {RAW_CSV.name} ...")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw_discharges AS
        SELECT * FROM read_csv_auto('{RAW_CSV.as_posix()}', ALL_VARCHAR=TRUE)
    """)
    n_raw = con.execute("SELECT COUNT(*) FROM raw_discharges").fetchone()[0]
    print(f"  raw_discharges: {n_raw:,} rows")

    print("Running staging layer...")
    run_sql_file(con, SQL_DIR / "01_staging" / "01_staging.sql")

    print("Building dimensions...")
    run_sql_file(con, SQL_DIR / "02_dimensions" / "02_dimensions.sql")

    print("Building fact table...")
    run_sql_file(con, SQL_DIR / "03_facts" / "03_facts.sql")

    print("Building marts...")
    run_sql_file(con, SQL_DIR / "04_marts" / "04_marts.sql")

    print("\nValidation:")
    n_stg = con.execute("SELECT COUNT(*) FROM stg_discharges").fetchone()[0]
    n_fact = con.execute("SELECT COUNT(*) FROM fact_discharges").fetchone()[0]
    print(f"  stg_discharges : {n_stg:,} rows (raw: {n_raw:,})")
    print(f"  fact_discharges: {n_fact:,} rows (raw: {n_raw:,})")
    assert n_stg == n_raw, "staging row count does not match raw"
    assert n_fact == n_raw, "fact row count does not match raw -- a join dropped rows"

    for dim in DIMS:
        n = con.execute(f"SELECT COUNT(*) FROM {dim}").fetchone()[0]
        print(f"  {dim:16s}: {n:,} rows")

    orphans = con.execute("""
        SELECT COUNT(*) FROM fact_discharges f
        LEFT JOIN dim_facility  fac ON fac.facility_key  = f.facility_key
        LEFT JOIN dim_drg       d   ON d.drg_key         = f.drg_key
        LEFT JOIN dim_mdc       m   ON m.mdc_key         = f.mdc_key
        LEFT JOIN dim_diagnosis dx  ON dx.diagnosis_key  = f.diagnosis_key
        LEFT JOIN dim_procedure p   ON p.procedure_key   = f.procedure_key
        LEFT JOIN dim_payer     pay ON pay.payer_key     = f.payer_key
        WHERE fac.facility_key IS NULL OR d.drg_key IS NULL OR m.mdc_key IS NULL
           OR dx.diagnosis_key IS NULL OR p.procedure_key IS NULL OR pay.payer_key IS NULL
    """).fetchone()[0]
    print(f"  orphan fact rows (unresolved FK): {orphans}")
    assert orphans == 0, "found fact rows with an unresolved dimension key"

    print("\nExporting to data/processed/ ...")
    for t in DIMS + ["fact_discharges"] + MARTS:
        out = PROCESSED_DIR / f"{t}.csv"
        con.execute(f"COPY (SELECT * FROM {t}) TO '{out.as_posix()}' (HEADER, DELIMITER ',')")
        print(f"  wrote {out.name}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
