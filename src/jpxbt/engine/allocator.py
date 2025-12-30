"""Capital allocation with lot size constraints."""

import numpy as np
import pandas as pd

from ..io.schemas import StrategyConfig
from ..utils.constants import SIDE_LONG, SIDE_SHORT


def calculate_shares(
    positions: pd.DataFrame,
    strategy: StrategyConfig,
    initial_capital: float = 10_000_000.0
) -> pd.DataFrame:
    """
    Calculate number of shares for each position with lot size constraints.

    Args:
        positions: DataFrame with selected positions (must have 'Side' and 'Open' columns)
        strategy: Strategy configuration
        initial_capital: Initial capital amount (default: 10M JPY)

    Returns:
        DataFrame with added 'Shares' column

    Notes:
        - Equal-weight allocation among positions
        - Rounds down to nearest lot_size
        - Applies leverage to capital
    """
    if positions.empty:
        positions['Shares'] = []
        return positions

    # Calculate total capital with leverage
    total_capital = initial_capital * strategy.leverage

    # Count positions by side
    num_positions = len(positions)

    # Equal allocation per position
    capital_per_position = total_capital / num_positions

    # Calculate shares with lot size constraint
    shares = []
    for _, row in positions.iterrows():
        open_price = row['Open']

        if open_price <= 0:
            shares.append(0)
            continue

        # Calculate raw shares from allocated capital
        raw_shares = capital_per_position / open_price

        # Round down to nearest lot
        lot_shares = np.floor(raw_shares / strategy.lot_size) * strategy.lot_size

        shares.append(int(lot_shares))

    positions = positions.copy()
    positions['Shares'] = shares

    # Warn about zero share allocations
    zero_shares = (positions['Shares'] == 0)
    if zero_shares.any():
        zero_count = zero_shares.sum()
        print(
            f"WARNING: {zero_count} positions allocated 0 shares due to insufficient capital or high price"
        )

        # Show details
        for _, row in positions[zero_shares].iterrows():
            allocated = capital_per_position
            print(
                f"  - Code: {row['Code']}, Open: {row['Open']:.2f}, "
                f"Allocated: {allocated:.2f}, Lot size: {strategy.lot_size}"
            )

    return positions


def validate_capital_usage(
    positions: pd.DataFrame,
    initial_capital: float = 10_000_000.0
) -> None:
    """
    Validate that capital usage is within reasonable bounds.

    Args:
        positions: DataFrame with 'Shares' and 'Open' columns
        initial_capital: Initial capital amount

    Notes:
        Logs warnings if capital usage seems problematic
    """
    if positions.empty:
        return

    # Calculate total capital used
    positions['CapitalUsed'] = positions['Shares'] * positions['Open']
    total_used = positions['CapitalUsed'].sum()

    # Calculate utilization percentage (consider leverage)
    max_capital = initial_capital * 10  # Assume max reasonable leverage

    if total_used > max_capital:
        print(
            f"WARNING: Total capital used ({total_used:,.0f}) exceeds reasonable bounds "
            f"(max expected: {max_capital:,.0f})"
        )


def allocate_positions(
    long_positions: pd.DataFrame,
    short_positions: pd.DataFrame,
    strategy: StrategyConfig,
    initial_capital: float = 10_000_000.0
) -> pd.DataFrame:
    """
    Allocate capital to long and short positions.

    Args:
        long_positions: Long positions DataFrame
        short_positions: Short positions DataFrame
        strategy: Strategy configuration
        initial_capital: Initial capital amount

    Returns:
        Combined DataFrame with all positions and share allocations

    Notes:
        - Combines long and short positions
        - Applies equal-weight allocation
        - Validates capital usage
    """
    # Combine positions
    all_positions = pd.concat([long_positions, short_positions], ignore_index=True)

    if all_positions.empty:
        return all_positions

    # Calculate shares
    all_positions = calculate_shares(all_positions, strategy, initial_capital)

    # Filter out zero-share positions
    valid_positions = all_positions[all_positions['Shares'] > 0].copy()

    if len(valid_positions) < len(all_positions):
        removed = len(all_positions) - len(valid_positions)
        print(f"Removed {removed} positions with 0 shares from execution")

    # Validate capital usage
    validate_capital_usage(valid_positions, initial_capital)

    return valid_positions
