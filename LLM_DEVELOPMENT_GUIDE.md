# JPX Backtest Engine - Development Guide for Claude Code

## Project Overview
Create a **deterministic backtesting engine** for Japanese equities that evaluates Open→Close trading strategies. This is a pure evaluator (like Kaggle evaluation server) that does NOT generate predictions, fetch data, or train models.

---

## Technical Stack

### Language & Core Libraries
- **Python 3.11+**
- **pandas**: Data manipulation
- **pyarrow**: Parquet file I/O
- **python-dotenv**: Environment variable management
- **typer**: CLI framework
- **pydantic**: Configuration validation
- **J-Quants API**: Historical data fetching (API key from `.env`)

### Optional
- pytest: Unit testing
- toml/tomli: TOML parsing

---

## Project Structure

```
jpx-backtest/
├── README.md
├── SUBMISSION_GUIDE.md
├── LLM_DEVELOPMENT_GUIDE.md
├── pyproject.toml            # Poetry or pip-installable package
├── .env                      # J-Quants API key (JQUANTS_API_KEY=xxx)
├── .gitignore
│
├── src/
│   └── jpxbt/                # Package name
│       ├── __init__.py
│       │
│       ├── cli.py             # CLI entry point (typer)
│       │
│       ├── engine/            # Core evaluation logic
│       │   ├── __init__.py
│       │   ├── evaluator.py   # Main Open→Close evaluator
│       │   ├── allocator.py   # Capital allocation with 100-share lot constraints
│       │   ├── ranking.py     # Rank stocks by prediction score
│       │   └── costs.py       # Transaction cost calculation
│       │
│       ├── io/                # Input/Output handling
│       │   ├── __init__.py
│       │   ├── readers.py     # Load predictions.parquet & strategy.toml
│       │   ├── writers.py     # Export result.json, trades.parquet
│       │   └── schemas.py     # Required column definitions
│       │
│       ├── reporting/         # Report generation (read-only)
│       │   ├── __init__.py
│       │   ├── daily.py       # Daily performance report
│       │   └── summary.py     # Aggregate metrics (PnL, Sharpe, DD, etc.)
│       │
│       └── utils/             # Generic utilities
│           ├── __init__.py
│           ├── dates.py       # Trading date utilities
│           ├── validation.py  # Fail-fast validation
│           └── constants.py   # Constants (LOT_SIZE=100, etc.)
│
├── runs/                      # Execution results (git-ignored)
│   └── .gitkeep
│
├── tests/                     # Minimal unit tests
│   ├── test_allocator.py
│   ├── test_ranking.py
│   └── test_evaluator.py
│
└── examples/
    ├── submission_sample/
    │   ├── predictions.parquet
    │   └── strategy.toml
    └── run_example.sh
```

---

## Input Specifications

### 1. predictions.parquet

**Required columns:**

| Column          | Type      | Description                          |
|-----------------|-----------|--------------------------------------|
| Date            | datetime  | Trading date                         |
| Code            | str       | Stock code (5-digit JPX format)      |
| Prediction      | float     | Prediction score (higher = bullish)  |
| Open            | float     | Opening price                        |
| Close           | float     | Closing price                        |
| MarketCodeName  | str       | Market category (e.g. "プライム")     |

**Optional columns:**

| Column          | Type      | Description                          |
|-----------------|-----------|--------------------------------------|
| Shortable       | bool      | Whether the stock can be shorted     |

**Notes:**
- Extra columns are ignored
- Missing required columns → fail-fast error
- NaN in Open/Close → skip that record with warning
- **Shortable column behavior:**
  - `True` or `1`: Stock is eligible for short positions
  - `False` or `0`: Stock is excluded from short candidate selection
  - Column not present: All stocks are treated as shortable (backward compatible)

---

### 2. strategy.toml

```toml
[strategy]
name = "ridge_ls_v1"

# Portfolio construction
top_k = 10                    # Number of long positions
bottom_k = 10                 # Number of short positions (optional, default=0)
min_k = 1                     # Minimum positions to trade (default=1)

# Capital & execution
leverage = 3.3                # Leverage multiplier
lot_size = 100                # Shares per lot (JPX standard)
cost_bps = 2.0                # Transaction cost (basis points, 2.0 = 0.02%)

# Market filters
ban_long_markets = ["グロース", "スタンダード"]   # Markets to exclude from long
ban_short_markets = ["グロース", "スタンダード"]  # Markets to exclude from short
```

