# Run the v2 unlock prototype in development mode
$ErrorActionPreference = "Stop"

$venv = Join-Path $PSScriptRoot "..\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) { & $venv }

$env:QT_QUICK_CONTROLS_STYLE = "Basic"

$src = Join-Path $PSScriptRoot "..\src"
Set-Location $src
python -m vault_app_v2
