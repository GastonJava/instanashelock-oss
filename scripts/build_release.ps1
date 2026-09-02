# Build standalone release with Nuitka
$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot
$venv = Join-Path $root ".venv\Scripts\Activate.ps1"
$python = Join-Path $root ".venv\Scripts\python.exe"
$flagsFile = Join-Path $root "packaging\nuitka_flags.txt"
$entry = Join-Path $root "src\vault_app"
$icon = Join-Path $root "assets\app\instanashelock.ico"

if (-not (Test-Path $venv) -or -not (Test-Path $python)) {
    throw "No encontre .venv listo para build. Instala dependencias antes de correr este script."
}

if (-not (Test-Path $flagsFile)) {
    throw "No encontre packaging\\nuitka_flags.txt."
}

if (-not (Test-Path -LiteralPath $entry -PathType Container)) {
    throw "No encontre el paquete ejecutable src\\vault_app."
}

& $venv
Set-Location $root
$env:PYTHONPATH = Join-Path $root "src"
$env:NUITKA_CACHE_DIR = Join-Path $root ".nuitka-cache"

$nuitkaArgs = Get-Content $flagsFile |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith("#") }
$nuitkaArgs += "--assume-yes-for-downloads"

if (-not (Test-Path $icon)) {
    Write-Host "assets\\app\\instanashelock.ico no existe. Voy a compilar la build local sin icono Windows." -ForegroundColor Yellow
    $nuitkaArgs = $nuitkaArgs | Where-Object { -not $_.StartsWith("--windows-icon-from-ico=") }
}

$nuitkaArgs += $entry

Write-Host "Building with Nuitka..." -ForegroundColor Cyan
& $python -m nuitka @nuitkaArgs
$nuitkaExit = $LASTEXITCODE
if ($nuitkaExit -ne 0) {
    throw "Nuitka fallo con codigo de salida $nuitkaExit. No se genero una release valida."
}

$buildOutputCandidates = @(
    (Join-Path $root "dist\__main__.dist"),
    (Join-Path $root "dist\vault_app.dist")
)
$buildOutputCandidates = @(
    $buildOutputCandidates |
        Where-Object { Test-Path -LiteralPath $_ -PathType Container }
)

if ($buildOutputCandidates.Count -gt 1) {
    throw "Nuitka genero multiples carpetas .dist candidatas; limpia dist/ y reintenta."
}

$normalizedOutput = Join-Path $root "dist\instanashelock.dist"
if ($buildOutputCandidates.Count -eq 1) {
    $buildOutput = $buildOutputCandidates[0]
    if (Test-Path $normalizedOutput) {
        Remove-Item -LiteralPath $normalizedOutput -Recurse -Force
    }
    Move-Item -LiteralPath $buildOutput -Destination $normalizedOutput
}

$expectedExe = Join-Path $normalizedOutput "instanashelock.exe"
if (-not (Test-Path -LiteralPath $expectedExe -PathType Leaf)) {
    throw "La compilacion termino sin el ejecutable esperado en dist\\instanashelock.dist."
}

$buildCacheCandidates = @(
    (Join-Path $root "dist\__main__.build"),
    (Join-Path $root "dist\vault_app.build")
)
$buildCacheCandidates = @(
    $buildCacheCandidates |
        Where-Object { Test-Path -LiteralPath $_ -PathType Container }
)

if ($buildCacheCandidates.Count -gt 1) {
    throw "Nuitka genero multiples carpetas .build candidatas; limpia dist/ y reintenta."
}

$normalizedBuildCache = Join-Path $root "dist\instanashelock.build"
if ($buildCacheCandidates.Count -eq 1) {
    $buildCache = $buildCacheCandidates[0]
    if (Test-Path $normalizedBuildCache) {
        Remove-Item -LiteralPath $normalizedBuildCache -Recurse -Force
    }
    Move-Item -LiteralPath $buildCache -Destination $normalizedBuildCache
}

Write-Host ""
Write-Host "Build complete. Output in dist/" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Compile installer:  iscc packaging\installer.iss"
Write-Host "  2. Sign binaries later (optional / deferred): .\packaging\sign_release.ps1"


