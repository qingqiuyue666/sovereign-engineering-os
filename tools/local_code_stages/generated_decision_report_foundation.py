
"""Generated bounded local-only decision report foundation module.

v1 — contract-only. No production report publication.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

SUPPORTED_ACTIONS = frozenset({"HOLD", "FLAG", "ESCALATE", "REVIEW"})
FORBIDDEN_ACTIONS = frozenset({"BUY", "SELL", "EXECUTE", "ORDER", "TRADE"})


@dataclass(frozen=True)
class DecisionReportReceipt:
    receipt_id: str
    decision_id: str
    action: str
    evidence_links_present: bool
    confidence_rationale_present: bool
    friction_summary_present: bool
    human_review_present: bool
    overclaim_detected: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_report_publication: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_decision_report(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"decision_id", "action", "evidence_links", "confidence_rationale", "friction_summary", "human_review"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("decision_id"):
        raise ValueError("missing_decision_id")
    action = payload.get("action", "")
    if action in FORBIDDEN_ACTIONS:
        raise ValueError(f"forbidden_action: {action}")
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"unsupported_action: {action}")
    return {"valid": True, "decision_id": payload["decision_id"]}


def validate_report_evidence_links(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    links = payload.get("evidence_links", [])
    if not isinstance(links, list) or len(links) == 0:
        raise ValueError("evidence_links_must_be_non_empty_list")
    return {"evidence_links_present": True, "count": len(links)}


def validate_report_non_overclaim(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    claims = payload.get("confidence_rationale", {})
    if not isinstance(claims, dict):
        raise TypeError("confidence_rationale must be a mapping")
    confidence = claims.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        raise TypeError("confidence must be numeric")
    overclaim = confidence > 0.95
    if overclaim:
        raise ValueError(f"overclaim_detected: confidence {confidence} exceeds max 0.95")
    claims_made = claims.get("claims", [])
    if not isinstance(claims_made, list):
        raise TypeError("claims must be a list")
    bounded = all(isinstance(c, str) and len(c) > 0 for c in claims_made)
    return {"overclaim": overclaim, "confidence": confidence, "claims_bounded": bounded}


def produce_decision_report_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_decision_report(payload)
    evidence = validate_report_evidence_links(payload)
    non_overclaim = validate_report_non_overclaim(payload)
    hr = payload.get("human_review", {})
    has_review = isinstance(hr, dict) and hr.get("reviewed", False) and bool(hr.get("reviewer_id"))
    friction = payload.get("friction_summary", {})
    has_friction = isinstance(friction, dict) and bool(friction.get("summary"))
    receipt = DecisionReportReceipt(
        receipt_id=_hash_id(payload.get("decision_id", "unknown"), _utcnow()),
        decision_id=payload.get("decision_id", "unknown"),
        action=payload.get("action", ""),
        evidence_links_present=evidence["evidence_links_present"],
        confidence_rationale_present=bool(payload.get("confidence_rationale")),
        friction_summary_present=has_friction,
        human_review_present=has_review,
        overclaim_detected=non_overclaim["overclaim"],
        status="published" if (evidence["evidence_links_present"] and has_review and has_friction and not non_overclaim["overclaim"]) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "DecisionReportReceipt",
    "validate_decision_report",
    "validate_report_evidence_links",
    "validate_report_non_overclaim",
    "produce_decision_report_receipt",
]
