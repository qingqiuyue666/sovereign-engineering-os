"""Replay modes — validates and enforces replay mode constraints.

Supported modes: strict, dry_run
No cloud re-query mode. No nondeterministic mode.
No live execution mode.
"""

from __future__ import annotations

from typing import Any, Dict


VALID_MODES = frozenset({"strict", "dry_run"})
FORBIDDEN_MODES = frozenset({
    "cloud_requery", "nondeterministic", "live", "production",
    "network", "external", "remote",
})


class ReplayModes:
    """Replay mode validator and enforcer."""

    @staticmethod
    def validate(mode: str) -> Dict[str, Any]:
        if not isinstance(mode, str) or not mode.strip():
            return {"valid": False, "mode": mode, "reason": "mode_required"}
        if mode in FORBIDDEN_MODES:
            return {"valid": False, "mode": mode, "reason": f"forbidden_mode: {mode}"}
        if mode not in VALID_MODES:
            return {"valid": False, "mode": mode, "reason": f"unsupported_mode: {mode}"}
        return {"valid": True, "mode": mode}

    @staticmethod
    def enforce(mode: str) -> None:
        result = ReplayModes.validate(mode)
        if not result["valid"]:
            raise ValueError(result["reason"])

    @staticmethod
    def allowed_modes() -> frozenset:
        return VALID_MODES

    @staticmethod
    def is_dry_run(mode: str) -> bool:
        return mode == "dry_run"

    @staticmethod
    def is_strict(mode: str) -> bool:
        return mode == "strict"
