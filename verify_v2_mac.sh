#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "=== SIGNAL v2.1 Verification ==="
cd "$ROOT/backend"
python3 -m pytest -q
cd "$ROOT/frontend"
npm run build
echo "Verification complete."
