$ErrorActionPreference = "Stop"
$activate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $activate)) { throw "No encontre la .venv del proyecto en $activate" }
& $activate
