"""
Load and validate HINTS 7 public use file from .rda format.

Preserves categorical value labels (critical for outcome code identification).
Validates shape and records package versions used.
"""

import pyreadr
import pandas as pd
from pathlib import Path

# Package versions used
PACKAGE_VERSIONS = {
    'pyreadr': '0.5.6',
    'pandas': '3.0.5',
    'numpy': '2.5.2',
}

def load_hints_data(rda_path: str) -> pd.DataFrame:
    """
    Load HINTS 7 public use file from .rda format.

    Args:
        rda_path: Full path to hints7_public.rda

    Returns:
        DataFrame with categorical value labels preserved

    Raises:
        FileNotFoundError: If file does not exist
        AssertionError: If shape is not 7,278 x 515
    """
    rda_path = Path(rda_path)
    if not rda_path.exists():
        raise FileNotFoundError(f"HINTS data file not found: {rda_path}")

    # Read .rda file. pyreadr preserves categorical labels.
    result = pyreadr.read_r(str(rda_path))

    # The object inside is named 'public' per the bundle documentation
    if 'public' not in result:
        raise ValueError(
            f"Expected object named 'public' in .rda file. Found: {list(result.keys())}"
        )

    df = result['public']

    # Validate shape
    expected_shape = (7278, 515)
    actual_shape = df.shape

    assert actual_shape == expected_shape, (
        f"Shape mismatch. Expected {expected_shape}, got {actual_shape}. "
        f"DATA-01 validation: 143,613 = 143,613. "
        f"This validation: {actual_shape[0]:,} rows, {actual_shape[1]} columns. "
        f"Expected: 7,278 rows, 515 columns."
    )

    return df

if __name__ == '__main__':
    # Example usage
    hints_path = (
        Path(__file__).parent.parent / 'data' / 'raw' /
        'HINTS7_R_20250731' / 'hints7_public.rda'
    )

    df = load_hints_data(str(hints_path))
    print(f"Loaded HINTS data: {df.shape}")
    print(f"Package versions: {PACKAGE_VERSIONS}")
    print(f"Columns: {list(df.columns[:10])}...")
    print(f"Dtypes sample:\n{df.dtypes.head()}")
    print(f"\nCategorical columns (with value labels): {df.select_dtypes('category').shape[1]}")
