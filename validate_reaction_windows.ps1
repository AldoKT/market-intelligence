$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$Root\research"

python -m pip install -r requirements-validation.txt

python signal_reaction_validation_v1.py `
  --timeline "data\cross_stock_timeline_v0_3_1.csv" `
  --outdir "..\validation_recheck\reaction_v1" `
  --bootstrap-reps 10000

Write-Host ""
Write-Host "Reaction validation complete." -ForegroundColor Green
Write-Host "Report: $Root\validation_recheck\reaction_v1\REACTION_VALIDATION_REPORT.md"
Write-Host ""
Write-Host "Note: full-universe validation is close-based because the derived timeline"
Write-Host "does not retain daily high/low. Supply --raw-zip when raw OHLC is available."
