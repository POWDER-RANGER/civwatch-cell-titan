# Security policy

CELL TITAN is **defensive-only** RF observability software.

## Reporting

Report vulnerabilities privately via GitHub Security Advisories on this repository, or contact the maintainers listed on the POWDER-RANGER org profile.

## Scope notes

- Demo telemetry is synthetic and labeled `demo: true`.
- ADB collectors read device service dumps on a USB-debuggable handset you control. Do not point them at devices you do not own.
- Evidence files under `EVIDENCE_DIR` may contain RF metrics. Treat them as sensitive operational data; do not commit them.
- Default CORS is open (`*`) for local demos. Set `CORS_ORIGINS` to explicit origins before any public deployment.
- v0.1.x is not a multi-tenant service. Prefer localhost or an authenticated reverse proxy.

## Network exposure (v0.1.2+)

- Default `HOST=127.0.0.1` (loopback only).
- Set `TITAN_API_TOKEN` and send `Authorization: Bearer <token>` on all **write** and **ADB** routes.
- `ADB_ENABLED` defaults to `false`.
- Production (`CELL_TITAN_ENV=production`) or `REQUIRE_AUTH=true` **refuses to start** without `TITAN_API_TOKEN`.
- Token comparison uses `hmac.compare_digest` with a length-mismatch guard.
- WebSocket `/ws/live` authenticates with a first-frame JSON message
  (`{"type":"auth","token":"..."}`), **not** a query string (avoids proxy/history leakage).
- Do **not** bind `0.0.0.0` without a token **and** TLS (or Tailscale/WireGuard).
- Supported client posture until TLS is in front: **localhost / emulator only**.

## Read routes

GET health, status, recent telemetry, and evidence remain open for local operator dashboards.
If remote access is ever enabled, plan to require auth on reads as well.
