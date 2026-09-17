"""
Build the applicable-item denominator and three outcome families.

CRITICAL: This script runs BLIND to treatment arm. No grouping, sorting, or
summary by Treatment_H7_2. Every validation is pooled across all 7,278 respondents.

Outcome families:
  A (Primary): Item nonresponse (Missing data - Not Ascertained)
  B (Secondary): Break-off (Missing data - Web partial - Question Never Seen), web-only
  C (Secondary): Response error (Multiple selections in error, Commission Error)

The denominator construction is the core of this phase. See pre-registration.md
for the rules.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Set
import json

# ============================================================================
# PART 1: Load data and categorize the 515 columns
# ============================================================================

class ItemUniverse:
    """
    Categorize all 515 columns into: items, design variables, derived variables, etc.
    Applies the pre-registration rule:
      "An item is part of the analyzable outcome universe if and only if:
       1. It is coded in the HINTS 7 public use file as a numbered survey response variable
       2. It has one of these code patterns in its value labels:
          - Missing data (Not Ascertained)
          - Missing data (Web partial - Question Never Seen)
          - Missing data (Filter Missing)
          - Multiple responses selected in error
          - Question answered in error (Commission Error)
          - Inapplicable, coded N in [VAR]
          - A substantive response (not entirely empty or metadata)"
    """

    # Columns known to be design/admin variables (from pre-registration)
    DESIGN_VARIABLES = {
        'HHID',
        'PERSON_FINWT0', 'PERSON_FINWT1', 'PERSON_FINWT2', 'PERSON_FINWT3',
        'PERSON_FINWT4', 'PERSON_FINWT5', 'PERSON_FINWT6', 'PERSON_FINWT7',
        'PERSON_FINWT8', 'PERSON_FINWT9', 'PERSON_FINWT10',
        'PERSON_FINWT11', 'PERSON_FINWT12', 'PERSON_FINWT13', 'PERSON_FINWT14',
        'PERSON_FINWT15', 'PERSON_FINWT16', 'PERSON_FINWT17', 'PERSON_FINWT18',
        'PERSON_FINWT19', 'PERSON_FINWT20',
        'PERSON_FINWT21', 'PERSON_FINWT22', 'PERSON_FINWT23', 'PERSON_FINWT24',
        'PERSON_FINWT25', 'PERSON_FINWT26', 'PERSON_FINWT27', 'PERSON_FINWT28',
        'PERSON_FINWT29', 'PERSON_FINWT30',
        'PERSON_FINWT31', 'PERSON_FINWT32', 'PERSON_FINWT33', 'PERSON_FINWT34',
        'PERSON_FINWT35', 'PERSON_FINWT36', 'PERSON_FINWT37', 'PERSON_FINWT38',
        'PERSON_FINWT39', 'PERSON_FINWT40',
        'PERSON_FINWT41', 'PERSON_FINWT42', 'PERSON_FINWT43', 'PERSON_FINWT44',
        'PERSON_FINWT45', 'PERSON_FINWT46', 'PERSON_FINWT47', 'PERSON_FINWT48',
        'PERSON_FINWT49', 'PERSON_FINWT50',
        'STRATUM', 'VAR_STRATUM',
        'Weight',  # Any other weight variable
    }

    # Experiment flags (excluded)
    EXPERIMENT_FLAGS = {
        'Treatment_H7_1', 'Treatment_H7_2', 'CommitmentStmt'
    }

    # Outcome codes that mark an item as belonging to the outcome universe
    OUTCOME_CODE_PATTERNS = {
        'Missing data (Not Ascertained)',
        'Missing data (Web partial - Question Never Seen)',
        'Missing data (Filter Missing)',
        'Multiple responses selected in error',
        'Question answered in error (Commission Error)',
        'Inapplicable, coded N in',  # Prefix pattern
    }

    def __init__(self, df: pd.DataFrame):
        """Initialize with the loaded DataFrame."""
        self.df = df
        self.classifications = {}
        self.outcomes = {}

    def extract_value_labels(self, col_name: str) -> Dict[str, str]:
        """
        Extract value labels from a categorical column.
        Returns a dict mapping code (as string) to label.
        """
        labels = {}
        if pd.api.types.is_categorical_dtype(self.df[col_name]):
            cat = self.df[col_name].cat
            if hasattr(cat, 'categories') and hasattr(cat, 'codes'):
                # Map code integers to category names
                categories = cat.categories
                for i, cat_name in enumerate(categories):
                    labels[str(i)] = str(cat_name)
        return labels

    def has_outcome_codes(self, col_name: str) -> Tuple[bool, str]:
        """
        Check if a column has any outcome codes in its value labels.
        Returns (has_outcome_codes: bool, first_matching_label: str)
        """
        labels = self.extract_value_labels(col_name)

        # Collect all label strings
        all_labels = set(labels.values())

        # Check for exact matches and prefix matches
        for label in all_labels:
            # Exact matches
            if label in self.OUTCOME_CODE_PATTERNS:
                return True, label

            # Prefix matches (e.g., "Inapplicable, coded N in ...")
            if label.startswith('Inapplicable, coded N in'):
                return True, label

            # Case-insensitive substring check for common variants
            label_lower = label.lower()
            if 'missing data' in label_lower and 'not ascertained' in label_lower:
                return True, label
            if 'web partial' in label_lower and 'never seen' in label_lower:
                return True, label

        return False, ""

    def classify_all_items(self) -> Dict:
        """
        Classify all 515 columns. Returns a dict mapping variable name to
        classification info.
        """
        results = {}

        for col_name in self.df.columns:
            if col_name in self.DESIGN_VARIABLES:
                results[col_name] = {
                    'in_item_universe': False,
                    'exclusion_reason': 'design_variable',
                    'applicable_rule': '',
                    'notes': ''
                }
            elif col_name in self.EXPERIMENT_FLAGS:
                results[col_name] = {
                    'in_item_universe': False,
                    'exclusion_reason': 'experiment_flag',
                    'applicable_rule': '',
                    'notes': ''
                }
            elif col_name.endswith('_Cat'):
                # Derived/recoded categorical (e.g., TelehealthReasons_Cat)
                results[col_name] = {
                    'in_item_universe': False,
                    'exclusion_reason': 'derived_variable',
                    'applicable_rule': '',
                    'notes': 'collapsed or recoded from source items'
                }
            elif col_name.endswith('_OS'):
                # Open-text fields
                results[col_name] = {
                    'in_item_universe': False,
                    'exclusion_reason': 'open_text_field',
                    'applicable_rule': '',
                    'notes': ''
                }
            else:
                # Check if it has outcome codes
                has_codes, first_code = self.has_outcome_codes(col_name)

                if has_codes:
                    # Determine applicability rule
                    if 'Web partial' in first_code or 'Never Seen' in first_code:
                        applicable_rule = 'conditional_on:mode_web'
                    elif 'Inapplicable' in first_code:
                        applicable_rule = 'universal_with_skip'
                    else:
                        applicable_rule = 'universal'

                    results[col_name] = {
                        'in_item_universe': True,
                        'exclusion_reason': '',
                        'applicable_rule': applicable_rule,
                        'notes': f'Outcome code found: {first_code[:60]}...'
                    }
                else:
                    # No outcome codes found—likely metadata or administrative
                    results[col_name] = {
                        'in_item_universe': False,
                        'exclusion_reason': 'no_outcome_codes',
                        'applicable_rule': '',
                        'notes': ''
                    }

        self.classifications = results
        return results

    def to_csv(self, output_path: str):
        """Write the item_denominator_map.csv."""
        rows = []
        for var_name, info in sorted(self.classifications.items()):
            rows.append({
                'variable': var_name,
                'in_item_universe': info['in_item_universe'],
                'exclusion_reason': info['exclusion_reason'],
                'applicable_rule': info['applicable_rule'],
                'notes': info['notes']
            })

        df_map = pd.DataFrame(rows)
        df_map.to_csv(output_path, index=False)
        return df_map

    def get_items(self) -> List[str]:
        """Return list of variables in the item universe."""
        return [
            var for var, info in self.classifications.items()
            if info['in_item_universe']
        ]


# ============================================================================
# PART 2: Build the applicable-item denominator per respondent
# ============================================================================

class DenominatorBuilder:
    """
    For each respondent and each item, decide: was this item applicable?
    Applicable items go in the denominator.

    The rule: An item is applicable if it was not marked as Inapplicable
    (due to branching logic skip) and it was presented to the respondent.

    This is the R2 risk: denominator construction determines the result.
    """

    def __init__(self, df: pd.DataFrame, items: List[str]):
        """Initialize with full DataFrame and list of items."""
        self.df = df
        self.items = items
        self.inapplicable_masks = {}  # Cache for inapplicable masks

    def _build_inapplicable_mask(self, col_name: str) -> np.ndarray:
        """
        Build a boolean mask for inapplicable values (True = inapplicable).
        Returns array of shape (n_respondents,).
        """
        if col_name in self.inapplicable_masks:
            return self.inapplicable_masks[col_name]

        mask = np.zeros(len(self.df), dtype=bool)

        if pd.api.types.is_categorical_dtype(self.df[col_name]):
            cat = self.df[col_name].cat
            categories = cat.categories
            codes = cat.codes.values

            # Find which code indices represent Inapplicable
            inapp_code_indices = []
            for i, cat_name in enumerate(categories):
                if isinstance(cat_name, str) and cat_name.startswith('Inapplicable'):
                    inapp_code_indices.append(i)

            # Mark all respondents with those codes as inapplicable
            for code_idx in inapp_code_indices:
                mask[codes == code_idx] = True

        self.inapplicable_masks[col_name] = mask
        return mask

    def build_applicable_counts(self) -> np.ndarray:
        """
        For each respondent, count how many items are applicable.
        Returns array of shape (n_respondents,).

        Vectorized version: build inapplicable masks for each item,
        then sum across items.
        """
        applicable_count = np.zeros(len(self.df), dtype=int)

        for item in self.items:
            inapp_mask = self._build_inapplicable_mask(item)
            # Count item as applicable if NOT inapplicable
            applicable_count += (~inapp_mask).astype(int)

        return applicable_count


# ============================================================================
# PART 3: Build the three outcome families
# ============================================================================

class OutcomesBuilder:
    """
    Build the three outcome families per respondent:
      Family A: Item nonresponse (Missing data - Not Ascertained)
      Family B: Break-off (Web partial - Never Seen), web-only
      Family C: Response error (Multiple selections in error, Commission Error)

    Each respondent gets rates for each family (count / denominator).

    Uses vectorized operations for speed (7,278 respondents × ~400 items).
    """

    # Code patterns for each family (case-insensitive substring match)
    FAMILY_A_PATTERNS = ['missing data', 'not ascertained']
    FAMILY_B_PATTERNS = ['web partial', 'never seen']
    FAMILY_C_PATTERNS = [
        'multiple responses', 'selected in error',
        'commission error'
    ]

    def __init__(self, df: pd.DataFrame, items: List[str]):
        """Initialize with full DataFrame and list of items."""
        self.df = df
        self.items = items
        self.code_masks = {}  # Cache for matching masks by family

    def _build_outcome_masks(self, patterns: List[str]) -> Dict[str, np.ndarray]:
        """
        Build boolean masks for items where the value label matches any pattern.
        Returns dict mapping item name to boolean mask (shape n_respondents).
        """
        masks = {}

        for item in self.items:
            mask = np.zeros(len(self.df), dtype=bool)

            if pd.api.types.is_categorical_dtype(self.df[item]):
                cat = self.df[item].cat
                categories = cat.categories
                codes = cat.codes.values

                # Find which code indices have labels matching our patterns
                matching_code_indices = []
                for i, cat_name in enumerate(categories):
                    label_lower = str(cat_name).lower()
                    # Check if any pattern matches
                    for pattern in patterns:
                        if pattern.lower() in label_lower:
                            matching_code_indices.append(i)
                            break

                # Mark all respondents with matching codes
                for code_idx in matching_code_indices:
                    mask[codes == code_idx] = True

            masks[item] = mask

        return masks

    def build_family_a(self, applicable_counts: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Family A: Item nonresponse.
        Returns (numerator_array, denominator_array, rate_array)
        """
        masks = self._build_outcome_masks(self.FAMILY_A_PATTERNS)

        numerator = np.zeros(len(self.df), dtype=int)
        for item, mask in masks.items():
            numerator += mask.astype(int)

        # Denominator is the applicable count
        denominator = applicable_counts

        # Rate: numerator / denominator, with 0/0 = 0
        rate = np.divide(numerator, denominator, where=denominator > 0, out=np.zeros_like(numerator, dtype=float))

        return numerator, denominator, rate

    def build_family_c(self, applicable_counts: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Family C: Response error.
        Returns (numerator_array, denominator_array, rate_array)
        """
        masks = self._build_outcome_masks(self.FAMILY_C_PATTERNS)

        numerator = np.zeros(len(self.df), dtype=int)
        for item, mask in masks.items():
            numerator += mask.astype(int)

        denominator = applicable_counts

        rate = np.divide(numerator, denominator, where=denominator > 0, out=np.zeros_like(numerator, dtype=float))

        return numerator, denominator, rate

    def build_family_b(self, applicable_counts: np.ndarray, web_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Family B: Break-off. Web-mode respondents only per pre-registration
        ("Paper respondents are not included in this analysis").

        Numerator, denominator, and rate are all NaN for paper respondents,
        not zero: the pre-registration excludes them from the analysis rather
        than defining a valid zero-rate observation for them. See
        docs/decisions.md, Phase 3b entry, for the ambiguity and the
        alternative (code paper as zero) that was not chosen.

        Returns (numerator_array, denominator_array, rate_array), float64,
        NaN outside the web subgroup.
        """
        masks = self._build_outcome_masks(self.FAMILY_B_PATTERNS)

        numerator_all = np.zeros(len(self.df), dtype=int)
        for item, mask in masks.items():
            numerator_all += mask.astype(int)

        numerator = np.full(len(self.df), np.nan)
        denominator = np.full(len(self.df), np.nan)
        rate = np.full(len(self.df), np.nan)

        numerator[web_mask] = numerator_all[web_mask]
        denominator[web_mask] = applicable_counts[web_mask]
        web_num = numerator_all[web_mask]
        web_denom = applicable_counts[web_mask]
        rate[web_mask] = np.divide(
            web_num, web_denom, where=web_denom > 0,
            out=np.zeros_like(web_num, dtype=float)
        )

        return numerator, denominator, rate


# ============================================================================
# PART 3b: Filter Missing sensitivity denominator, mode variable, Family B
# ============================================================================

def build_filter_missing_mask(df: pd.DataFrame, col_name: str) -> np.ndarray:
    """Boolean mask, True where the item's value is coded Filter Missing."""
    mask = np.zeros(len(df), dtype=bool)
    if isinstance(df[col_name].dtype, pd.CategoricalDtype):
        categories = df[col_name].cat.categories
        codes = df[col_name].cat.codes.values
        fm_indices = [
            i for i, cat_name in enumerate(categories)
            if isinstance(cat_name, str) and 'filter missing' in cat_name.lower()
        ]
        for idx in fm_indices:
            mask[codes == idx] = True
    return mask


def build_applicable_counts_sensitivity(denom_builder: 'DenominatorBuilder', df: pd.DataFrame, items: List[str]) -> np.ndarray:
    """
    Sensitivity denominator: exclude Inapplicable items (as primary does)
    AND items coded Filter Missing. Pre-registered alternative to the primary
    rule, which includes Filter Missing in the denominator.
    """
    applicable_count_sens = np.zeros(len(df), dtype=int)
    for item in items:
        inapp_mask = denom_builder._build_inapplicable_mask(item)
        fm_mask = build_filter_missing_mask(df, item)
        excluded = inapp_mask | fm_mask
        applicable_count_sens += (~excluded).astype(int)
    return applicable_count_sens


def extend_frame_phase3b(df: pd.DataFrame, existing_frame: pd.DataFrame, items: List[str],
                          denom_builder: 'DenominatorBuilder', applicable_count: np.ndarray) -> pd.DataFrame:
    """
    Phase 3b: add the mode variable, Family B (web-scoped break-off), and the
    Filter Missing sensitivity variant to the frozen Phase 3 frame.

    Does not touch family_a_* or family_c_* (primary). Extends in place.
    """
    applicable_count_sens = build_applicable_counts_sensitivity(denom_builder, df, items)

    web_mask = (df['FormType'] == 'HINTS7, standard version - web').values
    paper_mask = (df['FormType'] == 'HINTS7, standard version - paper').values
    assert (web_mask | paper_mask).all(), "FormType has a value outside web/paper"

    outcomes_builder = OutcomesBuilder(df, items)
    family_b_num, family_b_denom, family_b_rate = outcomes_builder.build_family_b(applicable_count, web_mask)

    family_a_num = existing_frame['family_a_numerator'].values
    family_c_num = existing_frame['family_c_numerator'].values

    family_a_rate_sens = np.divide(
        family_a_num, applicable_count_sens, where=applicable_count_sens > 0,
        out=np.zeros_like(family_a_num, dtype=float)
    )
    family_c_rate_sens = np.divide(
        family_c_num, applicable_count_sens, where=applicable_count_sens > 0,
        out=np.zeros_like(family_c_num, dtype=float)
    )

    family_b_denom_sens = np.full(len(df), np.nan)
    family_b_rate_sens = np.full(len(df), np.nan)
    web_denom_sens = applicable_count_sens[web_mask]
    web_num = family_b_num[web_mask]
    family_b_denom_sens[web_mask] = web_denom_sens
    family_b_rate_sens[web_mask] = np.divide(
        web_num, web_denom_sens, where=web_denom_sens > 0,
        out=np.zeros_like(web_num, dtype=float)
    )

    extended = existing_frame.copy()
    extended['FormType'] = df['FormType'].values
    extended['applicable_count_sens'] = applicable_count_sens
    extended['family_a_rate_sens'] = family_a_rate_sens
    extended['family_c_rate_sens'] = family_c_rate_sens
    extended['family_b_numerator'] = family_b_num
    extended['family_b_denominator'] = family_b_denom
    extended['family_b_rate'] = family_b_rate
    extended['family_b_denominator_sens'] = family_b_denom_sens
    extended['family_b_rate_sens'] = family_b_rate_sens

    return extended


# ============================================================================
# PART 4: Assemble the analysis frame
# ============================================================================

def build_analysis_frame(df: pd.DataFrame, item_universe: ItemUniverse) -> pd.DataFrame:
    """
    Assemble the analysis frame with outcomes and design variables.
    One row per respondent.
    """
    items = item_universe.get_items()

    # Build denominators and outcomes
    denom_builder = DenominatorBuilder(df, items)
    applicable_counts = denom_builder.build_applicable_counts()

    outcomes_builder = OutcomesBuilder(df, items)
    family_a_num, family_a_denom, family_a_rate = outcomes_builder.build_family_a(applicable_counts)
    family_c_num, family_c_denom, family_c_rate = outcomes_builder.build_family_c(applicable_counts)

    # Build frame
    frame = pd.DataFrame({
        'respondent_id': range(len(df)),
        'applicable_count': applicable_counts,
        'family_a_numerator': family_a_num,
        'family_a_denominator': family_a_denom,
        'family_a_rate': family_a_rate,
        'family_c_numerator': family_c_num,
        'family_c_denominator': family_c_denom,
        'family_c_rate': family_c_rate,
    })

    # Add design variables (NOT split by arm—pooled only)
    frame['Treatment_H7_2'] = df['Treatment_H7_2'].values
    frame['CommitmentStmt'] = df['CommitmentStmt'].values
    frame['PERSON_FINWT0'] = df['PERSON_FINWT0'].astype(float).values

    # Add all 50 replicate weights
    for i in range(1, 51):
        weight_col = f'PERSON_FINWT{i}'
        frame[weight_col] = df[weight_col].astype(float).values

    # Add strata
    frame['STRATUM'] = df['STRATUM'].values
    frame['VAR_STRATUM'] = df['VAR_STRATUM'].values

    return frame


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the full Phase 3 pipeline."""
    from load_hints import load_hints_data

    # Paths
    project_root = Path(__file__).parent.parent
    rda_path = project_root / 'data' / 'raw' / 'HINTS7_R_20250731' / 'hints7_public.rda'
    output_map = project_root / 'data' / 'processed' / 'item_denominator_map.csv'
    output_frame = project_root / 'data' / 'processed' / 'analysis_frame.parquet'

    # Create output directory
    output_map.parent.mkdir(parents=True, exist_ok=True)

    # Load data
    print("Loading HINTS data...")
    df = load_hints_data(str(rda_path))
    print(f"  Loaded: {df.shape}")

    # Classify items
    print("\nClassifying 515 columns...")
    universe = ItemUniverse(df)
    classifications = universe.classify_all_items()

    items = universe.get_items()
    print(f"  Items in universe: {len(items)}")
    print(f"  Excluded: {len(classifications) - len(items)}")

    # Write item_denominator_map.csv
    print(f"\nWriting item_denominator_map.csv...")
    item_map = universe.to_csv(str(output_map))
    print(f"  Written to {output_map}")

    # Build analysis frame
    print("\nBuilding analysis frame...")
    frame = build_analysis_frame(df, universe)
    print(f"  Frame shape: {frame.shape}")

    # Write analysis frame
    print(f"Writing analysis_frame.parquet...")
    frame.to_parquet(str(output_frame), index=False)
    print(f"  Written to {output_frame}")

    print("\nPhase 3 Part 1-4 complete.")
    print(f"  {len(items)} items in universe")
    print(f"  {frame.shape[0]} respondents with outcomes")


def main_phase3b():
    """
    Phase 3b: extend the frozen analysis_frame.parquet in place with the
    mode variable, Family B (break-off, web-scoped), and the Filter Missing
    sensitivity variant. Does not rebuild Families A or C; verifies parity
    with the frozen frame before writing anything.

    Pooled only. No Treatment_H7_2 grouping anywhere in this function.
    """
    from load_hints import load_hints_data

    project_root = Path(__file__).parent.parent
    rda_path = project_root / 'data' / 'raw' / 'HINTS7_R_20250731' / 'hints7_public.rda'
    frame_path = project_root / 'data' / 'processed' / 'analysis_frame.parquet'
    item_map_path = project_root / 'data' / 'processed' / 'item_denominator_map.csv'

    print("Loading HINTS raw data and the frozen analysis frame...")
    df = load_hints_data(str(rda_path))
    existing_frame = pd.read_parquet(str(frame_path))
    assert existing_frame.shape[0] == 7278, f"frozen frame row count drifted: {existing_frame.shape[0]}"

    universe = ItemUniverse(df)
    universe.classify_all_items()
    items = universe.get_items()
    assert len(items) == 368, f"item universe drifted: {len(items)}"

    existing_map = pd.read_csv(str(item_map_path))
    existing_items = set(existing_map.loc[existing_map['in_item_universe'] == True, 'variable'])
    assert set(items) == existing_items, "recomputed item universe does not match the frozen map on disk"

    denom_builder = DenominatorBuilder(df, items)
    applicable_count = denom_builder.build_applicable_counts()
    assert np.array_equal(applicable_count, existing_frame['applicable_count'].values), (
        "recomputed applicable_count does not match the frozen frame; "
        "the denominator freeze would be violated by proceeding"
    )
    print("  Parity confirmed: recomputed applicable_count matches the frozen frame exactly.")

    extended = extend_frame_phase3b(df, existing_frame, items, denom_builder, applicable_count)
    assert extended.shape[0] == 7278, f"row count changed during extension: {extended.shape[0]}"
    print(f"  Extended frame shape: {extended.shape}")

    extended.to_parquet(str(frame_path), index=False)
    print(f"  Written to {frame_path}")


if __name__ == '__main__':
    main()
