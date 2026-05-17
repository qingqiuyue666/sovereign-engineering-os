"""Task state constants and narrow transition validation."""

from __future__ import annotations

TASK_STATES = ("INTAKE", "VALIDATED", "PLANNED", "DRY_RUN_COMPLETE", "FAILED")
_ALLOWED = {
    "INTAKE": {"VALIDATED", "FAILED"},
    "VALIDATED": {"PLANNED", "FAILED"},
    "PLANNED": {"DRY_RUN_COMPLETE", "FAILED"},
}


def transition_allowed(current: str, requested: str) -> bool:
    return requested in _ALLOWED.get(current, set())
