# CELL TITAN — status

**Version:** 0.2.0 (Ed25519-signed evidence)
**Updated:** 2026-10-13

## Shipped

- [x] Ed25519-signed evidence records (schema v2) with public key at `GET /api/evidence/pubkey`; forged chains with rebuilt hashes fail verification
- [x] Bearer token on write + ADB routes
- [x] ADB disabled by default
- [x] Default bind 127.0.0.1
- [x] WS token handshake via first JSON message (token never appears in URL)
- [x] Auth tests
- [x] Remote telemetry/evidence reads require bearer auth; loopback development remains available when explicitly enabled
- [x] `GET /api/capabilities` — hardware-bounded capability registry (schema 1.0)
- [x] `GET /api/observations` — bounded CIVINTELLIGENCE observation envelope (schema 1.0)
- [x] Test suite isolated per test (199 passing, order-independent)
- [x] CI boots the production configuration and runs `scripts/smoke_deploy.py`
- [x] `scripts/device_acceptance.py` — physical-device acceptance that API-injected samples cannot satisfy

## Phase gate — "operational and validated"

| Gate | Evidence | State |
|------|----------|-------|
| CI green on `main` | GitHub Actions, Python 3.11 + 3.12 | pending merge |
| Render runs current `main` | `smoke_deploy.py --expect-version 0.2.0` against production | pending deploy |
| Production contract reachable with token | `smoke_deploy.py` token checks | pending deploy |
| CIVINTELLIGENCE consumes the contract server-side | `/titan` shows schema 1.0 state, not UNREACHABLE | pending |
| One authorized physical-device observation | `state: live`, `source: adb`, evidence chain verifies | pending — requires operator + device |

See `docs/PHASE1_VALIDATION.md` for the exact procedure.

## Client policy

Localhost / emulator only until TLS (or Tailscale) is in front of Titan for remote devices.
