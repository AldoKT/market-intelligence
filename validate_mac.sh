#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/research"

python3 -m pip install -r requirements-validation.txt

python3 signal_validation_v1.py \
  --timeline-v02 "data/cross_stock_timeline_v0_2_all.csv" \
  --timeline-v031 "data/cross_stock_timeline_v0_3_1.csv" \
  --episodes-v031 "data/investigation_episodes_v0_3_1.csv" \
  --universe "data/signal_universe_v0_3.csv" \
  --engine "signal_engine_v0_3_1.py" \
  --detector "signal_detector_v0_2.py" \
  --cross-stock-summary "data/cross_stock_summary_v0_2_all.csv" \
  --payload-dir "../payloads/demo_2026-09-09" \
  --snapshot-date "2026-09-09" \
  --outdir "../validation_recheck"

echo "Validation complete."
echo "Report: $ROOT/validation_recheck/VALIDATION_REPORT.md"
