"""Plain-language setup messages, keyed by diagnosis code.

Rules for every entry:
- says what is happening in everyday words (no "adb", "RSA", "udev" in titles),
- says what the person should do next, in order,
- names the button that re-verifies (the UI never flips to "Ready" on its own).
Technical vocabulary is allowed only in ``detail``, shown in the diagnostic view.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HostOS = Literal["windows", "macos", "linux", "unknown"]


@dataclass(frozen=True)
class Message:
    title: str
    message: str
    action: str          # machine id of the recovery action
    action_label: str    # button text
    detail: str = ""     # technical note for the diagnostic view


_GENERIC: dict[str, Message] = {
    "adb_missing": Message(
        "The phone connection tool isn't installed",
        "Titan needs Google's Android connection tool and couldn't find it on this computer. "
        "Close Titan and run START-TITAN again so it can set up its built-in copy. "
        "If this message comes back, install Google's \"Android SDK Platform-Tools\" and try again.",
        "check_again", "Check again",
        "No adb on ADBUTILS_ADB_PATH, PATH, or bundled with adbutils.",
    ),
    "adb_broken": Message(
        "The phone connection tool won't start",
        "Titan found the Android connection tool but it didn't respond. Restart your computer, "
        "then run START-TITAN again. Security software sometimes blocks it — allow it if asked.",
        "check_again", "Check again",
        "adb exists but `adb version` failed or was unparseable.",
    ),
    "adb_server_failed": Message(
        "The phone connection service didn't start",
        "Another program may be using the phone connection service. Close phone-management apps "
        "(Android Studio, phone sync tools, screen-mirroring apps), then select Restart connection service.",
        "restart_adb", "Restart connection service",
        "adb server failed to start or port 5037 is held by another process.",
    ),
    "adb_version_conflict": Message(
        "Two copies of the phone connection tool are fighting",
        "This computer has more than one version of the Android connection tool, and they keep "
        "interrupting each other. Close other phone apps, then select Restart connection service.",
        "restart_adb", "Restart connection service",
        "Multiple adb binaries with different protocol revisions share port 5037.",
    ),
    "no_device": Message(
        "No phone found yet",
        "Connect your Android phone with a USB cable that supports data (some charging cables don't). "
        "Unlock the phone. If you haven't yet, turn on USB debugging: open Settings → About phone and tap "
        "\"Build number\" 7 times (on some phones it's under \"Software information\"), then open "
        "Developer options in Settings (often under System) and turn on USB debugging.",
        "check_again", "Check again",
        "`adb devices -l` listed no transports.",
    ),
    "unauthorized": Message(
        "Approve this computer on your phone",
        "Your phone is connected, but Android has not approved this computer yet. Unlock your phone "
        "and approve the debugging prompt. Then select Try again.",
        "check_again", "Try again",
        "adb state 'unauthorized': RSA key not yet accepted on device.",
    ),
    "authorizing": Message(
        "Waiting for your phone's approval",
        "Your phone is finishing the approval step. Keep it unlocked; if a prompt is showing, approve it. "
        "Then select Try again.",
        "check_again", "Try again",
        "adb state 'authorizing'.",
    ),
    "no_permissions": Message(
        "This computer isn't allowed to talk to the phone yet",
        "Your computer can see the phone but doesn't have permission to use it.",
        "open_instructions", "Show me how",
        "adb state 'no permissions'.",
    ),
    "offline": Message(
        "Your phone stopped responding",
        "The phone is plugged in but not answering. Unplug the cable, plug it back in, and unlock the phone. "
        "If that doesn't work, turn USB debugging off and on again in Developer options.",
        "check_again", "Try again",
        "adb state 'offline' or 'detached'.",
    ),
    "connecting": Message(
        "Connecting to your phone over Wi-Fi",
        "Titan is connecting to your phone. Keep both devices on the same Wi-Fi network.",
        "check_again", "Check again",
        "adb state 'connecting' (wireless transport).",
    ),
    "special_mode": Message(
        "Your phone is in a special startup mode",
        "Your phone is in a maintenance mode (such as recovery or bootloader). Restart it normally, "
        "unlock it, then select Check again.",
        "check_again", "Check again",
        "adb state bootloader/recovery/sideload/rescue.",
    ),
    "unknown_state": Message(
        "Your phone is in a state Titan doesn't recognize",
        "Unplug the phone, restart it, plug it back in and unlock it. Then select Check again. "
        "If this keeps happening, copy the diagnostic report and share it with support.",
        "copy_diagnostics", "Copy diagnostic report",
        "Unrecognised adb state.",
    ),
    "selected_device_missing": Message(
        "The phone you chose is no longer connected",
        "The phone you selected disconnected. Titan will not switch to a different phone on its own. "
        "Reconnect it and select Check again, or choose another phone.",
        "rescan", "Re-scan phones",
        "Selected device_ref not present in current adb transport list.",
    ),
    "multiple_devices": Message(
        "More than one phone is connected",
        "Choose which phone Titan should use. Titan only ever reads from the phone you choose.",
        "choose_device", "Choose phone",
        "More than one authorized transport; explicit selection required for capture.",
    ),
    "device_connected": Message(
        "Phone connected",
        "Your phone is connected and approved. Titan will now check which features it supports.",
        "verify_features", "Check features",
        "adb state 'device'; capability probe not yet run.",
    ),
    "ready": Message(
        "Ready to use",
        "Your phone is connected and Titan confirmed which features work on it.",
        "none", "",
        "adb state 'device' and at least one capability probe succeeded.",
    ),
    "no_supported_features": Message(
        "Connected, but no supported features answered",
        "Your phone is connected, but it didn't share the information Titan reads. Some phone makers and "
        "Android versions restrict this. Nothing is wrong with your setup.",
        "check_again", "Check again",
        "All capability probes returned unavailable.",
    ),
    "adb_timeout": Message(
        "The phone took too long to answer",
        "The phone didn't answer in time. Unlock it, keep it connected, and select Try again.",
        "check_again", "Try again",
        "adb command exceeded its timeout.",
    ),
}

_NO_PERMISSIONS_BY_HOST: dict[HostOS, str] = {
    "linux": (
        "On Linux, add the Android USB rules and your user to the plugdev group, then unplug and replug "
        "the phone. On Debian/Ubuntu: install the package \"android-sdk-platform-tools-common\", then run "
        "\"sudo usermod -aG plugdev $USER\" and log out and back in."
    ),
    "windows": (
        "On Windows, install the USB driver for your phone (Google USB Driver for Pixel, or your phone "
        "maker's driver), then unplug and replug the phone."
    ),
    "macos": "Unplug the phone, plug it back in, unlock it, and approve any prompt on the phone.",
    "unknown": "Unplug the phone, plug it back in, unlock it, and approve any prompt on the phone.",
}

_ADB_MISSING_BY_HOST: dict[HostOS, str] = {
    "macos": (
        " On Apple Silicon Macs, Titan has no built-in copy: install Platform-Tools with Homebrew "
        "(\"brew install --cask android-platform-tools\") or from developer.android.com."
    ),
    "linux": " On ARM Linux, install your distribution's \"adb\" package.",
    "windows": "",
    "unknown": "",
}


def message_for(code: str, host: HostOS = "unknown") -> Message:
    base = _GENERIC.get(code) or _GENERIC["unknown_state"]
    if code == "no_permissions":
        return Message(base.title, base.message + " " + _NO_PERMISSIONS_BY_HOST[host],
                       base.action, base.action_label, base.detail)
    if code == "adb_missing" and _ADB_MISSING_BY_HOST[host]:
        return Message(base.title, base.message + _ADB_MISSING_BY_HOST[host],
                       base.action, base.action_label, base.detail)
    return base


# Collector / discovery error categories (titan.adb_collect.classify_adb_exception)
# mapped onto the setup message catalog.
COLLECTOR_ERROR_CODES: dict[str, str] = {
    "adbutils_missing": "adb_missing",
    "server_unreachable": "adb_server_failed",
    "device_not_found": "selected_device_missing",
    "device_unauthorized": "unauthorized",
    "device_offline": "offline",
    "timeout": "adb_timeout",
    "empty_output": "no_supported_features",
    "adb_error": "unknown_state",
}


def message_for_collector_error(category: str, host: HostOS = "unknown") -> dict[str, str]:
    code = COLLECTOR_ERROR_CODES.get(category, "unknown_state")
    m = message_for(code, host)
    return {"code": code, "category": category, "title": m.title, "message": m.message,
            "action": m.action, "action_label": m.action_label}


def known_codes() -> set[str]:
    return set(_GENERIC)
