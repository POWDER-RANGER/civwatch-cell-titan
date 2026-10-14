"""Console setup check:  python -m titan.adb [--json]

Resolves one verified adb, starts its server, diagnoses connected phones and
prints the same plain-language guidance the browser shows. Exit code 0 means an
approved phone connection exists (feature verification happens in the browser).
"""
from __future__ import annotations

import json
import os
import sys

from titan.adb.diagnosis import check_setup, host_os
from titan.adb.locate import resolve_adb


def main(argv: list[str]) -> int:
    res = resolve_adb()
    if res.available and res.path:
        os.environ.setdefault("ADBUTILS_ADB_PATH", res.path)
    diag, _devices = check_setup(res, host=host_os())
    if "--json" in argv:
        print(json.dumps({"adb": {k: v for k, v in res.to_dict().items() if k != "candidates"},
                          "setup": diag.to_dict()}))
    else:
        where = {"bundled": "built-in copy", "path": "your installed copy", "env": "configured copy"}
        if res.available:
            print(f"Phone connection tool: ready ({where.get(res.source or '', 'found')}, version {res.platform_tools or res.protocol}).")
        print(f"\n{diag.title}\n{diag.message}")
    return 0 if diag.ready else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
