# CELL TITAN v0.1.0 — Public operational release

**Date:** 2026-10-03  
**Tag suggestion:** `v0.1.0`

## Highlights

- Full FastAPI service with OpenAPI at `/docs`
- Hash-chained evidence log (`titan/evidence.py`) with verify + tail
- Demo telemetry across cellular, Wi-Fi, D2D, transport (no hardware required)
- Optional ADB sensor discovery and cellular/Wi-Fi dump capture
- WebSocket live stream at `/ws/live`
- Operator dashboard at `/`
- 11 automated tests + GitHub Actions CI
- SECURITY.md, CONTRIBUTING.md, CHANGELOG.md, MIT license

## Run

```bash
pip install -r requirements.txt
./launch.sh
# http://127.0.0.1:8000
```

## Verify

```bash
pytest -q
curl -s localhost:8000/api/health
curl -s -X POST localhost:8000/api/telemetry/demo?count=4
curl -s localhost:8000/api/evidence/verify
```

## Tag on GitHub

```bash
git tag -a v0.1.0 -m "CELL TITAN public operational release"
git push origin v0.1.0
# Then create a Release from the tag in the GitHub UI
```
