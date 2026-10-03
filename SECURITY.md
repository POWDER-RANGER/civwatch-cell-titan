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
- `ADB_ENABLED` defaults to `false`. Device capture is unavailable until explicitly enabled.
- Do **not** bind `0.0.0.0` without a token **and** TLS (or a VPN such as Tailscale/WireGuard).
- WebSocket `/ws/live` accepts `?token=` when a token is configured.
- Supported client posture until TLS is in front: **localhost / emulator only**. Physical-phone LAN access is unsupported without auth + encrypted transport.
