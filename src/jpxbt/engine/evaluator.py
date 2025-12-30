"""Main backtesting evaluator for Open->Close trading."""

from typing import Dict, List, Any
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from ..io.schemas import StrategyConfig
from ..utils.constants import SIDE_LONG, SIDE_SHORT
from .ranking import rank_and_select, filter_valid_prices, validate_min_positions
from .allocator import allocate_positions


@dataclass
class BacktestResults:
    """Container for backtest results."""

    strategy_name: str
    trades: pd.DataFrame
    daily_summary: List[Dict[str, Any]] = field(default_factory=list)
    initial_capital: float = 10_000_000.0

    def get_period(self) -> Dict[str, str]:
        """Get start and end dates of backtest period."""
        if self.trades.empty:
            return {"start": None, "end": None}

        dates = pd.to_datetime(self.trades['Date'])
        return {
            "start": dates.min().strftime('%Y-%m-%d'),
            "end": dates.max().strftime('%Y-%m-%d')
        }

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if not self.daily_summary:
            return {
                "total_pnl": 0.0,
                "total_return_pct": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "avg_daily_turnover": 0.0
            }

        # Extract daily PnLs
        daily_pnls = [day['pnl'] for day in self.daily_summary]
        total_pnl = sum(daily_pnls)

        # Calculate returns
        total_return_pct = (total_pnl / self.initial_capital) * 100

        # Sharpe ratio (annualized)
        if len(daily_pnls) > 1:
            daily_returns = np.array(daily_pnls) / self.initial_capital
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max drawdown
        cumulative_pnl = np.cumsum(daily_pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = np.min(drawdown)
        max_drawdown_pct = (max_drawdown / self.initial_capital) * 100

        # Win rate
        winning_days = sum(1 for pnl in daily_pnls if pnl > 0)
        win_rate = winning_days / len(daily_pnls)

        # Total trades
        total_trades = sum(day['num_trades'] for day in self.daily_summary)

        # Average daily turnover
        daily_turnovers = [day.get('turnover', 0.0) for day in self.daily_summary]
        avg_daily_turnover = np.mean(daily_turnovers) if daily_turnovers else 0.0

        return {
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,
            "avg_daily_turnover": round(avg_daily_turnover, 2)
        }


class Evaluator:
    """Main backtesting evaluator."""

    def __init__(self, strategy: StrategyConfig, initial_capital: float = 10_000_000.0):
        """
        Initialize evaluator.

        Args:
            strategy: Strategy configuration
            initial_capital: Initial capital amount (default: 10M JPY)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital

    def calculate_trade_pnl(
        self,
        shares: int,
        entry_price: float,
        exit_price: float,
        side: str
    ) -> tuple[float, float, float]:
        """
        Calculate PnL and costs for a single trade.

        Args:
            shares: Number of shares
            entry_price: Entry price (Open)
            exit_price: Exit price (Close)
            side: Trade side (LONG or SHORT)

        Returns:
            Tuple of (pnl, entry_cost, exit_cost)
        """
        # Calculate transaction costs
        cost_rate = self.strategy.cost_bps / 10000
        entry_cost = shares * entry_price * cost_rate
        exit_cost = shares * exit_price * cost_rate

        # Calculate gross PnL based on side
        if side == SIDE_LONG:
            gross_pnl = shares * (exit_price - entry_price)
        else:  # SHORT
            gross_pnl = shares * (entry_price - exit_price)

        # Net PnL after costs
        net_pnl = gross_pnl - entry_cost - exit_cost

        return net_pnl, entry_cost, exit_cost

    def execute_daily_trades(
        self,
        daily_data: pd.DataFrame,
        date: pd.Timestamp
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Execute trades for a single day.

        Args:
            daily_data: Predictions for a single trading day
            date: Trading date

        Returns:
            Tuple of (trades_df, daily_summary_dict)
        """
        # Rank and select positions
        long_positions, short_positions = rank_and_select(daily_data, self.strategy)

        # Filter out invalid prices
        long_positions = filter_valid_prices(long_positions)
        short_positions = filter_valid_prices(short_positions)

        # Check minimum position requirement
        if not validate_min_positions(long_positions, short_positions, self.strategy, date):
            return pd.DataFrame(), {
                "date": date.strftime('%Y-%m-%d'),
                "pnl": 0.0,
                "num_trades": 0,
                "long_positions": 0,
                "short_positions": 0,
                "turnover": 0.0
            }

        # Allocate capital
        all_positions = allocate_positions(
            long_positions,
            short_positions,
            self.strategy,
            self.initial_capital
        )

        if all_positions.empty:
            return pd.DataFrame(), {
                "date": date.strftime('%Y-%m-%d'),
                "pnl": 0.0,
                "num_trades": 0,
                "long_positions": 0,
                "short_positions": 0,
                "turnover": 0.0
            }

        # Execute trades and calculate PnL
        trades = []
        total_pnl = 0.0
        total_turnover = 0.0

        for _, position in all_positions.iterrows():
            pnl, entry_cost, exit_cost = self.calculate_trade_pnl(
                shares=position['Shares'],
                entry_price=position['Open'],
                exit_price=position['Close'],
                side=position['Side']
            )

            total_pnl += pnl
            total_turnover += position['Shares'] * position['Open']

            trades.append({
                'Date': date,
                'Code': position['Code'],
                'Side': position['Side'],
                'Shares': position['Shares'],
                'EntryPrice': position['Open'],
                'ExitPrice': position['Close'],
                'PnL': pnl,
                'EntryCost': entry_cost,
                'ExitCost': exit_cost
            })

        trades_df = pd.DataFrame(trades)

        # Daily summary
        num_long = len(all_positions[all_positions['Side'] == SIDE_LONG])
        num_short = len(all_positions[all_positions['Side'] == SIDE_SHORT])

        daily_summary = {
            "date": date.strftime('%Y-%m-%d'),
            "pnl": round(total_pnl, 2),
            "num_trades": len(trades),
            "long_positions": num_long,
            "short_positions": num_short,
            "turnover": round(total_turnover, 2)
        }

        return trades_df, daily_summary

    def run(self, predictions: pd.DataFrame) -> BacktestResults:
        """
        Run backtest on predictions.

        Args:
            predictions: DataFrame with predictions and prices

        Returns:
            BacktestResults object with trades and metrics
        """
        print(f"Starting backtest for strategy: {self.strategy.name}")
        print(f"Initial capital: {self.initial_capital:,.0f} JPY")
        print(f"Leverage: {self.strategy.leverage}x")
        print(f"Long positions: {self.strategy.top_k}, Short positions: {self.strategy.bottom_k}")
        print()

        all_trades = []
        daily_summaries = []

        # Group by date and execute daily
        dates = sorted(predictions['Date'].unique())
        print(f"Processing {len(dates)} trading days...")
        print()

        for i, date in enumerate(dates, 1):
            if i % 50 == 0 or i == len(dates):
                print(f"Progress: {i}/{len(dates)} days processed")

            daily_data = predictions[predictions['Date'] == date]
            trades_df, daily_summary = self.execute_daily_trades(daily_data, date)

            if not trades_df.empty:
                all_trades.append(trades_df)

            daily_summaries.append(daily_summary)

        # Combine all trades
        if all_trades:
            all_trades_df = pd.concat(all_trades, ignore_index=True)
        else:
            all_trades_df = pd.DataFrame(columns=[
                'Date', 'Code', 'Side', 'Shares', 'EntryPrice',
                'ExitPrice', 'PnL', 'EntryCost', 'ExitCost'
            ])

        print()
        print(f"Backtest completed!")
        print(f"Total trades: {len(all_trades_df)}")

        return BacktestResults(
            strategy_name=self.strategy.name,
            trades=all_trades_df,
            daily_summary=daily_summaries,
            initial_capital=self.initial_capital
        )
