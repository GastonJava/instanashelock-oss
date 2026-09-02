param(
    [string]$PythonPath = ""
)

# Regenerate the dependency inventory/SBOM and run the live dependency audit.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = $PythonPath
if (-not $python) {
    $python = Join-Path $root ".venv\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment not found at '$python'. Create .venv and install requirements\audit.txt first."
}

Push-Location $root
try {
    & $python .\scripts\generate_dependency_report.py
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency inventory generation failed with exit code $LASTEXITCODE."
    }

    & $python -m pip_audit -r requirements\audit.txt
    if ($LASTEXITCODE -ne 0) {
        throw "pip-audit failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
