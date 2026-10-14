#!/usr/bin/env python3
"""Physical-device acceptance check for a LOCAL Cell Titan. Stdlib only.

Run after START-TITAN and "Connect & Capture" with an authorized Android phone:

    python scripts/device_acceptance.py            # reads TITAN_API_TOKEN from ./.env
    python scripts/device_acceptance.py --report acceptance.json

Pass criteria (all required):
  1. /api/observations returns schema 1.0 with state "live".
  2. At least one sample has metrics.source == "adb" and metrics.available is true.
  3. The evidence chain contains a "telemetry_adb" record. Only the ADB capture
     route writes that kind, so samples POSTed through the API cannot satisfy it.
  4. The evidence chain verifies end to end.

The report records which fields the device actually exposed per domain, so the
capability registry can be checked against real hardware instead of assumptions.
Serials are redacted in the report by default.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_FIELDS = {
    "cellular": ["operator", "data_reg", "voice_reg", "rsrp_dbm", "mci"],
    "wifi": ["rssi_dbm", "freq_mhz", "wifi_info_present"],
}
REDACT = {"serial"}


def token_from_env_file(path: Path) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("TITAN_API_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def get(base: str, path: str, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(base + path, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {}
    except urllib.error.URLError as e:
        raise SystemExit(f"FAIL: cannot reach {base} ({e.reason}). Start Titan with START-TITAN first.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--env-file", default=".env")
    ap.add_argument("--report", default=None, help="Write a JSON acceptance report here")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    token = os.environ.get("TITAN_API_TOKEN", "").strip() or token_from_env_file(Path(args.env_file))

    status, obs = get(base, "/api/observations?n=200", token)
    if status != 200:
        raise SystemExit(f"FAIL: /api/observations returned {status}. Check TITAN_API_TOKEN / --env-file.")
    _, tail = get(base, "/api/evidence/tail?n=200", token)
    _, verify = get(base, "/api/evidence/verify", token)
    _, health = get(base, "/api/health", "")
    _, sensors = get(base, "/api/sensors", token)

    samples = obs.get("samples", [])
    adb = [s for s in samples if s.get("metrics", {}).get("source") == "adb"]
    adb_ok = [s for s in adb if s.get("metrics", {}).get("available") is True]
    kinds = [r.get("kind") for r in tail.get("records", [])]

    fields: dict[str, dict[str, bool]] = {}
    for domain, expected in EXPECTED_FIELDS.items():
        seen = [s["metrics"] for s in adb_ok if s.get("domain") == domain]
        fields[domain] = {f: any(f in m for m in seen) for f in expected}

    checks = [
        ("observation schema 1.0", obs.get("schema_version") == "1.0", obs.get("schema_version")),
        ("observation state live", obs.get("state") == "live", obs.get("state")),
        ("ADB-sourced sample with data", bool(adb_ok), f"{len(adb_ok)} of {len(adb)} ADB samples available"),
        ("telemetry_adb evidence record", "telemetry_adb" in kinds, f"{kinds.count('telemetry_adb')} records"),
        ("evidence chain verifies", verify.get("ok") is True, json.dumps({k: verify.get(k) for k in ("ok", "length", "broken_at")})),
    ]

    failed = 0
    for name, ok, detail in checks:
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:<32} {detail}")
    print("\nFields exposed by this device (ADB samples with data):")
    for domain, present in fields.items():
        got = [f for f, v in present.items() if v] or ["none"]
        missing = [f for f, v in present.items() if not v]
        print(f"  {domain:<9} present: {', '.join(got)}" + (f"  | absent: {', '.join(missing)}" if missing else ""))

    if args.report:
        device_meta = [
            {k: (s.get("meta") or {}).get(k) for k in ("model", "android")}
            for s in sensors.get("sensors", [])
            if s.get("mode") == "adb"
        ]
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "titan_version": health.get("version"),
            "passed": failed == 0,
            "checks": [{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in checks],
            "fields_present": fields,
            "evidence_tip": (tail.get("records") or [{}])[-1].get("hash"),
            "sample_count": {"total": len(samples), "adb": len(adb), "adb_available": len(adb_ok)},
            "sample_example": {
                k: ("<redacted>" if k in REDACT else v)
                for k, v in (adb_ok[-1]["metrics"] if adb_ok else {}).items()
                if k != "mci"
            },
            "device_meta": device_meta[:1],
        }
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport written: {args.report}")

    print(f"\n{'ACCEPTED' if failed == 0 else 'NOT ACCEPTED'}: {len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
