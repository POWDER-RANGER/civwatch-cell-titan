"""CIVWATCH CELL TITAN — FastAPI entrypoint.

Defensive RF observability baseline. Demo mode works with zero hardware.
ADB sensors are optional. Evidence is hash-chained and append-only.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from titan.config import settings
from titan.evidence import EvidenceChain
from titan.sensors import SensorRegistry
from titan.telemetry import Domain, SampleBuffer, synthetic_sample

DOMAINS: tuple[Domain, ...] = ("cellular", "wifi", "d2d", "transport")

registry = SensorRegistry(settings.sensor_id)
buffer = SampleBuffer(capacity=1000)
chain = EvidenceChain(settings.evidence_dir, settings.sensor_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(settings.evidence_dir).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    chain.append(
        "boot",
        {
            "version": "0.1.0",
            "sensor_id": settings.sensor_id,
            "mode": "demo",
            "platform": "cell-titan",
        },
    )
    yield


app = FastAPI(
    title="CIVWATCH CELL TITAN",
    description="Defensive RF observability — federated sensors, hash-chained evidence.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SampleIn(BaseModel):
    domain: Literal["cellular", "wifi", "d2d", "transport"]
    metrics: dict[str, Any] = Field(default_factory=dict)
    sensor_id: str | None = None


@app.get("/api/health")
def health() -> dict[str, Any]:
    v = chain.verify()
    return {
        "status": "ok" if v["ok"] else "degraded",
        "service": "cell-titan",
        "version": "0.1.0",
        "sensor_id": settings.sensor_id,
        "evidence": v,
        "buffer": buffer.stats(),
        "civintelligence": "https://github.com/POWDER-RANGER/CivilianIntelligence",
    }


@app.get("/api/sensors")
def list_sensors() -> dict[str, Any]:
    return {"sensors": registry.list()}


@app.post("/api/sensors/discover")
def discover_sensors() -> dict[str, Any]:
    found = registry.discover_adb()
    chain.append("sensor_discover", {"found": len(found), "items": found})
    return {"found": found}


@app.get("/api/domains")
def list_domains() -> dict[str, Any]:
    return {
        "domains": [
            {"id": "cellular", "protocols": ["LTE", "5G NR", "GSM"], "status": "demo"},
            {"id": "wifi", "protocols": ["802.11"], "status": "demo"},
            {"id": "d2d", "protocols": ["LTE-D2D", "NR Sidelink"], "status": "demo"},
            {"id": "transport", "protocols": ["Bluetooth", "BLE", "NFC"], "status": "demo"},
        ]
    }


@app.post("/api/telemetry/sample")
def ingest_sample(body: SampleIn) -> dict[str, Any]:
    sid = body.sensor_id or settings.sensor_id
    from titan.telemetry import RfSample, _utc

    sample = RfSample(
        domain=body.domain,
        sensor_id=sid,
        ts=_utc(),
        metrics={**body.metrics, "demo": body.metrics.get("demo", False)},
    )
    buffer.push(sample)
    registry.touch(sid)
    rec = chain.append(
        "telemetry",
        {"domain": sample.domain, "sensor_id": sid, "metrics": sample.metrics},
    )
    return {"sample": sample.to_dict(), "evidence_seq": rec.seq, "evidence_hash": rec.hash}


@app.post("/api/telemetry/demo")
def demo_burst(count: int = Query(4, ge=1, le=40)) -> dict[str, Any]:
    out = []
    for i in range(count):
        domain = DOMAINS[i % len(DOMAINS)]
        sample = synthetic_sample(domain, settings.sensor_id)
        buffer.push(sample)
        rec = chain.append(
            "telemetry_demo",
            {"domain": sample.domain, "sensor_id": sample.sensor_id, "metrics": sample.metrics},
        )
        out.append({"sample": sample.to_dict(), "evidence_seq": rec.seq})
    registry.touch(settings.sensor_id)
    return {"emitted": len(out), "items": out}


@app.get("/api/telemetry/recent")
def recent_telemetry(
    n: int = Query(50, ge=1, le=500),
    domain: Domain | None = None,
) -> dict[str, Any]:
    return {"samples": buffer.recent(n, domain)}


@app.get("/api/evidence/verify")
def evidence_verify() -> dict[str, Any]:
    return chain.verify()


@app.get("/api/evidence/tail")
def evidence_tail(n: int = Query(20, ge=1, le=200)) -> dict[str, Any]:
    return {"records": chain.tail(n)}


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "platform": "CIVWATCH CELL TITAN",
        "role": "Defensive RF observability pillar of CIVINTELLIGENCE",
        "upstream": "https://github.com/POWDER-RANGER/CivilianIntelligence",
        "health": health(),
        "sensors": registry.list(),
        "domains": list_domains()["domains"],
    }


STATIC = Path(__file__).parent / "static"
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> Any:
    index_path = STATIC / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        "<h1>CELL TITAN</h1><p>API up. See <a href='/docs'>/docs</a> and <a href='/api/health'>/api/health</a>.</p>"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
