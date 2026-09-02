param(
    [string]$PythonPath = ""
)

# Short alias for reproducible local validation.
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run_local_ci.ps1") -PythonPath $PythonPath
