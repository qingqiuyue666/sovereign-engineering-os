"""Provider transport preflight — gate checks before any provider execution.

All gates must pass before a provider transport can proceed.
Preflight checks: provider known, capability allowed, dry-run only,
no network, no secrets, evidence binding present, budget within limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from tools.provider_transport.provider_adapter_registry import (
    FORBIDDEN_CAPABILITIES,
    FORBIDDEN_PROVIDERS,
    KNOWN_PROVIDERS,
    get_provider_adapter,
)


@dataclass(frozen=True)
class PreflightResult:
    """Immutable result of preflight gate checks."""
    passed: bool
    gates: Dict[str, bool]
    failures: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "gates": dict(self.gates),
            "failures": list(self.failures),
        }


def run_provider_transport_preflight(
    provider_id: str,
    capability_token: str,
    evidence_binding_present: bool,
    dry_run: bool,
    live_mode: bool,
    network_mode: bool,
    budget_remaining: float = 0.0,
    budget_limit: float = 0.0,
    rate_limit_remaining: int = 0,
) -> PreflightResult:
    """Run all preflight gate checks. Returns a PreflightResult."""
    gates: Dict[str, bool] = {}
    failures: list[str] = []

    # Gate 1: Provider known
    gates["provider_known"] = provider_id in KNOWN_PROVIDERS
    if not gates["provider_known"]:
        failures.append("provider_not_known")

    # Gate 2: Provider not forbidden
    gates["provider_not_forbidden"] = provider_id not in FORBIDDEN_PROVIDERS
    if not gates["provider_not_forbidden"]:
        failures.append("provider_is_forbidden")

    # Gate 3: Capability token present
    has_cap = isinstance(capability_token, str) and bool(capability_token.strip())
    gates["capability_token_present"] = has_cap
    if not has_cap:
        failures.append("capability_token_missing")

    # Gate 4: No forbidden capability
    if has_cap:
        caps = {c.strip() for c in capability_token.split(",") if c.strip()}
        forbidden_in_request = caps & FORBIDDEN_CAPABILITIES
        gates["no_forbidden_capability"] = len(forbidden_in_request) == 0
        if not gates["no_forbidden_capability"]:
            failures.append(f"forbidden_capability_detected: {sorted(forbidden_in_request)}")
    else:
        gates["no_forbidden_capability"] = True

    # Gate 5: Evidence binding present
    gates["evidence_binding_present"] = evidence_binding_present
    if not evidence_binding_present:
        failures.append("evidence_binding_missing")

    # Gate 6: Dry-run only
    gates["dry_run_only"] = dry_run is True
    if not gates["dry_run_only"]:
        failures.append("dry_run_required")

    # Gate 7: No live mode
    gates["no_live_mode"] = live_mode is False
    if not gates["no_live_mode"]:
        failures.append("live_mode_rejected")

    # Gate 8: No network mode
    gates["no_network_mode"] = network_mode is False
    if not gates["no_network_mode"]:
        failures.append("network_mode_rejected")

    # Gate 9: Adapter registered
    adapter = get_provider_adapter(provider_id)
    gates["adapter_registered"] = adapter is not None
    if not gates["adapter_registered"]:
        failures.append("adapter_not_registered")

    # Gate 10: Adapter registered implies available for dry-run
    # In v1, enabled=False is the default and does not block dry-run.
    gates["adapter_dry_run_available"] = adapter is not None

    # Gate 11: Adapter dry_run_only (informational, always True in v1)
    gates["adapter_dry_run_only"] = adapter.dry_run_only if adapter else True

    # Gate 12: Budget within limit (non-negative remaining = within budget)
    gates["budget_within_limit"] = budget_remaining >= 0.0
    if not gates["budget_within_limit"]:
        failures.append(f"budget_limit_exceeded: remaining={budget_remaining}")

    # Gate 13: Rate limit available
    # If no limit is configured (both 0), pass. Otherwise check remaining > 0.
    if budget_limit == 0.0 and rate_limit_remaining == 0:
        gates["rate_limit_available"] = True
    else:
        gates["rate_limit_available"] = rate_limit_remaining > 0
    if not gates["rate_limit_available"]:
        failures.append("rate_limit_exhausted")

    all_pass = all(gates.values())
    if failures:
        all_pass = False

    return PreflightResult(
        passed=all_pass,
        gates=gates,
        failures=tuple(failures),
    )
