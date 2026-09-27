$ErrorActionPreference = "Stop"
$env:GEMINI_CLI_HOME = Join-Path $PSScriptRoot ".gemini-home"
$authWorkdir = Join-Path $env:TEMP "lionel-gemini-auth"
New-Item -ItemType Directory -Path $authWorkdir -Force | Out-Null
Push-Location $authWorkdir
try {
    gemini
}
finally {
    Pop-Location
}
