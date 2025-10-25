"""Command-line entry point to train and log the classification model."""

from __future__ import annotations

import click

from src.pipelines.train_pipeline import run_training_pipeline


@click.command()
@click.option("--experiment-name", default="bank_marketing_classification", help="MLflow experiment name.")
def main(experiment_name: str) -> None:
    _, metrics = run_training_pipeline(experiment_name=experiment_name)
    for name, value in metrics.items():
        click.echo(f"{name}: {value:.4f}")


if __name__ == "__main__":
    main()
