#!/usr/bin/env python3
"""One-click local Titan bootstrap for users who can use Android ADB."""
from __future__ import annotations
import os, platform, secrets, shutil, subprocess, sys, time, webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VENV=ROOT/".titan-venv"
ENV=ROOT/".env"
URL="http://127.0.0.1:8000"

def run(cmd, *, check=False):
    return subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=check)

def pyexe():
    return VENV/("Scripts/python.exe" if os.name=="nt" else "bin/python")

def ensure_python():
    if sys.version_info < (3,11) or sys.version_info >= (3,14):
        raise SystemExit(f"Python 3.11–3.13 is required; found {platform.python_version()}.")

def ensure_adb():
    adb=shutil.which("adb")
    if not adb:
        print("\nADB was not found on PATH.")
        print("Install Android SDK Platform Tools, reopen this launcher, and try again.")
        return False
    run([adb,"start-server"])
    p=run([adb,"devices","-l"])
    print("\nADB devices:\n"+p.stdout.strip())
    return any(line.strip() and not line.startswith("List of devices") and len(line.split())>=2 and line.split()[1]=="device"
               for line in p.stdout.splitlines())

def ensure_venv():
    if not pyexe().exists():
        print("Creating Titan virtual environment…")
        subprocess.run([sys.executable,"-m","venv",str(VENV)],cwd=ROOT,check=True)
    print("Installing/refreshing Titan dependencies…")
    subprocess.run([str(pyexe()),"-m","pip","install","-r","requirements.txt","-q"],cwd=ROOT,check=True)

def ensure_env():
    if ENV.exists():
        return
    token=secrets.token_urlsafe(32)
    ENV.write_text("\n".join([
        "HOST=127.0.0.1","PORT=8000","DEBUG=false","CELL_TITAN_ENV=development",
        "SENSOR_ID=civwatch-titan-local","EVIDENCE_DIR=./data/evidence",
        "CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000",
        f"TITAN_API_TOKEN={token}","REQUIRE_AUTH=false",
        "ALLOW_UNAUTHENTICATED_LOOPBACK=true","ADB_ENABLED=true",
        "RATE_LIMIT_PER_MIN=120","MAX_BODY_BYTES=65536","",
    ]),encoding="utf-8")

def main():
    ensure_python()
    print("CELL TITAN — one-click local setup")
    print("This launcher keeps Titan on localhost and enables ADB only for the local collector.")
    adb_ready=ensure_adb()
    ensure_venv(); ensure_env()
    if adb_ready:
        print("\nADB is ready. Unlock your phone and accept the USB debugging prompt if Android asks.")
    else:
        print("\nTitan will start even without a device. Connect/authorize Android, then use Discover ADB in the browser.")
    os.environ.update({
        "HOST":"127.0.0.1","PORT":"8000","CELL_TITAN_ENV":"development",
        "ALLOW_UNAUTHENTICATED_LOOPBACK":"true","ADB_ENABLED":"true","REQUIRE_AUTH":"false",
    })
    print(f"\nOpening {URL}")
    time.sleep(1)
    try: webbrowser.open(URL)
    except Exception: pass
    os.execv(str(pyexe()),[str(pyexe()),"-m","uvicorn","main:app","--host","127.0.0.1","--port","8000"])

if __name__=="__main__":
    main()
