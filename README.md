# CIVWATCH CELL TITAN

**Defensive RF observability** — the sensing pillar of [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence).

Turn Android devices (optional) and local demo sensors into federated RF observers. Samples are sealed into a **hash-chained, append-only evidence log**. No offensive capability. No silent PII collection by default.

> Status: **operational baseline (v0.1)** — API, demo telemetry, evidence chain, and dashboard shell run offline with zero hardware.

## What works now

| Capability | Endpoint / path | Notes |
|------------|-----------------|-------|
| Health + chain verify | `GET /api/health` | Returns evidence integrity |
| Sensor registry | `GET /api/sensors` | Demo sensor always present |
| ADB discovery | `POST /api/sensors/discover` | Optional; needs `adbutils` + device |
| Domains | `GET /api/domains` | cellular · wifi · d2d · transport |
| Ingest sample | `POST /api/telemetry/sample` | Operator-supplied metrics |
| Demo burst | `POST /api/telemetry/demo` | Synthetic samples (`demo: true`) |
| Recent buffer | `GET /api/telemetry/recent` | In-memory ring buffer |
| Evidence | `GET /api/evidence/verify`, `/tail` | SHA-256 chain on disk |
| Dashboard | `GET /` | Minimal operator UI |
| OpenAPI | `GET /docs` | FastAPI Swagger |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
cp .env.example .env
./launch.sh
# → http://127.0.0.1:8000
# → http://127.0.0.1:8000/docs
```

```bash
curl -s localhost:8000/api/health | jq .
curl -s -X POST 'localhost:8000/api/telemetry/demo?count=4' | jq .
curl -s localhost:8000/api/evidence/verify | jq .
```

```bash
pytest -q
```

## Layout

```
main.py              FastAPI app
titan/
  config.py          env settings
  evidence.py        hash-chained JSONL log
  sensors.py         registry + optional ADB
  telemetry.py       domain samples + buffer
static/index.html    operator dashboard
tests/               evidence + telemetry tests
data/                runtime (gitignored)
```

## Evidence chain

Each event is a JSONL record: `seq`, `ts`, `kind`, `sensor_id`, `body`, `prev_hash`, `hash`.
`hash = SHA-256(canonical JSON of all fields except hash)`.
`GET /api/evidence/verify` recomputes the chain and reports `broken_at` if tampered.

## Principles

- **Defensive only** — observe local RF context; do not target individuals.
- **Demo is labeled** — synthetic samples always carry `demo: true`.
- **Keyless alignment** — no vendor API keys; optional link to CIVINTELLIGENCE public CIVINT snapshots via env `CIVINT_BASE`.
- **Consolidation** — merges into CIVINTELLIGENCE as the RF sensing module ([charter](https://github.com/POWDER-RANGER/CivilianIntelligence/blob/main/docs/CIVINTELLIGENCE.md)).

## License

MIT — built for citizens, by citizens.
