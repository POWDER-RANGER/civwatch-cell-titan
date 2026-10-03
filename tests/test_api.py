"""API smoke tests using FastAPI TestClient (no live server required)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import os

os.environ["EVIDENCE_DIR"] = str(Path("/tmp/titan-test-evidence"))
os.environ["AUTO_DEMO"] = "false"
os.environ["SENSOR_ID"] = "test-sensor"

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
    assert "evidence" in body
    assert body["status"] in ("ok", "degraded")


def test_version(client):
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json()["version"]


def test_demo_and_recent(client):
    r = client.post("/api/telemetry/demo?count=4")
    assert r.status_code == 200
    assert r.json()["emitted"] == 4
    recent = client.get("/api/telemetry/recent?n=10").json()
    assert len(recent["samples"]) >= 1


def test_sample_ingest(client):
    r = client.post(
        "/api/telemetry/sample",
        json={"domain": "wifi", "metrics": {"rssi_dbm": -55, "demo": True}},
    )
    assert r.status_code == 200
    assert "evidence_hash" in r.json()


def test_domains_and_sensors(client):
    assert client.get("/api/domains").status_code == 200
    assert client.get("/api/sensors").status_code == 200


def test_evidence_endpoints(client):
    client.post("/api/telemetry/demo?count=2")
    v = client.get("/api/evidence/verify").json()
    assert "ok" in v
    tail = client.get("/api/evidence/tail?n=5").json()
    assert "records" in tail


def test_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json()["release"] == "public"
