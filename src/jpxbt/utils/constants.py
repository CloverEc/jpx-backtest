"""Constants used throughout the backtesting engine."""

# Trading constraints
LOT_SIZE = 100  # JPX standard lot size (shares)

# Required columns in predictions.parquet
REQUIRED_PREDICTION_COLUMNS = [
    "Date",
    "Code",
    "Prediction",
    "Open",
    "Close",
    "MarketCodeName",
]

# Optional columns in predictions.parquet
OPTIONAL_PREDICTION_COLUMNS = [
    "Shortable",  # bool: Whether the stock can be shorted (default: True if not present)
]

# Column name for shortable flag
COL_SHORTABLE = "Shortable"

# Trade sides
SIDE_LONG = "LONG"
SIDE_SHORT = "SHORT"

# Annual trading days for Sharpe ratio calculation
ANNUAL_TRADING_DAYS = 252
