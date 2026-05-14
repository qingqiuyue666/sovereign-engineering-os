"""Fail-closed Personal AI adapter contracts and registries."""

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionDecision,
    AdapterAdmissionStatus,
    AdapterCapabilityRequest,
    AdapterEvidenceRequirement,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterOutputPolicy,
    AdapterQuarantinePolicy,
    AdapterRegistryEntry,
    AdapterResultManifest,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.adapter_registry import (
    DEFAULT_ADAPTER_REGISTRY,
    admit_adapter_capability,
    build_default_adapter_registry,
    find_adapter_entry,
    validate_adapter_registry_entry,
)

__all__ = [
    "AdapterAdmissionDecision",
    "AdapterAdmissionStatus",
    "AdapterCapabilityRequest",
    "AdapterEvidenceRequirement",
    "AdapterExecutionBoundary",
    "AdapterMode",
    "AdapterOutputPolicy",
    "AdapterQuarantinePolicy",
    "AdapterRegistryEntry",
    "AdapterResultManifest",
    "AdapterRiskClass",
    "DEFAULT_ADAPTER_REGISTRY",
    "admit_adapter_capability",
    "build_default_adapter_registry",
    "find_adapter_entry",
    "validate_adapter_registry_entry",
]
