#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP=${RESOURCE_GROUP:-rg-bank-marketing}
LOCATION=${LOCATION:-westeurope}
PLAN_NAME=${PLAN_NAME:-asp-bank-marketing}
APP_NAME=${APP_NAME:-bank-marketing-api}
STORAGE_ACCOUNT=${STORAGE_ACCOUNT:-stbankmarketing}
CONTAINER=${CONTAINER:-models}

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
az appservice plan create \
  --name "$PLAN_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku B1 \
  --is-linux
az webapp create \
  --name "$APP_NAME" \
  --plan "$PLAN_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --runtime "PYTHON:3.11"

az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

CONNECTION_STRING=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query connectionString -o tsv)

az storage container create --name "$CONTAINER" --connection-string "$CONNECTION_STRING"

echo "Upload your model artifact with:" >&2
echo "az storage blob upload-batch --destination $CONTAINER --source models/bank_marketing_model --connection-string $CONNECTION_STRING" >&2
