# Bank Marketing MLOps Demo (Direct-Use API)

End-to-end classification workflow that predicts whether a banking customer will subscribe to a term deposit.  
This fork removes the login flow: the predictor UI is available at **`/app`**, and the **`/predict`** API can be called directly.

The API **engineers helper features at inference time** (so your JSON only needs the raw fields).

---

## Tech Stack

- Python 3.11+
- Pandas, NumPy, scikit-learn
- MLflow (latest)
- FastAPI + Uvicorn (served with Gunicorn in Azure)
- Azure App Service (Linux, Basic B1)

---

## Project Layout (high level)

```
data/                 # raw dataset provided
models/               # trained MLflow model (created by training)
dist/                 # packaged model zip (created by packaging)
src/                  # config, data, features, training pipeline
app/                  # FastAPI app (main.py + templates)
scripts/              # CLI: train, package, setup_model, run_api
azure/                # Dockerfile, entrypoint, startup.txt, deploy scripts
requirements.txt
```

Key bits:
- **`app/main.py`** exposes:
  - `GET /` → marketing landing page
  - `GET /app` → predictor dashboard (no auth)
  - `POST /predict` → scoring endpoint (Pydantic schema below)
- **`src/features/engineering.py`** defines engineered columns used by the model.  
  The API **applies this automatically** before prediction.
- **`scripts/setup_model.py`** downloads/extracts a model when `MODEL_URI` is set (HTTP/HTTPS/Azure Blob/local path/zip).

---

## Local: setup, train, package, serve

```powershell
# 1) env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# 2) train (logs to ./mlruns; saves model to ./models/bank_marketing_model)
python -m scripts.train_model --experiment-name bank_marketing_classification

# 3) package (creates dist/bank_marketing_model.zip)
python -m scripts.package_model --output-dir dist

# 4) serve locally (expects model in ./models/bank_marketing_model)
uvicorn app.main:app --reload

# UI
#   http://127.0.0.1:8000/app
# API docs
#   http://127.0.0.1:8000/docs
```

**JSON request for `/predict`:**
```json
{
  "age": 42,
  "job": "blue-collar",
  "marital": "married",
  "education": "secondary",
  "default": "no",
  "balance": 1500,
  "housing": "yes",
  "loan": "no",
  "contact": "cellular",
  "day": 15,
  "month": "may",
  "duration": 180,
  "campaign": 2,
  "pdays": 999,
  "previous": 0,
  "poutcome": "unknown"
}
```
The service engineers these features internally: `log_duration`, `log_campaign`, `is_balance_positive`, `has_previous_contact`.

---

## Quick Deploy to **Azure App Service** (step‑by‑step)

**Prereqs**
- Azure CLI logged in: `az login`
- You ran: `powershell -ExecutionPolicy Bypass -File .\azure\deploy.ps1`  
  (creates Resource Group, Linux Plan, Web App, Storage account + container)

**Defaults used by the scripts (change if you used custom names):**
```powershell
$rg = "rg-bank-marketing"
$st = "stbankmarketing"
$app = "bank-marketing-api"
$container = "models"
```

### 1) Upload the model to Azure Blob Storage

```powershell
# From the mlops folder (where dist\bank_marketing_model.zip exists)
$CONN = az storage account show-connection-string `--name $st --resource-group $rg --query connectionString -o tsv

az storage blob upload --connection-string $CONN --container-name $container --file dist\bank_marketing_model.zip --name bank_marketing_model.zip
```

Generate a short‑lived SAS and construct the model URL:
```powershell
$SAS = az storage blob generate-sas --connection-string $CONN --container-name $container --name bank_marketing_model.zip --permissions r --expiry (Get-Date).AddDays(7).ToString("yyyy-MM-dd") -o tsv

$MODEL_URL = "https://$st.blob.core.windows.net/$container/bank_marketing_model.zip?$SAS"
```

### 2) App settings (point the Web App to the model)

```powershell
az webapp config appsettings set -g $rg -n $app --settings MODEL_URI="$MODEL_URL" WEBSITES_PORT=8000 SCM_DO_BUILD_DURING_DEPLOYMENT=trueMLFLOW_TRACKING_URI="file:/home/site/wwwroot/mlruns"
```

### 3) Zip‑deploy the code

```powershell
Remove-Item app.zip -ErrorAction Ignore
Compress-Archive -Path `
  app,src,scripts,azure,requirements.txt `
  -DestinationPath app.zip -Force

# New deploy command (extension)
az webapp deploy -g $rg -n $app --src-path .\app.zip --type zip

# If the above isn't available:
# az webapp deployment source config-zip -g $rg -n $app --src .\app.zip
```

### 4) Startup command and restart

```powershell
# Runs: pip install -> downloads model -> gunicorn uvicorn worker
az webapp config set -g $rg -n $app --startup-file "bash azure/startup.txt"
az webapp restart -g $rg -n $app
```

### 5) Verify

```powershell
az webapp browse -g $rg -n $app
# UI:    https://{app}.azurewebsites.net/app
# Docs:  https://{app}.azurewebsites.net/docs
```

### Logs / Troubleshooting

```powershell
az webapp log config -g $rg -n $app --application-logging true
az webapp log tail -g $rg -n $app
```

Common fixes:
- **500 "Model not available"** → Ensure `MODEL_URI` is set and SAS not expired, restart after updating settings.
- **502/timeout** → Confirm `WEBSITES_PORT=8000`, startup command set, and Python dep install finished.
- **403 when fetching model** → SAS expired or container/permissions mismatch; recreate SAS and update `MODEL_URI`.
- **Wrong predictions / 500 "columns are missing"** → Ensure you deployed the patched app (this fork engineers features inside `/predict`).

---

## Configuration

| Setting                | Purpose                                                   | Default / Example                                           |
|------------------------|-----------------------------------------------------------|-------------------------------------------------------------|
| `MODEL_URI`            | Remote/Local URI to **zip or directory** with MLflow model. Supports HTTPS & Azure Blob. | `https://stbankmarketing.blob.core.windows.net/models/bank_marketing_model.zip?...` |
| `MODEL_LOCAL_PATH`     | Where the model is placed inside the app container.       | `model/bank_marketing_model`                                |
| `MLFLOW_TRACKING_URI`  | Where MLflow logs (for the app).                          | `file:/home/site/wwwroot/mlruns`                            |
| `WEBSITES_PORT`        | Port to listen on in Azure App Service (Linux).           | `8000`                                                      |
| `PYTHONPATH`           | Optional module path.                                     | `/home/site/wwwroot`                                        |

---

## API Summary

- **POST `/predict`** → returns `{{ "probability": float, "prediction": 0|1 }}`  
  Request fields: `age, job, marital, education, default, balance, housing, loan, contact, day, month, duration, campaign, pdays, previous, poutcome`.
- **GET `/app`** → browser UI to submit a form and see the prediction.
- **GET `/docs`** → interactive OpenAPI docs.

---

## Notes & Next Steps

- To make `/` go straight to the predictor, change the index route to return `render_dashboard_html()` or add a redirect in `app/main.py`.
- CI/CD: Use GitHub Actions to run `train_model` → evaluate → `package_model` → upload to Blob → update `MODEL_URI` → zip‑deploy.
- Consider storing secrets (SAS, connection strings) in Azure Key Vault and referencing them from App Settings.

---

**Dataset:** UCI Bank Marketing – for research/education.  
**Security:** Never commit secrets. Rotate SAS regularly.
