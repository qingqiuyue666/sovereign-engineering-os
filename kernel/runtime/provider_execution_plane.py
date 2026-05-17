"""Provider execution plane boundary — deterministic validation only.

Default disabled. No real provider calls. Validates execution descriptors
against policy and enforces boundary constraints with strict field typing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    strict_bool,
    validate_required_bool_fields,
    validate_required_digest_fields,
    validate_required_string_fields,
)

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

_REQUIRED_STRING_FIELDS = (
    "provider_id",
    "policy_version",
    "code_version",
)

_REQUIRED_DIGEST_FIELDS = (
    "request_digest",
    "authorization_digest",
)

_BOOL_GATE_FIELDS = (
    "provider_enabled",
    "network_access",
    "tool_calls_enabled",
    "file_edits_enabled",
    "production_autonomy",
)


@dataclass(frozen=True)
class ProviderExecutionPlaneReceipt:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "failures": list(self.failures)}


def validate_provider_execution_plane(payload: Mapping[str, object]) -> ProviderExecutionPlaneReceipt:
    """Validate a provider execution plane request with strict typing.

    Default disabled — rejects provider_enabled=true.
    Rejects network_access, tool_calls_enabled, file_edits_enabled, production_autonomy.
    All boolean gate fields must be actual booleans (not strings or integers).
    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    # Gate boolean fields — must be actual bool type
    for field in _BOOL_GATE_FIELDS:
        value = payload_dict.get(field)
        if value is not None and not isinstance(value, bool):
            failures.append(f"{field}_must_be_bool")
        elif value is True:
            if field == "provider_enabled":
                failures.append("provider_enabled_rejected_default_disabled")
            elif field == "network_access":
                failures.append("network_access_rejected")
            elif field == "tool_calls_enabled":
                failures.append("tool_calls_enabled_rejected")
            elif field == "file_edits_enabled":
                failures.append("file_edits_enabled_rejected")
            elif field == "production_autonomy":
                failures.append("production_autonomy_rejected")

    # Forbidden fields
    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    # Required string fields — strict typing
    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)

    # Required digest fields — strict format
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    if failures:
        return ProviderExecutionPlaneReceipt(False, tuple(failures))
    return ProviderExecutionPlaneReceipt(True, ())
