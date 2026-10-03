"""Hash-chained evidence records.

Design invariants (enforced in tests):
1. Append-only: never rewrite prior lines.
2. Hash covers seq, ts, kind, sensor_id, body, prev_hash, schema_version — never the hash field.
3. Canonical JSON: sort_keys=True, separators=(',', ':'), UTF-8, no NaN.
4. Concurrent writers serialize via exclusive file lock.
5. verify() recomputes every link; any mismatch returns broken_at=seq.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
GENESIS_HASH = "0" * 64

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _file_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_material(
    *,
    seq: int,
    ts: str,
    kind: str,
    sensor_id: str,
    body: dict[str, Any],
    prev_hash: str,
    schema_version: int = SCHEMA_VERSION,
) -> str:
    """Deterministic serialization used for hashing. Single source of truth for seal + verify."""
    payload = {
        "body": body,
        "kind": kind,
        "prev_hash": prev_hash,
        "schema_version": schema_version,
        "sensor_id": sensor_id,
        "seq": seq,
        "ts": ts,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    seq: int
    ts: str
    kind: str
    sensor_id: str
    body: dict[str, Any]
    prev_hash: str
    hash: str
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceChain:
    """Filesystem-backed append-only chain. One JSONL file per sensor_id."""

    def __init__(self, root: str | Path, sensor_id: str) -> None:
        if not sensor_id or len(sensor_id) > 128 or "/" in sensor_id or "\\" in sensor_id:
            raise ValueError("sensor_id must be 1..128 chars without path separators")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sensor_id = sensor_id
        self.path = self.root / f"{sensor_id}.jsonl"
        self._last_hash = GENESIS_HASH
        self._seq = 0
        self._lock = _file_lock(self.path)
        self._reload_tip()

    def _reload_tip(self) -> None:
        if not self.path.exists():
            return
        with self._lock:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                self._seq = int(rec["seq"])
                self._last_hash = rec["hash"]

    def append(self, kind: str, body: dict[str, Any]) -> EvidenceRecord:
        if not kind or len(kind) > 64:
            raise ValueError("kind must be 1..64 chars")
        if not isinstance(body, dict):
            raise TypeError("body must be a dict")
        json.dumps(body, allow_nan=False)

        with self._lock:
            self._seq += 1
            ts = _utc_now()
            material = canonical_material(
                seq=self._seq,
                ts=ts,
                kind=kind,
                sensor_id=self.sensor_id,
                body=body,
                prev_hash=self._last_hash,
            )
            h = digest(material)
            rec = EvidenceRecord(
                seq=self._seq,
                ts=ts,
                kind=kind,
                sensor_id=self.sensor_id,
                body=body,
                prev_hash=self._last_hash,
                hash=h,
            )
            line = json.dumps(rec.to_dict(), separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            self._last_hash = h
            return rec

    def verify(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"ok": True, "length": 0, "broken_at": None, "schema_version": SCHEMA_VERSION}
        prev = GENESIS_HASH
        n = 0
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue
            rec = json.loads(line)
            n += 1
            sv = int(rec.get("schema_version", 1))
            material = canonical_material(
                seq=int(rec["seq"]),
                ts=rec["ts"],
                kind=rec["kind"],
                sensor_id=rec["sensor_id"],
                body=rec["body"],
                prev_hash=rec["prev_hash"],
                schema_version=sv,
            )
            expected = digest(material)
            if rec["prev_hash"] != prev or rec["hash"] != expected or int(rec["seq"]) != n:
                return {
                    "ok": False,
                    "length": n,
                    "broken_at": rec.get("seq"),
                    "schema_version": SCHEMA_VERSION,
                }
            prev = rec["hash"]
        return {"ok": True, "length": n, "broken_at": None, "schema_version": SCHEMA_VERSION}

    def tail(self, n: int = 20) -> list[dict[str, Any]]:
        if n < 1:
            return []
        if not self.path.exists():
            return []
        with self._lock:
            lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return [json.loads(ln) for ln in lines[-n:]]

    @property
    def length(self) -> int:
        return self._seq
