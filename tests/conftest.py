"""Deterministic, per-test-isolated configuration.

Base environment is set at import time (before any test module imports
``main``), and an autouse fixture re-applies it and refreshes the shared
``settings`` object before every test. Tests that need a different
configuration use the ``titan_env`` fixture instead of mutating
``os.environ`` at module level, which leaks across modules at collection time.
"""
from __future__ import annotations

import os
import tempfile
from typing import Callable

import pytest

_SESSION_DIR = tempfile.mkdtemp(prefix="titan-test-")

BASE_ENV: dict[str, str] = {
    "CELL_TITAN_ENV": "development",
    "REQUIRE_AUTH": "false",
    "TITAN_API_TOKEN": "",
    "ALLOW_UNAUTHENTICATED_LOOPBACK": "true",
    "ADB_ENABLED": "true",
    "AUTO_DEMO": "false",
    "SENSOR_ID": "test-sensor",
    "EVIDENCE_DIR": os.path.join(_SESSION_DIR, "evidence"),
}

os.environ.update(BASE_ENV)


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch):
    from titan.config import settings

    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    settings.reload()
    yield
    monkeypatch.undo()
    settings.reload()


@pytest.fixture
def titan_env(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Override environment for one test and refresh shared settings in place."""
    from titan.config import settings

    def apply(**overrides: str) -> None:
        for key, value in overrides.items():
            monkeypatch.setenv(key, value)
        settings.reload()

    return apply
