"""Utility helpers for configuring MLflow tracking."""

from __future__ import annotations

from typing import Optional

import mlflow

from src.config.settings import MLFLOW_DIR


def configure_mlflow(tracking_uri: Optional[str] = None) -> None:
    """Configure the MLflow tracking URI, defaulting to the local mlruns directory."""
    uri = tracking_uri or MLFLOW_DIR.as_uri()
    mlflow.set_tracking_uri(uri)
    MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
