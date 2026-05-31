# Start the Celery worker (Windows: solo pool). Requires Redis running on :6379.
# Run from the backend/ directory.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\celery.exe -A app.worker.celery_app worker --loglevel=info --pool=solo
