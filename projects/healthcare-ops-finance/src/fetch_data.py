"""
Reproducible fetch of the raw SPARCS extract used by this project.

Source: NY State SPARCS, Hospital Inpatient Discharges (De-Identified), 2024.
https://health.data.ny.gov/Health/Hospital-Inpatient-Discharges-SPARCS-De-Identified/sf4k-39ay/about_data

Pulls the same region/year slice documented in docs/project_context.md,
directly from the state's public Socrata API (no auth required, public data).

Note: the raw file in data/raw/ was originally downloaded by visiting this
exact URL in a browser rather than by running this script. Included here so
anyone with a normal internet connection can reproduce the pull directly.
"""
from pathlib import Path
import urllib.request
import urllib.parse

RESOURCE_ID = "sf4k-39ay"
WHERE_CLAUSE = "health_service_area='Capital/Adirondacks'"
LIMIT = 200_000  # comfortably above the ~143,613 rows actually returned

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "sparcs_inpatient_discharges_2024.csv"


def main():
    base = f"https://health.data.ny.gov/resource/{RESOURCE_ID}.csv"
    params = {"$where": WHERE_CLAUSE, "$limit": str(LIMIT)}
    url = base + "?" + urllib.parse.urlencode(params)
    print(f"Fetching: {url}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, OUT_PATH)
    size_mb = OUT_PATH.stat().st_size / 1e6
    print(f"Saved {OUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
