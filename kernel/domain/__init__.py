"""Domain pipeline contract skeletons."""

from .domain_adapter_foundation import (
    AdapterAdmissionRules,
    AssetHashBinding,
    DomainAdapterContract,
    DomainAdapterFamily,
    DomainOperationClass,
    OperationPlanDescriptor,
    OutputManifestContract,
    ProvenancePolicy,
    ReplayPolicy,
    StateProxyDescriptor,
    build_default_domain_adapter_contracts,
    build_domain_adapter_contract,
    validate_asset_hash_binding,
    validate_domain_adapter_contract,
)
from .source_reliability import validate_source_metadata

__all__ = [
    "AdapterAdmissionRules",
    "AssetHashBinding",
    "DomainAdapterContract",
    "DomainAdapterFamily",
    "DomainOperationClass",
    "OperationPlanDescriptor",
    "OutputManifestContract",
    "ProvenancePolicy",
    "ReplayPolicy",
    "StateProxyDescriptor",
    "build_default_domain_adapter_contracts",
    "build_domain_adapter_contract",
    "validate_asset_hash_binding",
    "validate_domain_adapter_contract",
    "validate_source_metadata",
]
