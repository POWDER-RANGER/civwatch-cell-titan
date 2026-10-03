"""Sensor registry. ADB discovery is optional; demo mode always works offline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Sensor:
    id: str
    label: str
    mode: str
    last_seen: str
    domains: list[str] = field(default_factory=lambda: ["cellular", "wifi"])
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SensorRegistry:
    def __init__(self, default_id: str) -> None:
        self._sensors: dict[str, Sensor] = {}
        self.register(
            Sensor(
                id=default_id,
                label="Local demo sensor",
                mode="demo",
                last_seen=_utc(),
                domains=["cellular", "wifi", "d2d", "transport"],
                meta={"note": "Synthetic samples only until an ADB device is attached"},
            )
        )

    def register(self, sensor: Sensor) -> Sensor:
        self._sensors[sensor.id] = sensor
        return sensor

    def list(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._sensors.values()]

    def get(self, sensor_id: str) -> Sensor | None:
        return self._sensors.get(sensor_id)

    def touch(self, sensor_id: str) -> None:
        s = self._sensors.get(sensor_id)
        if s:
            s.last_seen = _utc()

    def discover_adb(self) -> list[dict[str, Any]]:
        try:
            import adbutils
        except ImportError:
            return []
        found: list[dict[str, Any]] = []
        try:
            from titan.adb_collect import collect_device_props

            for d in adbutils.adb.device_list():
                sid = f"adb-{d.serial}"
                props = collect_device_props(d.serial)
                sensor = Sensor(
                    id=sid,
                    label=f"ADB {props.get('model') or d.serial}",
                    mode="adb",
                    last_seen=_utc(),
                    domains=["cellular", "wifi"],
                    meta={"serial": d.serial, **{k: v for k, v in props.items() if k != "serial"}},
                )
                self.register(sensor)
                found.append(sensor.to_dict())
        except Exception as ex:
            return [{"error": str(ex)}]
        return found
