#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/research"

python3 -m pip install -r requirements-validation.txt

python3 signal_reaction_validation_v1.py \
  --timeline "data/cross_stock_timeline_v0_3_1.csv" \
  --outdir "../validation_recheck/reaction_v1" \
  --bootstrap-reps 10000

echo ""
echo "Reaction validation complete."
echo "Report: $ROOT/validation_recheck/reaction_v1/REACTION_VALIDATION_REPORT.md"
echo ""
echo "Note: full-universe validation is close-based because the derived timeline"
echo "does not retain daily high/low. Supply --raw-zip when raw OHLC is available."
