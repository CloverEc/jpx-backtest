# JPX Backtest Engine (Open→Close Evaluator)

## Purpose
This repository provides a **minimal, deterministic backtesting engine** for Japanese equities.

The engine is designed as a **pure evaluator**, similar to a Kaggle evaluation server:

- It does **not** generate predictions
- It does **not** fetch data
- It does **not** train models
- It **only evaluates** submitted predictions under fixed trading rules

The primary goal is **fair comparison of strategies or models** under identical execution conditions.

---

## Scope

### ✅ Included
- Ranking stocks by prediction score
- Portfolio construction (Top / Bottom K)
- Capital allocation with unit-lot constraints (100 shares)
- Execution at **Open → Close**
- Transaction cost handling
- PnL aggregation
- Result export (JSON, trades, daily summary)
- CLI interface

### ❌ Explicitly Excluded
- Data collection (e.g. J-Quants API)
- Feature engineering
- Model training or inference
- Look-ahead or leakage validation
- Overnight or multi-day positions
- Execution timing variants

This engine assumes **all predictions are valid and pre-generated**.

---

## Trading Rule (Fixed)

- **Entry price**: Open
- **Exit price**: Close
- **Holding period**: Same trading day only
- No overnight positions
- No execution mode switching

Even if a strategy conceptually spans days,  
the engine always evaluates **Open → Close only**.

---

## Inputs

### 1. predictions.parquet

Required columns:

| Column | Description |
|------|------------|
| Date | Trading date |
| Code | Stock code (5-digit JPX format) |
| Prediction | Higher = more bullish |
| Open | Opening price |
| Close | Closing price |
| MarketCodeName | Market category |

Extra columns are ignored.

---

### 2. strategy.toml

```toml
[strategy]
name = "ridge_ls_v1"

top_k = 10
min_k = 1
leverage = 3.3
lot_size = 100
cost_bps = 2.0

ban_long_markets = ["グロース", "スタンダード"]
ban_short_markets = ["グロース", "スタンダード"]

