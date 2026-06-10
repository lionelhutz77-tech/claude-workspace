@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\HP\Documents\Claude\trading-system"

:: Warte 2 Minuten damit Netzwerk nach PC-Start/Anmeldung bereit ist
ping -n 121 127.0.0.1 >nul

:: Datum fuer Log-Dateiname (format: JJJJ-MM-TT) -- PowerShell (WMIC deprecated auf Windows 11)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATUM=%%I

:: Schutz: Wenn der Task heute schon gelaufen ist, nicht nochmal starten
:: (verhindert Doppellauf wenn 08:00-Trigger + Anmelde-Trigger gleichzeitig aktiv)
if exist "logs\run_%LOGDATUM%.log" (
    echo [%LOGDATUM%] Task heute bereits ausgefuehrt -- wird uebersprungen.
    exit /b 0
)

call venv\Scripts\activate.bat
echo [%LOGDATUM%] Trading Intelligence System startet... >> logs\run_%LOGDATUM%.log
python main.py >> logs\run_%LOGDATUM%.log 2>&1
echo [%LOGDATUM%] Abgeschlossen. >> logs\run_%LOGDATUM%.log
