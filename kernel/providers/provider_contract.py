"""Provider adapter metadata contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = ["ProviderContractResult", "validate_provider_contract"]


@dataclass(frozen=True)
class ProviderContractResult:
    accepted: bool
    failures: tuple[str, ...]


def validate_provider_contract(contract: Mapping[str, object]) -> ProviderContractResult:
    if not isinstance(contract, Mapping):
        return ProviderContractResult(False, ("provider_contract_must_be_mapping",))
    failures: list[str] = []
    if not isinstance(contract.get("provider_id"), str) or not contract.get("provider_id"):
        failures.append("provider_id_required")
    if contract.get("mode") != "mock_only":
        failures.append("mock_only_mode_required")
    for flag in ("network_allowed", "live_provider_allowed", "raw_response_persistence_allowed"):
        if contract.get(flag) is not False:
            failures.append(f"{flag}_must_be_false")
    return ProviderContractResult(not failures, tuple(sorted(set(failures))))
