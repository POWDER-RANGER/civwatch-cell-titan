# Assurance case — CELL TITAN v0.1.1

## Claims

| ID | Claim | Evidence |
|----|-------|----------|
| C1 | Evidence tampering is detectable | `EvidenceChain.verify`, tests `test_tamper_detected`, `test_seq_must_be_dense` |
| C2 | Hash inputs are deterministic | Shared `canonical_material`, `test_canonical_is_stable` |
| C3 | Concurrent appends do not interleave lines | Thread lock + `test_concurrent_appends` |
| C4 | Mutating API rejects unknown fields | Pydantic `extra=forbid`, `test_sample_rejects_extra_fields` |
| C5 | Oversized bodies rejected | `BodySizeLimitMiddleware` |
| C6 | Production refuses wildcard CORS | `Settings.cors_list` |

## Test command

```bash
pytest -q
```

## Operational verify

```bash
curl -s localhost:8000/api/evidence/verify
```
