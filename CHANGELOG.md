# Changelog

## 0.1.3 — green CI + deploy verification (2026-10-13)

- Fix: `titan.config.settings` now reloads **in place**. Tests previously used
  `importlib.reload(titan.config)`, creating a second settings object; auth checks
  read the new object while `main` held the old one, and module-level env writes
  leaked across test files at collection time. Result: 10 order-dependent failures
  and red CI on `main` since 2026-10-05, which blocked Render deploys.
- Tests: per-test environment isolation (`conftest.py` autouse fixture + `titan_env`);
  suite passes in any order. New regression guard and anonymous-vs-token test for
  `/api/observations`.
- CI: asserts production refuses to boot without a token, then boots the production
  configuration and runs the deploy smoke check.
- New `scripts/smoke_deploy.py`: stdlib post-deploy validator with Render cold-start
  tolerance and `--expect-version` to prove which build is live.
- Includes the capability registry and observation envelope merged in PR #9.

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
