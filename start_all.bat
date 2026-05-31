@echo off
REM Double-click this to start all services (backend, frontend, mlflow).
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_all.ps1" %*
