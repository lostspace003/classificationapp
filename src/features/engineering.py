"""Feature engineering transformations applied prior to model training."""

from __future__ import annotations

import numpy as np
import pandas as pd


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create domain-inspired helper columns."""
    engineered = df.copy()
    engineered["is_balance_positive"] = (engineered["balance"] > 0).astype(int)
    engineered["log_campaign"] = np.log1p(engineered["campaign"])
    engineered["log_duration"] = np.log1p(engineered["duration"])
    engineered["has_previous_contact"] = (engineered["previous"] > 0).astype(int)
    return engineered

