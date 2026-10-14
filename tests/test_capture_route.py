"""ADB discover + capture through the real routes, with adbutils replaced by a test double.

Guards the property the device acceptance check relies on: only the capture
route writes ``telemetry_adb`` evidence, and API-submitted samples never do.
"""
import sys
import types

import pytest
from fastapi.testclient import TestClient

from main import app

TOKEN = "capture-test-token"


class _Dev:
    serial = "FAKE0001"

    def shell(self, cmd, timeout=None):
        if "telephony.registry" in cmd:
            return "mDataRegState=0\nmVoiceRegState=0\nmOperatorNumeric=310260\nrsrp=-101\n"
        if "dumpsys wifi" in cmd:
            return "mWifiInfo SSID: <x>, RSSI: -58, Frequency: 5180\n"
        if "ro.product.model" in cmd:
            return "Pixel 4a\n"
        if "ro.build.version.release" in cmd:
            return "13\n"
        return ""


@pytest.fixture
def client(titan_env, monkeypatch):
    fake = types.ModuleType("adbutils")
    fake.adb = types.SimpleNamespace(device_list=lambda: [_Dev()], device=lambda serial: _Dev())
    monkeypatch.setitem(sys.modules, "adbutils", fake)
    titan_env(TITAN_API_TOKEN=TOKEN, ADB_ENABLED="true")
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _kinds(client):
    return [r["kind"] for r in client.get("/api/evidence/tail?n=200", headers=AUTH).json()["records"]]


def test_capture_writes_adb_evidence_and_live_samples(client):
    before = _kinds(client).count("telemetry_adb")
    found = client.post("/api/sensors/discover", headers=AUTH).json()["found"]
    assert [s["id"] for s in found] == ["adb-FAKE0001"]
    assert found[0]["meta"]["model"] == "Pixel 4a"

    r = client.post("/api/sensors/capture", headers=AUTH, json={"sensor_id": "adb-FAKE0001"})
    assert r.status_code == 200 and r.json()["emitted"] == 2
    assert _kinds(client).count("telemetry_adb") == before + 2

    obs = client.get("/api/observations?n=10", headers=AUTH).json()
    adb = [s for s in obs["samples"] if s["metrics"].get("source") == "adb"]
    cell = next(s["metrics"] for s in adb if s["domain"] == "cellular")
    wifi = next(s["metrics"] for s in adb if s["domain"] == "wifi")
    assert cell["available"] is True and cell["rsrp_dbm"] == -101 and cell["operator"] == "310260"
    assert wifi["rssi_dbm"] == -58 and wifi["freq_mhz"] == 5180
    assert client.get("/api/evidence/verify", headers=AUTH).json()["ok"] is True


def test_api_submitted_sample_never_writes_adb_evidence(client):
    before = _kinds(client).count("telemetry_adb")
    client.post(
        "/api/telemetry/sample",
        headers=AUTH,
        json={"domain": "cellular", "metrics": {"source": "adb", "available": True}},
    )
    assert _kinds(client).count("telemetry_adb") == before


def test_capture_unknown_sensor_is_404(client):
    r = client.post("/api/sensors/capture", headers=AUTH, json={"sensor_id": "adb-NOPE"})
    assert r.status_code == 404
