"""Hash-chained evidence records.

Design invariants (enforced in tests):
1. Append-only: never rewrite prior lines.
2. Hash covers seq, ts, kind, sensor_id, body, prev_hash, schema_version — never the hash field.
3. Canonical JSON: sort_keys=True, separators=(',', ':'), UTF-8, no NaN.
4. Concurrent writers (threads AND processes) serialize via fcntl.flock.
5. verify() recomputes every link; tip file stores length+last_hash so truncation is detectable.
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

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore


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


class _FileLock:
    """Process-wide exclusive lock (fcntl) with thread lock for same-process callers."""

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._thread = threading.Lock()
        self._fh = None

    def __enter__(self):
        self._thread.acquire()
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._lock_path, "a+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            if self._fh is not None and fcntl is not None:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            if self._fh is not None:
                self._fh.close()
                self._fh = None
            self._thread.release()


class EvidenceChain:
    """Filesystem-backed append-only chain. One JSONL + tip file per sensor_id."""

    def __init__(self, root: str | Path, sensor_id: str) -> None:
        if not sensor_id or len(sensor_id) > 128 or "/" in sensor_id or "\\" in sensor_id:
            raise ValueError("sensor_id must be 1..128 chars without path separators")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sensor_id = sensor_id
        self.path = self.root / f"{sensor_id}.jsonl"
        self.tip_path = self.root / f"{sensor_id}.tip.json"
        self.lock_path = self.root / f"{sensor_id}.lock"
        self._last_hash = GENESIS_HASH
        self._seq = 0
        self._file_lock = _FileLock(self.lock_path)
        with self._file_lock:
            self._reload_tip_unlocked()

    def _read_tip(self) -> dict[str, Any] | None:
        if not self.tip_path.exists():
            return None
        try:
            return json.loads(self.tip_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_tip(self, seq: int, last_hash: str) -> None:
        tip = {"seq": seq, "last_hash": last_hash, "schema_version": SCHEMA_VERSION}
        tmp = self.tip_path.with_suffix(".tip.tmp")
        tmp.write_text(json.dumps(tip, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, self.tip_path)

    def _reload_tip_unlocked(self) -> None:
        self._last_hash = GENESIS_HASH
        self._seq = 0
        if self.path.exists():
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

        with self._file_lock:
            self._reload_tip_unlocked()
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
            self._write_tip(self._seq, h)
            return rec

    def verify(self) -> dict[str, Any]:
        with self._file_lock:
            if not self.path.exists():
                tip = self._read_tip()
                if tip and int(tip.get("seq", 0)) > 0:
                    return {
                        "ok": False,
                        "length": 0,
                        "broken_at": "truncated",
                        "schema_version": SCHEMA_VERSION,
                        "detail": "tip expects records but jsonl missing/empty",
                    }
                return {"ok": True, "length": 0, "broken_at": None, "schema_version": SCHEMA_VERSION}

            prev = GENESIS_HASH
            n = 0
            last_hash = GENESIS_HASH
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
                last_hash = rec["hash"]

            tip = self._read_tip()
            if tip is not None:
                if int(tip.get("seq", -1)) != n or tip.get("last_hash") != last_hash:
                    return {
                        "ok": False,
                        "length": n,
                        "broken_at": "truncated",
                        "schema_version": SCHEMA_VERSION,
                        "detail": "jsonl tip mismatch (possible truncation or rewrite)",
                        "tip_seq": tip.get("seq"),
                        "jsonl_seq": n,
                    }
            return {"ok": True, "length": n, "broken_at": None, "schema_version": SCHEMA_VERSION}

    def tip_snapshot(self) -> dict[str, Any]:
        with self._file_lock:
            tip = self._read_tip()
            if tip:
                return {"seq": tip.get("seq", 0), "last_hash": tip.get("last_hash", GENESIS_HASH)}
            return {"seq": self._seq, "last_hash": self._last_hash}

    def tail(self, n: int = 20) -> list[dict[str, Any]]:
        if n < 1:
            return []
        with self._file_lock:
            if not self.path.exists():
                return []
            lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return [json.loads(ln) for ln in lines[-n:]]

    @property
    def length(self) -> int:
        return self._seq
