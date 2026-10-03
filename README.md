# CIVWATCH CELL TITAN

**Defensive RF observability** for [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence).

![version](https://img.shields.io/badge/version-0.1.2-00E5FF)
![license](https://img.shields.io/badge/license-MIT-3fb950)

> **v0.1.2** — bearer auth on writes/ADB, ADB off by default, loopback bind.  
> Supported clients until TLS is in place: **localhost and emulator only**.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
./launch.sh   # binds 127.0.0.1:8000
pytest -q
```

## Auth (required before any LAN exposure)

```bash
export TITAN_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export REQUIRE_AUTH=true
# Optional device capture:
# export ADB_ENABLED=true
./launch.sh

curl -s -X POST localhost:8000/api/telemetry/demo?count=1 \
  -H "Authorization: Bearer $TITAN_API_TOKEN"
```

| Route class | Auth |
|-------------|------|
| GET health/status/recent/evidence | Open (local) |
| POST telemetry, sample, demo | Bearer when token set / production |
| POST sensors/discover, capture | Bearer **and** `ADB_ENABLED=true` |
| WS `/ws/live` | `?token=` when token configured |

**Do not** use `HOST=0.0.0.0` for a phone on Wi‑Fi unless the token is set **and** Titan sits behind TLS or a VPN.

## Assurance

See [docs/ASSURANCE.md](docs/ASSURANCE.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## License

MIT
