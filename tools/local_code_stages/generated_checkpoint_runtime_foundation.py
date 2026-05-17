
"""Generated bounded local-only checkpoint runtime foundation module.

v1 — contract-only. No real checkpoint mutation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class CheckpointRuntimeReceipt:
    receipt_id: str
    checkpoint_id: str
    source_revision: str
    content_hash: str
    rollback_reference: str
    scope_valid: bool
    integrity_valid: bool
    state_clean: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_checkpoint_mutation: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_checkpoint_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"checkpoint_id", "scope", "content_hash", "source_revision", "rollback_reference", "state_status", "approval"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("content_hash"):
        raise ValueError("checkpoint_without_hash")
    if not payload.get("source_revision"):
        raise ValueError("checkpoint_without_source_revision")
    if not payload.get("rollback_reference"):
        raise ValueError("checkpoint_without_rollback_reference")
    return {"valid": True, "checkpoint_id": payload["checkpoint_id"]}


def validate_checkpoint_scope(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    scope = payload.get("scope", {})
    if not isinstance(scope, dict):
        raise TypeError("scope must be a mapping")
    checks = {
        "paths_present": isinstance(scope.get("paths"), list) and len(scope.get("paths", [])) > 0,
        "module_present": bool(scope.get("module")),
    }
    valid = all(checks.values())
    return {"scope_valid": valid, "checks": checks}


def validate_checkpoint_integrity_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    ch = payload.get("content_hash", "")
    sr = payload.get("source_revision", "")
    rr = payload.get("rollback_reference", "")
    valid = all([
        isinstance(ch, str) and len(ch) == 64,
        isinstance(sr, str) and len(sr) > 0,
        isinstance(rr, str) and len(rr) > 0,
    ])
    return {"integrity_valid": valid}


def produce_checkpoint_runtime_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_checkpoint_request(payload)
    scope = validate_checkpoint_scope(payload)
    integrity = validate_checkpoint_integrity_contract(payload)
    state_status = payload.get("state_status", {})
    dirty = isinstance(state_status, dict) and state_status.get("dirty", True)
    unapproved = not (isinstance(state_status, dict) and state_status.get("approved", False))
    if dirty and unapproved:
        raise ValueError("checkpoint_on_dirty_unapproved_state")
    approval = payload.get("approval", {})
    approved = isinstance(approval, dict) and approval.get("approved", False)
    receipt = CheckpointRuntimeReceipt(
        receipt_id=_hash_id(payload.get("checkpoint_id", "unknown"), "v1"),
        checkpoint_id=payload.get("checkpoint_id", "unknown"),
        source_revision=payload.get("source_revision", ""),
        content_hash=payload.get("content_hash", ""),
        rollback_reference=payload.get("rollback_reference", ""),
        scope_valid=scope["scope_valid"],
        integrity_valid=integrity["integrity_valid"],
        state_clean=not dirty,
        status="created" if (scope["scope_valid"] and integrity["integrity_valid"] and approved and not dirty) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "CheckpointRuntimeReceipt",
    "validate_checkpoint_request",
    "validate_checkpoint_scope",
    "validate_checkpoint_integrity_contract",
    "produce_checkpoint_runtime_receipt",
]
