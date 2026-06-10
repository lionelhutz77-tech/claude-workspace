@echo off
:: ============================================================
:: Trading Intelligence System - Task Scheduler Setup
:: EINMALIG ALS ADMINISTRATOR AUSFUEHREN:
::   Rechtsklick auf diese Datei -> "Als Administrator ausfuehren"
:: ============================================================

echo Trading Intelligence System - Task Scheduler Setup
echo ====================================================
echo Starte PowerShell-Setup (Admin erforderlich)...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0setup_task_admin.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [FEHLER] PowerShell-Script konnte nicht ausgefuehrt werden.
    echo Bitte diese Datei als Administrator ausfuehren:
    echo   Rechtsklick ^> "Als Administrator ausfuehren"
    pause
)
