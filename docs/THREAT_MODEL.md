# CELL TITAN threat model (v0.1)

## Mission

Provide **defensive** RF situational awareness with **tamper-evident** local evidence. Not a weapon system. Not a surveillance product aimed at individuals.

## Assets

| Asset | Sensitivity | Protection |
|-------|-------------|------------|
| Evidence JSONL | High (integrity) | Hash chain, fsync, exclusive lock, verify endpoint |
| Live telemetry buffer | Medium | In-memory only, bounded capacity |
| Operator host | High | Deploy behind auth proxy; no built-in auth in v0.1 |
| ADB device dumps | Medium | Operator-owned device only; best-effort parse |

## Adversaries

1. **Local file tamperer** — modifies historical evidence lines → `verify()` returns `broken_at`.
2. **Network abuser** — floods POST endpoints → rate limit (default 120/min/IP).
3. **Payload attacker** — oversized or hostile JSON → body size limit + Pydantic `extra=forbid`.
4. **Confused deputy** — wildcard CORS in production → refused when `CELL_TITAN_ENV=production`.

## Non-goals (explicit)

- Cryptographic signatures from a hardware root of trust (future)
- Multi-tenant isolation
- Real-time spectrum warfare / jamming detection as a product claim
- Guaranteed OEM-complete cellular parse coverage

## Trust boundaries

```
[Operator browser] --HTTP/WS--> [CELL TITAN process] --JSONL--> [Evidence disk]
                                      |
                                      +--optional ADB--> [USB device you own]
```

## Residual risks

- Process-level compromise can append false evidence (mitigation: external log shipping / future signatures).
- Demo samples could be mistaken for live captures if UI is ignored (mitigation: mandatory `demo: true` flag).
- ADB dumps vary by OEM; absence of fields is not proof of absence of RF activity.
