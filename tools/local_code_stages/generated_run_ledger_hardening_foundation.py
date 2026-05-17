
"""Generated bounded local-only run ledger hardening foundation module.

v1 — contract-only. No mutable ledger claim.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

ALLOWED_STATUSES = frozenset({"pending", "running", "completed", "failed", "rolled_back", "cancelled"})
VALID_TRANSITIONS = {
    "pending": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": {"rolled_back"},
    "failed": {"rolled_back", "pending"},
    "rolled_back": set(),
    "cancelled": set(),
}
FORBIDDEN_TRANSITIONS = frozenset({"completed_to_running", "rolled_back_to_running", "completed_to_pending"})


@dataclass(frozen=True)
class RunLedgerReceipt:
    receipt_id: str
    run_id: str
    operator_id: str
    status: str
    previous_status: str
    transition_valid: bool
    sequence_valid: bool
    evidence_link_present: bool
    mutable_claim: bool
    created_at: str
    module_version: str = "v1"
    no_ledger_write: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_run_ledger_entry(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"run_id", "operator_id", "status", "previous_status", "sequence_number", "evidence_link"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("run_id"):
        raise ValueError("missing_run_id")
    if not payload.get("operator_id"):
        raise ValueError("missing_operator_id")
    status = payload["status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid_status: {status}")
    return {"valid": True, "run_id": payload["run_id"]}


def validate_run_sequence_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    seq = payload.get("sequence_number", 0)
    if not isinstance(seq, (int, float)):
        raise TypeError("sequence_number must be numeric")
    return {"sequence_valid": seq > 0, "sequence_number": seq}


def validate_run_status_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    current = payload.get("status", "")
    previous = payload.get("previous_status", "")
    valid = False
    if previous in VALID_TRANSITIONS:
        valid = current in VALID_TRANSITIONS[previous]
    return {
        "transition_valid": valid,
        "current": current,
        "previous": previous,
        "forbidden": f"{previous}_to_{current}" in FORBIDDEN_TRANSITIONS,
    }


def produce_run_ledger_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_run_ledger_entry(payload)
    seq_check = validate_run_sequence_contract(payload)
    status_check = validate_run_status_contract(payload)
    mutable = payload.get("mutable_ledger", False)
    if mutable:
        raise ValueError("mutable_ledger_claim_rejected")
    receipt = RunLedgerReceipt(
        receipt_id=_hash_id(payload.get("run_id", "unknown"), _utcnow()),
        run_id=payload.get("run_id", "unknown"),
        operator_id=payload.get("operator_id", "unknown"),
        status=payload.get("status", ""),
        previous_status=payload.get("previous_status", ""),
        transition_valid=status_check["transition_valid"],
        sequence_valid=seq_check["sequence_valid"],
        evidence_link_present=bool(payload.get("evidence_link")),
        mutable_claim=mutable,
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "RunLedgerReceipt",
    "validate_run_ledger_entry",
    "validate_run_sequence_contract",
    "validate_run_status_contract",
    "produce_run_ledger_receipt",
]
