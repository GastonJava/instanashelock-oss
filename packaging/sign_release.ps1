# Authenticode signing template
# Requires:
#   - Windows SDK (signtool.exe)
#   - A code signing certificate (.pfx on USB token, or in cert store)
#
# Where to get a certificate:
#   - Free/cheap: Certum Open Source Code Signing, SignPath Foundation
#   - Paid: DigiCert, Sectigo, GlobalSign
#
# IMPORTANT: The signing key must NEVER be in the repo.
#            Store it on a hardware token (USB) or cloud HSM.
#
# Why sign?
#   - Windows SmartScreen trusts signed binaries
#   - Antivirus/EDR is less likely to flag signed executables
#   - Users can verify the publisher and that the binary was not tampered with

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot

$exe      = Join-Path $root "dist\instanashelock.dist\instanashelock.exe"
$installer = Join-Path $root "dist\Instanashelock_Setup_1.0.0.exe"

# Sign the main executable
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a $exe

# Sign the installer
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a $installer

Write-Host "Signing complete." -ForegroundColor Green
