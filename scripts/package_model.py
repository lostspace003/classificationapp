"""Create a distributable archive of the trained MLflow model."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from src.config.settings import MODEL_DIR


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("dist"),
    help="Directory to place the packaged model archive.",
)
def main(output_dir: Path) -> None:
    model_path = MODEL_DIR / "bank_marketing_model"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Expected model directory at {model_path}. Run scripts/train_model.py first."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "bank_marketing_model"
    shutil.make_archive(str(archive_path), "zip", root_dir=model_path)
    click.echo(f"Packaged model at {archive_path}.zip")


if __name__ == "__main__":
    main()
