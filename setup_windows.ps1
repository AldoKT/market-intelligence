$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "====================================" -ForegroundColor Magenta
Write-Host " SIGNAL Complete Project v1 - Setup " -ForegroundColor Magenta
Write-Host "====================================" -ForegroundColor Magenta
Write-Host ""

Write-Host "[1/2] Installing backend dependencies..."
Set-Location "$Root\backend"
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "[2/2] Installing frontend dependencies..."
Set-Location "$Root\frontend"
npm install

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run: .\run_demo_windows.ps1"
