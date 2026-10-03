# Changelog

## 0.1.2 — auth boundary (2026-10-03)

- Bearer token on write + ADB routes; `hmac.compare_digest` with length guard
- Production / REQUIRE_AUTH: **refuse-to-start** without `TITAN_API_TOKEN`
- ADB off by default; default bind `127.0.0.1`
- WebSocket auth via first JSON message (not `?token=` query)
- Auth + boot tests

## 0.1.1 — assurance hardening (2026-10-03)

- Strict schemas, concurrent-safe evidence, middleware, threat model

## 0.1.0 — public operational release (2026-10-03)

- FastAPI + WebSocket + demo telemetry + dashboard + CI
