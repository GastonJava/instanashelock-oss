param(
    [switch]$reset
)

$ErrorActionPreference = "Stop"

if ($reset) {
    & (Join-Path $PSScriptRoot "scripts\launch_dev_smoke.ps1") -ResetSession
    exit
}

& (Join-Path $PSScriptRoot "scripts\launch_dev_smoke.ps1")
