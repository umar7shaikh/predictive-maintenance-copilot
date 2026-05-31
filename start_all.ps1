# One-command launcher for the Predictive Maintenance Copilot.
# Opens each long-running server in its own window so you can read logs and
# Ctrl+C them individually. Postgres + Redis are Windows services (auto-start).
#
#   Run:        .\start_all.ps1            (backend + frontend + mlflow)
#   With Celery: .\start_all.ps1 -Celery   (also starts the Celery worker)
param([switch]$Celery)

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$celeryExe = Join-Path $backend ".venv\Scripts\celery.exe"
$mlflowExe = Join-Path $backend ".venv\Scripts\mlflow.exe"

function Start-Window($title, $workdir, $command) {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle='$title'; Set-Location '$workdir'; $command"
    )
    Write-Host "  started: $title"
}

Write-Host "Ensuring Postgres + Redis services are running..."
foreach ($svc in @("postgresql-x64-18", "Redis")) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s -and $s.Status -ne "Running") {
        try { Start-Service $svc; Write-Host "  started service: $svc" }
        catch { Write-Host "  NOTE: could not start $svc (may need admin): $($_.Exception.Message)" }
    } elseif ($s) { Write-Host "  ok: $svc already running" }
    else { Write-Host "  NOTE: service $svc not found" }
}

Write-Host "`nLaunching app services..."
Start-Window "PdM Backend"  $backend  "& '$py' -m uvicorn app.main:app --port 8000"
Start-Window "PdM Frontend" $frontend "npm run dev"
Start-Window "PdM MLflow"   $backend  "& '$mlflowExe' server --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000"
if ($Celery) {
    Start-Window "PdM Celery" $backend "& '$celeryExe' -A app.worker.celery_app worker --loglevel=info --pool=solo"
}

Write-Host "`nAll set. Give them ~10s, then open:"
Write-Host "  App     -> http://localhost:5173"
Write-Host "  API     -> http://localhost:8000/docs"
Write-Host "  MLflow  -> http://localhost:5000"
Write-Host "`nStop everything with:  .\stop_all.ps1"
