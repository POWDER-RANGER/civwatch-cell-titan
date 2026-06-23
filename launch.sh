#!/bin/bash
set -e
echo "🚀 CIVWATCH CELL TITAN - Live RF Observability"
pip install -r requirements.txt --quiet
echo "🌐 Starting..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload