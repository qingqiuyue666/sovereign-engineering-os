"""OSINT task contract skeleton. No ingestion or network fetch."""

from __future__ import annotations

from typing import Mapping

from .source_reliability import validate_source_metadata

__all__ = ["validate_osint_task_contract"]


def validate_osint_task_contract(contract: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(contract, Mapping):
        return ("osint_task_contract_must_be_mapping",)
    failures: list[str] = []
    for field in ("task_id", "source_refs", "freshness_metadata"):
        if field not in contract:
            failures.append(f"{field}_required")
    if not isinstance(contract.get("source_refs"), list) or not contract.get("source_refs"):
        failures.append("source_refs_required")
    if isinstance(contract.get("freshness_metadata"), Mapping):
        failures.extend(validate_source_metadata(contract["freshness_metadata"]))  # type: ignore[arg-type]
    if contract.get("network_fetch_performed") is True or contract.get("live_ingestion") is True:
        failures.append("osint_live_ingestion_forbidden")
    return tuple(sorted(set(failures)))
