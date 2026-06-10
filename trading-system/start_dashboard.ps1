# Trading Intelligence System — Startup-Skript
# Wird beim PC-Start ausgefuehrt.
# Wartet bis die Analyse fertig ist, dann oeffnet das Dashboard im Browser.

$projektPfad = "C:\Users\HP\Documents\Claude\trading-system"
$dashboard   = "$projektPfad\output\dashboard_aktuell.html"
$logOrdner   = "$projektPfad\logs"

# 1. Sicherstellen dass der Task laeuft (falls noch nicht gestartet)
$taskName = "TradingIntelligenceSystem"
$taskStatus = (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State

if ($taskStatus -eq "Ready") {
    # Task hat noch nicht gelaufen heute — starten
    $letzterLauf = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
    $heute = (Get-Date).Date
    if ($letzterLauf -lt $heute) {
        Start-ScheduledTask -TaskName $taskName
        Write-Host "Trading-System gestartet..."
    }
}

# 2. Warten bis Analyse abgeschlossen (max. 15 Minuten)
$maxWartezeit = 900  # Sekunden
$gewartet     = 0
$intervall    = 15

Write-Host "Warte auf Analyse-Abschluss..."

while ($gewartet -lt $maxWartezeit) {
    Start-Sleep -Seconds $intervall
    $gewartet += $intervall

    # Pruefen ob heute eine neue Dashboard-Datei erstellt wurde
    if (Test-Path $dashboard) {
        $dashboardDatum = (Get-Item $dashboard).LastWriteTime
        if ($dashboardDatum -gt (Get-Date).Date) {
            Write-Host "Analyse fertig — oeffne Dashboard..."
            Start-Process $dashboard
            exit 0
        }
    }

    # Falls Task nicht mehr laeuft aber Dashboard existiert: oeffnen
    $aktuellerStatus = (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State
    if ($aktuellerStatus -eq "Ready" -and (Test-Path $dashboard)) {
        Write-Host "Task abgeschlossen — oeffne Dashboard..."
        Start-Process $dashboard
        exit 0
    }
}

# Fallback: Dashboard oeffnen auch wenn Timeout (zeigt letzten bekannten Stand)
if (Test-Path $dashboard) {
    Write-Host "Timeout — oeffne letztes verfuegbares Dashboard."
    Start-Process $dashboard
}
