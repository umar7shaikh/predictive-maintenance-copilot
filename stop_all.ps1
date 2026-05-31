# Stop the app services started by start_all.ps1 (backend, frontend, mlflow, celery).
# Leaves the Postgres + Redis Windows services running.
$ErrorActionPreference = "Continue"

# Kill whatever is listening on the app ports.
foreach ($port in @(8000, 5173, 5000)) {
    $conns = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop; Write-Host "stopped process on :$port" }
        catch {}
    }
}

# Stop any Celery worker (no fixed port — match by command line).
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "celery" } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force; Write-Host "stopped celery worker (pid $($_.ProcessId))" } catch {} }

Write-Host "Done. (Postgres + Redis services left running.)"
