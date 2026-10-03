"""CIVWATCH CELL TITAN - hardened public operational release."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from titan import __version__
from titan.adb_collect import collect_cellular, collect_wifi
from titan.auth import assert_boot_auth, require_adb_enabled, require_bearer, tokens_equal
from titan.config import settings
from titan.evidence import EvidenceChain
from titan.health_cache import cached_verify
from titan.live import hub
from titan.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from titan.schemas.api import CaptureIn, SampleIn
from titan.sensors import SensorRegistry
from titan.telemetry import Domain, RfSample, SampleBuffer, synthetic_sample, _utc

DOMAINS: tuple[Domain, ...] = ("cellular", "wifi", "d2d", "transport")

registry = SensorRegistry(settings.sensor_id)
buffer = SampleBuffer(capacity=2000)
chain = EvidenceChain(settings.evidence_dir, settings.sensor_id)
_demo_task: asyncio.Task | None = None


async def _demo_loop(interval: float) -> None:
    while True:
        for domain in DOMAINS:
            sample = synthetic_sample(domain, settings.sensor_id)
            buffer.push(sample)
            rec = chain.append(
                "telemetry_demo",
                {"domain": sample.domain, "sensor_id": sample.sensor_id, "metrics": sample.metrics},
            )
            await hub.publish(
                {
                    "type": "telemetry",
                    "sample": sample.to_dict(),
                    "evidence_seq": rec.seq,
                    "evidence_hash": rec.hash,
                }
            )
        registry.touch(settings.sensor_id)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _demo_task
    assert_boot_auth()
    Path(settings.evidence_dir).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    chain.append(
        "boot",
        {
            "version": __version__,
            "sensor_id": settings.sensor_id,
            "mode": "demo",
            "platform": "cell-titan",
            "auto_demo": settings.auto_demo,
            "env": settings.env,
        },
    )
    if settings.auto_demo:
        _demo_task = asyncio.create_task(_demo_loop(settings.demo_interval_sec))
    yield
    if _demo_task:
        _demo_task.cancel()
        try:
            await _demo_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="CIVWATCH CELL TITAN",
    description="Defensive RF observability for CIVINTELLIGENCE.",
    version=__version__,
    lifespan=lifespan,
    contact={"name": "POWDER-RANGER / CIVWATCH", "url": "https://github.com/POWDER-RANGER/civwatch-cell-titan"},
    license_info={"name": "MIT"},
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_body_bytes)
app.add_middleware(RateLimitMiddleware, limit=settings.rate_limit_per_min, window_sec=60.0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    v = cached_verify(chain)
    return {
        "status": "ok" if v["ok"] else "degraded",
        "service": "cell-titan",
        "version": __version__,
        "sensor_id": settings.sensor_id,
        "evidence": v,
        "buffer": buffer.stats(),
        "listeners": hub.listener_count,
        "auto_demo": settings.auto_demo,
        "env": settings.env,
        "auth_required": bool(settings.api_token) or settings.require_auth or settings.env == "production",
        "adb_enabled": settings.adb_enabled,
        "bind_hint": settings.host,
        "civintelligence": "https://github.com/POWDER-RANGER/CivilianIntelligence",
    }


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": __version__, "service": "cell-titan"}


@app.get("/api/sensors")
def list_sensors() -> dict[str, Any]:
    return {"sensors": registry.list()}


@app.post("/api/sensors/discover", dependencies=[Depends(require_bearer), Depends(require_adb_enabled)])
async def discover_sensors() -> dict[str, Any]:
    found = registry.discover_adb()
    rec = chain.append("sensor_discover", {"found": len(found), "items": found})
    await hub.publish({"type": "sensors", "found": found, "evidence_seq": rec.seq})
    return {"found": found, "evidence_seq": rec.seq, "evidence_hash": rec.hash}


@app.post("/api/sensors/capture", dependencies=[Depends(require_bearer), Depends(require_adb_enabled)])
async def capture_adb(body: CaptureIn) -> Any:
    sensor = registry.get(body.sensor_id)
    if not sensor or sensor.mode != "adb":
        return JSONResponse(
            status_code=404,
            content={"error": "adb_sensor_not_found", "hint": "POST /api/sensors/discover first"},
        )
    serial = str(sensor.meta.get("serial") or body.sensor_id.replace("adb-", "", 1))
    emitted = []
    for domain in body.domains:
        metrics = collect_cellular(serial) if domain == "cellular" else collect_wifi(serial)
        sample = RfSample(domain=domain, sensor_id=body.sensor_id, ts=_utc(), metrics=metrics)
        buffer.push(sample)
        rec = chain.append(
            "telemetry_adb",
            {"domain": domain, "sensor_id": body.sensor_id, "metrics": metrics},
        )
        event = {
            "type": "telemetry",
            "sample": sample.to_dict(),
            "evidence_seq": rec.seq,
            "evidence_hash": rec.hash,
        }
        await hub.publish(event)
        emitted.append(event)
    registry.touch(body.sensor_id)
    return {"emitted": len(emitted), "items": emitted}


@app.get("/api/domains")
def list_domains() -> dict[str, Any]:
    return {
        "domains": [
            {"id": "cellular", "protocols": ["LTE", "5G NR", "GSM"], "status": "demo+adb"},
            {"id": "wifi", "protocols": ["802.11"], "status": "demo+adb"},
            {"id": "d2d", "protocols": ["LTE-D2D", "NR Sidelink"], "status": "demo"},
            {"id": "transport", "protocols": ["Bluetooth", "BLE", "NFC"], "status": "demo"},
        ]
    }


@app.post("/api/telemetry/sample", dependencies=[Depends(require_bearer)])
async def ingest_sample(body: SampleIn) -> dict[str, Any]:
    sid = body.sensor_id or settings.sensor_id
    sample = RfSample(
        domain=body.domain,
        sensor_id=sid,
        ts=_utc(),
        metrics={**body.metrics, "demo": bool(body.metrics.get("demo", False))},
    )
    buffer.push(sample)
    registry.touch(sid)
    rec = chain.append(
        "telemetry",
        {"domain": sample.domain, "sensor_id": sid, "metrics": sample.metrics},
    )
    out = {"sample": sample.to_dict(), "evidence_seq": rec.seq, "evidence_hash": rec.hash}
    await hub.publish({"type": "telemetry", **out})
    return out


@app.post("/api/telemetry/demo", dependencies=[Depends(require_bearer)])
async def demo_burst(count: int = Query(4, ge=1, le=40)) -> dict[str, Any]:
    out = []
    for i in range(count):
        domain = DOMAINS[i % len(DOMAINS)]
        sample = synthetic_sample(domain, settings.sensor_id)
        buffer.push(sample)
        rec = chain.append(
            "telemetry_demo",
            {"domain": sample.domain, "sensor_id": sample.sensor_id, "metrics": sample.metrics},
        )
        item = {"sample": sample.to_dict(), "evidence_seq": rec.seq, "evidence_hash": rec.hash}
        await hub.publish({"type": "telemetry", **item})
        out.append(item)
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
        "version": __version__,
        "role": "Defensive RF observability pillar of CIVINTELLIGENCE",
        "upstream": "https://github.com/POWDER-RANGER/CivilianIntelligence",
        "release": "public",
        "assurance": "hash-chain+strict-schema+rate-limit+bearer-auth",
        "health": health(),
        "sensors": registry.list(),
        "domains": list_domains()["domains"],
    }


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket) -> None:
    await ws.accept()
    need = bool(settings.api_token) or settings.require_auth or settings.env == "production"
    if need:
        client_host = ws.client.host if ws.client else ""
        loop = client_host in ("127.0.0.1", "::1", "localhost", "testclient")
        open_loop = (
            settings.allow_unauthenticated_loopback
            and loop
            and not settings.api_token
            and settings.env != "production"
        )
        if not open_loop:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
                if len(raw) > 4096:
                    await ws.close(code=4401)
                    return
                msg = json.loads(raw)
                tok = str(msg.get("token") or "")
                if msg.get("type") != "auth" or not tokens_equal(tok, settings.api_token):
                    await ws.close(code=4401)
                    return
            except Exception:
                await ws.close(code=4401)
                return
    q = hub.subscribe()
    try:
        await ws.send_json({"type": "hello", "version": __version__, "sensor_id": settings.sensor_id})
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=25.0)
                await ws.send_text(msg)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(q)


STATIC = Path(__file__).parent / "static"
if STATIC.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC)), name="assets")


@app.get("/", response_class=HTMLResponse)
def index() -> Any:
    index_path = STATIC / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>CELL TITAN</h1><p>API up. See <a href='/docs'>/docs</a>.</p>")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
