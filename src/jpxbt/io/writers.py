"""Output file writers for backtest results."""

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..engine.evaluator import BacktestResults


def export_results(
    results: BacktestResults,
    output_dir: str | Path,
    export_trades: bool = True,
    export_daily_csv: bool = True
) -> None:
    """
    Export backtest results to files.

    Args:
        results: BacktestResults object
        output_dir: Directory to save output files
        export_trades: Whether to export trades.parquet (default: True)
        export_daily_csv: Whether to export daily_summary.csv (default: True)

    Creates:
        - result.json: Summary metrics and daily performance
        - trades.parquet: Trade-level details (if export_trades=True)
        - daily_summary.csv: Daily performance table (if export_daily_csv=True)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Exporting results to: {output_path}")

    # 1. Export result.json
    result_json = create_result_json(results)
    json_path = output_path / "result.json"

    with open(json_path, 'w') as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Saved result.json ({json_path})")

    # 2. Export trades.parquet
    if export_trades and not results.trades.empty:
        trades_path = output_path / "trades.parquet"
        results.trades.to_parquet(trades_path, index=False)
        print(f"  ✓ Saved trades.parquet ({trades_path})")
    elif export_trades:
        print(f"  ⚠ No trades to export")

    # 3. Export daily_summary.csv
    if export_daily_csv and results.daily_summary:
        daily_df = pd.DataFrame(results.daily_summary)
        csv_path = output_path / "daily_summary.csv"
        daily_df.to_csv(csv_path, index=False)
        print(f"  ✓ Saved daily_summary.csv ({csv_path})")

    print()
    print("Export completed successfully!")


def create_result_json(results: BacktestResults) -> Dict[str, Any]:
    """
    Create result.json structure from BacktestResults.

    Args:
        results: BacktestResults object

    Returns:
        Dictionary matching the required result.json format
    """
    period = results.get_period()
    metrics = results.calculate_metrics()

    return {
        "strategy_name": results.strategy_name,
        "period": period,
        "metrics": metrics,
        "daily_summary": results.daily_summary
    }


def print_summary(results: BacktestResults) -> None:
    """
    Print a human-readable summary of backtest results.

    Args:
        results: BacktestResults object
    """
    metrics = results.calculate_metrics()
    period = results.get_period()

    print()
    print("=" * 60)
    print(f"BACKTEST SUMMARY: {results.strategy_name}")
    print("=" * 60)
    print()
    print(f"Period: {period['start']} to {period['end']}")
    print(f"Initial Capital: {results.initial_capital:,.0f} JPY")
    print()
    print("Performance Metrics:")
    print(f"  Total PnL:          {metrics['total_pnl']:>15,.2f} JPY")
    print(f"  Total Return:       {metrics['total_return_pct']:>15,.2f} %")
    print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:>15,.2f}")
    print(f"  Max Drawdown:       {metrics['max_drawdown_pct']:>15,.2f} %")
    print(f"  Win Rate:           {metrics['win_rate']:>15,.2%}")
    print()
    print("Trading Statistics:")
    print(f"  Total Trades:       {metrics['total_trades']:>15,}")
    print(f"  Avg Daily Turnover: {metrics['avg_daily_turnover']:>15,.2f} JPY")
    print()

    # Show best and worst days
    if results.daily_summary:
        daily_pnls = [(day['date'], day['pnl']) for day in results.daily_summary]
        daily_pnls.sort(key=lambda x: x[1], reverse=True)

        print("Top 5 Best Days:")
        for date, pnl in daily_pnls[:5]:
            print(f"  {date}: {pnl:>12,.2f} JPY")
        print()

        print("Top 5 Worst Days:")
        for date, pnl in daily_pnls[-5:]:
            print(f"  {date}: {pnl:>12,.2f} JPY")
        print()

    print("=" * 60)
    print()
