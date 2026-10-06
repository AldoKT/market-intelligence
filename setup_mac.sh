#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "===================================="
echo " SIGNAL UI Contract Project v2.0 - Setup "
echo "===================================="
echo ""

echo "[1/2] Installing backend dependencies..."
cd "$ROOT/backend"
python3 -m pip install -r requirements.txt

echo ""
echo "[2/2] Installing frontend dependencies..."
cd "$ROOT/frontend"
npm install

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo ""
echo "Setup complete."
echo "Run: ./run_demo_mac.sh"
