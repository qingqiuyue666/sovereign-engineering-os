"""Replay helpers for the durable operator review store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_nonempty_string
from kernel.runtime.operator_review_store import OperatorReviewStore

__all__ = ["OperatorReviewStoreReplayReceipt", "replay_review_store"]

_POLICY_VERSION = "operator-review-store-replay-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class OperatorReviewStoreReplayReceipt:
    """Deterministic receipt for read-only review-store replay."""

    store_id: str
    total_records: int
    session_count: int
    approval_count: int
    rejection_count: int
    review_history_hash: str
    verification_hash: str
    replayed: bool
    reasons: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_count": self.approval_count,
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "reasons": list(self.reasons),
            "rejection_count": self.rejection_count,
            "replayed": self.replayed,
            "review_history_hash": self.review_history_hash,
            "session_count": self.session_count,
            "store_id": self.store_id,
            "total_records": self.total_records,
            "verification_hash": self.verification_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def replay_review_store(
    path: str | Path,
    *,
    store_id: str,
    observed_at: str | None = None,
) -> OperatorReviewStoreReplayReceipt:
    """Rebuild and verify a review store without mutating it."""

    if not strict_nonempty_string(store_id):
        raise ValueError("store_id_must_be_nonempty_string")
    observed = _observed_at(observed_at)
    store = OperatorReviewStore(path, store_id=store_id)
    verification = store.verify_store(observed_at=observed)
    receipt = OperatorReviewStoreReplayReceipt(
        store_id=store_id,
        total_records=verification.total_records,
        session_count=verification.session_count,
        approval_count=verification.approval_count,
        rejection_count=verification.rejection_count,
        review_history_hash=verification.review_history_hash,
        verification_hash=verification.content_hash,
        replayed=verification.valid,
        reasons=verification.reasons,
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(receipt)


def _with_hash(receipt: OperatorReviewStoreReplayReceipt) -> OperatorReviewStoreReplayReceipt:
    return OperatorReviewStoreReplayReceipt(
        store_id=receipt.store_id,
        total_records=receipt.total_records,
        session_count=receipt.session_count,
        approval_count=receipt.approval_count,
        rejection_count=receipt.rejection_count,
        review_history_hash=receipt.review_history_hash,
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
