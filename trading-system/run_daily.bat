@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\HP\Documents\Claude\trading-system"

:: Seit 27.09.2026 laeuft das Trading-System ausschliesslich in der Cloud
:: (GitHub Actions, daily_trading.yml). Ein lokaler Lauf wuerde einen zweiten,
:: abweichenden Depotstand erzeugen. Deshalb holt dieser Task nur noch den
:: Cloud-Stand auf den PC. Fuer einen bewussten lokalen Testlauf: python main.py
if not exist logs mkdir logs
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATUM=%%I
echo [%LOGDATUM%] Cloud-Betrieb: lokaler Lauf deaktiviert, hole Cloud-Stand. >> logs\lokal_task.log
venv\Scripts\python.exe cloud_daten_holen.py >> logs\lokal_task.log 2>&1
