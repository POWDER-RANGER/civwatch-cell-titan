# Security policy

CELL TITAN is **defensive-only** RF observability software.

## Reporting

Report vulnerabilities privately via GitHub Security Advisories on this repository, or contact the maintainers listed on the POWDER-RANGER org profile.

## Scope notes

- Demo telemetry is synthetic and labeled `demo: true`.
- ADB collectors read device service dumps on a USB-debuggable handset you control. Do not point them at devices you do not own.
- Evidence files under `EVIDENCE_DIR` may contain RF metrics. Treat them as sensitive operational data; do not commit them.
- Default CORS is open (`*`) for local demos. Set `CORS_ORIGINS` to explicit origins before any public deployment.
- This project does not implement user authentication in v0.1. Bind to localhost or place behind a reverse proxy with access control for network exposure.
