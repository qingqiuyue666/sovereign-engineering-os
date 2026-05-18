from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ReplayReceipt:
    receipt_id: str
    anchor_id: str
    snapshot_id: str
    version_tuple_id: str
    status: str
    mode: str
    evidence_binding_valid: bool
    evidence_binding_hash: str
    evidence_artifact_ids: List[str]
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_replay_execution: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayReadinessReceipt:
    receipt_id: str
    anchor_id: str
    snapshot_id: str
    version_tuple_id: str
    ready: bool
    gates: Dict[str, bool]
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_replay_execution: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayFailureReceipt:
    receipt_id: str
    anchor_id: str
    failure_reason: str
    failure_code: str
    evidence_corrupted: bool
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_replay_execution: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hash_id(*parts: str) -> str:
    return hashlib.blake2b("|".join(parts).encode(), digest_size=16).hexdigest()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def produce_replay_receipt(
    anchor_id: str,
    snapshot_id: str,
    version_tuple_id: str,
    status: str,
    mode: str,
    evidence_binding_valid: bool,
    evidence_binding_hash: str = "",
    evidence_artifact_ids: Optional[List[str]] = None,
    created_at: str = "",
) -> ReplayReceipt:
    if not anchor_id.strip():
        raise ValueError("anchor_id required")
    if status not in ("ready", "rejected", "failed"):
        raise ValueError(f"invalid status: {status}")
    if mode not in ("strict", "dry_run"):
        raise ValueError(f"invalid mode: {mode}")
    ids = sorted(evidence_artifact_ids or [])
    if evidence_binding_valid and (not evidence_binding_hash.strip() or not ids):
        raise ValueError("evidence binding hash and ids required")

    raw = "|".join([
        anchor_id, snapshot_id, version_tuple_id, status, mode,
        str(evidence_binding_valid), evidence_binding_hash, "|".join(ids),
    ])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(anchor_id, snapshot_id, canonical)
    return ReplayReceipt(
        receipt_id=receipt_id,
        anchor_id=anchor_id,
        snapshot_id=snapshot_id,
        version_tuple_id=version_tuple_id,
        status=status,
        mode=mode,
        evidence_binding_valid=evidence_binding_valid,
        evidence_binding_hash=evidence_binding_hash,
        evidence_artifact_ids=ids,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )


def produce_readiness_receipt(
    anchor_id: str,
    snapshot_id: str,
    version_tuple_id: str,
    gates: Dict[str, bool],
    created_at: str = "",
) -> ReplayReadinessReceipt:
    ready = all(gates.values())
    raw = "|".join([
        anchor_id, snapshot_id, version_tuple_id, str(ready),
        "|".join(f"{k}={v}" for k, v in sorted(gates.items())),
    ])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(anchor_id, "readiness", canonical)
    return ReplayReadinessReceipt(
        receipt_id=receipt_id,
        anchor_id=anchor_id,
        snapshot_id=snapshot_id,
        version_tuple_id=version_tuple_id,
        ready=ready,
        gates=gates,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )


def produce_failure_receipt(
    anchor_id: str,
    failure_reason: str,
    failure_code: str,
    evidence_corrupted: bool = False,
    created_at: str = "",
) -> ReplayFailureReceipt:
    if not failure_reason.strip():
        raise ValueError("failure_reason required")
    if not failure_code.strip():
        raise ValueError("failure_code required")
    raw = "|".join([anchor_id, failure_reason, failure_code, str(evidence_corrupted)])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(anchor_id, "failure", canonical)
    return ReplayFailureReceipt(
        receipt_id=receipt_id,
        anchor_id=anchor_id,
        failure_reason=failure_reason,
        failure_code=failure_code,
        evidence_corrupted=evidence_corrupted,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )
