"""API smoke + contract tests."""
from pathlib import Path

import os
import pytest
from fastapi.testclient import TestClient

os.environ["EVIDENCE_DIR"] = str(Path("/tmp/titan-test-evidence-api"))
os.environ["AUTO_DEMO"] = "false"
os.environ["SENSOR_ID"] = "test-sensor"
os.environ["CELL_TITAN_ENV"] = "development"
os.environ["ALLOW_UNAUTHENTICATED_LOOPBACK"] = "true"

from main import app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "ev"))
    monkeypatch.setenv("AUTO_DEMO", "false")
    with TestClient(app) as c:
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


def test_demo_and_recent(client):
    r = client.post("/api/telemetry/demo?count=4")
    assert r.status_code == 200
    assert r.json()["emitted"] == 4
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
    client.post("/api/telemetry/demo?count=2")
    r = client.get("/api/observations?n=5")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert body["owner_scope"] == "user_device"
    assert body["state"] == "demo"
    assert isinstance(body["samples"], list)
    assert body["privacy"]["public_submission"] == "explicit_user_action"
    assert body["privacy"]["server_side_discovery"] is False
    assert any("do not by themselves prove interception" in x for x in body["limitations"])
