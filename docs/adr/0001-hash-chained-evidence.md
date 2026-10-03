# ADR 0001: Hash-chained append-only evidence

## Status

Accepted (v0.1)

## Context

Operators need to detect silent alteration of historical RF observations without depending on a remote service.

## Decision

Store events as JSONL. Each record includes `prev_hash` and `hash = SHA-256(canonical JSON of fields excluding hash)`. Seal and verify share one `canonical_material()` function. Concurrent appends take a process-local exclusive lock and `fsync` after each write.

## Consequences

- Integrity is self-auditable offline.
- Availability is local-disk dependent.
- Does not prove authorship (no signatures yet).
