"""Scheduler metadata contract. No scheduler runtime is started."""

from __future__ import annotations

from typing import Mapping

__all__ = ["validate_scheduler_config"]


def validate_scheduler_config(config: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(config, Mapping):
        return ("scheduler_config_must_be_mapping",)
    failures: list[str] = []
    if config.get("single_run_mode") is not True:
        failures.append("single_run_mode_required")
    if not isinstance(config.get("max_runtime_seconds"), int) or int(config.get("max_runtime_seconds", 0)) <= 0:
        failures.append("max_runtime_seconds_required")
    if config.get("unbounded_loop") is True:
        failures.append("unbounded_loop_forbidden")
    if config.get("scheduler_runtime") is True:
        failures.append("scheduler_runtime_forbidden")
    return tuple(sorted(set(failures)))
