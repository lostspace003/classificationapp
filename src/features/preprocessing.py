"""Feature engineering helpers for preprocessing the dataset."""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.features.engineering import engineer_features

TARGET_COL = "y"
CATEGORICAL_COLS: List[str] = [
    "job",
    "marital",
    "education",
    "default",
    "housing",
    "loan",
    "contact",
    "month",
    "poutcome",
]
ORDINAL_COLS: List[str] = []
NUMERIC_COLS: List[str] = [
    "age",
    "balance",
    "day",
    "duration",
    "campaign",
    "pdays",
    "previous",
    "log_campaign",
    "log_duration",
    "is_balance_positive",
    "has_previous_contact",
]


def build_preprocessing_pipeline() -> ColumnTransformer:
    """Create the preprocessing pipeline with scaling and encoding."""
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_COLS),
            ("categorical", categorical_pipeline, CATEGORICAL_COLS),
        ]
    )
    return preprocessor


def split_features_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Split the target column from the feature set."""
    features = engineer_features(df.drop(columns=[TARGET_COL]))
    target = df[TARGET_COL].map({"yes": 1, "no": 0})
    return features, target
