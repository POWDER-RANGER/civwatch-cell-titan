#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt -q
mkdir -p data/evidence
export SENSOR_ID="${SENSOR_ID:-civwatch-titan-local}"
export AUTO_DEMO="${AUTO_DEMO:-false}"
echo "CELL TITAN v0.1.0 → http://127.0.0.1:${PORT:-8000}"
echo "  docs  /docs   health /api/health   live /ws/live"
exec python3 -m uvicorn main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --reload
