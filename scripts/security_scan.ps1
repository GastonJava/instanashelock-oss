param(
    [string]$GitleaksPath = "gitleaks"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$config = Join-Path $root ".gitleaks.toml"

if (-not (Test-Path -LiteralPath $config)) {
    throw "No se encontro .gitleaks.toml en la raiz del repositorio."
}

$scanner = Get-Command $GitleaksPath -ErrorAction SilentlyContinue
if (-not $scanner) {
    throw "No se encontro Gitleaks. Instalalo o pasa -GitleaksPath con la ruta al ejecutable."
}

Push-Location $root
try {
    Write-Host "Scanning current tree with redacted output..." -ForegroundColor Cyan
    & $scanner.Source dir . --config $config --redact=100 --no-banner --no-color --verbose
    $treeExit = $LASTEXITCODE

    Write-Host "Scanning all reachable Git history with redacted output..." -ForegroundColor Cyan
    & $scanner.Source git . --config $config --log-opts="--all --full-history" --redact=100 --no-banner --no-color --verbose
    $historyExit = $LASTEXITCODE

    if ($treeExit -ne 0 -or $historyExit -ne 0) {
        throw "Secret scan failed. Review only the redacted locations above."
    }

    Write-Host "Secret scan passed for the current tree and reachable history." -ForegroundColor Green
}
finally {
    Pop-Location
}
