"""RF domain sample models and in-memory ring buffer (demo / no-device mode)."""
from __future__ import annotations

import random
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


def synthetic_sample(domain: Domain, sensor_id: str) -> RfSample:
    if domain == "cellular":
        metrics = {
            "rat": random.choice(["LTE", "NR", "LTE"]),
            "rsrp_dbm": random.randint(-110, -70),
            "rsrq_db": random.randint(-18, -6),
            "pci": random.randint(1, 503),
            "earfcn": random.randint(0, 65535),
            "demo": True,
        }
    elif domain == "wifi":
        metrics = {
            "ssid_hash": f"h{random.randint(1000, 9999)}",
            "bssid_prefix": "aa:bb:cc",
            "rssi_dbm": random.randint(-90, -40),
            "freq_mhz": random.choice([2412, 2437, 2462, 5180, 5220]),
            "demo": True,
        }
    elif domain == "d2d":
        metrics = {"sidelink": True, "rssi_dbm": random.randint(-100, -50), "demo": True}
    else:
        metrics = {
            "tech": random.choice(["BLE", "BT", "NFC"]),
            "rssi_dbm": random.randint(-90, -30),
            "demo": True,
        }
    return RfSample(domain=domain, sensor_id=sensor_id, ts=_utc(), metrics=metrics)


class SampleBuffer:
    def __init__(self, capacity: int = 500) -> None:
        self._buf: Deque[RfSample] = deque(maxlen=capacity)

    def push(self, sample: RfSample) -> None:
        self._buf.append(sample)

    def recent(self, n: int = 50, domain: Domain | None = None) -> list[dict[str, Any]]:
        items = list(self._buf)
        if domain:
            items = [s for s in items if s.domain == domain]
        return [s.to_dict() for s in items[-n:]]

    def stats(self) -> dict[str, Any]:
        by: dict[str, int] = {}
        for s in self._buf:
            by[s.domain] = by.get(s.domain, 0) + 1
        return {"buffered": len(self._buf), "by_domain": by}
