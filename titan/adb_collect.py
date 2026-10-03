"""Best-effort ADB shell collectors. Missing adbutils or device → empty structured result."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _shell(serial: str, cmd: str, timeout: float = 8.0) -> str:
    try:
        import adbutils
    except ImportError:
        return ""
    try:
        d = adbutils.adb.device(serial)
        out = d.shell(cmd, timeout=timeout)
        return out if isinstance(out, str) else str(out)
    except Exception:
        return ""


def collect_cellular(serial: str) -> dict[str, Any]:
    raw = _shell(serial, "dumpsys telephony.registry")
    metrics: dict[str, Any] = {"source": "adb", "demo": False, "serial": serial}
    if not raw:
        metrics["available"] = False
        metrics["note"] = "no_telephony_dump"
        return metrics
    metrics["available"] = True
    for key, pat in (
        ("mci", r"mCellInfo=([^\n]+)"),
        ("operator", r"mOperatorNumeric=(\S+)"),
        ("data_reg", r"mDataRegState=(\S+)"),
        ("voice_reg", r"mVoiceRegState=(\S+)"),
    ):
        m = re.search(pat, raw)
        if m:
            metrics[key] = m.group(1)[:200]
    rsrp = re.search(r"rsrp\s*[=:]?\s*(-?\d+)", raw, re.I)
    if rsrp:
        metrics["rsrp_dbm"] = int(rsrp.group(1))
    metrics["dump_chars"] = len(raw)
    metrics["ts"] = _utc()
    return metrics


def collect_wifi(serial: str) -> dict[str, Any]:
    raw = _shell(serial, "dumpsys wifi")
    metrics: dict[str, Any] = {"source": "adb", "demo": False, "serial": serial}
    if not raw:
        metrics["available"] = False
        metrics["note"] = "no_wifi_dump"
        return metrics
    metrics["available"] = True
    rssi = re.search(r"RSSI:\s*(-?\d+)", raw)
    if rssi:
        metrics["rssi_dbm"] = int(rssi.group(1))
    freq = re.search(r"Frequency:\s*(\d+)", raw)
    if freq:
        metrics["freq_mhz"] = int(freq.group(1))
    if re.search(r"mWifiInfo\s+[^\n]*", raw):
        metrics["wifi_info_present"] = True
    metrics["dump_chars"] = len(raw)
    metrics["ts"] = _utc()
    return metrics


def collect_device_props(serial: str) -> dict[str, Any]:
    model = _shell(serial, "getprop ro.product.model").strip()
    release = _shell(serial, "getprop ro.build.version.release").strip()
    return {
        "serial": serial,
        "model": model or None,
        "android": release or None,
        "ts": _utc(),
    }
