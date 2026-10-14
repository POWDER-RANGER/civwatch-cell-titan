"""Sensor registry for user-owned physical collectors."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


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
        """Public view: the raw ADB serial stays server-side in ``meta['serial']``."""
        d = asdict(self)
        d["meta"] = {k: v for k, v in self.meta.items() if k != "serial"}
        return d


@dataclass
class DiscoveryResult:
    found: list[dict[str, Any]]
    error: Optional[dict[str, str]] = None


class SensorRegistry:
    def __init__(self, default_id: str) -> None:
        self._sensors: dict[str, Sensor] = {}
        # Do not register a fictional/default sensor. A sensor becomes real only
        # after an attached collector is discovered or explicitly registered.

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

    def discover(self) -> DiscoveryResult:
        """Register every authorized ADB device. Errors are reported, never counted as devices.

        Sensors registered earlier but absent now are kept (so a reconnect resumes the
        same identity) and marked ``connected: False`` — they are stale, not live.
        """
        try:
            import adbutils
        except ImportError:
            return DiscoveryResult(found=[], error={"code": "adbutils_missing"})
        from titan.adb_collect import classify_adb_exception, collect_device_props

        try:
            listed = list(adbutils.adb.device_list())
        except Exception as ex:  # noqa: BLE001
            return DiscoveryResult(found=[], error={"code": classify_adb_exception(ex)})

        found: list[dict[str, Any]] = []
        present: set[str] = set()
        for d in listed:
            props = collect_device_props(d.serial)
            ref = props["device_ref"]
            sid = f"adb-{ref}"
            present.add(sid)
            sensor = Sensor(
                id=sid,
                label=f"{props.get('model') or 'Android device'} ({ref})",
                mode="adb",
                last_seen=_utc(),
                domains=["cellular", "wifi"],
                meta={
                    "serial": d.serial,
                    "device_ref": ref,
                    "model": props.get("model"),
                    "android": props.get("android"),
                    "api_level": props.get("api_level"),
                    "connected": True,
                    "probe_error": props.get("error_category"),
                },
            )
            self.register(sensor)
            found.append(sensor.to_dict())
        for sid, s in self._sensors.items():
            if s.mode == "adb" and sid not in present:
                s.meta["connected"] = False
        return DiscoveryResult(found=found)

    def discover_adb(self) -> list[dict[str, Any]]:
        """Backward-compatible list view of :meth:`discover`."""
        return self.discover().found
