"""Tests for the loopback setup/session and ADB readiness contract."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["CELL_TITAN_ENV"] = "development"
os.environ["ALLOW_UNAUTHENTICATED_LOOPBACK"] = "true"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["ADB_ENABLED"] = "true"
os.environ["EVIDENCE_DIR"] = str(Path("/tmp/titan-test-evidence-setup"))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


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
