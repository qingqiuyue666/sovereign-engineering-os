"""Asset mapping contract shape. No trading execution."""

from __future__ import annotations

from typing import Mapping

__all__ = ["validate_asset_mapping_contract"]


def validate_asset_mapping_contract(contract: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(contract, Mapping):
        return ("asset_mapping_contract_must_be_mapping",)
    failures: list[str] = []
    for field in ("mapping_id", "macro_regime_ref", "asset_refs", "mapping_digest"):
        if field not in contract:
            failures.append(f"{field}_required")
    if not isinstance(contract.get("asset_refs"), list) or not contract.get("asset_refs"):
        failures.append("asset_refs_required")
    if not isinstance(contract.get("mapping_digest"), str) or not str(contract.get("mapping_digest")).startswith("sha256:"):
        failures.append("mapping_digest_required")
    if contract.get("trading_execution_performed") is True or contract.get("telegram_push_performed") is True:
        failures.append("execution_or_push_forbidden")
    return tuple(sorted(set(failures)))
