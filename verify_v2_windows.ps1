$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "" 
Write-Host "=== SIGNAL v2.1 Verification ===" -ForegroundColor Magenta

Write-Host "[1/2] Backend tests..." -ForegroundColor Cyan
Set-Location "$Root\backend"
python -m pytest -q

Write-Host "" 
Write-Host "[2/2] Frontend production build..." -ForegroundColor Cyan
Set-Location "$Root\frontend"
npm run build

Write-Host "" 
Write-Host "Verification complete." -ForegroundColor Green
