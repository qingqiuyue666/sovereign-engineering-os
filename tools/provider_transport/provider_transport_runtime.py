"""Provider transport runtime — main orchestrator for dry-run provider execution.

Ties together: request validation, preflight, capability boundary, evidence
binding, budget/rate-limit, no-network enforcement, and receipt production.

Returns either a ProviderDryRunReceipt (success) or ProviderFailureReceipt
(failure). Never makes a live provider call. Never touches the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from tools.provider_transport.provider_adapter_registry import (
    ProviderAdapterDescriptor,
    ProviderAdapterRegistry,
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


@dataclass(frozen=True)
class TransportExecutionResult:
    """Top-level result of a provider transport execution."""
    accepted: bool
    dry_run_receipt: Optional[ProviderDryRunReceipt]
    failure_receipt: Optional[ProviderFailureReceipt]
    preflight_result: Optional[PreflightResult]
    capability_result: Optional[CapabilityBoundaryResult]
    evidence_result: Optional[EvidenceBindingResult]
    budget_result: Optional[RateLimitBudgetResult]
    network_result: Optional[NetworkEnforcementResult]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "dry_run_receipt": self.dry_run_receipt.as_dict() if self.dry_run_receipt else None,
            "failure_receipt": self.failure_receipt.as_dict() if self.failure_receipt else None,
            "preflight_result": self.preflight_result.as_dict() if self.preflight_result else None,
            "capability_result": self.capability_result.as_dict() if self.capability_result else None,
            "evidence_result": self.evidence_result.as_dict() if self.evidence_result else None,
            "budget_result": self.budget_result.as_dict() if self.budget_result else None,
            "network_result": self.network_result.as_dict() if self.network_result else None,
        }


class ProviderTransportRuntime:
    """Main orchestrator for provider transport dry-run execution.

    Wire together all validation layers and produce a receipt.
    Never makes live provider calls. Never touches network.
    """

    def __init__(self) -> None:
        self._registry = ProviderAdapterRegistry()

    @property
    def registry(self) -> ProviderAdapterRegistry:
        return self._registry

    def register_adapter(self, descriptor: ProviderAdapterDescriptor) -> None:
        self._registry.register(descriptor)

    def execute(self, payload: Dict[str, Any]) -> TransportExecutionResult:
        """Execute a provider transport request — dry-run only.

        Full pipeline:
        1. No-network enforcement
        2. Request validation
        3. Preflight checks
        4. Capability boundary
        5. Evidence binding
        6. Budget/rate-limit
        7. Produce receipt
        """
        # Step 1: No-network enforcement
        network_result = enforce_no_network()
        if not network_result.valid:
            failure = produce_failure_receipt(
                provider_id=str(payload.get("provider_id", "unknown")),
                request_id=str(payload.get("request_id", "unknown")),
                failure_reason="network_violation_detected",
                rejected_at_gate="no_network",
            )
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=failure,
                preflight_result=None,
                capability_result=None,
                evidence_result=None,
                budget_result=None,
                network_result=network_result,
            )

        # Step 2: Request validation
        request_result = validate_provider_request(payload)
        if not request_result["valid"]:
            failure = produce_failure_receipt(
                provider_id=str(payload.get("provider_id", "unknown")),
                request_id=str(payload.get("request_id", "unknown")),
                failure_reason=f"request_validation_failed: {request_result['failures']}",
                rejected_at_gate="request_contract",
            )
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=failure,
                preflight_result=None,
                capability_result=None,
                evidence_result=None,
                budget_result=None,
                network_result=network_result,
            )

        contract: ProviderRequestContract = request_result["contract"]

        # Step 3: Preflight checks
        preflight_result = run_provider_transport_preflight(
            provider_id=contract.provider_id,
            capability_token=contract.capability_token,
            evidence_binding_present=bool(contract.evidence_binding),
            dry_run=contract.dry_run,
            live_mode=contract.live_mode,
            network_mode=contract.network_mode,
        )
        if not preflight_result.passed:
            failure = produce_failure_receipt(
                provider_id=contract.provider_id,
                request_id=contract.request_id,
                failure_reason=f"preflight_failed: {preflight_result.failures}",
                rejected_at_gate="preflight",
            )
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=failure,
                preflight_result=preflight_result,
                capability_result=None,
                evidence_result=None,
                budget_result=None,
                network_result=network_result,
            )

        # Step 4: Capability boundary
        capability_result = validate_capability_boundary(
            provider_id=contract.provider_id,
            requested_capabilities=contract.capabilities,
        )
        if not capability_result.valid:
            failure = produce_failure_receipt(
                provider_id=contract.provider_id,
                request_id=contract.request_id,
                failure_reason=f"capability_boundary_rejected: {capability_result.failures}",
                rejected_at_gate="capability_boundary",
            )
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=failure,
                preflight_result=preflight_result,
                capability_result=capability_result,
                evidence_result=None,
                budget_result=None,
                network_result=network_result,
            )

        # Step 5: Evidence binding
        evidence_result = validate_evidence_binding(
            evidence_binding=contract.evidence_binding,
            require_present=True,
        )
        if not evidence_result.valid:
            failure = produce_failure_receipt(
                provider_id=contract.provider_id,
                request_id=contract.request_id,
                failure_reason="evidence_binding_missing",
                rejected_at_gate="evidence_binding",
            )
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=failure,
                preflight_result=preflight_result,
                capability_result=capability_result,
                evidence_result=evidence_result,
                budget_result=None,
                network_result=network_result,
            )

        # Step 6: Budget/rate-limit
        budget_result = validate_rate_limit_budget(
            provider_id=contract.provider_id,
        )
        if not budget_result.valid:
            failure = produce_failure_receipt(
                provider_id=contract.provider_id,
                request_id=contract.request_id,
                failure_reason=f"budget_rate_limit_rejected: {budget_result.failures}",
                rejected_at_gate="budget_rate_limit",
            )
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=failure,
                preflight_result=preflight_result,
                capability_result=capability_result,
                evidence_result=evidence_result,
                budget_result=budget_result,
                network_result=network_result,
            )

        # Step 7: Produce deterministic dry-run receipt
        receipt = produce_dry_run_receipt(
            provider_id=contract.provider_id,
            request_id=contract.request_id,
            request_digest=contract.request_digest,
            capability_token=contract.capability_token,
            evidence_binding=contract.evidence_binding,
        )

        return TransportExecutionResult(
            accepted=True,
            dry_run_receipt=receipt,
            failure_receipt=None,
            preflight_result=preflight_result,
            capability_result=capability_result,
            evidence_result=evidence_result,
            budget_result=budget_result,
            network_result=network_result,
        )


def execute_provider_transport(payload: Dict[str, Any]) -> TransportExecutionResult:
    """Convenience function to execute a single provider transport."""
    runtime = ProviderTransportRuntime()
    return runtime.execute(payload)
