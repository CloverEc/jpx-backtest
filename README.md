# JPX Backtest Engine

A **deterministic backtesting engine** for Japanese equities that evaluates Open→Close trading strategies.

## Features

- ✅ Pure evaluation engine (no prediction generation or model training)
- ✅ Deterministic execution (same inputs → same outputs)
- ✅ Support for long/short portfolios with customizable positions
- ✅ Japanese lot size constraints (100 shares per lot)
- ✅ Transaction cost modeling
- ✅ Comprehensive performance metrics (Sharpe, Drawdown, Win Rate, etc.)
- ✅ Fail-fast validation with clear error messages

## Installation

```bash
# Clone repository
cd jpx-backtest

# Install package in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Generate Sample Data (for testing)

```bash
cd examples
python generate_sample_data.py
```

This creates `examples/submission_sample/predictions.parquet` with synthetic data.

### 2. Run Backtest

```bash
jpxbt run \
  --predictions examples/submission_sample/predictions.parquet \
  --strategy examples/submission_sample/strategy.toml \
  --output runs/result_001
```

Or use the example script:

```bash
chmod +x examples/run_example.sh
./examples/run_example.sh
```

### 3. View Results

Results are saved to the output directory:

- `result.json` - Summary metrics and daily performance
- `trades.parquet` - Trade-level details
- `daily_summary.csv` - Daily performance table

## Input Files

### predictions.parquet

Required columns:

| Column          | Type      | Description                          |
|-----------------|-----------|--------------------------------------|
| Date            | datetime  | Trading date                         |
| Code            | str       | Stock code (5-digit JPX format)      |
| Prediction      | float     | Prediction score (higher = bullish)  |
| Open            | float     | Opening price                        |
| Close           | float     | Closing price                        |
| MarketCodeName  | str       | Market category (e.g. "プライム")     |

### strategy.toml

Example configuration:

```toml
[strategy]
name = "ridge_ls_v1"

# Portfolio construction
top_k = 10                    # Number of long positions
bottom_k = 10                 # Number of short positions
min_k = 1                     # Minimum positions to trade

# Capital & execution
leverage = 3.3                # Leverage multiplier
lot_size = 100                # Shares per lot (JPX standard)
cost_bps = 2.0                # Transaction cost (basis points, 2.0 = 0.02%)

# Market filters
ban_long_markets = ["グロース", "スタンダード"]   # Markets to exclude from long
ban_short_markets = ["グロース", "スタンダード"]  # Markets to exclude from short
```

## Trading Rules

1. **Entry price**: Open
2. **Exit price**: Close
3. **Holding period**: Same trading day only (no overnight positions)
4. **Ranking**: Sort by `Prediction` (descending for long, ascending for short)
5. **Allocation**: Equal-weight among selected stocks
6. **Lot constraint**: Round down to nearest 100 shares
7. **Transaction cost**: Applied symmetrically on entry and exit

## CLI Usage

```bash
# Basic usage
jpxbt run -p predictions.parquet -s strategy.toml -o runs/result_001

# With custom initial capital
jpxbt run -p predictions.parquet -s strategy.toml -o runs/result_001 --capital 50000000

# Skip exporting trades.parquet
jpxbt run -p predictions.parquet -s strategy.toml -o runs/result_001 --no-trades

# Show version
jpxbt version

# Show help
jpxbt run --help
```

## Python API

```python
from jpxbt.engine.evaluator import Evaluator
from jpxbt.io.readers import load_predictions, load_strategy
from jpxbt.io.writers import export_results, print_summary

# Load inputs
predictions = load_predictions("data/predictions.parquet")
strategy = load_strategy("strategy.toml")

# Run backtest
evaluator = Evaluator(strategy, initial_capital=10_000_000)
results = evaluator.run(predictions)

# Print summary
print_summary(results)

# Export results
export_results(results, "runs/result_001")
```

## Output Format

### result.json

```json
{
  "strategy_name": "ridge_ls_v1",
  "period": {
    "start": "2024-01-04",
    "end": "2024-12-30"
  },
  "metrics": {
    "total_pnl": 1234567.89,
    "total_return_pct": 12.34,
    "sharpe_ratio": 1.56,
    "max_drawdown_pct": -8.45,
    "win_rate": 0.62,
    "total_trades": 2500,
    "avg_daily_turnover": 15000000.0
  },
  "daily_summary": [
    {
      "date": "2024-01-04",
      "pnl": 12345.67,
      "num_trades": 20,
      "long_positions": 10,
      "short_positions": 10
    }
  ]
}
```

## Validation Rules

### Fail-Fast Errors

The engine aborts immediately with a clear error message for:

- ❌ Missing required columns in predictions.parquet
- ❌ Empty predictions file
- ❌ Duplicate (Date, Code) pairs
- ❌ Invalid strategy configuration (negative values, etc.)

### Warnings (Continues Execution)

The engine logs warnings and skips problematic records for:

- ⚠️ NaN values in Open/Close/Prediction columns
- ⚠️ Invalid prices (zero or negative)
- ⚠️ Insufficient capital for position allocation
- ⚠️ Days with fewer positions than `min_k`

## Development

### Project Structure

```
jpx-backtest/
├── src/jpxbt/           # Main package
│   ├── engine/          # Core backtesting logic
│   ├── io/              # Input/output handling
│   ├── reporting/       # Report generation (future)
│   └── utils/           # Utilities
├── tests/               # Unit tests
├── examples/            # Example data and scripts
└── runs/                # Output directory (git-ignored)
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

## Key Principles

1. **Deterministic**: Same inputs → Same outputs (no randomness)
2. **Minimal**: Only evaluation logic, no data fetching or model training
3. **Transparent**: Clear logging of all actions and decisions
4. **Testable**: Unit tests for all core components
5. **Fail-fast**: Invalid inputs cause immediate errors with clear messages

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
