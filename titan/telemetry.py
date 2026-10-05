"""RF domain samples and bounded ring buffer."""
from __future__ import annotations

import random
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Literal

Domain = Literal["cellular", "wifi", "d2d", "transport"]


@dataclass
class RfSample:
    domain: Domain
    sensor_id: str
    ts: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")



class SampleBuffer:
    def __init__(self, capacity: int = 500) -> None:
        if capacity < 1 or capacity > 100_000:
            raise ValueError("capacity out of bounds")
        self._buf: Deque[RfSample] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(self, sample: RfSample) -> None:
        with self._lock:
            self._buf.append(sample)

    def recent(self, n: int = 50, domain: Domain | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._buf)
        if domain:
            items = [s for s in items if s.domain == domain]
        return [s.to_dict() for s in items[-n:]]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by: dict[str, int] = {}
            for s in self._buf:
                by[s.domain] = by.get(s.domain, 0) + 1
            return {"buffered": len(self._buf), "by_domain": by, "capacity": self._buf.maxlen}
