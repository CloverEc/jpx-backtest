"""Stock ranking and selection logic."""

from typing import List, Tuple

import pandas as pd

from ..io.schemas import StrategyConfig
from ..utils.constants import SIDE_LONG, SIDE_SHORT, COL_SHORTABLE


def rank_and_select(
    daily_data: pd.DataFrame,
    strategy: StrategyConfig
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Rank stocks by prediction score and select top/bottom positions.

    Args:
        daily_data: DataFrame with predictions for a single trading day
        strategy: Strategy configuration

    Returns:
        Tuple of (long_positions, short_positions) DataFrames

    Notes:
        - Filters out banned markets
        - Sorts by Prediction score (descending for long, ascending for short)
        - Selects top_k and bottom_k positions
    """
    if daily_data.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Filter for long positions (exclude banned markets)
    long_candidates = daily_data[
        ~daily_data['MarketCodeName'].isin(strategy.ban_long_markets)
    ].copy()

    # Filter for short positions (exclude banned markets and non-shortable stocks)
    short_candidates = daily_data[
        ~daily_data['MarketCodeName'].isin(strategy.ban_short_markets)
    ].copy()

    # Apply Shortable filter if column exists
    if COL_SHORTABLE in short_candidates.columns:
        non_shortable_count = (~short_candidates[COL_SHORTABLE].astype(bool)).sum()
        short_candidates = short_candidates[
            short_candidates[COL_SHORTABLE].astype(bool)
        ]
        if non_shortable_count > 0:
            print(f"  Filtered out {non_shortable_count} non-shortable stocks")

    # Rank and select long positions (highest predictions)
    long_positions = pd.DataFrame()
    if strategy.top_k > 0 and not long_candidates.empty:
        long_positions = (
            long_candidates
            .sort_values('Prediction', ascending=False)
            .head(strategy.top_k)
            .copy()
        )
        long_positions['Side'] = SIDE_LONG

    # Rank and select short positions (lowest predictions)
    short_positions = pd.DataFrame()
    if strategy.bottom_k > 0 and not short_candidates.empty:
        short_positions = (
            short_candidates
            .sort_values('Prediction', ascending=True)
            .head(strategy.bottom_k)
            .copy()
        )
        short_positions['Side'] = SIDE_SHORT

    return long_positions, short_positions


def filter_valid_prices(positions: pd.DataFrame) -> pd.DataFrame:
    """
    Filter out positions with invalid prices (zero or negative).

    Args:
        positions: DataFrame with Open and Close prices

    Returns:
        Filtered DataFrame with valid prices only

    Notes:
        Logs warnings for skipped positions
    """
    if positions.empty:
        return positions

    # Check for invalid prices
    invalid_open = (positions['Open'] <= 0) | positions['Open'].isna()
    invalid_close = (positions['Close'] <= 0) | positions['Close'].isna()
    invalid = invalid_open | invalid_close

    invalid_count = invalid.sum()
    if invalid_count > 0:
        print(f"WARNING: Skipping {invalid_count} positions with invalid prices (zero, negative, or NaN)")

        # Show details of invalid positions
        invalid_positions = positions[invalid]
        for _, row in invalid_positions.iterrows():
            print(f"  - Date: {row['Date']}, Code: {row['Code']}, Open: {row['Open']}, Close: {row['Close']}")

    return positions[~invalid].copy()


def validate_min_positions(
    long_positions: pd.DataFrame,
    short_positions: pd.DataFrame,
    strategy: StrategyConfig,
    date: pd.Timestamp
) -> bool:
    """
    Check if minimum position count is met.

    Args:
        long_positions: Long positions DataFrame
        short_positions: Short positions DataFrame
        strategy: Strategy configuration
        date: Trading date

    Returns:
        True if minimum positions met, False otherwise

    Notes:
        Logs warning if minimum not met
    """
    total_positions = len(long_positions) + len(short_positions)

    if total_positions < strategy.min_k:
        print(
            f"WARNING: Date {date.date()}: Only {total_positions} positions available, "
            f"less than min_k={strategy.min_k}. Skipping this day."
        )
        return False

    return True
