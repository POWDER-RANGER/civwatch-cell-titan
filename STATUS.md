# CELL TITAN — operational status

**Version:** 0.1.0
**Updated:** 2026-10-03
**Upstream:** [CivilianIntelligence](https://github.com/POWDER-RANGER/CivilianIntelligence)

## Baseline (this release)

- [x] FastAPI service with `/api/health`
- [x] Hash-chained evidence log (`titan/evidence.py`)
- [x] Sensor registry + optional ADB discovery
- [x] Four RF domains with demo telemetry
- [x] Operator dashboard (`static/index.html`)
- [x] Pytest coverage for chain + buffer
- [x] README aligned with CIVINTELLIGENCE

## Next

- [ ] Live cellular/Wi-Fi dumps via ADB shell (device-bound)
- [ ] Postgres/SQLite event store (replace pure JSONL for query)
- [ ] WebSocket live feed for the dashboard
- [ ] Publish evidence digests into CIVINTELLIGENCE Veil (optional)

## Runbook

```bash
./launch.sh
pytest -q
curl -s localhost:8000/api/status | jq .
```
