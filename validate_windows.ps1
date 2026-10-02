$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location "$Root\research"
python -m pip install -r requirements-validation.txt

python signal_validation_v1.py `
  --timeline-v02 "data\cross_stock_timeline_v0_2_all.csv" `
  --timeline-v031 "data\cross_stock_timeline_v0_3_1.csv" `
  --episodes-v031 "data\investigation_episodes_v0_3_1.csv" `
  --universe "data\signal_universe_v0_3.csv" `
  --engine "signal_engine_v0_3_1.py" `
  --detector "signal_detector_v0_2.py" `
  --cross-stock-summary "data\cross_stock_summary_v0_2_all.csv" `
  --payload-dir "..\payloads\demo_2026-09-09" `
  --snapshot-date "2026-09-09" `
  --outdir "..\validation_recheck"

Write-Host ""
Write-Host "Validation complete." -ForegroundColor Green
Write-Host "Report: $Root\validation_recheck\VALIDATION_REPORT.md"
