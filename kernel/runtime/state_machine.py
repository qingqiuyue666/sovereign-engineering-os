"""Deterministic runtime state machine foundation.

This module provides a pure, side-effect-free state transition validator that
enforces the legal state transitions for the V12 runtime runner. It rejects
unknown states, illegal transitions, and forbidden fields, and produces a
deterministic transition receipt.

No provider calls, no network, no SQLite, no file mutation, no production
autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Mapping

__all__ = [
    "StateMachineRejection",
    "StateTransitionReceipt",
    "validate_state_transition",
    "ALLOWED_STATES",
    "TERMINAL_STATES",
    "ALLOWED_TRANSITIONS",
]

_ALLOWED_STATES: tuple[str, ...] = (
    "planned",
    "validated",
    "dry_run",
    "executed",
    "failed",
    "quarantined",
    "completed",
)

_TERMINAL_STATES: tuple[str, ...] = ("completed",)

_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

# Each entry: (from_state, to_state, requires_recovery_allowed)
_ALLOWED_TRANSITIONS: tuple[tuple[str, str, bool], ...] = (
    ("planned", "validated", False),
    ("validated", "dry_run", False),
    ("dry_run", "executed", False),
    ("dry_run", "failed", False),
    ("executed", "completed", False),
    ("executed", "failed", False),
    ("failed", "quarantined", False),
    ("quarantined", "planned", True),
)

# Fast lookup sets
_ALLOWED_FROM: dict[str, set[tuple[str, bool]]] = {}
for f, t, r in _ALLOWED_TRANSITIONS:
    _ALLOWED_FROM.setdefault(f, set()).add((t, r))

ALLOWED_STATES: FrozenSet[str] = frozenset(_ALLOWED_STATES)
TERMINAL_STATES: FrozenSet[str] = frozenset(_TERMINAL_STATES)
ALLOWED_TRANSITIONS: tuple[tuple[str, str, bool], ...] = _ALLOWED_TRANSITIONS


class StateMachineRejection(ValueError):
    """Raised when state machine input violates a policy boundary."""


@dataclass(frozen=True)
class StateTransitionReceipt:
    """Deterministic receipt produced by the state transition validator."""

    from_state: str
    to_state: str
    accepted: bool
    reasons: tuple[str, ...]
    policy_version: str
    code_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "policy_version": self.policy_version,
            "code_version": self.code_version,
        }


def validate_state_transition(payload: Mapping[str, object]) -> StateTransitionReceipt:
    """Validate a state transition request against policy boundaries.

    Returns a StateTransitionReceipt with accepted=True and empty reasons if
    the transition is legal, or accepted=False with reasons listing failures.

    Checks:
    1. Forbidden fields absent
    2. from_state is a known allowed state
    3. to_state is a known allowed state
    4. from_state is not a terminal state (completed)
    5. quarantined -> planned requires recovery_allowed=true
    6. The transition is in the allowed set
    """
    failures: list[str] = []

    # Gate 1: forbidden fields
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    # Extract fields with safe defaults
    from_state = str(payload.get("from_state", ""))
    to_state = str(payload.get("to_state", ""))
    recovery_allowed = payload.get("recovery_allowed", False)
    policy_version = str(payload.get("policy_version", ""))
    code_version = str(payload.get("code_version", ""))

    # Gate 2: from_state must be known
    if from_state not in _ALLOWED_STATES:
        failures.append(f"from_state_not_allowed:{from_state}")

    # Gate 3: to_state must be known
    if to_state not in _ALLOWED_STATES:
        failures.append(f"to_state_not_allowed:{to_state}")

    # Gate 4: terminal states cannot transition
    if from_state in _TERMINAL_STATES:
        failures.append(f"terminal_state_cannot_transition:{from_state}")

    # Gate 5: quarantined -> planned requires recovery
    if from_state == "quarantined" and to_state == "planned" and not recovery_allowed:
        failures.append("recovery_allowed_required_for_quarantined_to_planned")

    # Gate 6: check if transition is in the allowed set
    if from_state in _ALLOWED_STATES and to_state in _ALLOWED_STATES:
        allowed_targets = _ALLOWED_FROM.get(from_state, set())
        match = any(t == to_state for t, _ in allowed_targets)
        if not match and from_state not in _TERMINAL_STATES and not (
            from_state == "quarantined" and to_state == "planned" and not recovery_allowed
        ):
            failures.append(f"illegal_transition:{from_state}->{to_state}")

    if failures:
        return StateTransitionReceipt(
            from_state=from_state,
            to_state=to_state,
            accepted=False,
            reasons=tuple(failures),
            policy_version=policy_version,
            code_version=code_version,
        )

    return StateTransitionReceipt(
        from_state=from_state,
        to_state=to_state,
        accepted=True,
        reasons=(),
        policy_version=policy_version,
        code_version=code_version,
    )
