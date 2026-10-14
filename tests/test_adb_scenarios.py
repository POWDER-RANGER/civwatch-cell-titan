"""Layer A scenario regression suite + invariants of the setup engine.

Configuration-independent: nothing here imports ``main`` or reads Settings.
"""
from __future__ import annotations

import copy
import json
import os

import pytest

from titan.adb.devices import device_ref, parse_devices
from titan.adb.diagnosis import CapabilityResult, check_setup, diagnose
from titan.adb.locate import AdbResolution, bundled_adb_path, resolve_adb
from titan.adb.machine import InvalidTransition, ReadinessProof, SetupMachine, UnverifiedReadiness
from titan.adb.messages import known_codes, message_for
from titan.adb.scenario import has_jargon, load_catalog, run_catalog, run_scenario, validate_catalog

CATALOG = load_catalog()
IMPLEMENTED = [s for s in CATALOG["scenarios"] if s.get("implemented", True)]


def test_catalog_is_valid_and_simulation_classified():
    assert validate_catalog(CATALOG) == []
    assert CATALOG["source_classification"] == "simulation"
    assert len(IMPLEMENTED) >= 30


@pytest.mark.parametrize("scenario", IMPLEMENTED, ids=[s["id"] for s in IMPLEMENTED])
def test_scenario(scenario):
    result = run_scenario(scenario)
    assert result.status == "passed", "\n".join(result.failures)


def test_report_never_counts_untested_as_passed():
    report = run_catalog(CATALOG, commit="test")
    untested = [s for s in CATALOG["scenarios"] if not s.get("implemented", True)]
    assert report["totals"]["untested"] == len(untested) > 0
    assert report["totals"]["passed"] + report["totals"]["failed"] == len(IMPLEMENTED)
    assert report["source_classification"] == "simulation"
    assert all(r["status"] == "untested" for r in report["results"] if r["id"] in {u["id"] for u in untested})


# ------------------------------------------------------------ engine self-tests

def test_engine_detects_wrong_expectation():
    sc = copy.deepcopy(next(s for s in IMPLEMENTED if s["id"] == "ADB-021"))
    sc["expect"]["state"] = "ready"
    assert run_scenario(sc).status == "failed"


def test_engine_detects_serial_leak(monkeypatch):
    from titan.adb import devices as dev_mod

    monkeypatch.setattr(dev_mod.AdbDevice, "public", lambda self: {"device_ref": self.serial, "category": self.category,
                                                                   "transport": self.transport, "adb_state": self.adb_state})
    sc = next(s for s in IMPLEMENTED if s["id"] == "ADB-002")
    result = run_scenario(sc)
    assert result.status == "failed"
    assert any("serial leaked" in f for f in result.failures)


def test_validate_catalog_rejects_untested_without_reason():
    bad = copy.deepcopy(CATALOG)
    bad["scenarios"].append({"id": "X-1", "name": "x", "layer": "B", "implemented": False})
    assert any("untested_reason" in p for p in validate_catalog(bad))


# ------------------------------------------------------------ state machine

def test_machine_rejects_ready_without_proof():
    m = SetupMachine()
    m.transition("checking", reason="t")
    m.transition("verifying", reason="t")
    with pytest.raises(UnverifiedReadiness):
        m.transition("ready", reason="t")
    with pytest.raises(UnverifiedReadiness):
        m.transition("ready", reason="t", proof=ReadinessProof("dev-x", (), "now"))
    m.transition("ready", reason="t", proof=ReadinessProof("dev-x", ("wifi",), "now"))
    assert m.state == "ready"


def test_machine_rejects_invalid_transitions():
    m = SetupMachine()
    with pytest.raises(InvalidTransition):
        m.transition("ready", reason="skip", proof=ReadinessProof("dev-x", ("wifi",), "now"))
    m.transition("checking", reason="t")
    m.transition("action_required", reason="t")
    with pytest.raises(InvalidTransition):
        m.transition("verifying", reason="UI may not jump past a re-check")


def test_leaving_ready_voids_proof():
    m = SetupMachine()
    for s in ("checking", "verifying"):
        m.transition(s, reason="t")
    m.transition("ready", reason="t", proof=ReadinessProof("dev-x", ("wifi",), "now"))
    m.transition("checking", reason="recheck")
    assert m.proof is None


# ------------------------------------------------------------ parser

def test_parse_no_permissions_is_one_state():
    out = ("List of devices attached\n"
           "ABC123\tno permissions (missing udev rules? user is in the plugdev group); "
           "see [http://developer.android.com/tools/device.html] usb:1-1 transport_id:7\n")
    (d,) = parse_devices(out)
    assert d.adb_state == "no permissions"
    assert d.category == "no_permissions"
    assert d.details == {"usb": "1-1", "transport_id": "7"}
    assert "udev" in d.note


def test_parse_keeps_unknown_states_unknown():
    (d,) = parse_devices("List of devices attached\nXYZ\tsomething-new usb:1-1\n")
    assert d.category == "unknown"


def test_public_view_has_no_serial():
    (d,) = parse_devices("List of devices attached\nSECRETSERIAL123\tdevice usb:1-1 model:Pixel_7\n")
    assert "SECRETSERIAL123" not in json.dumps(d.public())
    assert d.public()["device_ref"] == device_ref("SECRETSERIAL123")


# ------------------------------------------------------------ messages

@pytest.mark.parametrize("code", sorted(known_codes()))
@pytest.mark.parametrize("host", ["windows", "macos", "linux", "unknown"])
def test_messages_are_plain_language(code, host):
    m = message_for(code, host)
    assert m.title and m.message
    assert not has_jargon(m.title), m.title
    assert not has_jargon(m.message), m.message
    if code != "ready":
        assert m.action_label, f"{code} needs a visible recovery action"


# ------------------------------------------------------------ resolver (real process, no device)

def test_resolver_finds_bundled_adb_when_path_has_none():
    path = bundled_adb_path()
    if not path:
        pytest.skip("adbutils ships no adb for this platform (e.g. Apple Silicon / ARM Linux)")
    res = resolve_adb(env={}, which=lambda _n: None)
    assert res.available and res.source == "bundled"
    assert res.protocol and res.protocol.startswith("1.0.")


def test_check_setup_with_missing_resolution_never_runs_adb():
    called = []
    diag, devices = check_setup(AdbResolution(status="missing", error="adb_missing"), host="linux",
                                run_devices=lambda p: called.append(p) or (0, "", "", False))
    assert diag.code == "adb_missing" and devices == [] and called == []


def test_capability_for_other_device_does_not_grant_ready():
    devices = parse_devices("List of devices attached\nAAA\tdevice usb:1-1\n")
    res = AdbResolution(status="found", path="/x/adb", source="bundled", protocol="1.0.41")
    diag = diagnose(res, devices, capability=CapabilityResult(device_ref=device_ref("BBB"), probes={"wifi": "available"}))
    assert diag.state == "verifying"
