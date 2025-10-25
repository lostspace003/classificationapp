# ASCII Architecture Diagrams

```
BANK MARKETING API — RUNTIME (INFERENCE) FLOW
==============================================================

        +--------------------+         +-----------------------------+
        |  Browser / User    |-------> |  GET /app (dashboard UI)   |
        +--------------------+         +-----------------------------+
                    |
                    |  POST /predict  (JSON body: age, job, marital, education,
                    |                   default, balance, housing, loan, contact,
                    |                   day, month, duration, campaign, pdays,
                    |                   previous, poutcome)
                    v
   +--------------------------------------------------------------------------+
   | FastAPI app (app/main.py)  — served by Gunicorn/Uvicorn on port 8000     |
   | (Azure App Service — Linux B1)                                            |
   +--------------------------------------------------------------------------+
                    |  Pydantic validation
                    v
   +-----------------------------------+
   | Feature Engineering (at inference)|
   |  src/features/engineering.py      |
   |   - log_duration                  |
   |   - log_campaign                  |
   |   - is_balance_positive           |
   |   - has_previous_contact          |
   +-----------------------------------+
                    |
                    v
   +-----------------------------------+
   | MLflow Model (scikit-learn)       |
   |  MODEL_LOCAL_PATH                  |
   +-----------------------------------+
                    |
                    v
   +-----------------------------------+
   | JSON Response                     |
   |  { "probability": float,          |
   |    "prediction": 0 | 1 }          |
   +-----------------------------------+
                    |
                    +--> (optional) MLflow logs → file:/home/site/wwwroot/mlruns

STARTUP ON AZURE APP SERVICE
----------------------------
[Container start]
   -> run bash azure/startup.txt
      -> pip install deps
      -> scripts/setup_model.py
            • Fetch model from MODEL_URI (HTTPS/Azure Blob, zip or dir)
            • Extract to MODEL_LOCAL_PATH
      -> launch gunicorn/uvicorn (WEBSITES_PORT=8000)

Key env:
  MODEL_URI, MODEL_LOCAL_PATH, MLFLOW_TRACKING_URI, WEBSITES_PORT, PYTHONPATH
```

```
CI/CD & MODEL ARTIFACT FLOW
==============================================================

   (Offline ML loop)                                      (App runtime)
   ------------------                                     -------------
   +-----------------------+         +------------------+
   | scripts.train_model   |         |  dist/.zip       |
   |  → models/...         |  -----> |  (packaged via   |
   +-----------------------+         |  scripts.package)|
                                     +------------------+
                                                |
                                                |  az storage blob upload (models container)
                                                v
                                         +-----------------------------+
                                         |  Azure Blob Storage         |
                                         |  container: models          |
                                         |  bank_marketing_model.zip   |
                                         +-----------------------------+
                                                |
                                                |  MODEL_URI (SAS URL) in App Settings
                                                v
 Developer push                                +------------------------------------+
 ---------->  GitHub repo (main)  -----------> |  GitHub Actions Workflow           |
                                               |  build: setup-python, upload       |
                                               |  deploy: azure/login (OIDC),       |
                                               |          azure/webapps-deploy      |
                                               +------------------+-----------------+
                                                                  |
                                                                  v
                                                         +-----------------------+
                                                         |  Azure App Service    |
                                                         |  (Linux, Python 3.11) |
                                                         +----------+------------+
                                                                    |
                                                                    | startup.txt
                                                                    v
                                                         +-----------------------+
                                                         | setup_model.py pulls  |
                                                         | MODEL_URI → extract   |
                                                         | → start Gunicorn      |
                                                         +-----------------------+
                                                                    |
                                                                    v
                                                         https://{app}.azurewebsites.net
                                                             /app (UI)   /docs (OpenAPI)
```
