# Launch the built app against an isolated Windows profile for manual smoke tests.
param(
    [switch]$ResetSession
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $root "dist\instanashelock.dist\instanashelock.exe"
$sessionRoot = Join-Path $root "dist\smoke_session"
$localAppData = Join-Path $sessionRoot "LOCALAPPDATA"
$appData = Join-Path $sessionRoot "APPDATA"
$legacyVaultDir = Join-Path $appData "Vault"
$canonicalVaultDir = Join-Path $localAppData "Instanashelock"

if (-not (Test-Path -LiteralPath $exe)) {
    throw "No encontre la build candidata en '$exe'. Corre .\scripts\build.ps1 primero."
}

if ($ResetSession -and (Test-Path -LiteralPath $sessionRoot)) {
    Remove-Item -LiteralPath $sessionRoot -Recurse -Force
}

foreach ($dir in @($sessionRoot, $localAppData, $appData, $legacyVaultDir, $canonicalVaultDir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.WorkingDirectory = Split-Path -Parent $exe
$psi.UseShellExecute = $false
$psi.EnvironmentVariables["LOCALAPPDATA"] = $localAppData
$psi.EnvironmentVariables["APPDATA"] = $appData

[System.Diagnostics.Process]::Start($psi) | Out-Null

Write-Host "Smoke-test session launched." -ForegroundColor Green
Write-Host "Executable:      $exe"
Write-Host "Session root:    $sessionRoot"
Write-Host "LOCALAPPDATA:    $localAppData"
Write-Host "APPDATA:         $appData"
Write-Host "Legacy vault dir $legacyVaultDir"
Write-Host "Canonical dir:   $canonicalVaultDir"
Write-Host ""
Write-Host "Tip: use -ResetSession to start from a clean smoke-test profile."
