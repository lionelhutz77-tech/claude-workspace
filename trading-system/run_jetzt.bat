@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\HP\Documents\Claude\trading-system"

echo ============================================================
echo  Trading Intelligence System -- MANUELLER START
echo  Ausgabe erscheint direkt im Fenster
echo  Telegram-Bericht kommt am Ende automatisch
echo ============================================================
echo.

call venv\Scripts\activate.bat
python main.py

echo.
echo ============================================================
echo  FERTIG. Drücke eine Taste zum Schliessen.
echo ============================================================
pause
