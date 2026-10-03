# CIVWATCH CELL TITAN

**Defensive RF observability** — public operational release for the [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence) platform.

Federated sensors (demo always; Android via ADB optional). Every sample can be sealed into a **SHA-256 hash chain** on disk. No offensive capability.

![version](https://img.shields.io/badge/version-0.1.0-00E5FF)
![license](https://img.shields.io/badge/license-MIT-3fb950)
![use](https://img.shields.io/badge/use-defensive_only-00C853)

> **v0.1.0 public release** — install, run, verify the chain, and stream live events with zero hardware.

## Install & run

```bash
git clone https://github.com/POWDER-RANGER/civwatch-cell-titan.git
cd civwatch-cell-titan
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./launch.sh
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/ | Operator dashboard |
| http://127.0.0.1:8000/docs | OpenAPI (Swagger) |
| http://127.0.0.1:8000/api/health | Liveness + evidence integrity |
| ws://127.0.0.1:8000/ws/live | Live event stream |

```bash
curl -s localhost:8000/api/health | jq .
curl -s -X POST 'localhost:8000/api/telemetry/demo?count=4' | jq .
curl -s localhost:8000/api/evidence/verify | jq .
pytest -q
```

Optional continuous demo: `AUTO_DEMO=true DEMO_INTERVAL_SEC=10 ./launch.sh`

## API surface

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Status, evidence verify, buffer stats |
| GET | `/api/version` | Semver |
| GET | `/api/status` | Full operational snapshot |
| GET | `/api/sensors` | Registered sensors |
| POST | `/api/sensors/discover` | Scan ADB devices |
| POST | `/api/sensors/capture` | Pull cellular/Wi-Fi dumps from ADB sensor |
| GET | `/api/domains` | RF domains |
| POST | `/api/telemetry/sample` | Ingest operator sample |
| POST | `/api/telemetry/demo` | Synthetic burst (`demo: true`) |
| GET | `/api/telemetry/recent` | Ring buffer |
| GET | `/api/evidence/verify` | Recompute hash chain |
| GET | `/api/evidence/tail` | Last N sealed records |
| WS | `/ws/live` | Push telemetry + sensor events |

## Evidence chain

Each JSONL record: `seq`, `ts`, `kind`, `sensor_id`, `body`, `prev_hash`, `hash`.
`hash = SHA-256(canonical JSON without the hash field)`.
Tampering fails `GET /api/evidence/verify` (`broken_at` set).
Files under `EVIDENCE_DIR` — **do not commit them**.

## ADB (optional)

1. USB debugging on a device you own
2. `POST /api/sensors/discover`
3. `POST /api/sensors/capture` with `{"sensor_id":"adb-<serial>","domains":["cellular","wifi"]}`

## Principles

- **Defensive only** — never targeting individuals
- **Demo is labeled** — synthetic samples set `demo: true`
- **Fail soft** — missing ADB never takes down the API
- Sister pillar of CIVINTELLIGENCE

## Security

See [SECURITY.md](./SECURITY.md). Set `CORS_ORIGINS` and use a reverse proxy for network exposure. v0.1 has no built-in auth.

## License

MIT — built for citizens, by citizens.
