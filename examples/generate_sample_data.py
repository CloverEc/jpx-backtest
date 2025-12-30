"""Generate sample predictions.parquet for testing the backtest engine."""

import pandas as pd
import numpy as np
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Parameters
num_stocks = 50
num_days = 20
start_date = "2024-01-04"

# Generate dates (business days only)
dates = pd.bdate_range(start=start_date, periods=num_days)

# Stock codes (5-digit JPX format)
stock_codes = [f"{1000 + i:05d}" for i in range(num_stocks)]

# Market categories
markets = ["プライム", "グロース", "スタンダード"]
market_weights = [0.6, 0.2, 0.2]

# Generate data
data = []

for date in dates:
    for code in stock_codes:
        # Random market assignment
        market = np.random.choice(markets, p=market_weights)

        # Random opening price (1000-5000 JPY)
        open_price = np.random.uniform(1000, 5000)

        # Random return (-3% to +3%)
        daily_return = np.random.uniform(-0.03, 0.03)
        close_price = open_price * (1 + daily_return)

        # Prediction score (correlated with actual return + noise)
        # Add some predictive power
        prediction = daily_return + np.random.normal(0, 0.02)

        data.append({
            "Date": date,
            "Code": code,
            "Prediction": prediction,
            "Open": round(open_price, 2),
            "Close": round(close_price, 2),
            "MarketCodeName": market,
        })

# Create DataFrame
df = pd.DataFrame(data)

# Save to parquet
output_path = Path(__file__).parent / "submission_sample" / "predictions.parquet"
output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(output_path, index=False)

print(f"Generated sample predictions.parquet with {len(df):,} records")
print(f"Saved to: {output_path}")
print()
print("Summary:")
print(f"  Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
print(f"  Unique stocks: {df['Code'].nunique()}")
print(f"  Trading days: {df['Date'].nunique()}")
print(f"  Markets: {df['MarketCodeName'].value_counts().to_dict()}")
