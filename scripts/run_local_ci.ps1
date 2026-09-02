param(
    [string]$PythonPath = ""
)

# Reproducible local validation for Instanashelock.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = $PythonPath
if (-not $python) {
    $python = Join-Path $root ".venv\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment not found at '$python'. Create .venv and install requirements\audit.txt first."
}

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage Exit code: $LASTEXITCODE"
    }
}

Push-Location $root
try {
    Write-Host "Checking generated assets..." -ForegroundColor Cyan
    Invoke-PythonChecked -Arguments @("scripts\generate_assets.py", "--check") -FailureMessage "Asset check failed."

    Write-Host "Checking Markdown links..." -ForegroundColor Cyan
    Invoke-PythonChecked -Arguments @("scripts\check_markdown_links.py") -FailureMessage "Markdown link check failed."

    Write-Host "Running pytest..." -ForegroundColor Cyan
    Invoke-PythonChecked -Arguments @("-m", "pytest", "-q") -FailureMessage "pytest failed."

    Write-Host "Compiling Python sources and tests..." -ForegroundColor Cyan
    Invoke-PythonChecked -Arguments @("-m", "compileall", "-q", "src", "tests", "scripts") -FailureMessage "compileall failed."

    Write-Host "Checking runtime hygiene (no print/logging in app runtime)..." -ForegroundColor Cyan
    $matches = Get-ChildItem -LiteralPath (Join-Path $root "src") -Recurse -File |
        Select-String -Pattern '(^|[^A-Za-z0-9_])print\(|logging\.'

    if ($matches) {
        $details = ($matches | ForEach-Object { "$($_.Path):$($_.LineNumber)" }) -join [Environment]::NewLine
        throw "Runtime hygiene check failed. Matches found:$([Environment]::NewLine)$details"
    }

    Write-Host "Auditing declared dependencies..." -ForegroundColor Cyan
    Invoke-PythonChecked -Arguments @("-m", "pip_audit", "-r", "requirements\audit.txt") -FailureMessage "pip-audit failed."

    Write-Host ""
    Write-Host "Local CI checks passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
