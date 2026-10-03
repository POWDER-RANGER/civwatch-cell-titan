"""Strict request/response contracts. Invalid input is rejected before side effects."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

DomainName = Literal["cellular", "wifi", "d2d", "transport"]


class SampleIn(BaseModel):
    model_config = {"extra": "forbid"}

    domain: DomainName
    metrics: dict[str, Any] = Field(default_factory=dict, max_length=64)
    sensor_id: str | None = Field(default=None, max_length=128)

    @field_validator("metrics")
    @classmethod
    def metrics_bounded(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > 64:
            raise ValueError("metrics may contain at most 64 keys")
        for k, val in v.items():
            if not isinstance(k, str) or len(k) > 64:
                raise ValueError("metric keys must be strings ≤64 chars")
            if isinstance(val, str) and len(val) > 2048:
                raise ValueError("metric string values must be ≤2048 chars")
            if isinstance(val, (list, dict)):
                raise ValueError("metric values must be scalars")
        return v


class CaptureIn(BaseModel):
    model_config = {"extra": "forbid"}

    sensor_id: str = Field(..., min_length=1, max_length=128)
    domains: list[Literal["cellular", "wifi"]] = Field(
        default_factory=lambda: ["cellular", "wifi"],
        max_length=2,
    )


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    sensor_id: str
    evidence: dict[str, Any]
    buffer: dict[str, Any]
    listeners: int
    auto_demo: bool
    civintelligence: str


class StatusOut(BaseModel):
    platform: str
    version: str
    role: str
    upstream: str
    release: str
    health: dict[str, Any]
    sensors: list[dict[str, Any]]
    domains: list[dict[str, Any]]
