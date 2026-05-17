
"""Generated bounded local-only replay engine foundation module.

v1 — contract-only. No actual replay execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = frozenset({
    "replay_anchor_id", "input_snapshot_hash", "policy_version",
    "code_version", "environment_fingerprint", "deterministic_mode",
    "no_cloud_requery",
})


@dataclass(frozen=True)
class ReplayEngineReceipt:
    receipt_id: str
    replay_anchor_id: str
    input_snapshot_hash: str
    policy_version: str
    code_version: str
    environment_fingerprint: str
    deterministic_mode: bool
    no_cloud_requery: bool
    anchor_valid: bool
    snapshot_valid: bool
    version_tuple_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_replay_execution: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_replay_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not isinstance(payload.get("deterministic_mode"), bool):
        raise TypeError("deterministic_mode must be a boolean")
    if not isinstance(payload.get("no_cloud_requery"), bool):
        raise TypeError("no_cloud_requery must be a boolean")
    if not payload.get("no_cloud_requery", False):
        raise ValueError("no_cloud_requery_must_be_true_for_replay")
    return {"valid": True, "replay_anchor_id": payload["replay_anchor_id"]}


def validate_replay_anchor_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    anchor = payload.get("replay_anchor_id", "")
    valid = isinstance(anchor, str) and len(anchor) > 0
    return {"anchor_valid": valid, "replay_anchor_id": anchor}


def validate_replay_input_snapshot_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    snap = payload.get("input_snapshot_hash", "")
    valid = isinstance(snap, str) and len(snap) == 64
    if not valid and len(snap) > 0:
        raise ValueError("input_snapshot_hash_must_be_sha256_hex_64_chars")
    return {"snapshot_valid": valid, "input_snapshot_hash": snap}


def validate_replay_version_tuple(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    pv = payload.get("policy_version", "")
    cv = payload.get("code_version", "")
    ef = payload.get("environment_fingerprint", "")
    valid = all(isinstance(v, str) and len(v) > 0 for v in (pv, cv, ef))
    return {"version_tuple_valid": valid, "policy_version": pv, "code_version": cv, "environment_fingerprint": ef}


def produce_replay_engine_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_replay_request(payload)
    anchor = validate_replay_anchor_contract(payload)
    snapshot = validate_replay_input_snapshot_contract(payload)
    version = validate_replay_version_tuple(payload)
    receipt = ReplayEngineReceipt(
        receipt_id=_hash_id(payload.get("replay_anchor_id", "unknown"), "v1"),
        replay_anchor_id=payload.get("replay_anchor_id", "unknown"),
        input_snapshot_hash=payload.get("input_snapshot_hash", ""),
        policy_version=payload.get("policy_version", ""),
        code_version=payload.get("code_version", ""),
        environment_fingerprint=payload.get("environment_fingerprint", ""),
        deterministic_mode=payload.get("deterministic_mode", True),
        no_cloud_requery=payload.get("no_cloud_requery", True),
        anchor_valid=anchor["anchor_valid"],
        snapshot_valid=snapshot["snapshot_valid"],
        version_tuple_valid=version["version_tuple_valid"],
        status="ready" if (anchor["anchor_valid"] and snapshot["snapshot_valid"] and version["version_tuple_valid"]) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "ReplayEngineReceipt",
    "validate_replay_request",
    "validate_replay_anchor_contract",
    "validate_replay_input_snapshot_contract",
    "validate_replay_version_tuple",
    "produce_replay_engine_receipt",
]
