
"""Generated bounded local-only evidence index foundation module.

v1 — contract-only. No vault write.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

CONFLICT_POLICIES = frozenset({"REJECT_DUPLICATE", "OVERWRITE_OLDEST", "KEEP_NEWEST", "MANUAL_RESOLVE"})


@dataclass(frozen=True)
class EvidenceIndexReceipt:
    receipt_id: str
    artifact_id: str
    content_hash: str
    index_key: str
    conflict_policy: str
    lookup_valid: bool
    consistency_valid: bool
    is_duplicate: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_vault_write: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_evidence_index_entry(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"artifact_id", "content_hash", "index_key", "conflict_policy"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("artifact_id"):
        raise ValueError("missing_artifact_id")
    if not payload.get("content_hash"):
        raise ValueError("missing_content_hash")
    if not payload.get("index_key"):
        raise ValueError("missing_index_key")
    cp = payload.get("conflict_policy", "")
    if cp not in CONFLICT_POLICIES:
        raise ValueError(f"unsupported_conflict_policy: {cp}")
    return {"valid": True, "artifact_id": payload["artifact_id"]}


def validate_evidence_lookup_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    aid = payload.get("artifact_id", "")
    ik = payload.get("index_key", "")
    ch = payload.get("content_hash", "")
    valid = all([isinstance(aid, str) and len(aid) > 0,
                 isinstance(ik, str) and len(ik) > 0,
                 isinstance(ch, str) and len(ch) == 64])
    return {"lookup_valid": valid}


def validate_index_consistency_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    is_dup = payload.get("is_duplicate", False)
    cp = payload.get("conflict_policy", "")
    if is_dup and cp == "REJECT_DUPLICATE":
        raise ValueError("duplicate_rejected_by_policy")
    if is_dup and cp not in CONFLICT_POLICIES:
        raise ValueError("duplicate_without_explicit_conflict_policy")
    return {"is_duplicate": is_dup, "conflict_policy": cp, "consistent": not (is_dup and cp == "REJECT_DUPLICATE")}


def produce_evidence_index_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_evidence_index_entry(payload)
    lookup = validate_evidence_lookup_contract(payload)
    consistency = validate_index_consistency_contract(payload)
    receipt = EvidenceIndexReceipt(
        receipt_id=_hash_id(payload.get("artifact_id", "unknown"), "v1"),
        artifact_id=payload.get("artifact_id", "unknown"),
        content_hash=payload.get("content_hash", ""),
        index_key=payload.get("index_key", ""),
        conflict_policy=payload.get("conflict_policy", "REJECT_DUPLICATE"),
        lookup_valid=lookup["lookup_valid"],
        consistency_valid=consistency["consistent"],
        is_duplicate=consistency["is_duplicate"],
        status="indexed" if (lookup["lookup_valid"] and consistency["consistent"]) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "EvidenceIndexReceipt",
    "validate_evidence_index_entry",
    "validate_evidence_lookup_contract",
    "validate_index_consistency_contract",
    "produce_evidence_index_receipt",
]
