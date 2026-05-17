
"""Generated bounded local-only asset mapping foundation module.

v1 — contract-only. No real trading decision.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ALLOWED_ASSET_CLASSES = frozenset({"equity", "option", "future", "forex", "crypto", "index", "commodity"})
REQUIRED_FIELDS = frozenset({"candidate_id", "asset_class", "venue", "product_id", "evidence_refs", "confidence", "friction_data"})


@dataclass(frozen=True)
class AssetMappingReceipt:
    receipt_id: str
    candidate_id: str
    asset_class: str
    venue: str
    product_id: str
    evidence_present: bool
    confidence: float
    confidence_overclaim: bool
    friction_data_present: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_trading_decision: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_asset_mapping_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    ac = payload["asset_class"]
    if ac not in ALLOWED_ASSET_CLASSES:
        raise ValueError(f"unsupported_asset_class: {ac}")
    if not payload.get("venue"):
        raise ValueError("venue_is_required")
    if not payload.get("product_id"):
        raise ValueError("product_id_is_required")
    evidence = payload.get("evidence_refs", [])
    if not isinstance(evidence, list) or len(evidence) == 0:
        raise ValueError("evidence_refs_must_be_non_empty_list")
    return {"valid": True, "candidate_id": payload["candidate_id"]}


def validate_asset_candidate_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks = {
        "venue_present": bool(payload.get("venue")),
        "product_id_present": bool(payload.get("product_id")),
        "asset_class_supported": payload.get("asset_class") in ALLOWED_ASSET_CLASSES,
    }
    return {"candidate_valid": all(checks.values()), "checks": checks}


def validate_mapping_confidence_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    conf = payload.get("confidence", 0.0)
    if not isinstance(conf, (int, float)):
        raise TypeError("confidence must be numeric")
    overclaim = conf > 0.95
    if overclaim:
        raise ValueError(f"confidence_overclaim: {conf} exceeds max 0.95")
    return {"confidence": conf, "overclaim": overclaim, "within_bounds": not overclaim}


def produce_asset_mapping_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_asset_mapping_request(payload)
    candidate = validate_asset_candidate_contract(payload)
    conf_check = validate_mapping_confidence_contract(payload)
    receipt = AssetMappingReceipt(
        receipt_id=_hash_id(payload.get("candidate_id", "unknown"), _utcnow()),
        candidate_id=payload.get("candidate_id", "unknown"),
        asset_class=payload.get("asset_class", ""),
        venue=payload.get("venue", ""),
        product_id=payload.get("product_id", ""),
        evidence_present=len(payload.get("evidence_refs", [])) > 0,
        confidence=conf_check["confidence"],
        confidence_overclaim=conf_check["overclaim"],
        friction_data_present=bool(payload.get("friction_data")),
        status="mapped" if (candidate["candidate_valid"] and conf_check["within_bounds"]) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "AssetMappingReceipt",
    "validate_asset_mapping_request",
    "validate_asset_candidate_contract",
    "validate_mapping_confidence_contract",
    "produce_asset_mapping_receipt",
]
