"""Download and unpack model artifacts specified by MODEL_URI."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import click
import requests
from azure.storage.blob import BlobClient

DEFAULT_TARGET_DIR = Path("model")


def _download_http(uri: str, destination: Path) -> Path:
    response = requests.get(uri, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def _download_blob(uri: str, destination: Path) -> Path:
    blob_client = BlobClient.from_blob_url(uri)
    with destination.open("wb") as file_obj:
        data = blob_client.download_blob()
        file_obj.write(data.readall())
    return destination


def _extract_if_needed(archive_path: Path, target_dir: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)
    else:
        raise ValueError(f"Unsupported archive type: {archive_path}")


def _copy_directory(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


@click.command()
@click.option(
    "--target-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_TARGET_DIR,
    help="Directory where the model will be stored.",
)
@click.option(
    "--model-uri",
    default=None,
    help="Optional model URI override. Defaults to MODEL_URI environment variable.",
)
def main(target_dir: Path, model_uri: Optional[str]) -> None:
    uri = model_uri or os.environ.get("MODEL_URI")
    if not uri:
        click.echo("MODEL_URI not provided; skipping download.")
        return

    target_dir = target_dir.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    if uri.startswith(("http://", "https://")):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / "model.zip"
            _download_http(uri, archive_path)
            _extract_if_needed(archive_path, target_dir)
    elif uri.startswith("wasbs://"):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / "model.zip"
            _download_blob(uri, archive_path)
            _extract_if_needed(archive_path, target_dir)
    else:
        source_path = Path(uri).resolve()
        if source_path.is_dir():
            _copy_directory(source_path, target_dir)
        elif source_path.suffix == ".zip":
            _extract_if_needed(source_path, target_dir)
        else:
            raise FileNotFoundError(f"Unsupported MODEL_URI path: {uri}")

    click.echo(f"Model available at {target_dir}")


if __name__ == "__main__":
    main()
