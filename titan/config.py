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
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = int(os.environ.get("PORT", "8000"))
    debug: bool = _bool("DEBUG", "true")
    env: str = os.environ.get("CELL_TITAN_ENV", "development")
    sensor_id: str = os.environ.get("SENSOR_ID", "civwatch-titan-local")
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./data/civwatch_titan.db")
    evidence_dir: str = os.environ.get("EVIDENCE_DIR", "./data/evidence")
    operator_contact: str = os.environ.get("OPERATOR_CONTACT", "")
    cors_origins: str = os.environ.get("CORS_ORIGINS", "*")
    auto_demo: bool = _bool("AUTO_DEMO", "false")
    demo_interval_sec: float = float(os.environ.get("DEMO_INTERVAL_SEC", "15"))
    rate_limit_per_min: int = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
    max_body_bytes: int = int(os.environ.get("MAX_BODY_BYTES", "65536"))
    civint_base: str = os.environ.get(
        "CIVINT_BASE",
        "https://raw.githubusercontent.com/POWDER-RANGER/CivilianIntelligence/main/public/civint",
    )

    def cors_list(self) -> list[str]:
        if self.env == "production" and self.cors_origins.strip() == "*":
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
