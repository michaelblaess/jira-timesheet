#Requires -Version 5.1
<#
.SYNOPSIS
    Sets up the jira-timesheet development environment.

.DESCRIPTION
    Creates the .venv via uv, installs runtime + dev dependencies and the
    Nuitka build tool (for compile-win64.ps1). Run once after cloning the repo.
#>

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Corporate-Proxy (Zscaler/EON): uv soll den Windows-Zertifikatspeicher nutzen,
# in dem die "EON Internal Root CA" liegt - sonst scheitern HTTPS-Downloads an
# "invalid peer certificate: UnknownIssuer".
$env:UV_NATIVE_TLS = "1"
# SSL_CERT_FILE wuerde uv ein von rustls abgelehntes Bundle aufzwingen und
# native-tls aushebeln - daher fuer die uv-Aufrufe in diesem Skript leeren.
$env:SSL_CERT_FILE = $null
# Kein Python herunterladen - lokal installiertes 3.12 verwenden.
$env:UV_PYTHON_DOWNLOADS = "never"

Write-Host "=== jira-timesheet - dev environment ===" -ForegroundColor Cyan

Write-Host "[1/2] venv + dependencies (uv sync)..."
uv sync --extra dev --python 3.12
if ($LASTEXITCODE -ne 0) { throw "uv sync fehlgeschlagen" }

Write-Host "[2/2] Nuitka build tool..."
uv pip install nuitka
if ($LASTEXITCODE -ne 0) { throw "nuitka-Installation fehlgeschlagen" }

Write-Host ""
Write-Host "Done. Start with: .\run.ps1" -ForegroundColor Green
