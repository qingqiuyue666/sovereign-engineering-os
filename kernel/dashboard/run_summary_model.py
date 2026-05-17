"""Run summary model."""

from __future__ import annotations

from typing import Mapping

__all__ = ["validate_run_summary_model"]


def validate_run_summary_model(model: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(model, Mapping):
        return ("run_summary_model_must_be_mapping",)
    failures: list[str] = []
    for field in ("run_id", "task_id", "status", "event_count"):
        if field not in model:
            failures.append(f"{field}_required")
    if not isinstance(model.get("event_count"), int):
        failures.append("event_count_must_be_int")
    return tuple(sorted(set(failures)))
