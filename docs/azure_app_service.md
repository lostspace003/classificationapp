# Azure App Service Deployment Guide

This walkthrough describes how to deploy the FastAPI inference service and MLflow-tracked model to Azure App Service on a **Basic B1** plan. It assumes you have already trained the model locally, inspected the MLflow run, and archived the model with `scripts/package_model.py`.

## Prerequisites

- Azure subscription with permission to create resource groups, storage, and App Service plans.
- Azure CLI 2.53+ (`az version` to confirm).
- Docker (optional) if you prefer container-based deployment.
- Local Python environment with project dependencies installed.

Login to Azure first:

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

## 1. Create Azure resources

```powershell
$resourceGroup = "rg-bank-marketing"
$location = "westeurope"
$planName = "asp-bank-marketing"
$appName = "bank-marketing-api-<unique>"

az group create --name $resourceGroup --location $location
az appservice plan create `
    --name $planName `
    --resource-group $resourceGroup `
    --location $location `
    --sku B1 `
    --is-linux
az webapp create `
    --name $appName `
    --plan $planName `
    --resource-group $resourceGroup `
    --runtime "PYTHON:3.11"
```

> 🔁 Replace `<unique>` with a globally unique suffix (web app hostnames are unique).

## 2. Provision storage for model artifacts

You need a persistent location to host the MLflow model files. Options:

1. **Azure Blob Storage** – simple, inexpensive.
2. **Azure File Share** – allows mounting via `WEBSITE_CONTENTSHARE`.
3. **Azure Machine Learning model registry** – if you operate an Azure ML workspace.

For most App Service deployments, Blob Storage is the most direct:

```powershell
$storageAccount = "stbankmarketing<unique>"
$container = "models"

az storage account create `
    --name $storageAccount `
    --resource-group $resourceGroup `
    --location $location `
    --sku Standard_LRS `
    --kind StorageV2

$connectionString = az storage account show-connection-string `
    --name $storageAccount `
    --resource-group $resourceGroup `
    --query connectionString -o tsv

az storage container create --name $container --connection-string $connectionString
```

Upload the zipped model archive produced by `scripts/package_model.py`:

```powershell
az storage blob upload `
    --container-name $container `
    --file dist/bank_marketing_model.zip `
    --name bank_marketing_model.zip `
    --connection-string $connectionString

$expiry = (Get-Date).AddYears(1).ToString("yyyy-MM-ddTHH:mmZ")
$sasToken = az storage blob generate-sas `
    --container-name $container `
    --name bank_marketing_model.zip `
    --permissions r `
    --expiry $expiry `
    --connection-string $connectionString `
    -o tsv
```

During application startup, the model artifact will be downloaded and extracted to `/home/site/wwwroot/model`.

## 3. Configure application settings

Set environment variables required for the FastAPI app:

```powershell
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings `
        MODEL_URI="https://$storageAccount.blob.core.windows.net/$container/bank_marketing_model.zip?$sasToken" `
        MODEL_LOCAL_PATH="/home/site/wwwroot/model/bank_marketing_model" `
        MLFLOW_TRACKING_URI="file:/home/site/wwwroot/mlruns" `
        PYTHONPATH="/home/site/wwwroot"
```

If you use SAS tokens for storage, append `?{sas_token}` to `MODEL_URI`.

### Optional: connect to remote MLflow tracking server

If you stand up a managed MLflow server (e.g., Azure Machine Learning, Databricks, or MLflow on Azure Storage), update `MLFLOW_TRACKING_URI` to the remote endpoint and provide credentials via environment variables or Azure Managed Identity.

## 4. Deploy application code

### Option A – Zip Deploy

```powershell
$buildDir = "build"
Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $buildDir | Out-Null
Copy-Item -Path app,src,scripts,requirements.txt -Destination $buildDir -Recurse
Copy-Item dist\\bank_marketing_model.zip $buildDir\\model.zip
Compress-Archive -Path $buildDir\\* -DestinationPath webapp.zip -Force

az webapp deployment source config-zip `
    --resource-group $resourceGroup `
    --name $appName `
    --src webapp.zip
```

Add a `startup.txt` file in the archive containing:

```
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/setup_model.py --target-dir model/bank_marketing_model
gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 app.main:app
```

and configure App Service to use it:

```powershell
az webapp config set --resource-group $resourceGroup --name $appName --startup-file "startup.txt"
```

### Option B – Container deploy

1. Build a container image (Dockerfile provided at `azure/Dockerfile`).
2. Push to Azure Container Registry.
3. Configure the Web App to pull the image.

Container deployment allows more control over system dependencies and is recommended when serving large models.

## 5. Add MLflow tracking dashboard

App Service does not natively host MLflow UI, but you can:

- Run MLflow tracking server locally linked to the same storage account (`mlruns` directory).
- Deploy MLflow UI as a separate container in Azure Container Apps or Azure Kubernetes Service.
- Use Azure Machine Learning workspace, which exposes experiment tracking and model registry through Azure portal.

To launch a local MLflow UI that points to the remote artifact store:

```powershell
mlflow server `
    --backend-store-uri sqlite:///mlflow.db `
    --default-artifact-root wasbs://$container@$storageAccount.blob.core.windows.net/ `
    --host 0.0.0.0 --port 5000
```

Ensure the network and authentication settings for the storage account allow access (e.g., SAS token or account key).

## 6. Monitoring and alerting

- Enable Application Insights (`az monitor app-insights component create`) and link it using `az webapp insights connect`.
- Configure custom logs for prediction requests. Extend `app/main.py` to emit structured logs (JSON) and send them to Log Analytics.
- Set up alert rules on key metrics (HTTP 5xx count, latency, CPU).
- Use MLflow model comparison to detect drift; schedule periodic re-training and redeployment steps using Azure Pipelines, GitHub Actions, or Azure ML jobs.

## 7. Continuous Integration / Delivery

- Add a GitHub Actions workflow that runs the training pipeline (optional), executes tests, packages the model, uploads artifacts to storage, and deploys via `az webapp up` or zip deploy.
- Store sensitive configuration (storage keys, SAS tokens) in GitHub secrets and surface them as environment variables within the workflow.

## Next Steps

1. Parameterise the deployment scripts (PowerShell + Bash).
2. Add Infrastructure-as-Code for repeatable environment setup (Bicep or Terraform).
3. Integrate Azure ML for advanced experiment tracking, model registry, and managed online endpoints if you outgrow App Service.
