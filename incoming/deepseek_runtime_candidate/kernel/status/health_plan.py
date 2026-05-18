"""System health plan definitions."""

from __future__ import annotations

from collections.abc import Callable

__all__ = ["ordered_health_plan", "HealthCheck", "run_health_checks"]

HealthCheck = Callable[[], dict[str, object]]

_HEALTH_CHECKS: list[tuple[str, HealthCheck]] = []


def register_health_check(name: str, fn: HealthCheck) -> None:
    _HEALTH_CHECKS.append((name, fn))


def ordered_health_plan() -> list[str]:
    return [name for name, _ in _HEALTH_CHECKS]


def run_health_checks() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, fn in _HEALTH_CHECKS:
        try:
            result = fn()
            result.setdefault("check", name)
            results.append(result)
        except Exception as exc:
            results.append({"check": name, "ok": False, "error": str(exc), "exception_type": exc.__class__.__name__})
    return results


# Built-in health checks
def _check_pid1_alive() -> dict[str, object]:
    import os

    return {"ok": True, "component": "pid1", "pid": os.getpid()}


def _check_filesystem_root() -> dict[str, object]:
    from pathlib import Path

    root = Path("/")
    return {"ok": root.exists(), "component": "filesystem_root", "path": str(root)}


register_health_check("pid1-alive", _check_pid1_alive)
register_health_check("filesystem-root", _check_filesystem_root)
