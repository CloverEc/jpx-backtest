"""Input data loading and validation."""

import tomli
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..utils.constants import REQUIRED_PREDICTION_COLUMNS
from .schemas import StrategyConfig


def load_predictions(file_path: str | Path) -> pd.DataFrame:
    """
    Load and validate predictions from parquet file.

    Args:
        file_path: Path to predictions.parquet file

    Returns:
        DataFrame with validated predictions

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns are missing or data is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {file_path}")

    # Load parquet file
    df = pd.read_parquet(file_path)

    # Validate empty dataframe
    if df.empty:
        raise ValueError("Predictions file is empty")

    # Check required columns
    missing_cols = set(REQUIRED_PREDICTION_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Missing required columns in predictions.parquet: {missing_cols}"
        )

    # Convert Date to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])

    # Check for duplicates
    duplicates = df.duplicated(subset=['Date', 'Code'], keep=False)
    if duplicates.any():
        dup_count = duplicates.sum()
        raise ValueError(
            f"Found {dup_count} duplicate (Date, Code) pairs in predictions"
        )

    # Warn about NaN values in critical columns
    for col in ['Open', 'Close', 'Prediction']:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            print(f"WARNING: Found {nan_count} NaN values in column '{col}', these records will be skipped")

    # Drop rows with NaN in critical columns
    df_clean = df.dropna(subset=['Open', 'Close', 'Prediction'])

    if df_clean.empty:
        raise ValueError("No valid records remain after removing NaN values")

    dropped_count = len(df) - len(df_clean)
    if dropped_count > 0:
        print(f"Dropped {dropped_count} records with NaN values")

    return df_clean


def load_strategy(file_path: str | Path) -> StrategyConfig:
    """
    Load and validate strategy configuration from TOML file.

    Args:
        file_path: Path to strategy.toml file

    Returns:
        Validated StrategyConfig object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If configuration is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {file_path}")

    # Load TOML file
    with open(file_path, 'rb') as f:
        config_dict = tomli.load(f)

    # Extract strategy section
    if 'strategy' not in config_dict:
        raise ValueError("Missing 'strategy' section in TOML file")

    strategy_dict = config_dict['strategy']

    # Validate using pydantic
    try:
        strategy = StrategyConfig(**strategy_dict)
    except Exception as e:
        raise ValueError(f"Invalid strategy configuration: {e}")

    return strategy
