# CELL TITAN — status

**Version:** 0.1.1 (assurance hardening)
**Updated:** 2026-10-03
**Upstream:** [CivilianIntelligence](https://github.com/POWDER-RANGER/CivilianIntelligence)

## Assurance shipped

- [x] Strict Pydantic contracts (`extra=forbid`)
- [x] Canonical hash material shared by seal + verify
- [x] Concurrent-safe evidence append (lock + fsync)
- [x] Security headers, body size limit, rate limit
- [x] Production fail-closed CORS
- [x] Threat model + ADR + assurance case
- [x] Concurrent append test (100 events / 4 threads)
- [x] CI on Python 3.11 and 3.12

## Run

```bash
pytest -q
./launch.sh
curl -s localhost:8000/api/evidence/verify
```
