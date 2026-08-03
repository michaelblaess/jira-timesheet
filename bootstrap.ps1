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

# Corporate-Proxy (Corporate-Proxy/EON): uv soll den Windows-Zertifikatspeicher nutzen,
# in dem die "EON Internal Root CA" liegt - sonst scheitern HTTPS-Downloads an
# "invalid peer certificate: UnknownIssuer".
$env:UV_SYSTEM_CERTS = "1"
# SSL_CERT_FILE wuerde uv ein von rustls abgelehntes Bundle aufzwingen und
# die System-Zertifikate aushebeln - daher fuer die uv-Aufrufe in diesem Skript leeren.
$env:SSL_CERT_FILE = $null
# Kein Python herunterladen - lokal installiertes Python verwenden.
$env:UV_PYTHON_DOWNLOADS = "never"

Write-Host "=== jira-timesheet - dev environment ===" -ForegroundColor Cyan

# --inexact: laesst zusaetzlich installierte Pakete (v.a. das ad-hoc via Schritt
# 2 installierte Nuitka) in Ruhe. Ohne den Flag pruned uv sync die venv auf die
# Lock-Deps zurueck und wirft Nuitka jedes Mal raus - danach muss Schritt 2 es
# neu holen, was hinter dem Corporate-Proxy-Proxy an pypi.org scheitert.
Write-Host "[1/2] venv + dependencies (uv sync)..."
uv sync --extra dev --inexact --python 3.13
if ($LASTEXITCODE -ne 0) { throw "uv sync fehlgeschlagen" }

# Nuitka NUR fuer compile-*.ps1 noetig, nicht zum Ausfuehren der App. Wenn der
# Proxy pypi blockt (os error 10061) oder Nuitka schon da ist, darf das die
# Einrichtung NICHT abbrechen - sonst kann man die App nicht mal starten.
Write-Host "[2/2] Nuitka build tool (nur fuer compile-*.ps1)..."
uv pip install nuitka
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warnung: Nuitka konnte nicht installiert werden (Netz/Proxy?)." -ForegroundColor Yellow
    Write-Host "Die App laeuft trotzdem - Nuitka wird nur zum Kompilieren gebraucht." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Start with: .\run.ps1" -ForegroundColor Green
