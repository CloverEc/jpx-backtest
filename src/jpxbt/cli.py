"""CLI interface for JPX Backtest Engine."""

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from .io.readers import load_predictions, load_strategy
from .io.writers import export_results, print_summary
from .engine.evaluator import Evaluator

app = typer.Typer(
    name="jpxbt",
    help="JPX Backtest Engine - Deterministic backtesting for Japanese equities",
    add_completion=False,
)


@app.command()
def run(
    predictions: Annotated[
        Path,
        typer.Option(
            "--predictions",
            "-p",
            help="Path to predictions.parquet file",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    strategy: Annotated[
        Path,
        typer.Option(
            "--strategy",
            "-s",
            help="Path to strategy.toml file",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for results",
        ),
    ],
    initial_capital: Annotated[
        float,
        typer.Option(
            "--capital",
            "-c",
            help="Initial capital in JPY",
        ),
    ] = 10_000_000.0,
    no_trades: Annotated[
        bool,
        typer.Option(
            "--no-trades",
            help="Skip exporting trades.parquet",
        ),
    ] = False,
    no_csv: Annotated[
        bool,
        typer.Option(
            "--no-csv",
            help="Skip exporting daily_summary.csv",
        ),
    ] = False,
):
    """
    Run backtest on predictions with specified strategy.

    Example:
        jpxbt run -p data/predictions.parquet -s strategy.toml -o runs/result_001
    """
    try:
        # Load inputs
        typer.echo("Loading inputs...")
        predictions_df = load_predictions(predictions)
        strategy_config = load_strategy(strategy)

        typer.echo(f"Loaded {len(predictions_df):,} prediction records")
        typer.echo()

        # Run backtest
        evaluator = Evaluator(strategy_config, initial_capital)
        results = evaluator.run(predictions_df)

        # Print summary
        print_summary(results)

        # Export results
        export_results(
            results,
            output,
            export_trades=not no_trades,
            export_daily_csv=not no_csv,
        )

        typer.secho("✓ Backtest completed successfully!", fg=typer.colors.GREEN, bold=True)

    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information."""
    from . import __version__

    typer.echo(f"jpxbt version {__version__}")


if __name__ == "__main__":
    app()
