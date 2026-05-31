@echo off
REM Double-click this to stop the app services.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0stop_all.ps1"
