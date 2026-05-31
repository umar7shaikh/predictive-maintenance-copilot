# Start the MLflow tracking server + UI at http://localhost:5000
# backed by the local ./mlruns file store. Run from the backend/ directory.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\mlflow.exe server `
    --backend-store-uri "./mlruns" `
    --host 127.0.0.1 --port 5000
