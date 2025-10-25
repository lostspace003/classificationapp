"""Model training orchestration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, Tuple

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

from src.config.settings import MLFLOW_DIR, MODEL_DIR
from src.features.preprocessing import build_preprocessing_pipeline, split_features_target
from src.utils.mlflow_utils import configure_mlflow


def build_training_pipeline() -> Pipeline:
    """Compose the preprocessing and estimator pipeline."""
    preprocessor = build_preprocessing_pipeline()
    classifier = LogisticRegression(
        solver="lbfgs",
        max_iter=1000,
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", classifier),
        ]
    )
    return pipeline


def perform_hyperparameter_tuning(
    pipeline: Pipeline, X_train: pd.DataFrame, y_train: pd.Series
) -> GridSearchCV:
    """Execute grid search hyperparameter tuning."""
    param_grid = {
        "model__C": [0.1, 1.0, 10.0],
        "model__penalty": ["l2"],
    }
    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        scoring="roc_auc",
        n_jobs=-1,
        cv=5,
        verbose=2,
    )
    grid_search.fit(X_train, y_train)
    return grid_search


def evaluate_model(
    model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series
) -> Tuple[Dict[str, float], pd.Series, pd.Series]:
    """Run evaluation metrics on the test split."""
    predictions = pd.Series(model.predict(X_test), index=y_test.index, name="prediction")
    probabilities = pd.Series(
        model.predict_proba(X_test)[:, 1], index=y_test.index, name="probability"
    )
    report = classification_report(y_test, predictions, output_dict=True)
    auc = roc_auc_score(y_test, probabilities)
    metrics = {
        "test_precision": report["1"]["precision"],
        "test_recall": report["1"]["recall"],
        "test_f1": report["1"]["f1-score"],
        "test_auc": auc,
        "test_accuracy": report["accuracy"],
    }
    return metrics, predictions, probabilities


def train_and_log(
    dataset: pd.DataFrame,
    experiment_name: str = "bank_marketing_classification",
) -> Tuple[Pipeline, Dict[str, float]]:
    """Train the model, tune hyperparameters, log to MLflow, and return metrics."""
    configure_mlflow()
    mlflow.set_experiment(experiment_name)
    mlflow.sklearn.autolog(log_models=False)

    X, y = split_features_target(dataset)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    base_pipeline = build_training_pipeline()
    with mlflow.start_run(run_name="logistic_regression"):
        grid_search = perform_hyperparameter_tuning(base_pipeline, X_train, y_train)

        best_model = grid_search.best_estimator_
        metrics, predictions, probabilities = evaluate_model(best_model, X_test, y_test)

        mlflow.log_param("num_features", X_train.shape[1])
        mlflow.log_param("num_training_rows", X_train.shape[0])
        mlflow.log_param("num_test_rows", X_test.shape[0])
        mlflow.log_metric("cv_best_score", grid_search.best_score_)
        mlflow.log_params(grid_search.best_params_)
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)

        signature = infer_signature(X_train.head(), best_model.predict(X_train.head()))
        mlflow.sklearn.log_model(
            sk_model=best_model,
            artifact_path="model",
            registered_model_name="bank_marketing_model",
            signature=signature,
        )

        cm = confusion_matrix(y_test, predictions)
        disp = ConfusionMatrixDisplay(cm, display_labels=[0, 1])
        fig, ax = plt.subplots(figsize=(6, 6))
        disp.plot(ax=ax)
        ax.set_title("Confusion Matrix")
        plt.tight_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            fig_path = Path(tmpdir) / "confusion_matrix.png"
            fig.savefig(fig_path)
            mlflow.log_artifact(str(fig_path))
        plt.close(fig)

        evaluation_frame = pd.concat([y_test.rename("actual"), predictions, probabilities], axis=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_path = Path(tmpdir) / "evaluation.csv"
            evaluation_frame.to_csv(eval_path, index_label="row_id")
            mlflow.log_artifact(str(eval_path))

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODEL_DIR / "bank_marketing_model"
        mlflow.sklearn.save_model(best_model, path=str(model_path))

    return best_model, metrics
