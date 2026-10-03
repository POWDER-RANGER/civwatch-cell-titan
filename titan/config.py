"""Runtime configuration. Env-overridable; no secrets required for local demo mode."""
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
    sensor_id: str = os.environ.get("SENSOR_ID", "civwatch-titan-local")
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./data/civwatch_titan.db")
    evidence_dir: str = os.environ.get("EVIDENCE_DIR", "./data/evidence")
    operator_contact: str = os.environ.get("OPERATOR_CONTACT", "")
    cors_origins: str = os.environ.get("CORS_ORIGINS", "*")
    auto_demo: bool = _bool("AUTO_DEMO", "false")
    demo_interval_sec: float = float(os.environ.get("DEMO_INTERVAL_SEC", "15"))
    civint_base: str = os.environ.get(
        "CIVINT_BASE",
        "https://raw.githubusercontent.com/POWDER-RANGER/CivilianIntelligence/main/public/civint",
    )


settings = Settings()
