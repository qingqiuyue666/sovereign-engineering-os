"""Real Provider Transport Runtime v1 — local-only, deterministic, dry-run provider boundary.

No network. No live provider calls. No secrets. No trading.
Deterministic receipts only.
"""

from tools.provider_transport.provider_adapter_registry import (
    ProviderAdapterRegistry,
    register_provider_adapter,
    get_provider_adapter,
    list_registered_providers,
    validate_adapter_descriptor,
)
from tools.provider_transport.provider_request_contract import (
    ProviderRequestContract,
    validate_provider_request,
)
from tools.provider_transport.provider_transport_preflight import (
    PreflightResult,
    run_provider_transport_preflight,
)
from tools.provider_transport.provider_dry_run_receipt import (
    ProviderDryRunReceipt,
    produce_dry_run_receipt,
)
from tools.provider_transport.provider_failure_receipt import (
    ProviderFailureReceipt,
    produce_failure_receipt,
)
from tools.provider_transport.provider_capability_boundary import (
    CapabilityBoundaryResult,
    validate_capability_boundary,
)
from tools.provider_transport.provider_evidence_binding import (
    EvidenceBindingResult,
    validate_evidence_binding,
)
from tools.provider_transport.provider_rate_limit_budget import (
    RateLimitBudgetResult,
    validate_rate_limit_budget,
)
from tools.provider_transport.provider_no_network_enforcement import (
    NetworkEnforcementResult,
    enforce_no_network,
)
from tools.provider_transport.provider_transport_runtime import (
    ProviderTransportRuntime,
    execute_provider_transport,
)

__all__ = [
    "ProviderAdapterRegistry",
    "register_provider_adapter",
    "get_provider_adapter",
    "list_registered_providers",
    "validate_adapter_descriptor",
    "ProviderRequestContract",
    "validate_provider_request",
    "PreflightResult",
    "run_provider_transport_preflight",
    "ProviderDryRunReceipt",
    "produce_dry_run_receipt",
    "ProviderFailureReceipt",
    "produce_failure_receipt",
    "CapabilityBoundaryResult",
    "validate_capability_boundary",
    "EvidenceBindingResult",
    "validate_evidence_binding",
    "RateLimitBudgetResult",
    "validate_rate_limit_budget",
    "NetworkEnforcementResult",
    "enforce_no_network",
    "ProviderTransportRuntime",
    "execute_provider_transport",
]
