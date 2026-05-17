
"""Generated bounded local-only OSINT ingestion foundation module.

v1 — contract-only. No real ingestion.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

SOURCE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY", "TIER_3_TERTIARY"})
DOWNGRADE_ACTIONS = frozenset({"WAIT", "NO_TRADE", "FLAG_ONLY"})
FORBIDDEN_SOURCES = frozenset({"live_network", "live_scraper", "live_api"})


@dataclass(frozen=True)
class OsintIngestionReceipt:
    receipt_id: str
    source_id: str
    source_tier: str
    freshness_timestamp: str
    evidence_hash_present: bool
    conflict_resolution: str
    status: str
    created_at: str
    module_version: str = "v1"
    no_ingestion: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_osint_ingestion_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"source_id", "source_tier", "timestamp", "evidence_hash", "conflict_resolution"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    source_id = payload["source_id"]
    if source_id in FORBIDDEN_SOURCES:
        raise ValueError(f"forbidden_source: {source_id}")
    tier = payload["source_tier"]
    if tier not in SOURCE_TIERS:
        raise ValueError(f"unsupported_source_tier: {tier}")
    conflict = payload.get("conflict_resolution", "")
    if conflict and conflict not in DOWNGRADE_ACTIONS and conflict != "NONE":
        raise ValueError(f"invalid_conflict_resolution: {conflict}")
    return {"valid": True, "source_id": source_id}


def validate_source_tier_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    tier = payload.get("source_tier", "")
    downgraded = tier == "TIER_3_TERTIARY"
    return {"tier": tier, "downgraded": downgraded, "action_required": "NO_TRADE" if downgraded else "ALLOW"}


def validate_freshness_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    ts = payload.get("timestamp", "")
    if not ts:
        return {"fresh": False, "reason": "missing_timestamp"}
    return {"fresh": True, "timestamp": ts}


def produce_osint_ingestion_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_osint_ingestion_request(payload)
    tier_check = validate_source_tier_contract(payload)
    freshness = validate_freshness_contract(payload)
    status = "ingested"
    if tier_check["downgraded"]:
        status = "downgraded"
    if not freshness["fresh"]:
        status = "stale_rejected"
    receipt = OsintIngestionReceipt(
        receipt_id=_hash_id(payload.get("source_id", "unknown"), "v1"),
        source_id=payload.get("source_id", "unknown"),
        source_tier=payload.get("source_tier", ""),
        freshness_timestamp=payload.get("timestamp", ""),
        evidence_hash_present=bool(payload.get("evidence_hash")),
        conflict_resolution=payload.get("conflict_resolution", "NONE"),
        status=status,
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "OsintIngestionReceipt",
    "validate_osint_ingestion_request",
    "validate_source_tier_contract",
    "validate_freshness_contract",
    "produce_osint_ingestion_receipt",
]
