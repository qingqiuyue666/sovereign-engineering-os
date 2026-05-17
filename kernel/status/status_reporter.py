"""Local deterministic V12 status report.

Reports implementation status without overclaiming. Forbidden surfaces are
reported as unknown_without_gate_evidence rather than falsely claimed absent.
"""

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


def v12_status_report(repo_root: str | Path = ".", gate_results: dict[str, bool] | None = None) -> dict[str, object]:
    """Produce a V12 status report.

    If gate_results is provided, surfaces are checked against it.
    Without gate_results, forbidden surfaces are reported as
    unknown_without_gate_evidence rather than falsely claimed absent.
    """
    modules = known_v12_modules(repo_root)
    implemented = sorted(name for name, item in modules.items() if item["implemented"])
    missing = sorted(name for name, item in modules.items() if not item["implemented"])

    # Forbidden surfaces: only claim absent if gate evidence is provided.
    # Otherwise report unknown_without_gate_evidence.
    forbidden_status: dict[str, str] = {}
    if gate_results is not None and isinstance(gate_results, dict):
        for name in _FORBIDDEN_SURFACES:
            if gate_results.get(name) is True:
                forbidden_status[name] = "absent_by_gate_evidence"
            elif name in gate_results:
                forbidden_status[name] = "gate_check_failed"
            else:
                forbidden_status[name] = "unknown_without_gate_evidence"
    else:
        for name in _FORBIDDEN_SURFACES:
            forbidden_status[name] = "unknown_without_gate_evidence"

    return {
        "report_type": "v12_foundation_status_report",
        "implemented_modules": implemented,
        "missing_modules": missing,
        "implemented_count": len(implemented),
        "missing_count": len(missing),
        "health_plan": ordered_health_plan(),
        "forbidden_surfaces": forbidden_status,
        "production_autonomy_enabled": False,
        "forbidden_surfaces_absent": False,
        "forbidden_surfaces_status": "unknown_without_gate_evidence",
    }
