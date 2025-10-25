"""High-level training pipeline orchestration."""

from __future__ import annotations
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from src.data.cleaning import clean_dataset
from src.data.ingestion import load_raw_dataset
from src.training.train import train_and_log


def run_training_pipeline(
    experiment_name: str = "bank_marketing_classification",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Entry point to train the model and return metrics."""
    dataset = clean_dataset(load_raw_dataset())

    # 🔧 Fix pd.NA → np.nan and integer dtype issue
    dataset = dataset.replace({pd.NA: np.nan})
    int_cols = dataset.select_dtypes(include="Int64").columns
    if len(int_cols) > 0:
        dataset[int_cols] = dataset[int_cols].astype("float64")

    model, metrics = train_and_log(dataset, experiment_name=experiment_name)
    return dataset, metrics
