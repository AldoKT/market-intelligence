#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PAYLOAD="$ROOT/payloads/demo_2026-09-09"

echo "Starting SIGNAL v2.3 Historical Demo — 09 Sep 2026"
echo "No Sectors API calls are made."

osascript -e "tell application \"Terminal\" to do script \"cd '$BACKEND'; export SIGNAL_PAYLOAD_DIR='$PAYLOAD'; python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000\""
sleep 2
osascript -e "tell application \"Terminal\" to do script \"cd '$FRONTEND'; npm run dev\""

echo "Frontend: http://127.0.0.1:5173"
echo "API docs: http://127.0.0.1:8000/docs"
