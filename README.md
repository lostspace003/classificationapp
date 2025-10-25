# Bank Marketing MLOps Demo

End-to-end classification workflow that predicts whether a banking customer will subscribe to a term deposit. The project demonstrates local experimentation with MLflow, feature engineering, hyperparameter tuning, a FastAPI inference service, packaging, and deployment guidance to Azure App Service.

## Tech Stack

- Python 3.11+
- Pandas, NumPy, scikit-learn
- MLflow (latest release)
- FastAPI + Uvicorn
- Azure App Service (Linux, Basic B1)

## Dataset

- Source: [UCI Bank Marketing Dataset](https://archive.ics.uci.edu/ml/datasets/Bank+Marketing)
- Raw CSV downloaded to `data/raw/bank-full.csv` on first setup.
- Target: `y` (`yes` / `no`) indicates subscription outcome.

## Repository Layout

```
data/
├── raw/                # downloaded source data
└── processed/          # (available for generated intermediate data)
src/
├── config/             # path constants
├── data/               # ingestion & cleaning helpers
├── features/           # preprocessing & engineered features
├── pipelines/          # high-level orchestration
├── training/           # model training + MLflow logging
└── utils/              # MLflow configuration
app/
├── __init__.py
├── main.py             # FastAPI inference service
└── templates/index.html
scripts/
├── train_model.py      # CLI entry point for full pipeline
├── package_model.py    # zip model artifacts for deployment
├── run_api.py          # run FastAPI locally with Uvicorn
└── setup_model.py      # download/extract model artifacts (used in App Service)
azure/
├── deploy.ps1 / deploy.sh  # convenience provisioning scripts
├── Dockerfile & entrypoint.sh
└── startup.txt         # App Service startup command sequence
docs/
└── azure_app_service.md    # detailed cloud deployment instructions
requirements.txt
README.md
```

## Getting Started Locally

1. **Create a virtual environment**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Download the dataset**  
   Already placed in `data/raw/bank-full.csv`. If you need to refresh it, rerun:

   ```powershell
   Invoke-WebRequest -Uri https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank.zip -OutFile data/raw/bank.zip
   Expand-Archive data/raw/bank.zip -DestinationPath data/raw -Force
   ```

3. **Train and log the model**

   ```powershell
   python -m scripts.train_model --experiment-name bank_marketing_classification
   ```

   This command:

   - Cleans the raw data (`src/data/cleaning.py`).
   - Engineers helper features (`src/features/engineering.py`).
   - Builds a scikit-learn pipeline (scaling + one-hot encoding + logistic regression).
   - Performs 5-fold cross-validated grid search on `C`.
   - Evaluates on a hold-out set, logging metrics/plots to MLflow.
   - Saves the model in `models/bank_marketing_model`.

4. **Inspect MLflow UI**

   ```powershell
   mlflow ui --backend-store-uri ./mlruns --host 0.0.0.0 --port 5000
   ```

   Visit `http://localhost:5000` to compare runs, params, and artifacts (confusion matrix, evaluation CSV, model pickles).

5. **Package the model for deployment**

   ```powershell
   python -m scripts.package_model --output-dir dist
   ```

   Produces `dist/bank_marketing_model.zip`, which contains the MLflow model directory structure.

## Serving the Model Locally

1. Ensure the trained model exists (`models/bank_marketing_model`).
2. Run the API:

   ```powershell
   uvicorn app.main:app --reload
   ```

3. Browse to `http://127.0.0.1:8000/` to use the HTML form or send JSON to `POST /predict`.

   Request example:

   ```json
   {
     "age": 45,
     "job": "admin.",
     "marital": "married",
     "education": "secondary",
     "default": "no",
     "balance": 600,
     "housing": "yes",
     "loan": "no",
     "contact": "cellular",
     "day": 15,
     "month": "may",
     "duration": 210,
     "campaign": 1,
     "pdays": 999,
     "previous": 0,
     "poutcome": "unknown"
   }
   ```

   The index page is built with Tailwind CSS via CDN and includes an inline LLM-generated hero illustration—no additional build tooling or asset hosting required.

## Automated Scripts

- `scripts/train_model.py` – run full training + MLflow logging.
- `scripts/package_model.py` – create deployable archive.
- `scripts/setup_model.py` – download/extract model artifacts into `model/bank_marketing_model` given `MODEL_URI`.
- `scripts/run_api.py` – convenience wrapper around Uvicorn.

## Azure Deployment Overview

- Provision azure resources via command: 
  powershell -ExecutionPolicy Bypass -File .\azure\deploy.ps1
  or 
  `azure/deploy.sh`.
- Upload `models/bank_marketing_model` (directory or packaged zip) to Azure Blob Storage (instructions in `docs/azure_app_service.md`).
- Configure App Service application settings:
  - `MODEL_URI` – HTTPS SAS URL (or `wasbs://`) pointing to the zipped model.
  - `MODEL_LOCAL_PATH` – local destination (`/home/site/wwwroot/model/bank_marketing_model`).
  - `MLFLOW_TRACKING_URI` – `file:/home/site/wwwroot/mlruns` or remote tracking URI.
  - `PYTHONPATH` – `/home/site/wwwroot`.
- Deploy code via Zip Deploy or container image. The provided `azure/startup.txt` installs dependencies, downloads the model using `scripts/setup_model.py`, and launches Gunicorn with Uvicorn workers.
- Full step-by-step instructions, including SAS token generation, Application Insights integration, and MLflow monitoring options, are documented in `docs/azure_app_service.md`.

## Monitoring & Ops

- MLflow records experiment metadata, metrics, and artifacts.
- `evaluation.csv` artifact includes row-level predictions for deeper analysis.
- For production, enable Application Insights on the App Service and forward FastAPI logs.
- Schedule periodic re-training by triggering `scripts/train_model.py` via Azure Pipelines/GitHub Actions, then repackage and redeploy.

## Next Steps

1. Automate CI/CD with GitHub Actions (train, evaluate, package, deploy).
2. Introduce data drift monitoring (e.g., Evidently or custom analytics).
3. Expand hyperparameter search (Bayesian or randomized search) and compare models (e.g., gradient boosted trees).
4. Integrate Azure Machine Learning for managed MLflow tracking and model registry.

---

**Dataset License:** UCI datasets are free for research/education. Review original terms before production use.  
**Security:** Store SAS tokens/keys in Azure Key Vault or GitHub secrets—never commit secrets to source control.
