"""Runtime configuration. Production mode fail-closes unsafe defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    host: str = os.environ.get("HOST", "127.0.0.1")
    port: int = int(os.environ.get("PORT", "8000"))
    debug: bool = _bool("DEBUG", "true")
    env: str = os.environ.get("CELL_TITAN_ENV", "development")
    sensor_id: str = os.environ.get("SENSOR_ID", "civwatch-titan-local")
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./data/civwatch_titan.db")
    evidence_dir: str = os.environ.get("EVIDENCE_DIR", "./data/evidence")
    operator_contact: str = os.environ.get("OPERATOR_CONTACT", "")
    cors_origins: str = os.environ.get(
        "CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    )
    rate_limit_per_min: int = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
    max_body_bytes: int = int(os.environ.get("MAX_BODY_BYTES", "65536"))
    api_token: str = os.environ.get("TITAN_API_TOKEN", "")
    require_auth: bool = _bool("REQUIRE_AUTH", "false")
    allow_unauthenticated_loopback: bool = _bool("ALLOW_UNAUTHENTICATED_LOOPBACK", "false")
    adb_enabled: bool = _bool("ADB_ENABLED", "false")
    civint_base: str = os.environ.get(
        "CIVINT_BASE",
        "https://raw.githubusercontent.com/POWDER-RANGER/CivilianIntelligence/main/public/civint",
    )

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
