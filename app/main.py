"""FastAPI app for serving the trained MLflow model."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from src.features.engineering import engineer_features

from src.config.settings import MODEL_DIR


app = FastAPI(title="Bank Marketing Classifier", version="1.0.0")


class CustomerFeatures(BaseModel):
    age: int
    job: str
    marital: str
    education: str
    default: str
    balance: float
    housing: str
    loan: str
    contact: str
    day: int
    month: str
    duration: int
    campaign: int
    pdays: int
    previous: int
    poutcome: str


def _load_model() -> Any:
    candidates = []

    env_local = os.getenv("MODEL_LOCAL_PATH")
    if env_local:
        candidates.append(Path(env_local))

    env_uri = os.getenv("MODEL_URI")
    if env_uri:
        candidates.append(env_uri)

    candidates.extend(
        [
            Path("model/bank_marketing_model"),
            Path("model"),
            MODEL_DIR / "bank_marketing_model",
        ]
    )

    last_exception: Exception | None = None
    for candidate in candidates:
        try:
            if isinstance(candidate, Path):
                if candidate.is_dir():
                    return mlflow.sklearn.load_model(candidate.as_posix())
                if candidate.exists():
                    return mlflow.sklearn.load_model(str(candidate))
            else:
                return mlflow.sklearn.load_model(candidate)
        except Exception as exc:  # pylint: disable=broad-except
            last_exception = exc
            continue
    raise HTTPException(
        status_code=500,
        detail=f"Model could not be loaded. Last error: {last_exception}",
    )


def render_index_html() -> str:
    index_path = Path(__file__).parent / "templates" / "index.html"
    if not index_path.exists():
        return "<html><body><h1>Bank Marketing Classifier</h1><p>Index page missing.</p></body></html>"
    return index_path.read_text(encoding="utf-8")


model_instance = None


@app.on_event("startup")
def load_model_on_startup() -> None:
    global model_instance  # pylint: disable=global-statement
    model_instance = _load_model()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return render_index_html()


@app.get("/app", response_class=HTMLResponse)
def app_page() -> str:
    return render_dashboard_html()


@app.post("/predict")
def predict(payload: CustomerFeatures) -> Dict[str, Any]:
    if model_instance is None:
        raise HTTPException(status_code=500, detail="Model not available.")
    data_frame = pd.DataFrame([payload.model_dump()])
    data_frame = engineer_features(data_frame)
    prediction_proba = float(model_instance.predict_proba(data_frame)[0][1])
    prediction_label = int(prediction_proba >= 0.5)
    return {
        "probability": prediction_proba,
        "prediction": prediction_label,
    }

def render_dashboard_html() -> str:
    dashboard_path = Path(__file__).parent / "templates" / "dashboard.html"
    if not dashboard_path.exists():
        return "<html><body><h1>Predictor</h1><p>Dashboard page missing.</p></body></html>"
    return dashboard_path.read_text(encoding="utf-8")
