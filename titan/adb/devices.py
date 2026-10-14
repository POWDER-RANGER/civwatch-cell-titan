"""Parse ``adb devices -l`` into explicit, privacy-safe device records.

The exact ADB connection state is preserved verbatim in ``adb_state``. Higher
level Cell Titan meaning lives in ``category`` and is derived, never invented:
an unrecognised state is ``unknown``, not ``device``.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Category = Literal[
    "ready",            # adb state "device": authorized and responsive
    "unauthorized",     # RSA prompt not yet approved on the phone
    "authorizing",      # approval handshake in progress
    "no_permissions",   # host USB permission problem (Linux udev, etc.)
    "offline",          # transport present, device not responding
    "connecting",       # wireless transport being established
    "special_mode",     # bootloader / recovery / sideload / rescue
    "unknown",
]

Transport = Literal["usb", "wireless", "emulator", "unknown"]

# adb/transport.cpp ConnectionStateToString() values, plus "no permissions".
_STATE_CATEGORY: dict[str, Category] = {
    "device": "ready",
    "unauthorized": "unauthorized",
    "authorizing": "authorizing",
    "no permissions": "no_permissions",
    "offline": "offline",
    "connecting": "connecting",
    "detached": "offline",
    "bootloader": "special_mode",
    "recovery": "special_mode",
    "sideload": "special_mode",
    "rescue": "special_mode",
    "host": "unknown",
}

_REF_DOMAIN = "civwatch-cell-titan:device-ref:v1:"
_IP_PORT = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}:\d{1,5}$")
_DETAIL_TOKEN = re.compile(r"^(usb|product|model|device|transport_id):\S+$")


def device_ref(serial: str) -> str:
    """Stable, non-reversible-in-practice reference for logs, evidence and APIs."""
    return "dev-" + hashlib.sha256((_REF_DOMAIN + serial).encode("utf-8")).hexdigest()[:12]


def classify_transport(serial: str, details: dict[str, str]) -> Transport:
    if serial.startswith("emulator-"):
        return "emulator"
    if _IP_PORT.match(serial) or "._adb-tls-connect._tcp" in serial or "._adb-tls-pairing._tcp" in serial:
        return "wireless"
    if "usb" in details:
        return "usb"
    return "unknown"


@dataclass
class AdbDevice:
    serial: str
    adb_state: str
    category: Category
    transport: Transport
    details: dict[str, str] = field(default_factory=dict)
    note: str = ""

    @property
    def ref(self) -> str:
        return device_ref(self.serial)

    def public(self) -> dict[str, Any]:
        """Representation safe for evidence, logs and remote APIs (no raw serial)."""
        return {
            "device_ref": self.ref,
            "adb_state": self.adb_state,
            "category": self.category,
            "transport": self.transport,
            "model": self.details.get("model"),
        }

    def local(self) -> dict[str, Any]:
        """Loopback-only representation; includes the serial for explicit targeting."""
        out = asdict(self)
        out["device_ref"] = self.ref
        # Backward-compatible keys used by the original /api/setup/check contract.
        out["state"] = self.adb_state
        return out


def _parse_details(tokens: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for tok in tokens:
        if ":" in tok:
            k, v = tok.split(":", 1)
            if k and v and len(k) <= 32:
                out[k] = v[:128]
    return out


def parse_devices(output: str) -> list[AdbDevice]:
    """Parse ``adb devices -l`` stdout. Daemon chatter and blank lines are ignored."""
    devices: list[AdbDevice] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.lower().startswith("list of devices"):
            continue
        if line.lower().startswith(("adb:", "error:", "cannot connect", "failed to")):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial = parts[0]
        rest = parts[1:]
        note = ""
        if rest[0] == "no" and len(rest) > 1 and rest[1].startswith("permissions"):
            state = "no permissions"
            # Tokens before the first key:value pair (usb:, transport_id:, ...) are
            # adb's human-readable hint, e.g. "(missing udev rules? ...)".
            hint: list[str] = []
            tail: list[str] = []
            for tok in rest[2:]:
                if tail or _DETAIL_TOKEN.match(tok):
                    tail.append(tok)
                else:
                    hint.append(tok)
            note = " ".join(hint).strip()[:240]
            details = _parse_details(tail)
        else:
            state = rest[0]
            details = _parse_details(rest[1:])
        category: Category = _STATE_CATEGORY.get(state, "unknown")
        devices.append(
            AdbDevice(
                serial=serial,
                adb_state=state,
                category=category,
                transport=classify_transport(serial, details),
                details=details,
                note=note,
            )
        )
    return devices
