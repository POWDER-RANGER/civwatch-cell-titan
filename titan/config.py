"""Runtime configuration. Production mode fail-closes unsafe defaults.

``settings`` is a single long-lived object. Modules that do
``from titan.config import settings`` keep a reference to it, so configuration
must be refreshed *in place* via ``settings.reload()`` — never by
``importlib.reload(titan.config)``, which would create a second, divergent
object and split the process into two configurations.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


class Settings:
    host: str
    port: int
    debug: bool
    env: str
    sensor_id: str
    database_url: str
    evidence_dir: str
    operator_contact: str
    cors_origins: str
    rate_limit_per_min: int
    max_body_bytes: int
    api_token: str
    require_auth: bool
    allow_unauthenticated_loopback: bool
    adb_enabled: bool
    civint_base: str

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> "Settings":
        """Re-read every value from the process environment, in place."""
        self.host = os.environ.get("HOST", "127.0.0.1")
        self.port = int(os.environ.get("PORT", "8000"))
        self.debug = _bool("DEBUG", "true")
        self.env = os.environ.get("CELL_TITAN_ENV", "development")
        self.sensor_id = os.environ.get("SENSOR_ID", "civwatch-titan-local")
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///./data/civwatch_titan.db")
        self.evidence_dir = os.environ.get("EVIDENCE_DIR", "./data/evidence")
        self.operator_contact = os.environ.get("OPERATOR_CONTACT", "")
        self.cors_origins = os.environ.get(
            "CORS_ORIGINS",
            "http://127.0.0.1:8000,http://localhost:8000",
        )
        self.rate_limit_per_min = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
        self.max_body_bytes = int(os.environ.get("MAX_BODY_BYTES", "65536"))
        self.api_token = os.environ.get("TITAN_API_TOKEN", "")
        self.require_auth = _bool("REQUIRE_AUTH", "false")
        self.allow_unauthenticated_loopback = _bool("ALLOW_UNAUTHENTICATED_LOOPBACK", "false")
        self.adb_enabled = _bool("ADB_ENABLED", "false")
        self.civint_base = os.environ.get(
            "CIVINT_BASE",
            "https://raw.githubusercontent.com/POWDER-RANGER/CivilianIntelligence/main/public/civint",
        )
        return self

    def cors_list(self) -> list[str]:
        out = []
        for o in self.cors_origins.split(","):
            o = o.strip()
            if not o or o == "*":
                continue
            out.append(o)
        if self.env == "production" and not out:
            return []
        return out


settings = Settings()
