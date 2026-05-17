
"""Generated bounded local-only recovery rollback foundation module.

v1 — contract-only. No production mutation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

IRREVERSIBLE_OPERATIONS = frozenset({"DROP_TABLE", "DELETE_WAL", "PURGE_VAULT", "HARD_DELETE", "TRUNCATE"})


@dataclass(frozen=True)
class RecoveryRollbackReceipt:
    receipt_id: str
    recovery_id: str
    rollback_target: str
    failure_evidence_present: bool
    rollback_plan_valid: bool
    is_reversible: bool
    approval_gate_passed: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_mutation: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_recovery_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"recovery_id", "rollback_target", "failure_evidence", "rollback_plan", "approval", "operation_type"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    optype = payload.get("operation_type", "")
    if optype in IRREVERSIBLE_OPERATIONS:
        raise ValueError(f"irreversible_operation: {optype}")
    if not payload.get("rollback_target"):
        raise ValueError("rollback_target_is_required")
    return {"valid": True, "recovery_id": payload["recovery_id"]}


def validate_rollback_plan(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    plan = payload.get("rollback_plan", {})
    if not isinstance(plan, dict):
        raise TypeError("rollback_plan must be a mapping")
    checks = {
        "target_present": bool(plan.get("target")),
        "steps_present": isinstance(plan.get("steps"), list) and len(plan.get("steps", [])) > 0,
        "verification_present": bool(plan.get("verification")),
        "is_reversible": plan.get("reversible", False),
    }
    all_pass = checks["target_present"] and checks["steps_present"] and checks["verification_present"]
    return {"rollback_plan_valid": all_pass, "checks": checks, "is_reversible": checks["is_reversible"]}


def validate_failure_bundle_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    fb = payload.get("failure_evidence", {})
    if not isinstance(fb, dict):
        raise TypeError("failure_evidence must be a mapping")
    checks = {
        "error_message_present": bool(fb.get("error_message")),
        "timestamp_present": bool(fb.get("failure_timestamp")),
        "component_present": bool(fb.get("component")),
    }
    return {"failure_bundle_valid": all(checks.values()), "checks": checks}


def produce_recovery_rollback_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_recovery_request(payload)
    plan = validate_rollback_plan(payload)
    failure = validate_failure_bundle_contract(payload)
    approval = payload.get("approval", {})
    approved = isinstance(approval, dict) and approval.get("approved", False) and bool(approval.get("approver_id"))
    receipt = RecoveryRollbackReceipt(
        receipt_id=_hash_id(payload.get("recovery_id", "unknown"), _utcnow()),
        recovery_id=payload.get("recovery_id", "unknown"),
        rollback_target=payload.get("rollback_target", ""),
        failure_evidence_present=failure["failure_bundle_valid"],
        rollback_plan_valid=plan["rollback_plan_valid"],
        is_reversible=plan["is_reversible"],
        approval_gate_passed=approved,
        status="ready" if (plan["rollback_plan_valid"] and failure["failure_bundle_valid"] and approved) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "RecoveryRollbackReceipt",
    "validate_recovery_request",
    "validate_rollback_plan",
    "validate_failure_bundle_contract",
    "produce_recovery_rollback_receipt",
]
