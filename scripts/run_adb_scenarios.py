#!/usr/bin/env python3
"""Run the Layer A ADB setup scenario catalog and write a structured report.

    python scripts/run_adb_scenarios.py [--catalog PATH] [--out report.json]

Exit status: 0 when every implemented scenario passed, 1 otherwise.
Untested scenarios are listed with their reason and are never counted as passes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from titan.adb.scenario import DEFAULT_CATALOG, load_catalog, run_catalog  # noqa: E402


def _commit() -> str | None:
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        return p.stdout.strip() or None
    except OSError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    report = run_catalog(load_catalog(args.catalog), commit=_commit())
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    t = report["totals"]
    print(f"ADB setup scenarios — catalog {report['catalog_version']} — commit {(report['commit'] or 'unknown')[:12]}")
    print(f"source_classification={report['source_classification']}  layer={report['layer']}")
    for r in report["results"]:
        mark = {"passed": "PASS", "failed": "FAIL", "untested": "----"}[r["status"]]
        tail = " → ".join(r["state_path"]) if r["status"] != "untested" else r["reason"]
        print(f"  {mark} {r['id']:8} {r['name'][:58]:58} {tail}")
        for f in r["failures"]:
            print(f"         ✗ {f}")
    print(f"\npassed={t['passed']} failed={t['failed']} untested={t['untested']} (untested ≠ passed)")
    return 0 if t["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
