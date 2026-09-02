# Launch the source app against an isolated Windows profile for manual local testing.
param(
    [switch]$ResetSession
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$src = Join-Path $root "src"
$sessionRoot = Join-Path $root "dist\dev_smoke_session"
$localAppData = Join-Path $sessionRoot "LOCALAPPDATA"
$appData = Join-Path $sessionRoot "APPDATA"
$legacyVaultDir = Join-Path $appData "Vault"
$canonicalVaultDir = Join-Path $localAppData "Instanashelock"

if (-not (Test-Path -LiteralPath $python)) {
    throw "No encontre el interprete en '$python'."
}

if ($ResetSession -and (Test-Path -LiteralPath $sessionRoot)) {
    Remove-Item -LiteralPath $sessionRoot -Recurse -Force
}

foreach ($dir in @($sessionRoot, $localAppData, $appData, $legacyVaultDir, $canonicalVaultDir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = "-m vault_app"
$psi.WorkingDirectory = $src
$psi.UseShellExecute = $false
$psi.EnvironmentVariables["PYTHONPATH"] = $src
$psi.EnvironmentVariables["LOCALAPPDATA"] = $localAppData
$psi.EnvironmentVariables["APPDATA"] = $appData

[System.Diagnostics.Process]::Start($psi) | Out-Null

Write-Host "Dev smoke session launched." -ForegroundColor Green
Write-Host "Python:          $python"
Write-Host "Working dir:     $src"
Write-Host "Session root:    $sessionRoot"
Write-Host "LOCALAPPDATA:    $localAppData"
Write-Host "APPDATA:         $appData"
Write-Host "Legacy vault dir $legacyVaultDir"
Write-Host "Canonical dir:   $canonicalVaultDir"
Write-Host ""
Write-Host "Tip: use -ResetSession to start from a clean dev smoke profile."
