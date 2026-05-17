"""Provider execution plane boundary — deterministic validation only.

Default disabled. No real provider calls. Validates execution descriptors
against policy and enforces boundary constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "ProviderExecutionPlaneReceipt",
    "validate_provider_execution_plane",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_FIELDS = (
    "provider_id",
    "request_digest",
    "authorization_digest",
    "policy_version",
    "code_version",
)


@dataclass(frozen=True)
class ProviderExecutionPlaneReceipt:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "failures": list(self.failures)}


def validate_provider_execution_plane(payload: Mapping[str, object]) -> ProviderExecutionPlaneReceipt:
    """Validate a provider execution plane request.

    Default disabled — rejects provider_enabled=true.
    Rejects network_access, tool_calls_enabled, file_edits_enabled, production_autonomy.
    """
    failures: list[str] = []

    if payload.get("provider_enabled") is True:
        failures.append("provider_enabled_rejected_default_disabled")
    if payload.get("network_access") is True:
        failures.append("network_access_rejected")
    if payload.get("tool_calls_enabled") is True:
        failures.append("tool_calls_enabled_rejected")
    if payload.get("file_edits_enabled") is True:
        failures.append("file_edits_enabled_rejected")
    if payload.get("production_autonomy") is True:
        failures.append("production_autonomy_rejected")

    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    if failures:
        return ProviderExecutionPlaneReceipt(False, tuple(failures))
    return ProviderExecutionPlaneReceipt(True, ())
