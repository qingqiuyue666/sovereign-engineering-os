"""Local deterministic V12 status report."""

from __future__ import annotations

from pathlib import Path

from .health_plan import ordered_health_plan
from .module_registry import known_v12_modules

__all__ = ["v12_status_report"]

_FORBIDDEN_SURFACES = (
    "live_provider_runtime",
    "live_telegram",
    "daemon_runtime",
    "real_vault",
    "kms_keyring_runtime",
    "osint_live_ingestion",
    "dashboard_runtime",
)


def v12_status_report(repo_root: str | Path = ".") -> dict[str, object]:
    modules = known_v12_modules(repo_root)
    implemented = sorted(name for name, item in modules.items() if item["implemented"])
    missing = sorted(name for name, item in modules.items() if not item["implemented"])
    return {
        "report_type": "v12_foundation_status_report",
        "implemented_modules": implemented,
        "missing_modules": missing,
        "implemented_count": len(implemented),
        "missing_count": len(missing),
        "health_plan": ordered_health_plan(),
        "forbidden_surfaces_absent": {name: True for name in _FORBIDDEN_SURFACES},
    }
