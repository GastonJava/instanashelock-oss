# Dot-source this file to expose convenient repo-local commands, including venv activation.
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$global:InstanashelockRepoRoot = $repoRoot

function global:va {
    $activate = Join-Path $global:InstanashelockRepoRoot ".venv\Scripts\Activate.ps1"
    if (-not (Test-Path $activate)) {
        throw "No encontre la .venv del proyecto en $activate"
    }

    & $activate

    $pathParts = $env:PATH -split [System.IO.Path]::PathSeparator
    if ($pathParts -notcontains $global:InstanashelockRepoRoot) {
        $env:PATH = "$global:InstanashelockRepoRoot$([System.IO.Path]::PathSeparator)$env:PATH"
    }

    Write-Host "Entorno virtual de Instanashelock activado." -ForegroundColor Green
}
$pathParts = $env:PATH -split [System.IO.Path]::PathSeparator
if ($pathParts -notcontains $repoRoot) {
    $env:PATH = "$repoRoot$([System.IO.Path]::PathSeparator)$env:PATH"
}

Write-Host "Project commands enabled in this shell: va, run, runv2, runsm" -ForegroundColor Green
Write-Host "  va             -> activa la .venv del proyecto" -ForegroundColor DarkGray
Write-Host "  run            -> dev normal (v1)" -ForegroundColor DarkGray
Write-Host "  runv2          -> unlock slice QML (v2)" -ForegroundColor DarkGray
Write-Host "  runsm          -> dev smoke session aislada" -ForegroundColor DarkGray
Write-Host "  runsm -reset   -> reinicia la smoke session aislada" -ForegroundColor DarkGray
