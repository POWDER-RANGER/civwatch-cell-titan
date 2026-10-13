# Security Policy

## Project

civwatch-cell-titan: shell-based RF observability tooling for the CIVWATCH ecosystem. Defensive monitoring only.

## Supported Versions

No tagged, maintained release lines. Only the latest commit on the default branch (`main`) is supported. Fixes land on `main` only.

| Version | Supported |
| --- | --- |
| `main` (latest commit) | Yes |
| Anything else | No |

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability.

Use GitHub private vulnerability reporting: repository **Security** tab, then **Report a vulnerability**. If that is unavailable, open a public issue titled "Security contact request" with no vulnerability details, and the maintainer will arrange a private channel.

Include: affected script or component and commit, reproduction steps, impact assessment, and any proof-of-concept. Do not include captured traffic, identifiers, or other data belonging to third parties.

## Expected Response Times

Single-maintainer project. Targets, not guarantees:

| Stage | Target |
| --- | --- |
| Acknowledgement | 5 business days |
| Initial triage and severity assessment | 10 business days |
| Status updates while open | Every 14 days |
| Fix or mitigation for confirmed issues | Severity-dependent; critical prioritized first |

Default coordinated disclosure window: 90 days from acknowledgement, extendable by agreement.

## Security Maintainer

Curtis Charles Farrar (GitHub: [@POWDER-RANGER](https://github.com/POWDER-RANGER)) is responsible for security review and disclosure handling. There is no separate security team. See the ecosystem-level [MAINTAINERS.md](https://github.com/POWDER-RANGER/CIVWATCH/blob/main/MAINTAINERS.md).

- No bug bounty is offered.
- Non-security bugs: use public issues.

## Technical Scope and Hardening Notes

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
