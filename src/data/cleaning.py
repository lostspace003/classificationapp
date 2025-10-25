"""Data cleaning helpers prior to training."""

from __future__ import annotations

import pandas as pd

UNKNOWN_TOKEN = "unknown"


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Remove obvious issues and normalise string values."""
    cleaned = df.copy()
    # Replace UCI 'unknown' with pandas NA so imputers can handle them
    cleaned = cleaned.replace(UNKNOWN_TOKEN, pd.NA)
    # Ensure correct dtypes
    cleaned["y"] = cleaned["y"].astype(str).str.strip()
    return cleaned

