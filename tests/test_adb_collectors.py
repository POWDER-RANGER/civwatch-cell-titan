"""Collector, discovery and observation-state honesty tests (mocked adbutils).

Configuration-independent: nothing here imports ``main`` or reads Settings.
"""
from __future__ import annotations

import json

import adbutils
import adbutils.errors
import pytest

from titan import adb_collect
from titan.adb.devices import device_ref
from titan.sensors import SensorRegistry
from titan.telemetry import observation_state


class _FakeDevice:
    def __init__(self, serial, outputs=None, exc=None):
        self.serial = serial
        self.outputs = outputs or {}
        self.exc = exc

    def shell(self, cmd, timeout=None):
        if self.exc:
            raise self.exc
        return self.outputs.get(cmd, "")


@pytest.fixture
def fake_adb(monkeypatch):
    calls: list[str] = []
    state = {"devices": {}, "list_exc": None}

    def device(serial=None, **_):
        calls.append(serial)
        return state["devices"].get(serial) or _FakeDevice(serial, exc=adbutils.AdbError(f"device '{serial}' not found"))

    def device_list():
        if state["list_exc"]:
            raise state["list_exc"]
        return list(state["devices"].values())

    monkeypatch.setattr(adbutils.adb, "device", device)
    monkeypatch.setattr(adbutils.adb, "device_list", device_list)
    return state, calls


def test_collectors_target_exact_serial(fake_adb):
    state, calls = fake_adb
    state["devices"]["A1"] = _FakeDevice("A1", {"dumpsys wifi": "mWifiInfo SSID: x, RSSI: -55, Frequency: 5180\n"})
    state["devices"]["B2"] = _FakeDevice("B2", {"dumpsys wifi": "RSSI: -40\n"})
    m = adb_collect.collect_wifi("A1")
    assert calls == ["A1"]
    assert m["rssi_dbm"] == -55 and m["freq_mhz"] == 5180


def test_device_gone_is_unavailable_not_live(fake_adb):
    m = adb_collect.collect_cellular("GONE")
    assert m["available"] is False
    assert m["error_category"] == "device_not_found"
    assert observation_state([{"metrics": m}]) == "unavailable"


def test_timeout_is_classified(fake_adb):
    state, _ = fake_adb
    state["devices"]["T"] = _FakeDevice("T", exc=adbutils.AdbTimeout("timed out"))
    m = adb_collect.collect_wifi("T")
    assert m["available"] is False and m["error_category"] == "timeout"


def test_unauthorized_and_offline_are_classified(fake_adb):
    state, _ = fake_adb
    state["devices"]["U"] = _FakeDevice("U", exc=adbutils.AdbError("device unauthorized.\nThis adb server's $ADB_VENDOR_KEYS is not set"))
    state["devices"]["O"] = _FakeDevice("O", exc=adbutils.AdbError("device offline"))
    assert adb_collect.collect_wifi("U")["error_category"] == "device_unauthorized"
    assert adb_collect.collect_wifi("O")["error_category"] == "device_offline"


def test_rsrp_unavailable_sentinel_is_not_a_measurement(fake_adb):
    state, _ = fake_adb
    state["devices"]["S"] = _FakeDevice("S", {"dumpsys telephony.registry":
        "mCellInfo=[CellInfoLte:{CellSignalStrengthLte: rssi=2147483647 rsrp=2147483647 rsrq=2147483647}]\n"})
    m = adb_collect.collect_cellular("S")
    assert "rsrp_dbm" not in m and m["rsrp_unavailable"] is True


def test_rsrp_skips_sentinel_and_takes_first_valid(fake_adb):
    state, _ = fake_adb
    state["devices"]["S"] = _FakeDevice("S", {"dumpsys telephony.registry":
        "rsrp=2147483647\nCellSignalStrengthLte: rsrp=-97 rsrq=-11\n"})
    assert adb_collect.collect_cellular("S")["rsrp_dbm"] == -97


def test_wifi_invalid_rssi_sentinel(fake_adb):
    state, _ = fake_adb
    state["devices"]["W"] = _FakeDevice("W", {"dumpsys wifi": "mWifiInfo SSID: <unknown ssid>, RSSI: -127\n"})
    m = adb_collect.collect_wifi("W")
    assert "rssi_dbm" not in m and m["rssi_unavailable"] is True


def test_metrics_never_contain_raw_serial(fake_adb):
    state, _ = fake_adb
    state["devices"]["RAWSERIAL99"] = _FakeDevice("RAWSERIAL99", {"dumpsys wifi": "RSSI: -60\n"})
    m = adb_collect.collect_wifi("RAWSERIAL99")
    assert "RAWSERIAL99" not in json.dumps(m)
    assert m["device_ref"] == device_ref("RAWSERIAL99")


def test_discovery_error_is_not_counted_as_a_device(fake_adb):
    state, _ = fake_adb
    state["list_exc"] = adbutils.errors.AdbConnectionError("[Errno 111] Connection refused")
    result = SensorRegistry("x").discover()
    assert result.found == []
    assert result.error == {"code": "server_unreachable"}


def test_discovery_registers_by_ref_and_hides_serial(fake_adb):
    state, _ = fake_adb
    state["devices"]["PIX123"] = _FakeDevice("PIX123", {"getprop ro.product.model": "Pixel 7\n",
                                                         "getprop ro.build.version.release": "16\n",
                                                         "getprop ro.build.version.sdk": "36\n"})
    reg = SensorRegistry("x")
    (s,) = reg.discover().found
    assert s["id"] == "adb-" + device_ref("PIX123")
    assert "PIX123" not in json.dumps(s)
    assert reg.get(s["id"]).meta["serial"] == "PIX123"   # server-side only, for explicit targeting
    assert s["meta"]["api_level"] == 36


def test_absent_device_marked_disconnected_not_removed(fake_adb):
    state, _ = fake_adb
    state["devices"]["P1"] = _FakeDevice("P1")
    reg = SensorRegistry("x")
    (s,) = reg.discover().found
    del state["devices"]["P1"]
    assert reg.discover().found == []
    assert reg.get(s["id"]).meta["connected"] is False


@pytest.mark.parametrize("samples,expected", [
    ([], "unavailable"),
    ([{"metrics": {"demo": True}}], "demo"),
    ([{"metrics": {"demo": False, "available": False}}], "unavailable"),
    ([{"metrics": {"demo": True}}, {"metrics": {"demo": False, "available": False}}], "unavailable"),
    ([{"metrics": {"demo": False, "available": True}}], "live"),
    ([{"metrics": {"rat": "LTE", "observed": True}}], "live"),   # legacy ingest without 'available'
])
def test_observation_state(samples, expected):
    assert observation_state(samples) == expected
