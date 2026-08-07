"""
DEPRECATED — this project no longer uses synthetic generated data.

As of 2026-07-07 the project was rebuilt on a real, public, de-identified
dataset (NY SPARCS hospital discharges) instead of a seeded synthetic
generator -- see docs/decisions.md ("Reversed the earlier 'synthetic data
over real data' decision") for the full reasoning.

Use src/fetch_data.py to (re)acquire the raw extract instead.
This file is kept as a placeholder documenting the earlier synthetic-data
approach rather than removed outright, for traceability with docs/decisions.md.
"""

if __name__ == "__main__":
    raise SystemExit(
        "generate_data.py is deprecated. Run src/fetch_data.py instead "
        "(or use the already-downloaded file in data/raw/)."
    )
