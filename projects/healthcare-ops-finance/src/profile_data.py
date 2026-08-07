"""
Quick data-quality profile of the raw SPARCS extract.

Prints null rates, cardinality, duplicate-row counts, and the specific
known-issue checks that drove the cleaning decisions in docs/decisions.md
(length_of_stay censoring, payer-field ordering, facility ID split). This
script is what originally produced those findings; re-run it after any
raw-data refresh to re-verify nothing has changed upstream.
"""
import pandas as pd
from pathlib import Path

RAW_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "sparcs_inpatient_discharges_2024.csv"


def main():
    df = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False, na_values=[""])
    print(f"Rows: {len(df)}  Columns: {len(df.columns)}\n")

    print("--- Null counts (columns with > 0 nulls) ---")
    nulls = df.isna().sum().sort_values(ascending=False)
    print(nulls[nulls > 0])

    print("\n--- Exact duplicate rows ---")
    print(f"  involved in a duplicate group : {df.duplicated(keep=False).sum()}")
    print(f"  would be removed (keep first) : {df.duplicated(keep='first').sum()}")

    print("\n--- length_of_stay censoring ---")
    non_numeric = df["length_of_stay"][~df["length_of_stay"].str.match(r"^\d+$", na=False)]
    print(non_numeric.value_counts())

    print("\n--- payment_typology ordering check ---")
    p1_null = df["payment_typology_1"].isna()
    has_p2_or_p3 = df["payment_typology_2"].notna() | df["payment_typology_3"].notna()
    print(f"  payment_typology_1 null                : {p1_null.sum()}")
    print(f"  ...of which _2 or _3 populated instead : {(p1_null & has_p2_or_p3).sum()}")

    print("\n--- facility identity check (facility_name -> multiple permanent_facility_id) ---")
    mism = df.groupby("facility_name")["permanent_facility_id"].nunique()
    print(mism[mism > 1])


if __name__ == "__main__":
    main()
