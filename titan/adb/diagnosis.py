"""Turn observed ADB conditions into one setup state + plain-language guidance.

``diagnose`` is a pure function of evidence it is handed (executable resolution,
parsed device list, server errors, optional capability-probe results). It never
probes anything itself and never upgrades an unknown into a success.
"""
from __future__ import annotations

import platform
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Callable, Literal, Optional

from titan.adb.devices import AdbDevice, parse_devices
from titan.adb.locate import AdbResolution
from titan.adb.messages import HostOS, message_for

ProbeOutcome = Literal["available", "unavailable", "failed", "untested"]

_STATE_FOR_CATEGORY = {
    "unauthorized": ("awaiting_authorization", "unauthorized"),
    "authorizing": ("awaiting_authorization", "authorizing"),
    "no_permissions": ("action_required", "no_permissions"),
    "offline": ("retrying", "offline"),
    "connecting": ("connecting", "connecting"),
    "special_mode": ("unsupported", "special_mode"),
    "unknown": ("action_required", "unknown_state"),
}

_RETRY_ACTIONS = {"check_again", "restart_adb", "rescan", "verify_features"}


def host_os() -> HostOS:
    s = platform.system().lower()
    if s.startswith("win"):
        return "windows"
    if s == "darwin":
        return "macos"
    if s == "linux":
        return "linux"
    return "unknown"


@dataclass
class CapabilityResult:
    device_ref: str
    probes: dict[str, ProbeOutcome]

    @property
    def verified(self) -> list[str]:
        return sorted(k for k, v in self.probes.items() if v == "available")


@dataclass
class Diagnosis:
    state: str
    code: str
    ready: bool                      # an authorized ADB connection exists
    retryable: bool
    title: str
    message: str
    action: str
    action_label: str
    detail: str
    device_ref: Optional[str] = None
    devices: list[dict] = field(default_factory=list)   # public (serial-free) view
    warnings: list[str] = field(default_factory=list)
    verified_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _mismatch(text: str) -> bool:
    return "doesn't match this client" in text or "does not match this client" in text


def classify_server_output(returncode: int | None, stdout: str, stderr: str, timed_out: bool = False) -> Optional[str]:
    """Map `adb devices` process failure signatures to a diagnosis code (None = healthy)."""
    text = f"{stdout}\n{stderr}".lower()
    if timed_out:
        return "adb_timeout"
    if _mismatch(text) and "list of devices" not in text:
        return "adb_version_conflict"
    if ("cannot connect to daemon" in text or "failed to start daemon" in text
            or "could not install *smartsocket* listener" in text or "address already in use" in text):
        return "adb_server_failed"
    if returncode not in (0, None) and "list of devices" not in text:
        return "adb_server_failed"
    return None


def _build(code: str, state: str, host: HostOS, *, ready: bool, device: AdbDevice | None,
           devices: list[AdbDevice], warnings: list[str],
           verified: list[str] | None = None) -> Diagnosis:
    m = message_for(code, host)
    return Diagnosis(
        state=state, code=code, ready=ready, retryable=m.action in _RETRY_ACTIONS,
        title=m.title, message=m.message, action=m.action, action_label=m.action_label, detail=m.detail,
        device_ref=device.ref if device else None,
        devices=[d.public() for d in devices], warnings=list(warnings),
        verified_capabilities=list(verified or []),
    )


def diagnose(
    resolution: AdbResolution,
    devices: list[AdbDevice],
    *,
    host: HostOS = "unknown",
    server_error: Optional[str] = None,
    selected_ref: Optional[str] = None,
    capability: Optional[CapabilityResult] = None,
) -> Diagnosis:
    warnings = list(resolution.warnings)
    any_ready = any(d.category == "ready" for d in devices)

    if resolution.status == "missing":
        return _build("adb_missing", "action_required", host, ready=False, device=None, devices=[], warnings=warnings)
    if resolution.status == "broken":
        return _build("adb_broken", "action_required", host, ready=False, device=None, devices=[], warnings=warnings)
    if server_error:
        state = {"adb_timeout": "retrying", "adb_version_conflict": "action_required"}.get(server_error, "failed")
        return _build(server_error, state, host, ready=False, device=None, devices=devices, warnings=warnings)
    if selected_ref:
        target = next((d for d in devices if d.ref == selected_ref), None)
        if target is None:
            # Never fall back to another phone: that would silently retarget collection.
            return _build("selected_device_missing", "action_required", host, ready=any_ready,
                          device=None, devices=devices, warnings=warnings)
    elif not devices:
        return _build("no_device", "action_required", host, ready=False, device=None, devices=[], warnings=warnings)
    elif len(devices) == 1:
        target = devices[0]
    else:
        return _build("multiple_devices", "action_required", host, ready=any_ready,
                      device=None, devices=devices, warnings=warnings)

    if target.category != "ready":
        state, code = _STATE_FOR_CATEGORY[target.category]
        return _build(code, state, host, ready=any_ready, device=target, devices=devices, warnings=warnings)

    if capability is None or capability.device_ref != target.ref:
        return _build("device_connected", "verifying", host, ready=True, device=target,
                      devices=devices, warnings=warnings)
    verified = capability.verified
    if verified:
        return _build("ready", "ready", host, ready=True, device=target, devices=devices,
                      warnings=warnings, verified=verified)
    return _build("no_supported_features", "unsupported", host, ready=True, device=target,
                  devices=devices, warnings=warnings)


DevicesRunner = Callable[[str], "tuple[int | None, str, str, bool]"]


def run_adb_devices(adb_path: str, timeout: float = 15.0) -> tuple[int | None, str, str, bool]:
    """Run ``adb devices -l``. Returns (returncode, stdout, stderr, timed_out). Never raises."""
    try:
        p = subprocess.run([adb_path, "devices", "-l"], capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout or "", p.stderr or "", False
    except subprocess.TimeoutExpired:
        return None, "", "", True
    except OSError as ex:
        return 1, "", f"failed to start daemon: {type(ex).__name__}", False


def check_setup(
    resolution: AdbResolution,
    *,
    host: HostOS,
    run_devices: DevicesRunner = run_adb_devices,
    selected_ref: Optional[str] = None,
) -> tuple[Diagnosis, list[AdbDevice]]:
    """Observe ADB once and diagnose. The parsed device list is returned for loopback use."""
    if not resolution.available or not resolution.path:
        return diagnose(resolution, [], host=host), []
    rc, out, err, timed_out = run_devices(resolution.path)
    server_error = classify_server_output(rc, out, err, timed_out)
    devices = [] if server_error else parse_devices(out)
    diag = diagnose(resolution, devices, host=host, server_error=server_error, selected_ref=selected_ref)
    if not server_error and _mismatch(f"{out}\n{err}".lower()) and "adb_server_restarted" not in diag.warnings:
        # The client restarted a server started by a different adb build. The list is
        # valid now, but another tool may restart it again; surface it, don't block.
        diag.warnings.append("adb_server_restarted")
    return diag, devices
