
"""Generated bounded local-only operator daily run foundation module.

v1 — contract-only. No real execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class OperatorDailyRunReceipt:
    receipt_id: str
    run_id: str
    operator_id: str
    runbook_reference: str
    evidence_summary_present: bool
    human_review_completed: bool
    approval_gate_passed: bool
    run_window_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_execution_performed: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_operator_daily_run_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"run_id", "operator_id", "runbook_reference", "evidence_summary", "human_review", "approval", "run_window"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not isinstance(payload.get("human_review"), dict):
        raise TypeError("human_review must be a mapping")
    hr = payload["human_review"]
    if not hr.get("completed", False):
        raise ValueError("human_review_not_completed")
    if not hr.get("reviewer_id"):
        raise ValueError("human_review_missing_reviewer_id")
    return {"valid": True, "run_id": payload["run_id"]}


def validate_operator_run_window(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    window = payload.get("run_window", {})
    if not isinstance(window, dict):
        raise TypeError("run_window must be a mapping")
    start = window.get("start", "")
    end = window.get("end", "")
    valid = bool(start and end and start < end)
    return {"run_window_valid": valid, "start": start, "end": end}


def validate_operator_review_gate(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    approval = payload.get("approval", {})
    if not isinstance(approval, dict):
        raise TypeError("approval must be a mapping")
    checks = {
        "operator_approved": approval.get("operator_approved", False),
        "approver_id_present": bool(approval.get("approver_id")),
        "approval_timestamp_present": bool(approval.get("approval_timestamp")),
    }
    all_pass = all(checks.values())
    return {"approval_gate_passed": all_pass, "checks": checks}


def produce_operator_daily_run_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_operator_daily_run_request(payload)
    window = validate_operator_run_window(payload)
    review = validate_operator_review_gate(payload)
    receipt = OperatorDailyRunReceipt(
        receipt_id=_hash_id(payload.get("run_id", "unknown"), "v1"),
        run_id=payload.get("run_id", "unknown"),
        operator_id=payload.get("operator_id", "unknown"),
        runbook_reference=payload.get("runbook_reference", ""),
        evidence_summary_present=bool(payload.get("evidence_summary")),
        human_review_completed=payload.get("human_review", {}).get("completed", False),
        approval_gate_passed=review["approval_gate_passed"],
        run_window_valid=window["run_window_valid"],
        status="approved" if (review["approval_gate_passed"] and window["run_window_valid"]) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "OperatorDailyRunReceipt",
    "validate_operator_daily_run_request",
    "validate_operator_run_window",
    "validate_operator_review_gate",
    "produce_operator_daily_run_receipt",
]
