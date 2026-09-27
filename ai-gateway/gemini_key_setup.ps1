$ErrorActionPreference = "Stop"

$geminiDir = Join-Path $PSScriptRoot ".gemini-home\.gemini"
New-Item -ItemType Directory -Path $geminiDir -Force | Out-Null

Write-Host "Gemini-API-Schluessel einfuegen. Die Eingabe bleibt unsichtbar."
$secureKey = Read-Host "API-Schluessel" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "Es wurde kein API-Schluessel eingegeben."
    }
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $geminiDir ".env"), "GEMINI_API_KEY=$plainKey`n", $utf8WithoutBom)
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
}

Write-Host "Gespeichert: nur im isolierten, von Git ausgeschlossenen Gemini-Profil."
Write-Host "Dieses Fenster kann jetzt geschlossen werden."
