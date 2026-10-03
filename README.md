# CIVWATCH CELL TITAN

**Defensive RF observability** for [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence).

![version](https://img.shields.io/badge/version-0.1.2-00E5FF)
![license](https://img.shields.io/badge/license-MIT-3fb950)

> **v0.1.2** — bearer auth, ADB off by default, loopback bind, fail-closed production.  
> Supported clients until TLS/VPN: **localhost and emulator only**.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
./launch.sh   # binds 127.0.0.1:8000
pytest -q
```

## Auth (required before any LAN exposure)

Production (`CELL_TITAN_ENV=production`) or `REQUIRE_AUTH=true` **refuses to start** without `TITAN_API_TOKEN`.

```bash
export TITAN_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export REQUIRE_AUTH=true
# Optional device capture:
# export ADB_ENABLED=true
./launch.sh

curl -s -X POST 'localhost:8000/api/telemetry/demo?count=1' \
  -H "Authorization: Bearer $TITAN_API_TOKEN"
```

| Route class | Auth |
|-------------|------|
| GET health/status/recent/evidence | Open on loopback (reads stay local-first) |
| POST telemetry, sample, demo | Bearer when token set / production |
| POST sensors/discover, capture | Bearer **and** `ADB_ENABLED=true` |
| WS `/ws/live` | First message `{"type":"auth","token":"..."}` when token configured |

Token checks use `hmac.compare_digest`. Do **not** put the token in the WebSocket URL.

**Do not** use `HOST=0.0.0.0` for a phone on Wi‑Fi unless the token is set **and** Titan sits behind TLS or a VPN.

## License

MIT
