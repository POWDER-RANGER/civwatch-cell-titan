# CIVWATCH CELL TITAN

**Defensive RF observability for [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence).**

Cell Titan is the specialized RF telemetry and evidence pillar. It supports cellular, Wi-Fi, D2D, and transport-domain observability, demo telemetry, optional ADB sensor collection, live events, and a hash-chained evidence trail.

> **Status:** 0.1.2 security baseline; loopback-first and fail-closed production posture.

## Role in the ecosystem

**CivilianIntelligence is the system of record.**

Cell Titan owns:

- sensor and RF telemetry
- evidence-chain creation and verification
- optional ADB discovery/capture
- live telemetry streaming

The hub can consume Titan health, telemetry, and evidence snapshots through a server-side integration rail.

## Quick start

~~~bash
pip install -r requirements.txt
cp .env.example .env
./launch.sh
# http://127.0.0.1:8000

pytest -q
~~~

## Authentication

Production or REQUIRE_AUTH=true requires TITAN_API_TOKEN and refuses to start without it.

~~~bash
export TITAN_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export REQUIRE_AUTH=true
./launch.sh
~~~

Do not place bearer credentials in the WebSocket URL.

## Route security

| Route class | Security boundary |
|---|---|
| GET /api/health | Operational metadata for discovery |
| GET /api/status | Loopback in explicit development; bearer off-box |
| GET /api/sensors | Loopback in explicit development; bearer off-box |
| GET /api/telemetry/recent | Loopback in explicit development; bearer off-box |
| GET /api/evidence/* | Loopback in explicit development; bearer off-box |
| POST /api/telemetry/* | Bearer-controlled |
| POST /api/sensors/* | Bearer + ADB_ENABLED=true |
| WS /ws/live | First-message JSON bearer handshake |

Bearer checks use constant-time comparison.

## Network policy

Default bind is loopback. Do **not** expose Titan on open-LAN HTTP.

Remote device access requires:

1. a configured bearer token
2. TLS or a VPN such as Tailscale

ADB collection remains disabled unless explicitly enabled.

## Integration with CIVINTELLIGENCE

Configure the hub with:

~~~dotenv
CELL_TITAN_BASE_URL=https://titan.internal.example
CELL_TITAN_API_TOKEN=<server-side-secret>
~~~

The token belongs on the hub/server side. It is never a browser setting.

## Evidence

Telemetry events can be sealed into the evidence chain. Verify locally with:

~~~bash
curl -s http://127.0.0.1:8000/api/evidence/verify
curl -s 'http://127.0.0.1:8000/api/evidence/tail?n=20'
~~~

## Related repositories

- [CivilianIntelligence](https://github.com/POWDER-RANGER/CivilianIntelligence) — system of record
- [Watchtower](https://github.com/POWDER-RANGER/civwatch-watchtower) — geospatial oversight pillar
- [CIVWATCH v3](https://github.com/POWDER-RANGER/civwatch-v3) — predecessor/reference RF dashboard
- [CIVWATCH](https://github.com/POWDER-RANGER/CIVWATCH) — legacy migration source

## License

MIT
