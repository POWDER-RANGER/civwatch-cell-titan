# CIVWATCH CELL TITAN

**Defensive RF observability** — public operational release for [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence).

Federated sensors (demo always; Android via ADB optional). Every sample can be sealed into a **SHA-256 hash chain** on disk. No offensive capability.

![version](https://img.shields.io/badge/version-0.1.1-00E5FF)
![license](https://img.shields.io/badge/license-MIT-3fb950)
![use](https://img.shields.io/badge/use-defensive_only-00C853)

> **v0.1.1** — assurance hardening: concurrent-safe hash chain, strict schemas, rate limits, threat model.

## Assurance

| Control | Mechanism |
|---------|-----------|
| Evidence integrity | SHA-256 chain; shared `canonical_material()` for seal + verify |
| Concurrent writes | Process lock + `fsync` per append |
| Input validation | Pydantic v2 `extra=forbid`, bounded metrics |
| Abuse resistance | Body size limit, per-IP rate limit on mutations |
| Production CORS | Wildcard refused when `CELL_TITAN_ENV=production` |
| Docs | [Threat model](docs/THREAT_MODEL.md) · [Assurance case](docs/ASSURANCE.md) · [ADR](docs/adr/0001-hash-chained-evidence.md) |

```bash
pytest -q   # 21 tests: tamper detect, concurrent append, schema reject
```

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
| http://127.0.0.1:8000/docs | OpenAPI |
| http://127.0.0.1:8000/api/health | Liveness + evidence integrity |
| ws://127.0.0.1:8000/ws/live | Live event stream |

```bash
curl -s localhost:8000/api/health | jq .
curl -s -X POST 'localhost:8000/api/telemetry/demo?count=4' | jq .
curl -s localhost:8000/api/evidence/verify | jq .
```

Production-style local bind:

```bash
CELL_TITAN_ENV=production CORS_ORIGINS=https://your.origin HOST=127.0.0.1 ./launch.sh
```

## API surface

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Status, evidence verify, buffer stats |
| GET | `/api/version` | Semver |
| GET | `/api/status` | Full snapshot + assurance tag |
| GET | `/api/sensors` | Registered sensors |
| POST | `/api/sensors/discover` | Scan ADB devices |
| POST | `/api/sensors/capture` | Pull cellular/Wi-Fi dumps |
| GET | `/api/domains` | RF domains |
| POST | `/api/telemetry/sample` | Ingest (strict schema) |
| POST | `/api/telemetry/demo` | Synthetic burst |
| GET | `/api/telemetry/recent` | Ring buffer |
| GET | `/api/evidence/verify` | Recompute hash chain |
| GET | `/api/evidence/tail` | Last N records |
| WS | `/ws/live` | Push events |

## Evidence chain

`hash = SHA-256(canonical JSON of seq, ts, kind, sensor_id, body, prev_hash, schema_version)`.

Tampering fails `GET /api/evidence/verify` (`broken_at` set). Files under `EVIDENCE_DIR` — do not commit.

## Principles

- **Defensive only** — never targeting individuals
- **Demo is labeled** — synthetic samples set `demo: true`
- **Fail soft** on ADB; **fail closed** on production CORS
- Sister pillar of CIVINTELLIGENCE

## Security

See [SECURITY.md](./SECURITY.md). v0.1.x has no built-in auth — place behind an authenticated reverse proxy for network exposure.

## License

MIT — built for citizens, by citizens.