**Notes:**
- All fields are mandatory except `bottom_k` (default=0), `min_k` (default=1)
- Use pydantic for validation

---

## Trading Rules (Fixed)

1. **Entry price**: Open
2. **Exit price**: Close
3. **Holding period**: Same trading day only (no overnight positions)
4. **Ranking**: Sort by `Prediction` (descending for long, ascending for short)
5. **Allocation**: Equal-weight among selected stocks
6. **Lot constraint**: Round down to nearest 100 shares
7. **Transaction cost**: Applied symmetrically on entry and exit

**Formula:**
```
shares = floor(allocated_capital / open_price / lot_size) * lot_size
entry_cost = shares * open_price * (cost_bps / 10000)
exit_cost = shares * close_price * (cost_bps / 10000)
pnl = shares * (close_price - open_price) - entry_cost - exit_cost
```

---

## Output Specifications

### 1. result.json

**Must include:**

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

**Metric definitions:**
- **Sharpe Ratio**: `mean(daily_returns) / std(daily_returns) * sqrt(252)`
- **Max Drawdown**: Maximum cumulative loss from peak
- **Win Rate**: `(winning_days / total_trading_days)`

---

### 2. trades.parquet

**Columns:**

| Column       | Type      | Description                  |
|--------------|-----------|------------------------------|
| Date         | datetime  | Trading date                 |
| Code         | str       | Stock code                   |
| Side         | str       | "LONG" or "SHORT"            |
| Shares       | int       | Number of shares             |
| EntryPrice   | float     | Open price                   |
| ExitPrice    | float     | Close price                  |
| PnL          | float     | Realized profit/loss         |
| EntryCost    | float     | Transaction cost at entry    |
| ExitCost     | float     | Transaction cost at exit     |

---

## CLI Interface

### Installation
```bash
cd jpx-backtest
pip install -e .
```

### Usage
```bash
# Basic run
jpxbt run \
  --predictions data/predictions.parquet \
  --strategy strategy.toml \
  --output runs/result_001

# Options
jpxbt run --help
```

**Output:**
- `runs/result_001/result.json`
- `runs/result_001/trades.parquet`
- `runs/result_001/daily_summary.csv`

---

## Environment Variables

Create `.env` file in project root:

```bash
JQUANTS_API_KEY=your_api_key_here
```

Load using `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("JQUANTS_API_KEY")
```

**Note:** `.env` should be in `.gitignore`

---

## Development Priorities

### Phase 1: Core Engine (MVP)
1. ✅ `io/readers.py`: Load predictions.parquet + strategy.toml
2. ✅ `engine/ranking.py`: Rank by prediction, apply market filters
3. ✅ `engine/allocator.py`: Calculate shares with lot constraints
4. ✅ `engine/evaluator.py`: Execute Open→Close, compute PnL
5. ✅ `io/writers.py`: Export result.json + trades.parquet

### Phase 2: Reporting
6. ✅ `reporting/summary.py`: Sharpe, Drawdown, Win Rate
7. ✅ `reporting/daily.py`: Daily performance aggregation

### Phase 3: CLI & Testing
8. ✅ `cli.py`: Typer-based CLI
9. ✅ `tests/`: Unit tests for allocator, ranking, evaluator
10. ✅ `examples/`: Sample predictions + strategy

### Phase 4: Documentation
11. ✅ `README.md`: Usage guide
12. ✅ `SUBMISSION_GUIDE.md`: How to submit predictions

---

## Validation Rules (Fail-Fast)

### Input Validation
- ❌ Missing required columns → Abort with clear error
- ❌ Empty predictions → Abort
- ❌ Invalid dates (non-trading days) → Warning, skip
- ❌ Duplicate (Date, Code) pairs → Abort
- ❌ NaN in Open/Close → Warning, skip record

