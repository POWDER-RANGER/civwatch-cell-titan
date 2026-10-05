"""CIVWATCH CELL TITAN - hardened public operational release."""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from titan import __version__
from titan.adb_collect import collect_cellular, collect_wifi
from titan.auth import LOCAL_SESSION_COOKIE, assert_boot_auth, is_loopback, local_session_token, require_adb_enabled, require_bearer, require_local_or_bearer, require_privileged, tokens_equal
from titan.config import settings
from titan.evidence import EvidenceChain
from titan.health_cache import cached_verify
from titan.live import hub
from titan.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from titan.schemas.api import CaptureIn, SampleIn
from titan.sensors import SensorRegistry
from titan.telemetry import Domain, RfSample, SampleBuffer, _utc

DOMAINS: tuple[Domain, ...] = ("cellular", "wifi", "d2d", "transport")

registry = SensorRegistry(settings.sensor_id)
buffer = SampleBuffer(capacity=2000)
chain = EvidenceChain(settings.evidence_dir, settings.sensor_id)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_boot_auth()
    Path(settings.evidence_dir).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    chain.append(
        "boot",
        {
            "version": __version__,
            "sensor_id": settings.sensor_id,
            "mode": "live",
            "platform": "cell-titan",
            "env": settings.env,
        },
    )
    yield


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
        "env": settings.env,
        "auth_required": bool(settings.api_token) or settings.require_auth or settings.env == "production",
        "adb_enabled": settings.adb_enabled,
        "bind_hint": settings.host,
        "civintelligence": "https://github.com/POWDER-RANGER/CivilianIntelligence",
    }


@app.get("/api/setup/session")
def setup_session(request: Request, response: Response) -> dict[str, Any]:
    if settings.env == "production" or not is_loopback(request):
        raise HTTPException(status_code=404, detail="local_setup_only")
    response.set_cookie(
        key=LOCAL_SESSION_COOKIE,
        value=local_session_token(),
        max_age=86400,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )
    return {
        "ok": True,
        "mode": "local_setup",
        "adb_enabled": settings.adb_enabled,
        "message": "Local browser session established; privileged ADB actions remain loopback-only.",
    }


@app.get("/api/setup/check")
def setup_check(request: Request) -> dict[str, Any]:
    if settings.env == "production" or not is_loopback(request):
        raise HTTPException(status_code=404, detail="local_setup_only")
    adb = shutil.which("adb")
    devices: list[dict[str, Any]] = []
    if adb:
        try:
            p = subprocess.run([adb, "devices", "-l"], capture_output=True, text=True, timeout=8, check=False)
            for line in p.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("List of devices attached"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({"serial": parts[0], "state": parts[1], "details": parts[2:]})
        except Exception as ex:
            devices.append({"error": str(ex)})
    return {
        "python": sys.version.split()[0],
        "adb": {"available": bool(adb), "path": adb, "devices": devices},
        "adb_enabled": settings.adb_enabled,
        "ready": bool(adb) and any(d.get("state") == "device" for d in devices if isinstance(d, dict)),
        "next": "unlock_device_and_accept_usb_debugging" if any(d.get("state") == "unauthorized" for d in devices if isinstance(d, dict)) else None,
    }


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": __version__, "service": "cell-titan"}


@app.get("/api/sensors", dependencies=[Depends(require_local_or_bearer)])
def list_sensors() -> dict[str, Any]:
    return {"sensors": registry.list()}


@app.post("/api/sensors/discover", dependencies=[Depends(require_privileged), Depends(require_adb_enabled)])
async def discover_sensors() -> dict[str, Any]:
    found = registry.discover_adb()
    rec = chain.append("sensor_discover", {"found": len(found), "items": found})
    await hub.publish({"type": "sensors", "found": found, "evidence_seq": rec.seq})
    return {"found": found, "evidence_seq": rec.seq, "evidence_hash": rec.hash}


@app.post("/api/sensors/capture", dependencies=[Depends(require_privileged), Depends(require_adb_enabled)])
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


@app.get("/api/domains", dependencies=[Depends(require_local_or_bearer)])
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
        metrics=body.metrics,
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


@app.get("/api/telemetry/recent", dependencies=[Depends(require_local_or_bearer)])
def recent_telemetry(
    n: int = Query(50, ge=1, le=500),
    domain: Domain | None = None,
) -> dict[str, Any]:
    return {"samples": buffer.recent(n, domain)}


@app.get("/api/evidence/verify", dependencies=[Depends(require_local_or_bearer)])
def evidence_verify() -> dict[str, Any]:
    return chain.verify()


@app.get("/api/evidence/tail", dependencies=[Depends(require_local_or_bearer)])
def evidence_tail(n: int = Query(20, ge=1, le=200)) -> dict[str, Any]:
    return {"records": chain.tail(n)}


@app.get("/api/status", dependencies=[Depends(require_local_or_bearer)])
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
        local_session = False
        if client_host in ("127.0.0.1", "::1", "localhost", "testclient") and settings.env != "production":
            cookie = (ws.cookies.get(LOCAL_SESSION_COOKIE) or "").strip()
            local_session = bool(cookie) and tokens_equal(cookie, local_session_token())
        if not open_loop and not local_session:
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
