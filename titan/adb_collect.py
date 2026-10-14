"""ADB shell collectors for a single, explicitly targeted device.

Every call targets one serial (``adbutils.adb.device(serial)``); nothing here
enumerates or falls back to another device. Failures are classified rather
than flattened to an empty string, so "the phone is gone" is never confused
with "the phone reported nothing". Metrics carry ``device_ref``, never the raw
serial, because they flow into evidence and the CIVINTELLIGENCE envelope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from titan.adb.devices import device_ref

# CellInfo.UNAVAILABLE / WifiInfo.INVALID_RSSI sentinels and plausible ranges.
_INT_MAX = 2147483647
_RSRP_RANGE = (-156, -31)    # 3GPP TS 36.133 / 38.133 reporting range (dBm)
_WIFI_RSSI_RANGE = (-126, 0)  # -127 is WifiInfo.INVALID_RSSI


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ShellResult:
    output: str
    error: Optional[str] = None    # None | adbutils_missing | server_unreachable | device_not_found
                                   # | device_unauthorized | device_offline | timeout | adb_error


def classify_adb_exception(ex: BaseException) -> str:
    name = type(ex).__name__
    text = str(ex).lower()
    if name == "AdbTimeout" or isinstance(ex, TimeoutError):
        return "timeout"
    if name == "AdbConnectionError" or "connection refused" in text or "cannot connect" in text:
        return "server_unreachable"
    if "unauthorized" in text:
        return "device_unauthorized"
    if "offline" in text:
        return "device_offline"
    if "not found" in text or "no devices" in text or "device '" in text:
        return "device_not_found"
    return "adb_error"


def _run(serial: str, cmd: str, timeout: float = 8.0) -> ShellResult:
    try:
        import adbutils
    except ImportError:
        return ShellResult("", "adbutils_missing")
    try:
        d = adbutils.adb.device(serial=serial)
        out = d.shell(cmd, timeout=timeout)
        return ShellResult(out if isinstance(out, str) else str(out))
    except Exception as ex:  # noqa: BLE001 - classified, never swallowed silently
        return ShellResult("", classify_adb_exception(ex))


def _shell(serial: str, cmd: str, timeout: float = 8.0) -> str:
    """Backward-compatible string-only wrapper."""
    return _run(serial, cmd, timeout).output


def _unavailable(metrics: dict[str, Any], res: ShellResult, empty_note: str) -> dict[str, Any]:
    metrics["available"] = False
    metrics["error_category"] = res.error or "empty_output"
    metrics["note"] = res.error or empty_note
    metrics["ts"] = _utc()
    return metrics


def _in_range(v: int, lo_hi: tuple[int, int]) -> bool:
    return v != _INT_MAX and lo_hi[0] <= v <= lo_hi[1]


def collect_cellular(serial: str) -> dict[str, Any]:
    res = _run(serial, "dumpsys telephony.registry")
    raw = res.output
    metrics: dict[str, Any] = {"source": "adb", "demo": False, "device_ref": device_ref(serial)}
    if res.error or not raw.strip():
        return _unavailable(metrics, res, "no_telephony_dump")
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
    for m in re.finditer(r"\brsrp\s*[=:]?\s*(-?\d+)", raw, re.I):
        v = int(m.group(1))
        if _in_range(v, _RSRP_RANGE):
            metrics["rsrp_dbm"] = v
            break
    else:
        if re.search(r"\brsrp\s*[=:]?\s*-?\d+", raw, re.I):
            metrics["rsrp_unavailable"] = True
    metrics["dump_chars"] = len(raw)
    metrics["ts"] = _utc()
    return metrics


def collect_wifi(serial: str) -> dict[str, Any]:
    res = _run(serial, "dumpsys wifi")
    raw = res.output
    metrics: dict[str, Any] = {"source": "adb", "demo": False, "device_ref": device_ref(serial)}
    if res.error or not raw.strip():
        return _unavailable(metrics, res, "no_wifi_dump")
    metrics["available"] = True
    rssi = re.search(r"RSSI:\s*(-?\d+)", raw)
    if rssi:
        v = int(rssi.group(1))
        if _in_range(v, _WIFI_RSSI_RANGE):
            metrics["rssi_dbm"] = v
        else:
            metrics["rssi_unavailable"] = True
    freq = re.search(r"Frequency:\s*(\d+)", raw)
    if freq and 0 < int(freq.group(1)) < 100_000:
        metrics["freq_mhz"] = int(freq.group(1))
    if re.search(r"mWifiInfo\s+[^\n]*", raw):
        metrics["wifi_info_present"] = True
    metrics["dump_chars"] = len(raw)
    metrics["ts"] = _utc()
    return metrics


def collect_device_props(serial: str) -> dict[str, Any]:
    """Loopback-side identity probe. Includes the serial; callers must not publish it."""
    model = _run(serial, "getprop ro.product.model")
    release = _run(serial, "getprop ro.build.version.release")
    sdk = _run(serial, "getprop ro.build.version.sdk")
    error = model.error or release.error
    return {
        "serial": serial,
        "device_ref": device_ref(serial),
        "model": model.output.strip() or None,
        "android": release.output.strip() or None,
        "api_level": int(sdk.output.strip()) if sdk.output.strip().isdigit() else None,
        "error_category": error,
        "ts": _utc(),
    }
