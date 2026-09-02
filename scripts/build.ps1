# Short alias for local release build
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "build_release.ps1")
