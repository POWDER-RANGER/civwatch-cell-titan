"""Resolve one verified ADB executable for the whole process.

Resolution order (first candidate that passes ``adb version`` wins):

1. ``ADBUTILS_ADB_PATH`` — explicit operator override (also honoured by adbutils)
2. ``adb`` on PATH — the user's own Platform Tools
3. the adb binary shipped inside the ``adbutils`` wheel (Windows x64, Linux x64,
   macOS Intel). This removes the "install Platform Tools" step for most users.

"Found" always means the executable exists *and* reported a parseable version.
Every candidate is recorded so conflicting installations can be diagnosed.

CLI (used by setup_titan.py from inside the Titan venv)::

    python -m titan.adb.locate          # prints the resolution as JSON
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Literal, Mapping, Optional

# Wireless debugging pairing (`adb pair`) requires platform-tools >= 30.0.0.
MIN_PLATFORM_TOOLS: tuple[int, int, int] = (30, 0, 0)

Source = Literal["env", "path", "bundled"]
Status = Literal["found", "missing", "broken"]

VersionRunner = Callable[[str], "tuple[int, str, str]"]


@dataclass
class Candidate:
    path: str
    source: Source
    ok: bool
    platform_tools: Optional[str] = None
    protocol: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AdbResolution:
    status: Status
    path: Optional[str] = None
    source: Optional[Source] = None
    platform_tools: Optional[str] = None
    protocol: Optional[str] = None
    outdated: bool = False
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.status == "found"

    def to_dict(self) -> dict:
        return asdict(self)


def _version_tuple(v: str | None) -> tuple[int, ...]:
    if not v:
        return ()
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def parse_version_output(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return (platform_tools_version, protocol_version) from ``adb version``."""
    proto = re.search(r"Android Debug Bridge version\s+(\d+\.\d+\.\d+)", text)
    tools = re.search(r"^Version\s+(\d+\.\d+\.\d+)", text, re.M)
    return (tools.group(1) if tools else None, proto.group(1) if proto else None)


MIN_PROTOCOL: tuple[int, int, int] = (1, 0, 41)


def is_outdated(c: Candidate) -> bool:
    """Outdated if protocol < 1.0.41 or platform-tools < 30.0.0 (when reported)."""
    if _version_tuple(c.protocol) and _version_tuple(c.protocol) < MIN_PROTOCOL:
        return True
    return bool(c.platform_tools) and _version_tuple(c.platform_tools) < MIN_PLATFORM_TOOLS


def _default_version_runner(path: str) -> tuple[int, str, str]:
    p = subprocess.run([path, "version"], capture_output=True, text=True, timeout=10, check=False)
    return p.returncode, p.stdout or "", p.stderr or ""


def bundled_adb_path() -> Optional[str]:
    """Path of the adb shipped in the adbutils wheel, if this platform has one."""
    try:
        import adbutils  # noqa: F401
    except ImportError:
        return None
    import adbutils as _a

    module_file = getattr(_a, "__file__", None)   # absent on test doubles / namespace packages
    if not module_file:
        return None
    bin_dir = Path(module_file).resolve().parent / "binaries"
    exe = bin_dir / ("adb.exe" if os.name == "nt" else "adb")
    return str(exe) if exe.is_file() else None


def _probe(path: str, source: Source, run: VersionRunner, is_file: Callable[[str], bool]) -> Candidate:
    if not is_file(path):
        return Candidate(path=path, source=source, ok=False, error="not_a_file")
    try:
        rc, out, err = run(path)
    except subprocess.TimeoutExpired:
        return Candidate(path=path, source=source, ok=False, error="version_timeout")
    except PermissionError:
        return Candidate(path=path, source=source, ok=False, error="not_executable")
    except OSError as ex:
        return Candidate(path=path, source=source, ok=False, error=f"exec_failed:{type(ex).__name__}")
    tools, proto = parse_version_output(out + "\n" + err)
    if rc != 0 or not proto:
        return Candidate(path=path, source=source, ok=False, error="version_unparseable")
    return Candidate(path=path, source=source, ok=True, platform_tools=tools, protocol=proto)


def resolve_adb(
    env: Mapping[str, str] | None = None,
    which: Callable[[str], Optional[str]] = shutil.which,
    bundled: Callable[[], Optional[str]] = bundled_adb_path,
    run: VersionRunner = _default_version_runner,
    is_file: Callable[[str], bool] = os.path.isfile,
) -> AdbResolution:
    env = os.environ if env is None else env
    seen: set[str] = set()
    candidates: list[Candidate] = []

    def consider(path: Optional[str], source: Source) -> None:
        if not path:
            return
        key = os.path.normcase(os.path.realpath(path)) if os.path.exists(path) else path
        if key in seen:
            return
        seen.add(key)
        candidates.append(_probe(path, source, run, is_file))

    consider((env.get("ADBUTILS_ADB_PATH") or "").strip() or None, "env")
    consider(which("adb"), "path")
    consider(bundled(), "bundled")

    good = [c for c in candidates if c.ok]
    if not good:
        if not candidates:
            return AdbResolution(status="missing", error="adb_missing")
        return AdbResolution(status="broken", error=candidates[0].error or "adb_broken", candidates=candidates)

    # An explicit operator override always wins. Otherwise prefer a current
    # build over an outdated one (keeps wireless pairing possible), then order.
    if good[0].source == "env":
        chosen = good[0]
    else:
        chosen = sorted(good, key=lambda c: (is_outdated(c), good.index(c)))[0]
    warnings: list[str] = []
    protocols = {c.protocol for c in good}
    if len(protocols) > 1:
        # Different adb protocol revisions kill each other's server on port 5037.
        warnings.append("adb_version_conflict")
    if not candidates[0].ok:
        warnings.append("preferred_adb_unusable")
    elif candidates[0] is not chosen:
        warnings.append("outdated_adb_skipped")
    outdated = is_outdated(chosen)
    if outdated:
        warnings.append("adb_outdated")
    return AdbResolution(
        status="found",
        path=chosen.path,
        source=chosen.source,
        platform_tools=chosen.platform_tools,
        protocol=chosen.protocol,
        outdated=outdated,
        warnings=warnings,
        candidates=candidates,
    )


_cache: dict[str, object] = {"at": 0.0, "res": None}


def resolve_adb_cached(ttl: float = 60.0) -> AdbResolution:
    """Process-wide cached resolution. Misses/broken results are never cached."""
    import time

    now = time.monotonic()
    res = _cache["res"]
    if isinstance(res, AdbResolution) and res.available and now - float(_cache["at"]) < ttl:  # type: ignore[arg-type]
        return res
    res = resolve_adb()
    _cache.update(at=now, res=res)
    return res


def main() -> int:
    res = resolve_adb()
    print(json.dumps(res.to_dict()))
    return 0 if res.available else 1


if __name__ == "__main__":
    sys.exit(main())
