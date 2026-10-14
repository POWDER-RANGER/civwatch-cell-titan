"""Explicit setup state machine.

Invariants:
- only transitions listed in ``TRANSITIONS`` are allowed;
- entering ``ready`` requires a ``ReadinessProof`` naming the device and at
  least one capability probe that actually succeeded — the UI cannot declare
  readiness by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

SetupState = Literal[
    "not_started", "checking", "preparing", "awaiting_authorization", "connecting",
    "verifying", "ready", "action_required", "retrying", "unsupported", "failed", "cancelled",
]

STATES: tuple[str, ...] = SetupState.__args__  # type: ignore[attr-defined]

_ANY_OUTCOME = {"preparing", "awaiting_authorization", "connecting", "verifying",
                "action_required", "retrying", "unsupported", "failed", "cancelled"}

TRANSITIONS: dict[str, set[str]] = {
    "not_started": {"checking", "cancelled"},
    "checking": _ANY_OUTCOME | {"checking"},
    "preparing": {"checking", "action_required", "failed", "cancelled"},
    "awaiting_authorization": {"checking", "cancelled"},
    "connecting": {"checking", "cancelled"},
    "verifying": {"ready", "unsupported", "action_required", "retrying", "failed", "cancelled", "checking"},
    "ready": {"checking", "cancelled"},
    "action_required": {"checking", "cancelled"},
    "retrying": {"checking", "failed", "cancelled"},
    "unsupported": {"checking", "cancelled"},
    "failed": {"checking", "cancelled"},
    "cancelled": {"not_started", "checking"},
}


class InvalidTransition(ValueError):
    pass


class UnverifiedReadiness(ValueError):
    pass


@dataclass(frozen=True)
class ReadinessProof:
    device_ref: str
    verified_capabilities: tuple[str, ...]
    verified_at: str

    def valid(self) -> bool:
        return bool(self.device_ref) and len(self.verified_capabilities) > 0 and bool(self.verified_at)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SetupMachine:
    state: str = "not_started"
    history: list[dict] = field(default_factory=list)
    proof: ReadinessProof | None = None

    def can(self, target: str) -> bool:
        return target in TRANSITIONS.get(self.state, set())

    def transition(self, target: str, *, reason: str, proof: ReadinessProof | None = None) -> str:
        if target not in STATES:
            raise InvalidTransition(f"unknown state {target!r}")
        if not self.can(target):
            raise InvalidTransition(f"{self.state} -> {target} is not allowed")
        if target == "ready":
            if proof is None or not proof.valid():
                raise UnverifiedReadiness("ready requires a ReadinessProof with >=1 verified capability")
            self.proof = proof
        else:
            # Readiness is a point-in-time fact; leaving "ready" voids the proof.
            self.proof = None
        self.history.append({"from": self.state, "to": target, "reason": reason, "ts": _utc()})
        self.state = target
        return target

    def path(self) -> list[str]:
        return [self.history[0]["from"]] + [h["to"] for h in self.history] if self.history else [self.state]
