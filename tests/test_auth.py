import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["EVIDENCE_DIR"] = str(Path("/tmp/titan-auth-ev"))
os.environ["AUTO_DEMO"] = "false"
os.environ["SENSOR_ID"] = "auth-test"
os.environ["CELL_TITAN_ENV"] = "development"
os.environ["TITAN_API_TOKEN"] = "test-secret-token-xyz"
os.environ["REQUIRE_AUTH"] = "true"
os.environ["ADB_ENABLED"] = "false"
os.environ["ALLOW_UNAUTHENTICATED_LOOPBACK"] = "false"

import importlib
import titan.config as cfg

importlib.reload(cfg)
import main as main_mod

importlib.reload(main_mod)


@pytest.fixture
def client():
    with TestClient(main_mod.app) as c:
        yield c


def test_read_health_open(client):
    assert client.get("/api/health").status_code == 200


def test_write_requires_token(client):
    r = client.post("/api/telemetry/demo?count=1")
    assert r.status_code == 401


def test_write_with_token(client):
    r = client.post(
        "/api/telemetry/demo?count=1",
        headers={"Authorization": "Bearer test-secret-token-xyz"},
    )
    assert r.status_code == 200


def test_bad_token_rejected(client):
    r = client.post(
        "/api/telemetry/demo?count=1",
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_adb_disabled(client):
    r = client.post(
        "/api/sensors/discover",
        headers={"Authorization": "Bearer test-secret-token-xyz"},
    )
    assert r.status_code == 403
    assert "adb_disabled" in r.json()["detail"]
