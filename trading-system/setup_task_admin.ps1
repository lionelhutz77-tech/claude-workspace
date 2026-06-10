# setup_task_admin.ps1
# Erstellt den Windows Task Scheduler Eintrag fuer das Trading Intelligence System.
# MUSS als Administrator ausgefuehrt werden!
#
# Trigger: 1. Taeglich 08:00 Uhr
#          2. Beim Anmelden des Benutzers (Fallback wenn PC um 08:00 nicht laeuft)
# Timeout: 3 Stunden (PT3H)

$taskName  = "TradingIntelligenceSystem"
$batPfad   = "C:\Users\HP\Documents\Claude\trading-system\run_daily.bat"
$benutzer  = "$env:USERDOMAIN\$env:USERNAME"
$startDir  = "C:\Users\HP\Documents\Claude\trading-system"

Write-Host "Loesche alten Task (falls vorhanden)..." -ForegroundColor Yellow
schtasks /delete /tn $taskName /f 2>$null | Out-Null

# XML mit ZWEI Triggern: taeglich 08:00 + beim Anmelden
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Trading Intelligence System - Taeglich 08:00 Analyse + Fallback bei Anmeldung</Description>
    <Author>$benutzer</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T08:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$benutzer</UserId>
      <Delay>PT2M</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$benutzer</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT3H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$batPfad</Command>
      <WorkingDirectory>$startDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# XML als UTF-16 Datei speichern (Pflicht fuer schtasks)
$xmlPfad = "$env:TEMP\trading_task.xml"
[System.IO.File]::WriteAllText($xmlPfad, $xml, [System.Text.Encoding]::Unicode)

# Task importieren
$result = schtasks /create /xml $xmlPfad /tn $taskName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "ERFOLGREICH: Task '$taskName' wurde erstellt." -ForegroundColor Green
    Write-Host ""
    Write-Host "Trigger:" -ForegroundColor Cyan
    Write-Host "  1. Taeglich 08:00 Uhr" -ForegroundColor Cyan
    Write-Host "  2. Beim Anmelden (2 Minuten nach Login)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Doppelschutz: MultipleInstancesPolicy=IgnoreNew" -ForegroundColor Gray
    Write-Host "  -> Laeuft er schon, startet er nicht nochmal." -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "FEHLER beim Erstellen des Tasks:" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    Write-Host ""
    Write-Host "Bitte als Administrator ausfuehren!" -ForegroundColor Yellow
}

# Aufraumen
Remove-Item $xmlPfad -Force -ErrorAction SilentlyContinue
