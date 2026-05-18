"""Replay helpers for the durable operator decision store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_nonempty_string
from kernel.runtime.operator_decision_store import OperatorDecisionStore

__all__ = ["OperatorDecisionStoreReplayReceipt", "replay_decision_store"]

_POLICY_VERSION = "operator-decision-store-replay-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class OperatorDecisionStoreReplayReceipt:
    """Deterministic receipt for read-only decision-store replay."""

    store_id: str
    total_records: int
    decision_chain_head: str
    snapshot_hash: str
    verification_hash: str
    replayed: bool
    reasons: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "decision_chain_head": self.decision_chain_head,
            "policy_version": self.policy_version,
            "reasons": list(self.reasons),
            "replayed": self.replayed,
            "snapshot_hash": self.snapshot_hash,
            "store_id": self.store_id,
            "total_records": self.total_records,
            "verification_hash": self.verification_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def replay_decision_store(
    path: str | Path,
    *,
    store_id: str,
    observed_at: str | None = None,
) -> OperatorDecisionStoreReplayReceipt:
    """Rebuild and verify a decision store without mutating it."""

    if not strict_nonempty_string(store_id):
        raise ValueError("store_id_must_be_nonempty_string")
    observed = _observed_at(observed_at)
    store = OperatorDecisionStore(path, store_id=store_id)
    verification = store.verify_store(observed_at=observed)
    if not verification.valid:
        receipt = OperatorDecisionStoreReplayReceipt(
            store_id=store_id,
            total_records=0,
            decision_chain_head=verification.decision_chain_head,
            snapshot_hash=verification.snapshot_hash,
            verification_hash=verification.content_hash,
            replayed=False,
            reasons=verification.reasons,
            content_hash="",
            observed_at=observed,
        )
        return _with_hash(receipt)

    snapshot = store.export_snapshot()
    receipt = OperatorDecisionStoreReplayReceipt(
        store_id=store_id,
        total_records=verification.total_records,
        decision_chain_head=snapshot.decision_chain_head,
        snapshot_hash=snapshot.content_hash,
        verification_hash=verification.content_hash,
        replayed=True,
        reasons=(),
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(receipt)


def _with_hash(receipt: OperatorDecisionStoreReplayReceipt) -> OperatorDecisionStoreReplayReceipt:
    return OperatorDecisionStoreReplayReceipt(
        store_id=receipt.store_id,
        total_records=receipt.total_records,
        decision_chain_head=receipt.decision_chain_head,
        snapshot_hash=receipt.snapshot_hash,
        verification_hash=receipt.verification_hash,
        replayed=receipt.replayed,
        reasons=receipt.reasons,
        policy_version=receipt.policy_version,
        code_version=receipt.code_version,
        content_hash=digest_payload(receipt.deterministic_material()),
        observed_at=receipt.observed_at,
    )


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
