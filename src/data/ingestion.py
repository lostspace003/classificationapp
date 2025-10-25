"""Data ingestion utilities for the Bank Marketing dataset."""

from __future__ import annotations

import pandas as pd

from src.config.settings import RAW_DATA_PATH


def load_raw_dataset() -> pd.DataFrame:
    """Load the raw Bank Marketing CSV file into a DataFrame."""
    dataset = pd.read_csv(RAW_DATA_PATH, sep=";")
    return dataset

