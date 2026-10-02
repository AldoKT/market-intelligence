#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PAYLOAD="$ROOT/payloads/latest_2026-09-29"

osascript -e "tell application \"Terminal\" to do script \"cd '$BACKEND'; export SIGNAL_PAYLOAD_DIR='$PAYLOAD'; python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000\""
sleep 2
osascript -e "tell application \"Terminal\" to do script \"cd '$FRONTEND'; npm run dev\""

echo "Latest snapshot: 29 Sep 2026"
echo "Frontend: http://127.0.0.1:5173"