### Strategy Validation
- ❌ `top_k < 1` or `bottom_k < 0` → Abort
- ❌ `leverage <= 0` → Abort
- ❌ `cost_bps < 0` → Abort

### Execution Validation
- ⚠️ Insufficient capital for allocation → Warning, reduce positions
- ⚠️ Price = 0 → Skip record

---

## Error Handling Philosophy

1. **Fail-fast on invalid inputs**: Don't proceed with corrupted data
2. **Warn and skip on recoverable issues**: Log warnings, continue execution
3. **Never silently ignore errors**: Always log to console/file

---

## Testing Strategy

### Unit Tests
```python
# tests/test_allocator.py
def test_lot_rounding():
    # 100 lot constraint
    assert allocate(capital=100000, price=1000, lot=100) == 100

def test_insufficient_capital():
    # Cannot buy even 1 lot
    assert allocate(capital=50, price=1000, lot=100) == 0
```

### Integration Tests
```python
# tests/test_evaluator.py
def test_end_to_end():
    # Load sample predictions
    # Run evaluator
    # Verify output structure
```

---

## Code Style Guidelines

1. **Type hints**: Use for all function signatures
2. **Docstrings**: Google style for public APIs
3. **Constants**: ALL_CAPS in `utils/constants.py`
4. **Error messages**: Clear, actionable (e.g., "Missing column: 'Open' in predictions.parquet")

---

## Example Usage

```python
from jpxbt.engine.evaluator import Evaluator
from jpxbt.io.readers import load_predictions, load_strategy

# Load inputs
predictions = load_predictions("data/predictions.parquet")
strategy = load_strategy("strategy.toml")

# Run backtest
evaluator = Evaluator(strategy)
results = evaluator.run(predictions)

# Export
results.to_json("runs/result.json")
results.trades.to_parquet("runs/trades.parquet")
```

---

## Dependencies (pyproject.toml)

```toml
[tool.poetry.dependencies]
python = "^3.11"
pandas = "^2.2.0"
pyarrow = "^15.0.0"
typer = "^0.12.0"
pydantic = "^2.6.0"
python-dotenv = "^1.0.0"
tomli = "^2.0.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
black = "^24.0.0"
ruff = "^0.3.0"

[tool.poetry.scripts]
jpxbt = "jpxbt.cli:app"
```

---

## Key Principles

1. **Deterministic**: Same inputs → Same outputs (no randomness)
2. **Minimal**: Only evaluation logic, no data fetching or model training
3. **Transparent**: Clear logging of all actions and decisions
4. **Testable**: Unit tests for all core components
5. **Extensible**: Easy to add new cost models or execution rules

---

## Non-Goals (Explicitly Excluded)

- ❌ Data collection (J-Quants API integration for backtesting)
- ❌ Feature engineering
- ❌ Model training or inference
- ❌ Look-ahead bias detection
- ❌ Overnight position handling
- ❌ Alternative execution modes (VWAP, Close→Open, etc.)

---

## Questions for Clarification

Before starting development, confirm:

1. Should J-Quants API be used ONLY for data fetching, or also for validation?
2. Should the engine support multiple strategies in a single run?
3. What should happen if `top_k + bottom_k > available_stocks`?
4. Should transaction costs be configurable per market (e.g., different for Prime vs Growth)?

---

## Deliverables Checklist

- [ ] Functional CLI (`jpxbt run`)
- [ ] Example predictions.parquet + strategy.toml
- [ ] Unit tests (>80% coverage for engine/)
- [ ] README.md with installation & usage
- [ ] SUBMISSION_GUIDE.md for users
- [ ] .gitignore (includes runs/, .env)
- [ ] pyproject.toml with all dependencies

---

## Success Criteria

✅ Run `jpxbt run` with sample data → produces valid result.json
✅ All unit tests pass
✅ Clear error messages for invalid inputs
✅ JSON output matches schema
✅ No silent failures

---

## Additional Notes

- Use `pandas.Timestamp` for all date operations (avoid datetime.datetime)
- Store all intermediate results in memory (no temporary files)
- Log execution time for performance monitoring
- Consider adding `--verbose` flag for detailed logging

---

**Ready to start development? This guide should give you everything needed to build a production-ready backtesting engine. Good luck!**
