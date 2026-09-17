"""
Download the HINTS 7 R bundle from NCI and verify integrity.

Source: https://hints.cancer.gov/
License: US federal public domain, no restriction
"""

import os
import zipfile
from pathlib import Path
import pyreadr
import urllib.request


def fetch_hints_data(data_dir="data/raw", force_redownload=False):
    """
    Download HINTS 7 R bundle from NCI if not already present.

    Args:
        data_dir: Path to data directory (default: data/raw)
        force_redownload: If True, download even if folder exists

    Returns:
        Path to the extracted bundle folder
    """

    source_url = "https://hints.cancer.gov/dataset/HINTS7_R_20250731.zip"
    hints_folder = Path(data_dir) / "HINTS7_R_20250731"
    rda_file = hints_folder / "hints7_public.rda"

    # Check if data already exists
    if hints_folder.exists() and rda_file.exists() and not force_redownload:
        try:
            result = pyreadr.read_r(str(rda_file))
            if 'public' in result:
                df = result['public']
                if df.shape == (7278, 515):
                    print(f"✓ HINTS data already exists: {hints_folder}")
                    print(f"  Shape verified: {df.shape[0]} rows, {df.shape[1]} columns")
                    return hints_folder
        except Exception as e:
            print(f"  Existing data failed verification: {e}")
            print("  Re-downloading...")

    # Create data directory if it doesn't exist
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    # Download the bundle
    print(f"Downloading HINTS 7 bundle from NCI...")
    zip_path = data_path / "HINTS7_R_20250731.zip"

    try:
        urllib.request.urlretrieve(source_url, zip_path)
        print(f"✓ Downloaded: {zip_path}")
    except Exception as e:
        print(f"✗ Download failed: {e}")
        raise

    # Extract the bundle
    print(f"Extracting to {hints_folder}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(data_path)

    # Remove the zip file
    zip_path.unlink()
    print(f"✓ Extracted: {hints_folder}")

    # Verify the extraction
    if not rda_file.exists():
        raise FileNotFoundError(f"Expected {rda_file} not found after extraction")

    try:
        result = pyreadr.read_r(str(rda_file))
        if 'public' not in result:
            raise ValueError(f"Object 'public' not found in {rda_file}")

        df = result['public']
        if df.shape != (7278, 515):
            raise ValueError(
                f"Shape mismatch: expected (7278, 515), got {df.shape}"
            )

        print(f"✓ Data verified: {df.shape[0]} rows, {df.shape[1]} columns")
        print("✓ License: US federal public domain, no restriction")
        return hints_folder

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        raise


if __name__ == "__main__":
    fetch_hints_data()
