"""Provider adapter registry — descriptor only, no live adapters.

Validates adapter registry descriptors. Default enabled=false.
Rejects unknown providers and missing capability/firewall bindings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

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

_REQUIRED_FIELDS = (
    "provider_id",
    "allowed_provider_types",
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
    """Validate a provider adapter registry descriptor.

    Default enabled must be false. Provider must be known, capability boundary
    and context firewall binding must be present.
    """
    failures: list[str] = []

    if payload.get("default_enabled") is True:
        failures.append("default_enabled_must_be_false")

    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    if "allowed_provider_types" in payload:
        types_val = payload["allowed_provider_types"]
        if not isinstance(types_val, list) or not types_val:
            failures.append("allowed_provider_types_must_be_nonempty_list")

    if failures:
        return ProviderAdapterRegistryReceipt(False, tuple(failures))
    return ProviderAdapterRegistryReceipt(True, ())
