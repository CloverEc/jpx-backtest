#!/bin/bash
# Example: Run backtest with sample data

# Make sure the package is installed first:
# pip install -e .

jpxbt run \
  --predictions examples/submission_sample/predictions.parquet \
  --strategy examples/submission_sample/strategy.toml \
  --output runs/result_001

# View results
echo ""
echo "Results saved to runs/result_001/"
echo "  - result.json"
echo "  - trades.parquet"
echo "  - daily_summary.csv"
