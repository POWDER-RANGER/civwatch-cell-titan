"""Bearer-auth boundary with REQUIRE_AUTH=true and a configured token."""
import pytest
from fastapi.testclient import TestClient

from main import app

TOKEN = "test-secret-token-xyz"


@pytest.fixture
def client(titan_env):
    titan_env(
        TITAN_API_TOKEN=TOKEN,
        REQUIRE_AUTH="true",
        ADB_ENABLED="false",
        ALLOW_UNAUTHENTICATED_LOOPBACK="false",
        SENSOR_ID="auth-test",
    )
    with TestClient(app) as c:
        yield c


def test_read_health_open(client):
    assert client.get("/api/health").status_code == 200


def test_write_requires_token(client):
    r = client.post("/api/telemetry/sample", json={"domain": "cellular", "metrics": {"rat": "LTE"}})
    assert r.status_code == 401


def test_write_with_token(client):
    r = client.post(
        "/api/telemetry/sample",
        json={"domain": "cellular", "metrics": {"rat": "LTE"}},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 200


def test_bad_token_rejected(client):
    r = client.post(
        "/api/telemetry/sample",
        json={"domain": "cellular", "metrics": {"rat": "LTE"}},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_adb_disabled(client):
    r = client.post("/api/sensors/discover", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 403
    assert "adb_disabled" in r.json()["detail"]


def test_observations_require_token_off_loopback_config(client):
    assert client.get("/api/observations").status_code == 401
    r = client.get("/api/observations", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.json()["schema_version"] == "1.0"
