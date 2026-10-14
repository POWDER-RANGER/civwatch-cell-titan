"""Tests for the loopback setup/session and ADB readiness contract."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_local_setup_session_and_protected_read():
    with TestClient(app) as client:
        r = client.get("/api/setup/session")
        assert r.status_code == 200
        assert client.get("/api/sensors").status_code == 200


def test_setup_check_is_loopback_only():
    with TestClient(app) as client:
        r = client.get("/api/setup/check")
        assert r.status_code == 200
        body = r.json()
        assert "adb" in body
        assert "ready" in body
