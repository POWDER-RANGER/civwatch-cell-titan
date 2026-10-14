"""API smoke + contract tests."""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "cell-titan"
    assert body["status"] in ("ok", "degraded")
    assert "X-Content-Type-Options" in r.headers


def test_version(client):
    assert client.get("/api/version").json()["version"]


def test_observed_sample_and_recent(client):
    r = client.post(
        "/api/telemetry/sample",
        json={"domain": "cellular", "metrics": {"rat": "LTE", "rsrp_dbm": -91, "observed": True}},
    )
    assert r.status_code == 200
    assert len(client.get("/api/telemetry/recent?n=10").json()["samples"]) >= 1


def test_sample_ingest(client):
    r = client.post(
        "/api/telemetry/sample",
        json={"domain": "wifi", "metrics": {"rssi_dbm": -55, "demo": True}},
    )
    assert r.status_code == 200
    assert "evidence_hash" in r.json()


def test_sample_rejects_extra(client):
    r = client.post(
        "/api/telemetry/sample",
        json={"domain": "wifi", "metrics": {}, "nope": 1},
    )
    assert r.status_code == 422


def test_capabilities_distinguish_device_metadata_from_demo(client):
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["privacy"]["default_scope"] == "user_device"
    domains = {item["id"]: item for item in body["domains"]}
    cellular_modes = {item["id"]: item for item in domains["cellular"]["collection_modes"]}
    assert cellular_modes["android_adb"]["measurement_class"] == "device_reported_metadata"
    assert "Does not prove an interceptor is present or absent" in cellular_modes["android_adb"]["limitations"]
    d2d_modes = domains["d2d"]["collection_modes"]
    assert d2d_modes[0]["status"] == "demo_only"
    assert d2d_modes[0]["measurement_class"] == "synthetic"


def test_domains_and_sensors(client):
    assert client.get("/api/domains").status_code == 200
    assert client.get("/api/sensors").status_code == 200


def test_evidence_endpoints(client):
    client.post("/api/telemetry/demo?count=2")
    assert client.get("/api/evidence/verify").json()["ok"] is True
    assert "records" in client.get("/api/evidence/tail?n=5").json()


def test_status(client):
    body = client.get("/api/status").json()
    assert body["release"] == "public"
    assert "assurance" in body


def test_user_observation_contract(client):
    client.post(
        "/api/telemetry/sample",
        json={"domain": "cellular", "metrics": {"rat": "LTE", "rsrp_dbm": -91, "observed": True}},
    )
    r = client.get("/api/observations?n=5")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert body["owner_scope"] == "user_device"
    assert body["state"] == "live"
    assert isinstance(body["samples"], list)
    assert body["privacy"]["public_submission"] == "explicit_user_action"
    assert body["privacy"]["server_side_discovery"] is False
    assert any("do not by themselves prove interception" in x for x in body["limitations"])
