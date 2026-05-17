"""Source reliability and freshness metadata validation."""

from __future__ import annotations

from typing import Mapping

__all__ = ["SOURCE_RELIABILITY_TIERS", "validate_source_metadata"]

SOURCE_RELIABILITY_TIERS = ("PRIMARY", "SECONDARY", "TERTIARY", "UNVERIFIED")
_CONFLICT_STATUS = ("none", "conflicting", "unresolved")


def validate_source_metadata(metadata: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(metadata, Mapping):
        return ("source_metadata_must_be_mapping",)
    failures: list[str] = []
    if metadata.get("reliability_tier") not in SOURCE_RELIABILITY_TIERS:
        failures.append("reliability_tier_invalid")
    if not isinstance(metadata.get("freshness_timestamp"), str) or not metadata.get("freshness_timestamp"):
        failures.append("freshness_timestamp_required")
    if metadata.get("conflict_status") not in _CONFLICT_STATUS:
        failures.append("conflict_status_invalid")
    if metadata.get("network_fetch_performed") is True:
        failures.append("network_fetch_forbidden")
    return tuple(sorted(set(failures)))
