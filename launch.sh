#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt -q
mkdir -p data/evidence
export SENSOR_ID="${SENSOR_ID:-civwatch-titan-local}"
export HOST="${HOST:-127.0.0.1}"
echo "CELL TITAN v0.1.2 → http://${HOST}:${PORT:-8000}"
echo "  default bind is loopback; set TITAN_API_TOKEN before any LAN exposure"
echo "  docs  /docs   health /api/health   live /ws/live"
exec python3 -m uvicorn main:app --host "${HOST}" --port "${PORT:-8000}" --reload
