param(
    [string]$ResourceGroup = "rg-bank-marketing",
    [string]$Location = "westeurope",
    [string]$PlanName = "asp-bank-marketing",
    [string]$AppName = "bank-marketing-api",
    [string]$StorageAccount = "stbankmarketing",
    [string]$Container = "models"
)

az group create --name $ResourceGroup --location $Location
az appservice plan create `
    --name $PlanName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku B1 `
    --is-linux
az webapp create `
    --name $AppName `
    --plan $PlanName `
    --resource-group $ResourceGroup `
    --runtime "PYTHON:3.11"

az storage account create `
    --name $StorageAccount `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2

$connectionString = az storage account show-connection-string `
    --name $StorageAccount `
    --resource-group $ResourceGroup `
    --query connectionString -o tsv

az storage container create --name $Container --connection-string $connectionString

Write-Host "Upload your model artifact with:" -ForegroundColor Cyan
Write-Host "az storage blob upload-batch --destination $Container --source models/bank_marketing_model --connection-string $connectionString" -ForegroundColor Yellow
