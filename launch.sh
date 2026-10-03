#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt -q
mkdir -p data/evidence
export SENSOR_ID="${SENSOR_ID:-civwatch-titan-local}"
echo "CELL TITAN → http://127.0.0.1:8000  (docs: /docs  health: /api/health)"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
