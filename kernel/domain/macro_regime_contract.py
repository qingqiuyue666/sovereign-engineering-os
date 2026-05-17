"""Macro regime contract shape."""

from __future__ import annotations

from typing import Mapping

__all__ = ["validate_macro_regime_contract"]


def validate_macro_regime_contract(contract: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(contract, Mapping):
        return ("macro_regime_contract_must_be_mapping",)
    failures: list[str] = []
    for field in ("regime_id", "classification", "evidence_digest_refs", "conflict_status"):
        if field not in contract:
            failures.append(f"{field}_required")
    if not isinstance(contract.get("evidence_digest_refs"), list) or not all(isinstance(item, str) and item.startswith("sha256:") for item in contract.get("evidence_digest_refs", [])):
        failures.append("evidence_digest_refs_required")
    if contract.get("live_data_fetch_performed") is True:
        failures.append("live_data_fetch_forbidden")
    return tuple(sorted(set(failures)))
