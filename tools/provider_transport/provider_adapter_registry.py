"""Provider adapter registry — registers and validates provider adapters.

Only known providers are accepted. Forbidden providers are permanently rejected.
Each adapter must declare its capabilities, a non-empty provider_id, and a
boundary reference. Default disabled. No live adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Mapping, Optional

KNOWN_PROVIDERS: FrozenSet[str] = frozenset({
    "mock-finance",
    "mock-market-data",
    "mock-news",
    "mock-weather",
})

FORBIDDEN_PROVIDERS: FrozenSet[str] = frozenset({
    "live-broker",
    "live-exchange",
    "live-payment",
    "live-bank",
})

KNOWN_CAPABILITIES: FrozenSet[str] = frozenset({
    "fetch_price",
    "fetch_news",
    "fetch_weather",
    "calculate_risk",
    "validate_asset",
    "mock_execute",
})

FORBIDDEN_CAPABILITIES: FrozenSet[str] = frozenset({
    "live_trade",
    "live_transfer",
    "live_withdrawal",
    "live_deposit",
    "live_order",
})


@dataclass(frozen=True)
class ProviderAdapterDescriptor:
    """Immutable descriptor for a registered provider adapter."""
    provider_id: str
    capabilities: FrozenSet[str]
    boundary_ref: str
    enabled: bool = False
    dry_run_only: bool = True
    no_network: bool = True


class ProviderAdapterRegistry:
    """Thread-safe registry of provider adapter descriptors."""

    def __init__(self) -> None:
        self._adapters: Dict[str, ProviderAdapterDescriptor] = {}

    def register(self, descriptor: ProviderAdapterDescriptor) -> None:
        if not isinstance(descriptor, ProviderAdapterDescriptor):
            raise TypeError("descriptor must be ProviderAdapterDescriptor")
        pid = descriptor.provider_id
        if pid in FORBIDDEN_PROVIDERS:
            raise ValueError(f"forbidden_provider_rejected: {pid}")
        if pid not in KNOWN_PROVIDERS:
            raise ValueError(f"unknown_provider_rejected: {pid}")
        if not descriptor.capabilities:
            raise ValueError("capabilities_must_not_be_empty")
        for cap in descriptor.capabilities:
            if cap in FORBIDDEN_CAPABILITIES:
                raise ValueError(f"forbidden_capability_rejected: {cap}")
        self._adapters[pid] = descriptor

    def get(self, provider_id: str) -> Optional[ProviderAdapterDescriptor]:
        return self._adapters.get(provider_id)

    def list_providers(self) -> FrozenSet[str]:
        return frozenset(self._adapters.keys())

    def is_registered(self, provider_id: str) -> bool:
        return provider_id in self._adapters


_global_registry = ProviderAdapterRegistry()


def register_provider_adapter(descriptor: ProviderAdapterDescriptor) -> None:
    _global_registry.register(descriptor)


def get_provider_adapter(provider_id: str) -> Optional[ProviderAdapterDescriptor]:
    return _global_registry.get(provider_id)


def list_registered_providers() -> FrozenSet[str]:
    return _global_registry.list_providers()


def validate_adapter_descriptor(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate a raw adapter descriptor dict before constructing a descriptor."""
    failures: list[str] = []

    if not isinstance(payload, Mapping):
        return {"valid": False, "failures": ("payload_must_be_mapping",)}

    pid = payload.get("provider_id")
    if not isinstance(pid, str) or not pid.strip():
        failures.append("provider_id_must_be_nonempty_string")
    elif pid in FORBIDDEN_PROVIDERS:
        failures.append(f"forbidden_provider: {pid}")
    elif pid not in KNOWN_PROVIDERS:
        failures.append(f"unknown_provider: {pid}")

    caps = payload.get("capabilities")
    if caps is None:
        failures.append("capabilities_must_not_be_none")
    elif not isinstance(caps, (list, tuple, set, frozenset)):
        failures.append("capabilities_must_be_collection")
    else:
        cap_list = list(caps)
        if len(cap_list) == 0:
            failures.append("capabilities_must_not_be_empty")
        for i, c in enumerate(cap_list):
            if not isinstance(c, str) or not c.strip():
                failures.append(f"capability_{i}_must_be_nonempty_string")
            elif c in FORBIDDEN_CAPABILITIES:
                failures.append(f"forbidden_capability: {c}")

    boundary = payload.get("boundary_ref")
    if not isinstance(boundary, str) or not boundary.strip():
        failures.append("boundary_ref_must_be_nonempty_string")

    if payload.get("enabled") is not False and "enabled" in payload:
        failures.append("enabled_must_be_false")

    if payload.get("dry_run_only") is not True and "dry_run_only" in payload:
        failures.append("dry_run_only_must_be_true")

    if failures:
        return {"valid": False, "failures": tuple(failures)}
    return {"valid": True, "failures": ()}
