"""Provider adapter registry — descriptor only, no live adapters.

Validates adapter registry descriptors with strict membership enforcement.
Default enabled=false. Provider must be a member of allowed_provider_types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    strict_bool,
    strict_nonempty_string,
    validate_required_string_fields,
)

__all__ = [
    "ProviderAdapterRegistryReceipt",
    "validate_provider_adapter_registry",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_STRING_FIELDS = (
    "provider_id",
    "capability_boundary_ref",
    "context_firewall_binding_ref",
)


@dataclass(frozen=True)
class ProviderAdapterRegistryReceipt:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "failures": list(self.failures)}


def validate_provider_adapter_registry(payload: Mapping[str, object]) -> ProviderAdapterRegistryReceipt:
    """Validate a provider adapter registry descriptor with strict membership.

    Default enabled must be actual bool false.
    provider_id must be a non-empty string and must be a member of
    allowed_provider_types (non-empty list of non-empty strings).
    Capability boundary and context firewall binding must be non-empty strings.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    # default_enabled — must be actual bool
    de_val = payload_dict.get("default_enabled")
    if de_val is not None:
        if not isinstance(de_val, bool):
            failures.append("default_enabled_must_be_bool")
        elif de_val is True:
            failures.append("default_enabled_must_be_false")

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)

    # Strict provider_id validation
    provider_id = payload_dict.get("provider_id")
    if provider_id is not None:
        if not strict_nonempty_string(provider_id):
            failures.append("provider_id_must_be_nonempty_string")
        elif not isinstance(provider_id, str):
            failures.append("provider_id_must_be_string")

    # allowed_provider_types strict validation + membership check
    apt = payload_dict.get("allowed_provider_types")
    if apt is None:
        failures.append("allowed_provider_types_must_not_be_none")
    elif not isinstance(apt, list):
        failures.append("allowed_provider_types_must_be_list")
    elif len(apt) == 0:
        failures.append("allowed_provider_types_must_be_nonempty")
    else:
        valid_types: list[str] = []
        for i, entry in enumerate(apt):
            if entry is None:
                failures.append(f"allowed_provider_types[{i}]_must_not_be_none")
            elif not isinstance(entry, str):
                failures.append(f"allowed_provider_types[{i}]_must_be_string")
            elif not entry or not entry.strip():
                failures.append(f"allowed_provider_types[{i}]_must_be_nonempty_string")
            else:
                valid_types.append(str(entry))

        # Membership check: provider_id must be in valid_types
        if isinstance(provider_id, str) and provider_id.strip() and valid_types:
            if str(provider_id) not in valid_types:
                failures.append("provider_id_not_in_allowed_provider_types")

    if failures:
        return ProviderAdapterRegistryReceipt(False, tuple(failures))
    return ProviderAdapterRegistryReceipt(True, ())
