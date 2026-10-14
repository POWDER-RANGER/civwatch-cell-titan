# CELL TITAN — status

**Version:** 0.1.3 (green CI + deploy verification)
**Updated:** 2026-10-13

## Shipped

- [x] Bearer token on write + ADB routes
- [x] ADB disabled by default
- [x] Default bind 127.0.0.1
- [x] WS token handshake via first JSON message (token never appears in URL)
- [x] Auth tests
- [x] Remote telemetry/evidence reads require bearer auth; loopback development remains available when explicitly enabled
- [x] `GET /api/capabilities` — hardware-bounded capability registry (schema 1.0)
- [x] `GET /api/observations` — bounded CIVINTELLIGENCE observation envelope (schema 1.0)
- [x] Test suite isolated per test (37 passing, order-independent)
- [x] CI boots the production configuration and runs `scripts/smoke_deploy.py`

## Phase gate — "operational and validated"

| Gate | Evidence | State |
|------|----------|-------|
| CI green on `main` | GitHub Actions, Python 3.11 + 3.12 | pending merge |
| Render runs current `main` | `smoke_deploy.py --expect-version 0.1.3` against production | pending deploy |
| Production contract reachable with token | `smoke_deploy.py` token checks | pending deploy |
| CIVINTELLIGENCE consumes the contract server-side | `/titan` shows schema 1.0 state, not UNREACHABLE | pending |
| One authorized physical-device observation | `state: live`, `source: adb`, evidence chain verifies | pending — requires operator + device |

See `docs/PHASE1_VALIDATION.md` for the exact procedure.

## Client policy

Localhost / emulator only until TLS (or Tailscale) is in front of Titan for remote devices.
