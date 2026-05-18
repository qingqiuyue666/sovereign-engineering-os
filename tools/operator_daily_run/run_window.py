"""Run window — validates operator daily run time window.

Ensures runs happen within allowed windows. No wall-clock dependency
in hash/receipt generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RunWindow:
    """Immutable run window definition."""

    window_id: str
    label: str
    is_allowed: bool

    @staticmethod
    def create(label: str, is_allowed: bool = True) -> RunWindow:
        if not label.strip():
            raise ValueError("label required")
        # Window ID is deterministic from label
        import hashlib
        window_id = hashlib.blake2b(label.encode(), digest_size=8).hexdigest()
        return RunWindow(window_id=window_id, label=label, is_allowed=is_allowed)

    @staticmethod
    def validate(label: str) -> Dict[str, Any]:
        if not label or not label.strip():
            return {"valid": False, "reason": "window_label_required"}
        if label not in ("daily_review", "incident_response", "scheduled_maintenance"):
            return {"valid": False, "reason": f"unknown_window: {label}"}
        return {"valid": True, "window": label}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "label": self.label,
            "is_allowed": self.is_allowed,
        }
