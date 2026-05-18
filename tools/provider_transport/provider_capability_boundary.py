"""Provider capability boundary — enforces which capabilities each provider may use.

Maps provider -> allowed capabilities. Rejects forbidden capabilities.
Rejects capability requests for unsupported capabilities per provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from tools.provider_transport.provider_adapter_registry import (
    FORBIDDEN_CAPABILITIES,
    KNOWN_CAPABILITIES,
)

# Provider -> allowed capabilities mapping
PROVIDER_CAPABILITY_MAP: Dict[str, FrozenSet[str]] = {
    "mock-finance": frozenset({"fetch_price", "calculate_risk", "validate_asset", "mock_execute"}),
    "mock-market-data": frozenset({"fetch_price", "validate_asset", "mock_execute"}),
    "mock-news": frozenset({"fetch_news", "mock_execute"}),
    "mock-weather": frozenset({"fetch_weather", "mock_execute"}),
}


@dataclass(frozen=True)
class CapabilityBoundaryResult:
    """Immutable result of capability boundary validation."""
    valid: bool
    provider_id: str
    requested_capabilities: FrozenSet[str]
    allowed_capabilities: FrozenSet[str]
    rejected_capabilities: FrozenSet[str]
    failures: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "provider_id": self.provider_id,
            "requested_capabilities": sorted(self.requested_capabilities),
            "allowed_capabilities": sorted(self.allowed_capabilities),
            "rejected_capabilities": sorted(self.rejected_capabilities),
            "failures": list(self.failures),
        }


def validate_capability_boundary(
    provider_id: str,
    requested_capabilities: FrozenSet[str],
) -> CapabilityBoundaryResult:
    """Validate that a provider's requested capabilities are within its boundary.

    Args:
        provider_id: The provider requesting capabilities.
        requested_capabilities: The set of capabilities being requested.

    Returns:
        CapabilityBoundaryResult with validation details.
    """
    failures: list[str] = []

    if not isinstance(provider_id, str) or not provider_id.strip():
        failures.append("provider_id_must_be_nonempty_string")

    if not isinstance(requested_capabilities, (set, frozenset)):
        failures.append("requested_capabilities_must_be_set")

    requested = requested_capabilities if isinstance(requested_capabilities, frozenset) else frozenset(requested_capabilities)

    # Check for forbidden capabilities
    forbidden_in_request = requested & FORBIDDEN_CAPABILITIES
    for cap in sorted(forbidden_in_request):
        failures.append(f"forbidden_capability_rejected: {cap}")

    # Check against known capabilities
    unknown = requested - KNOWN_CAPABILITIES - FORBIDDEN_CAPABILITIES
    for cap in sorted(unknown):
        failures.append(f"unknown_capability_rejected: {cap}")

    # Check provider-specific capability allowlist
    allowed_caps: FrozenSet[str] = frozenset()
    if provider_id in PROVIDER_CAPABILITY_MAP:
        allowed_caps = PROVIDER_CAPABILITY_MAP[provider_id]
        unsupported = (requested - FORBIDDEN_CAPABILITIES - unknown) - allowed_caps
        for cap in sorted(unsupported):
            failures.append(f"capability_not_allowed_for_provider: {cap}:{provider_id}")

    rejected = forbidden_in_request | unknown
    if provider_id in PROVIDER_CAPABILITY_MAP:
        rejected = rejected | ((requested - FORBIDDEN_CAPABILITIES - unknown) - allowed_caps)

    return CapabilityBoundaryResult(
        valid=len(failures) == 0 and len(requested) > 0,
        provider_id=provider_id,
        requested_capabilities=requested,
        allowed_capabilities=allowed_caps,
        rejected_capabilities=rejected,
        failures=tuple(failures),
    )
