"""Hash-chained evidence records. Append-only; each entry seals the previous digest."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class EvidenceRecord:
    seq: int
    ts: str
    kind: str
    sensor_id: str
    body: dict[str, Any]
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceChain:
    """Filesystem-backed append-only chain. One JSONL file per sensor."""

    def __init__(self, root: str | Path, sensor_id: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sensor_id = sensor_id
        self.path = self.root / f"{sensor_id}.jsonl"
        self._last_hash = "0" * 64
        self._seq = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                self._seq = int(rec["seq"])
                self._last_hash = rec["hash"]

    def append(self, kind: str, body: dict[str, Any]) -> EvidenceRecord:
        self._seq += 1
        ts = _utc_now()
        material = json.dumps(
            {"seq": self._seq, "ts": ts, "kind": kind, "sensor_id": self.sensor_id, "body": body, "prev_hash": self._last_hash},
            sort_keys=True,
            separators=(",", ":"),
        )
        h = _digest(material)
        rec = EvidenceRecord(
            seq=self._seq,
            ts=ts,
            kind=kind,
            sensor_id=self.sensor_id,
            body=body,
            prev_hash=self._last_hash,
            hash=h,
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec.to_dict(), separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._last_hash = h
        return rec

    def verify(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"ok": True, "length": 0, "broken_at": None}
        prev = "0" * 64
        n = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            n += 1
            material = json.dumps(
                {
                    "seq": rec["seq"],
                    "ts": rec["ts"],
                    "kind": rec["kind"],
                    "sensor_id": rec["sensor_id"],
                    "body": rec["body"],
                    "prev_hash": rec["prev_hash"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            expected = _digest(material)
            if rec["prev_hash"] != prev or rec["hash"] != expected:
                return {"ok": False, "length": n, "broken_at": rec["seq"]}
            prev = rec["hash"]
        return {"ok": True, "length": n, "broken_at": None}

    def tail(self, n: int = 20) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return [json.loads(ln) for ln in lines[-n:]]
