# CELL TITAN v0.1.1 — Assurance release

**Date:** 2026-10-03  
**Tag suggestion:** `v0.1.1`

## Assurance deltas vs 0.1.0

- Strict Pydantic contracts (`extra=forbid`) on mutating inputs
- Evidence: `schema_version`, dense sequence check, thread lock, shared canonicalization
- Middleware: security headers, 64 KiB body limit, rate limit
- Production CORS fail-closed (`CELL_TITAN_ENV=production`)
- Threat model, ADR 0001, assurance case document
- Concurrent append test (100 events / 4 threads)
- CI matrix: Python 3.11 + 3.12

## Verify

```bash
pytest -q
./launch.sh
curl -s localhost:8000/api/evidence/verify
curl -s localhost:8000/api/status | jq .assurance
```

## Tag

```bash
git tag -a v0.1.1 -m "CELL TITAN assurance hardening"
git push origin v0.1.1
```
