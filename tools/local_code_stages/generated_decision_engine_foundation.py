
"""Generated bounded local-only decision engine foundation module.

v1 — contract-only. No real trade execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

ALLOWED_ACTIONS = frozenset({"HOLD", "FLAG", "ESCALATE", "REVIEW"})
FORBIDDEN_ACTIONS = frozenset({"BUY", "SELL", "EXECUTE", "ORDER", "TRADE", "SHORT", "COVER"})
MIN_CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class DecisionEngineReceipt:
    receipt_id: str
    decision_id: str
    action: str
    confidence: float
    confidence_gate_passed: bool
    friction_gate_passed: bool
    single_action_enforced: bool
    human_review_present: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_execution: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_decision_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"decision_id", "actions", "confidence", "friction_data", "human_review", "evidence_refs"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    actions = payload.get("actions", [])
    if not isinstance(actions, list):
        raise TypeError("actions must be a list")
    if len(actions) == 0:
        raise ValueError("actions_must_not_be_empty")
    return {"valid": True, "decision_id": payload["decision_id"]}


def validate_single_action_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    actions = payload.get("actions", [])
    if len(actions) > 1:
        raise ValueError("multiple_actions_forbidden")
    if not actions:
        raise ValueError("no_action_specified")
    action = actions[0]
    if not isinstance(action, str):
        raise TypeError("action must be a string")
    if action in FORBIDDEN_ACTIONS:
        raise ValueError(f"forbidden_action: {action}")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported_action: {action}")
    return {"action": action, "single_action": True}


def validate_confidence_gate(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    conf = payload.get("confidence", 0.0)
    if not isinstance(conf, (int, float)):
        raise TypeError("confidence must be numeric")
    overclaim = conf > 0.95
    if overclaim:
        raise ValueError(f"confidence_overclaim: {conf}")
    passed = conf >= MIN_CONFIDENCE_THRESHOLD
    return {"confidence": conf, "gate_passed": passed, "overclaim": overclaim}


def validate_friction_gate(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    fd = payload.get("friction_data", {})
    if not isinstance(fd, dict):
        raise TypeError("friction_data must be a mapping")
    checks = {
        "spread_present": "spread" in fd or "slippage" in fd or "impact" in fd,
        "venue_present": "venue" in fd,
    }
    passed = all(checks.values())
    return {"friction_gate_passed": passed, "checks": checks}


def produce_decision_engine_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_decision_request(payload)
    action_check = validate_single_action_contract(payload)
    conf_check = validate_confidence_gate(payload)
    friction_check = validate_friction_gate(payload)
    hr = payload.get("human_review", {})
    has_review = isinstance(hr, dict) and hr.get("reviewed", False) and bool(hr.get("reviewer_id"))
    receipt = DecisionEngineReceipt(
        receipt_id=_hash_id(payload.get("decision_id", "unknown"), "v1"),
        decision_id=payload.get("decision_id", "unknown"),
        action=action_check["action"],
        confidence=conf_check["confidence"],
        confidence_gate_passed=conf_check["gate_passed"],
        friction_gate_passed=friction_check["friction_gate_passed"],
        single_action_enforced=action_check["single_action"],
        human_review_present=has_review,
        status="approved" if (conf_check["gate_passed"] and friction_check["friction_gate_passed"] and has_review) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "DecisionEngineReceipt",
    "validate_decision_request",
    "validate_single_action_contract",
    "validate_confidence_gate",
    "validate_friction_gate",
    "produce_decision_engine_receipt",
]
