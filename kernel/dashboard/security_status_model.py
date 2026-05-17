"""Security status model."""

from __future__ import annotations

from typing import Mapping

__all__ = ["validate_security_status_model"]


def validate_security_status_model(model: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(model, Mapping):
        return ("security_status_model_must_be_mapping",)
    failures: list[str] = []
    for field in ("scanner_enabled", "redaction_enabled", "forbidden_surfaces_absent"):
        if field not in model:
            failures.append(f"{field}_required")
    if model.get("scanner_enabled") is not True:
        failures.append("scanner_enabled_required")
    if model.get("redaction_enabled") is not True:
        failures.append("redaction_enabled_required")
    if not isinstance(model.get("forbidden_surfaces_absent"), Mapping):
        failures.append("forbidden_surfaces_absent_required")
    return tuple(sorted(set(failures)))
