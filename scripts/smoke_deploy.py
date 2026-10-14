#!/usr/bin/env python3
"""Post-deploy smoke check for a running CELL TITAN service. Stdlib only.

Usage:
    TITAN_API_TOKEN=... python scripts/smoke_deploy.py https://civwatch-cell-titan.onrender.com
    python scripts/smoke_deploy.py http://127.0.0.1:8000 --expect-version 0.1.3

Exit code 0 only when every check passes. Tolerates Render Free cold starts:
the first request is retried with backoff for up to --wake-timeout seconds.
The token is read from the environment, never from argv, so it stays out of
shell history and process listings.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

OBSERVATION_KEYS = {
    "schema_version", "service", "state", "owner_scope", "generated_at",
    "samples", "evidence", "evidence_verification", "privacy", "limitations",
}


def fetch(url: str, token: str | None = None, timeout: float = 30.0) -> tuple[int, dict | None]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def wake(base: str, wake_timeout: float) -> float:
    start = time.monotonic()
    delay = 2.0
    while True:
        try:
            status, _ = fetch(f"{base}/api/health", timeout=60.0)
            if status == 200:
                return time.monotonic() - start
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        if time.monotonic() - start > wake_timeout:
            raise SystemExit(f"FAIL wake: {base}/api/health not 200 within {wake_timeout:.0f}s")
        time.sleep(delay)
        delay = min(delay * 1.5, 15.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="Service base URL, no trailing slash")
    ap.add_argument("--expect-version", default=None)
    ap.add_argument("--wake-timeout", type=float, default=120.0)
    args = ap.parse_args()
    base = args.base.rstrip("/")
    token = os.environ.get("TITAN_API_TOKEN", "").strip() or None

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    waited = wake(base, args.wake_timeout)
    check("wake", True, f"{waited:.1f}s")

    status, health = fetch(f"{base}/api/health")
    check("health 200", status == 200, str(status))
    if health:
        check("health status ok", health.get("status") == "ok", str(health.get("status")))
        check("evidence chain verifies", bool(health.get("evidence", {}).get("ok")), json.dumps(health.get("evidence")))
        if health.get("env") == "production":
            check("production requires auth", health.get("auth_required") is True, str(health.get("auth_required")))
            check("production ADB disabled", health.get("adb_enabled") is False, str(health.get("adb_enabled")))

    status, ver = fetch(f"{base}/api/version")
    live_version = (ver or {}).get("version")
    check("version 200", status == 200, str(live_version))
    if args.expect_version:
        check("version matches", live_version == args.expect_version, f"live={live_version} expected={args.expect_version}")

    status, _ = fetch(f"{base}/api/observations")
    check("observations route deployed (not 404)", status != 404, str(status))
    if health and health.get("auth_required"):
        check("observations rejects anonymous", status == 401, str(status))

    if token:
        status, obs = fetch(f"{base}/api/observations?n=5", token=token)
        check("observations 200 with token", status == 200, str(status))
        if status == 200 and obs:
            missing = OBSERVATION_KEYS - set(obs)
            check("observation envelope complete", not missing, f"missing={sorted(missing)}" if missing else "")
            check("schema_version 1.0", obs.get("schema_version") == "1.0", str(obs.get("schema_version")))
            check("state honest", obs.get("state") in ("live", "demo", "unavailable"), str(obs.get("state")))
            check("owner_scope user_device", obs.get("owner_scope") == "user_device", str(obs.get("owner_scope")))
            check("no server-side discovery", obs.get("privacy", {}).get("server_side_discovery") is False, "")
        status, caps = fetch(f"{base}/api/capabilities", token=token)
        check("capabilities 200 with token", status == 200, str(status))
    else:
        check("token-authenticated checks", True, "SKIPPED: TITAN_API_TOKEN not set")

    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    print(f"\n{len(results) - failed}/{len(results)} checks passed against {base}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
