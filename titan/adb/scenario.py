"""Scenario engine for the ADB setup simulation lab (Layer A: mocked, deterministic).

A scenario describes initial host/ADB/device conditions, the expected setup
state and user-facing explanation, and optional recovery steps. The engine
feeds those conditions through the *production* resolver, parser, diagnosis
and state machine — only process I/O is faked.

Every result is classified ``source_classification = "simulation"``. A passing
scenario proves application logic, never that a real device behaved this way.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from titan.adb.devices import device_ref
from titan.adb.diagnosis import CapabilityResult, Diagnosis, check_setup
from titan.adb.locate import resolve_adb
from titan.adb.machine import ReadinessProof, SetupMachine
from titan.adb.messages import known_codes

CATALOG_SCHEMA_VERSION = "1.0"
REQUIRED_FIELDS = ("id", "name", "layer", "spec_ref", "initial", "actions", "expect",
                   "verification", "evidence", "timeout_retry")
_JARGON = re.compile(r"\b(adb|rsa|daemon|transport|serial|traceback|exception|errno)\b", re.I)
_QUOTED = re.compile(r'"[^"]*"')


def has_jargon(text: str) -> bool:
    """Prose must be jargon-free; quoted copy-paste literals (commands, package names) are exempt."""
    return bool(_JARGON.search(_QUOTED.sub("", text)))

DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "scenarios" / "adb_setup" / "catalog.v1.json"


@dataclass
class StepResult:
    step: str
    diagnosis: dict
    failures: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    id: str
    name: str
    layer: str
    status: str                     # passed | failed | untested
    source_classification: str = "simulation"
    reason: str = ""
    state_path: list[str] = field(default_factory=list)
    steps: list[StepResult] = field(default_factory=list)

    @property
    def failures(self) -> list[str]:
        return [f for s in self.steps for f in s.failures]


def load_catalog(path: Path | str = DEFAULT_CATALOG) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = validate_catalog(data)
    if problems:
        raise ValueError("invalid scenario catalog: " + "; ".join(problems))
    return data


def validate_catalog(data: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if data.get("schema_version") != CATALOG_SCHEMA_VERSION:
        problems.append(f"schema_version must be {CATALOG_SCHEMA_VERSION}")
    if data.get("source_classification") != "simulation":
        problems.append("catalog source_classification must be 'simulation'")
    ids: set[str] = set()
    for sc in data.get("scenarios", []):
        sid = sc.get("id", "<missing id>")
        if sid in ids:
            problems.append(f"duplicate id {sid}")
        ids.add(sid)
        if not sc.get("implemented", True):
            if not sc.get("untested_reason"):
                problems.append(f"{sid}: unimplemented scenario needs untested_reason")
            continue
        for f in REQUIRED_FIELDS:
            if f not in sc:
                problems.append(f"{sid}: missing {f}")
        code = sc.get("expect", {}).get("code")
        if code and code not in known_codes() and code not in ("adb_missing",):
            problems.append(f"{sid}: unknown expected code {code}")
    return problems


# ---------------------------------------------------------------- fakes

def _fake_resolution(adb: dict[str, Any]):
    """Build an AdbResolution by running the real resolver against faked I/O."""
    files: dict[str, dict] = {}
    env: dict[str, str] = {}
    which_path = bundled_path = None
    if adb.get("env"):
        env["ADBUTILS_ADB_PATH"] = "/fake/env/adb"
        files["/fake/env/adb"] = adb["env"]
    if adb.get("path"):
        which_path = "/fake/path/adb"
        files[which_path] = adb["path"]
    if adb.get("bundled"):
        bundled_path = "/fake/bundled/adb"
        files[bundled_path] = adb["bundled"]

    def run(p: str):
        spec = files[p]
        if spec.get("error") == "timeout":
            import subprocess
            raise subprocess.TimeoutExpired(p, 10)
        if spec.get("error") == "permission":
            raise PermissionError(p)
        return spec.get("returncode", 0), spec.get("version_output", ""), spec.get("stderr", "")

    return resolve_adb(env=env, which=lambda _n: which_path, bundled=lambda: bundled_path,
                       run=run, is_file=lambda p: p in files)


def _diagnose_conditions(cond: dict[str, Any]) -> tuple[Diagnosis, Any]:
    resolution = _fake_resolution(cond.get("adb", {}))

    def run_devices(_path: str):
        return (cond.get("devices_returncode", 0), cond.get("devices_output", ""),
                cond.get("devices_stderr", ""), bool(cond.get("devices_timed_out", False)))

    selected = cond.get("selected_serial")
    diag, devices = check_setup(resolution, host=cond.get("host", "unknown"), run_devices=run_devices,
                                selected_ref=device_ref(selected) if selected else None)
    cap = cond.get("capability")
    if cap and diag.state == "verifying":
        from titan.adb.diagnosis import diagnose
        diag = diagnose(resolution, devices, host=cond.get("host", "unknown"),
                        selected_ref=device_ref(selected) if selected else None,
                        capability=CapabilityResult(device_ref=device_ref(cap["serial"]), probes=cap["probes"]))
    return diag, resolution


def _check(expect: dict[str, Any], diag: Diagnosis, resolution, serials: list[str]) -> list[str]:
    f: list[str] = []
    d = diag.to_dict()
    for key in ("state", "code", "ready", "retryable", "action"):
        if key in expect and d[key] != expect[key]:
            f.append(f"{key}: expected {expect[key]!r}, got {d[key]!r}")
    if "adb_source" in expect and resolution.source != expect["adb_source"]:
        f.append(f"adb_source: expected {expect['adb_source']!r}, got {resolution.source!r}")
    if "device_count" in expect and len(diag.devices) != expect["device_count"]:
        f.append(f"device_count: expected {expect['device_count']}, got {len(diag.devices)}")
    if "transports" in expect and [x["transport"] for x in diag.devices] != expect["transports"]:
        f.append(f"transports: expected {expect['transports']}, got {[x['transport'] for x in diag.devices]}")
    if "warnings_exact" in expect and sorted(diag.warnings) != sorted(expect["warnings_exact"]):
        f.append(f"warnings: expected {expect['warnings_exact']}, got {diag.warnings}")
    for w in expect.get("warnings_include", []):
        if w not in diag.warnings:
            f.append(f"warning {w!r} missing (got {diag.warnings})")
    for frag in expect.get("message_contains", []):
        if frag.lower() not in diag.message.lower():
            f.append(f"message missing {frag!r}")
    if "verified_capabilities" in expect and diag.verified_capabilities != expect["verified_capabilities"]:
        f.append(f"verified_capabilities: expected {expect['verified_capabilities']}, got {diag.verified_capabilities}")
    if "device_ref_of" in expect and diag.device_ref != device_ref(expect["device_ref_of"]):
        f.append("device_ref does not match the expected device")
    # Universal invariants
    if has_jargon(diag.title):
        f.append(f"title contains technical jargon: {diag.title!r}")
    if has_jargon(diag.message):
        f.append(f"message contains technical jargon: {diag.message!r}")
    blob = json.dumps(d)
    for s in serials:
        if s and s in blob:
            f.append("raw device serial leaked into diagnosis output")
    if diag.state == "ready" and not diag.verified_capabilities:
        f.append("ready without verified capabilities")
    return f


def _serials(cond: dict[str, Any]) -> list[str]:
    out = []
    for line in cond.get("devices_output", "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.startswith(("List", "*")):
            out.append(parts[0])
    return out


def run_scenario(sc: dict[str, Any]) -> ScenarioResult:
    res = ScenarioResult(id=sc["id"], name=sc["name"], layer=sc.get("layer", "A"), status="untested")
    if not sc.get("implemented", True):
        res.reason = sc.get("untested_reason", "")
        return res

    machine = SetupMachine()
    steps = [("initial", sc["initial"], sc["expect"])]
    cond = dict(sc["initial"])
    for i, rec in enumerate(sc.get("recovery", [])):
        cond = {**cond, **rec.get("then", {})}
        steps.append((f"recovery[{i}]:{rec['action']}", dict(cond), rec["expect"]))

    for label, conditions, expect in steps:
        diag, resolution = _diagnose_conditions(conditions)
        failures = _check(expect, diag, resolution, _serials(conditions))
        try:
            machine.transition("checking", reason=label)
            if diag.state == "ready":
                if machine.state == "checking":
                    machine.transition("verifying", reason="connection confirmed")
                machine.transition("ready", reason=diag.code, proof=ReadinessProof(
                    device_ref=diag.device_ref or "", verified_capabilities=tuple(diag.verified_capabilities),
                    verified_at=datetime.now(timezone.utc).isoformat(timespec="seconds")))
            else:
                machine.transition(diag.state, reason=diag.code)
        except ValueError as ex:
            failures.append(f"state machine rejected path: {ex}")
        res.steps.append(StepResult(step=label, diagnosis=diag.to_dict(), failures=failures))

    res.state_path = machine.path()
    res.status = "failed" if res.failures else "passed"
    return res


def run_catalog(catalog: dict[str, Any], *, commit: str | None = None) -> dict[str, Any]:
    results = [run_scenario(sc) for sc in catalog["scenarios"]]
    totals = {k: sum(1 for r in results if r.status == k) for k in ("passed", "failed", "untested")}
    return {
        "report_schema": "titan.adb-scenario-report/1",
        "run_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_classification": "simulation",
        "layer": "A",
        "catalog": catalog.get("catalog"),
        "catalog_version": catalog.get("catalog_version"),
        "commit": commit,
        "totals": totals,
        "note": "Untested scenarios are not passes. Layer A proves application logic only; "
                "it does not establish real-device, host-driver, or radio behaviour.",
        "results": [
            {**{k: v for k, v in asdict(r).items() if k != "steps"},
             "failures": r.failures,
             "final": r.steps[-1].diagnosis if r.steps else None}
            for r in results
        ],
    }
