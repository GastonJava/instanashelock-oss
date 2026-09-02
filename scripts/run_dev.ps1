# Run the app in development mode
$ErrorActionPreference = "Stop"

$venv = Join-Path $PSScriptRoot "..\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) { & $venv }

$src = Join-Path $PSScriptRoot "..\src"
Set-Location $src
python -m vault_app
