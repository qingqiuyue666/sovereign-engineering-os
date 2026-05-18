"""Read-only status helpers for durable operator review stores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_review_store import OperatorReviewStore

__all__ = [
    "ReviewStoreStatus",
    "summarize_review_store",
    "render_review_status_text",
]

_POLICY_VERSION = "operator-review-status-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class ReviewStoreStatus:
    store_id: str
    total_records: int
    session_count: int
    approval_count: int
    rejection_count: int
    review_history_hash: str
    verification_hash: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_count": self.approval_count,
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "rejection_count": self.rejection_count,
            "review_history_hash": self.review_history_hash,
            "session_count": self.session_count,
            "store_id": self.store_id,
            "total_records": self.total_records,
            "verification_hash": self.verification_hash,
        }


def summarize_review_store(path: str | Path, *, store_id: str) -> ReviewStoreStatus:
    """Summarize a durable review store without mutating it."""

    store = OperatorReviewStore(path, store_id=store_id)
    verification = store.verify_store()
    if not verification.valid:
        raise ValueError("review_store_invalid")
    status = ReviewStoreStatus(
        store_id=store_id,
        total_records=verification.total_records,
        session_count=verification.session_count,
        approval_count=verification.approval_count,
        rejection_count=verification.rejection_count,
        review_history_hash=verification.review_history_hash,
        verification_hash=verification.content_hash,
        content_hash="",
    )
    return ReviewStoreStatus(
        store_id=status.store_id,
        total_records=status.total_records,
        session_count=status.session_count,
        approval_count=status.approval_count,
        rejection_count=status.rejection_count,
        review_history_hash=status.review_history_hash,
        verification_hash=status.verification_hash,
        policy_version=status.policy_version,
        code_version=status.code_version,
        content_hash=digest_payload(status.deterministic_material()),
    )


def render_review_status_text(status: ReviewStoreStatus) -> str:
    """Render a concise read-only review-store status line."""

    if not isinstance(status, ReviewStoreStatus):
        raise ValueError("status_must_be_review_store_status")
    return (
        f"review_store={status.store_id} records={status.total_records} "
        f"sessions={status.session_count} approvals={status.approval_count} "
        f"rejections={status.rejection_count} history_hash={status.review_history_hash}"
    )
