@echo off
REM Taeglicher Paper-Trading-Bericht nach US-Boersenschluss.
REM Liest echte Alpaca-Positionen, gruppiert nach Segmenten, sendet Telegram.
cd /d "C:\Users\HP\Documents\Claude\alpaca-trader"
"C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe" portfolio.py --telegram >> "C:\Users\HP\Documents\Claude\alpaca-trader\daily.log" 2>&1
