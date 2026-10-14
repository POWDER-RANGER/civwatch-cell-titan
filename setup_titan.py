#!/usr/bin/env python3
"""One-click local Titan bootstrap.

Order matters: a compatible Python is selected first, then Titan's private
environment (which contains a built-in copy of the Android connection tool on
Windows x64, Linux x64 and Intel macOS), then configuration repair, then the
phone check. Every failure ends in a plain-language message, not a traceback.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".titan-venv"
ENV = ROOT / ".env"
STAMP = VENV / ".titan-requirements.sha256"
URL = "http://127.0.0.1:8000"
SUPPORTED = ((3, 11), (3, 12), (3, 13))   # pinned wheels (pydantic-core etc.) exist for these


def fail(message: str, code: int = 1) -> NoReturn:
    print("\n" + message)
    raise SystemExit(code)


def pyexe() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _find_supported_python() -> str | None:
    for major, minor in reversed(SUPPORTED):
        if os.name == "nt" and shutil.which("py"):
            try:
                p = subprocess.run(["py", f"-{major}.{minor}", "-c", "import sys;print(sys.executable)"],
                                   capture_output=True, text=True, timeout=20)
                if p.returncode == 0 and p.stdout.strip():
                    return p.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                pass
        exe = shutil.which(f"python{major}.{minor}")
        if exe:
            return exe
    return None


def ensure_python() -> None:
    if sys.version_info[:2] in SUPPORTED:
        return
    found = None if os.environ.get("TITAN_SETUP_REEXEC") else _find_supported_python()
    if found:
        print(f"Python {platform.python_version()} is too new/old for Cell Monitor; switching to {found}.")
        env = {**os.environ, "TITAN_SETUP_REEXEC": "1"}
        raise SystemExit(subprocess.call([found, str(Path(__file__).resolve()), *sys.argv[1:]], env=env))
    fail(
        f"Cell Monitor needs Python 3.11, 3.12 or 3.13, but this computer is running Python {platform.python_version()}.\n"
        "Install Python 3.13 from https://www.python.org/downloads/ (you can keep your current version), "
        "then run START-TITAN again."
    )


def _requirements_digest() -> str:
    h = hashlib.sha256((ROOT / "requirements.txt").read_bytes())
    h.update(platform.python_version().encode())
    return h.hexdigest()


def ensure_venv() -> None:
    try:
        if not pyexe().exists():
            print("Setting up Cell Monitor's private environment (first run only)…")
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], cwd=ROOT, check=True)
        digest = _requirements_digest()
        if STAMP.exists() and STAMP.read_text(encoding="utf-8").strip() == digest:
            return   # unchanged: no network needed, so offline relaunches work
        print("Installing Cell Monitor's components…")
        subprocess.run([str(pyexe()), "-m", "pip", "install", "-r", "requirements.txt", "-q",
                        "--disable-pip-version-check"], cwd=ROOT, check=True)
        STAMP.write_text(digest, encoding="utf-8")
    except subprocess.CalledProcessError:
        fail("Cell Monitor couldn't download its components. Check your internet connection and run START-TITAN again.\n"
             "(If you're behind a work or school network, it may block Python downloads.)")
    except OSError as ex:
        fail(f"Cell Monitor couldn't create its private environment ({type(ex).__name__}). "
             "Move the Cell Monitor folder somewhere you can write to (for example your Documents folder) and try again.")


def ensure_env() -> None:
    """Create .env, or repair one that lacks the local credential ADB requires."""
    if not ENV.exists():
        ENV.write_text("\n".join([
            "HOST=127.0.0.1", "PORT=8000", "DEBUG=false", "CELL_TITAN_ENV=development",
            "SENSOR_ID=civwatch-titan-local", "EVIDENCE_DIR=./data/evidence",
            "CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000",
            f"TITAN_API_TOKEN={secrets.token_urlsafe(32)}", "REQUIRE_AUTH=false",
            "ALLOW_UNAUTHENTICATED_LOOPBACK=true", "ADB_ENABLED=true",
            "RATE_LIMIT_PER_MIN=120", "MAX_BODY_BYTES=65536", "",
        ]), encoding="utf-8")
        return
    lines = ENV.read_text(encoding="utf-8").splitlines()
    token_lines = [i for i, l in enumerate(lines) if l.strip().startswith("TITAN_API_TOKEN=")]
    if token_lines and lines[token_lines[-1]].split("=", 1)[1].strip().strip('"\''):
        return
    new = f"TITAN_API_TOKEN={secrets.token_urlsafe(32)}"
    if token_lines:
        lines[token_lines[-1]] = new
    else:
        lines.append(new)
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Repaired Cell Monitor's local settings (added the missing local security key).")


def ensure_adb() -> bool:
    """Resolve one verified adb from inside the venv and print plain-language phone status."""
    try:
        p = subprocess.run([str(pyexe()), "-m", "titan.adb.locate"], cwd=ROOT,
                           capture_output=True, text=True, timeout=60)
        res = json.loads(p.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        res = {}
    if res.get("status") == "found" and res.get("path"):
        os.environ["ADBUTILS_ADB_PATH"] = res["path"]
    print()
    check = subprocess.run([str(pyexe()), "-m", "titan.adb"], cwd=ROOT, env=os.environ.copy(), timeout=90)
    return check.returncode == 0


def main() -> None:
    ensure_python()
    print("CIVWATCH Cell Monitor — one-click local setup")
    print("Cell Monitor stays on this computer (127.0.0.1) and only reads phones you connect and approve.")
    ensure_venv()
    ensure_env()
    try:
        phone_ready = ensure_adb()
    except subprocess.TimeoutExpired:
        phone_ready = False
    if not phone_ready:
        print("\nCell Monitor will open anyway — follow the steps on the page, then select Check ADB.")
    os.environ.update({
        "HOST": "127.0.0.1", "PORT": "8000", "CELL_TITAN_ENV": "development",
        "ALLOW_UNAUTHENTICATED_LOOPBACK": "true", "ADB_ENABLED": "true", "REQUIRE_AUTH": "false",
    })
    print(f"\nOpening {URL}")
    time.sleep(1)
    try:
        webbrowser.open(URL)
    except Exception:  # noqa: BLE001
        pass
    args = [str(pyexe()), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    if os.name == "nt":
        raise SystemExit(subprocess.call(args, cwd=ROOT))
    os.chdir(ROOT)
    os.execv(str(pyexe()), args)


if __name__ == "__main__":
    main()
