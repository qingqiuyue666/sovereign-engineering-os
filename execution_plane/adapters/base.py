"""Shared adapter contracts and constants."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

FAKE_DCC_ADAPTER = "fake_dcc"
HOUDINI_HYTHON_ADAPTER = "houdini_hython"
COMFYUI_LOCAL_ADAPTER = "comfyui_local"
DAVINCI_RESOLVE_ADAPTER = "davinci_resolve"

SUPPORTED_ADAPTER_ACTIONS = {
    FAKE_DCC_ADAPTER: frozenset({"smoke_generate_file"}),
    HOUDINI_HYTHON_ADAPTER: frozenset(
        {
            "version_probe",
            "smoke_cache_test",
            "geometry_cache_test",
            "hip_open_validate",
            "houdini_generate_geometry_cache",
        }
    ),
    COMFYUI_LOCAL_ADAPTER: frozenset({"service_probe", "submit_workflow", "poll_history", "collect_outputs"}),
    DAVINCI_RESOLVE_ADAPTER: frozenset(
        {"version_probe", "project_probe", "timeline_export_probe", "render_preset_test"}
    ),
}

SUPPORTED_ADAPTERS = tuple(SUPPORTED_ADAPTER_ACTIONS)


@dataclass(frozen=True)
class ProvisionResult:
    """Normalized auto-provision outcome."""

    adapter: str
    status: str
    method: str
    pid: int | None = None
    heartbeat_status: str = "NOT_REQUIRED"
    elapsed_ms: int = 0
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "adapter": self.adapter,
            "status": self.status,
            "method": self.method,
            "pid": self.pid,
            "heartbeat_status": self.heartbeat_status,
            "elapsed_ms": self.elapsed_ms,
            "details": dict(self.details),
        }
        return payload


class AdapterContract:
    """Interface shape required by the aggressive expansion plan."""

    name: str
    actions: frozenset[str]

    def detect(self) -> dict[str, Any]:
        raise NotImplementedError

    def preflight(self, action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def auto_provision(self, intent: Mapping[str, Any], policy: Mapping[str, Any]) -> ProvisionResult:
        raise NotImplementedError

    def execute(self, permit: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def collect_outputs(self, result: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [dict(item) for item in result.get("outputs", []) if isinstance(item, Mapping)]

    def classify_failure(self, result: Mapping[str, Any]) -> dict[str, Any]:
        status = str(result.get("status", "UNKNOWN"))
        failure = result.get("failure_summary")
        return {
            "adapter": self.name,
            "status": status,
            "failure_code": _failure_code_for_status(status, failure),
            "repairable": status in {"FAILED", "TIMED_OUT"},
        }

    def repair_hint(self, result: Mapping[str, Any]) -> dict[str, Any]:
        classification = self.classify_failure(result)
        return {
            "adapter": self.name,
            "failure_code": classification["failure_code"],
            "hint": "inspect failure bundle and rerun with bounded retry",
        }


def _failure_code_for_status(status: str, failure: object) -> str | None:
    if status == "SUCCEEDED":
        return None
    failure_text = str(failure or "").upper()
    if "TIMEOUT" in failure_text or status == "TIMED_OUT":
        return "TIMEOUT"
    if "ENV_NOT_FOUND" in failure_text:
        return "ADAPTER_UNAVAILABLE"
    if "DEPENDENCY" in failure_text:
        return "DEPENDENCY_BLOCKED"
    if "PATH_GUARD" in failure_text:
        return "OUTPUT_INVALID"
    if status == "BLOCKED":
        return "PREFLIGHT_FAILED"
    return "EXECUTION_FAILED"
