"""Deterministic read-only operator work queue derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string
from kernel.runtime.operator_decision_ledger import (
    OperatorDecisionLedgerEntry,
    validate_ledger_entry,
)
from kernel.runtime.operator_decision_store import OperatorDecisionStore
from kernel.runtime.operator_review_receipt import (
    ApprovalReceipt,
    RejectionReceipt,
    validate_approval_receipt,
    validate_rejection_receipt,
)
from kernel.runtime.operator_review_session import (
    OperatorReviewSession,
    validate_review_session_material,
)
from kernel.runtime.operator_review_store import OperatorReviewStore

__all__ = [
    "OperatorWorkQueueItem",
    "OperatorWorkQueue",
    "build_operator_work_queue_from_material",
    "build_operator_work_queue",
]

_POLICY_VERSION = "operator-work-queue-v1"
_CODE_VERSION = "0.1.0"
_VALID_QUEUE_STATUSES = frozenset({"pending_review", "approved", "rejected", "blocked"})


@dataclass(frozen=True)
class OperatorWorkQueueItem:
    session_id: str
    run_id: str
    task_id: str
    review_packet_hash: str
    promotion_receipt_hash: str
    queue_status: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "promotion_receipt_hash": self.promotion_receipt_hash,
            "queue_status": self.queue_status,
            "review_packet_hash": self.review_packet_hash,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


@dataclass(frozen=True)
class OperatorWorkQueue:
    queue_id: str
    items: tuple[OperatorWorkQueueItem, ...]
    pending_review_count: int
    approved_count: int
    rejected_count: int
    blocked_count: int
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approved_count": self.approved_count,
            "blocked_count": self.blocked_count,
            "code_version": self.code_version,
            "item_hashes": [item.content_hash for item in self.items],
            "pending_review_count": self.pending_review_count,
            "policy_version": self.policy_version,
            "queue_id": self.queue_id,
            "rejected_count": self.rejected_count,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["items"] = [item.as_dict() for item in self.items]
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_work_queue(
    *,
    queue_id: str,
    review_store_path: str | Path,
    review_store_id: str,
    decision_store_path: str | Path | None = None,
    decision_store_id: str | None = None,
    observed_at: str | None = None,
) -> OperatorWorkQueue:
    """Build a read-only queue from durable stores."""

    review_store = OperatorReviewStore(review_store_path, store_id=review_store_id)
    history = review_store.rebuild_review_history()
    decision_entries: tuple[OperatorDecisionLedgerEntry, ...] = ()
    if decision_store_path is not None:
        if not strict_nonempty_string(decision_store_id):
            raise ValueError("decision_store_id_must_be_nonempty_string")
        decision_store = OperatorDecisionStore(decision_store_path, store_id=decision_store_id or "")
        decision_entries = decision_store.load_entries()
    return build_operator_work_queue_from_material(
        queue_id=queue_id,
        sessions=history.sessions,
        approval_receipts=history.approval_receipts,
        rejection_receipts=history.rejection_receipts,
        decision_entries=decision_entries,
        observed_at=observed_at,
    )


def build_operator_work_queue_from_material(
    *,
    queue_id: str,
    sessions: tuple[OperatorReviewSession, ...],
    approval_receipts: tuple[ApprovalReceipt, ...] = (),
    rejection_receipts: tuple[RejectionReceipt, ...] = (),
    decision_entries: tuple[OperatorDecisionLedgerEntry, ...] = (),
    observed_at: str | None = None,
) -> OperatorWorkQueue:
    """Build a deterministic in-memory queue from validated review material."""

    if not strict_nonempty_string(queue_id):
        raise ValueError("queue_id_must_be_nonempty_string")
    observed = _observed_at(observed_at)
    _validate_material(sessions, approval_receipts, rejection_receipts, decision_entries)
    final_status = _final_status_by_session(approval_receipts, rejection_receipts, decision_entries)

    items = []
    seen_sessions: set[str] = set()
    for session in sessions:
        if session.session_id in seen_sessions:
            raise ValueError("duplicate_session_in_queue_material")
        seen_sessions.add(session.session_id)
        status = final_status.get(session.session_id)
        if status is None:
            if not session.promotion_accepted:
                status = "blocked"
            elif session.operator_action == "pending":
                status = "pending_review"
            else:
                status = session.operator_action
        item = OperatorWorkQueueItem(
            session_id=session.session_id,
            run_id=session.run_id,
            task_id=session.task_id,
            review_packet_hash=session.review_packet_hash,
            promotion_receipt_hash=session.promotion_receipt_hash,
            queue_status=status,
            content_hash="",
            observed_at=observed,
        )
        items.append(_with_item_hash(item))

    pending = sum(1 for item in items if item.queue_status == "pending_review")
    approved = sum(1 for item in items if item.queue_status == "approved")
    rejected = sum(1 for item in items if item.queue_status == "rejected")
    blocked = sum(1 for item in items if item.queue_status == "blocked")
    queue = OperatorWorkQueue(
        queue_id=queue_id,
        items=tuple(items),
        pending_review_count=pending,
        approved_count=approved,
        rejected_count=rejected,
        blocked_count=blocked,
        content_hash="",
        observed_at=observed,
    )
    return _with_queue_hash(queue)


def _validate_material(
    sessions: tuple[OperatorReviewSession, ...],
    approval_receipts: tuple[ApprovalReceipt, ...],
    rejection_receipts: tuple[RejectionReceipt, ...],
    decision_entries: tuple[OperatorDecisionLedgerEntry, ...],
) -> None:
    if not isinstance(sessions, tuple):
        raise ValueError("sessions_must_be_tuple")
    if not isinstance(approval_receipts, tuple):
        raise ValueError("approval_receipts_must_be_tuple")
    if not isinstance(rejection_receipts, tuple):
        raise ValueError("rejection_receipts_must_be_tuple")
    if not isinstance(decision_entries, tuple):
        raise ValueError("decision_entries_must_be_tuple")
    for session in sessions:
        if not validate_review_session_material(session):
            raise ValueError("invalid_review_session")
    for receipt in approval_receipts:
        if not validate_approval_receipt(receipt):
            raise ValueError("invalid_approval_receipt")
    for receipt in rejection_receipts:
        if not validate_rejection_receipt(receipt):
            raise ValueError("invalid_rejection_receipt")
    for entry in decision_entries:
        if not validate_ledger_entry(entry):
            raise ValueError("invalid_decision_entry")


def _final_status_by_session(
    approval_receipts: tuple[ApprovalReceipt, ...],
    rejection_receipts: tuple[RejectionReceipt, ...],
    decision_entries: tuple[OperatorDecisionLedgerEntry, ...],
) -> dict[str, str]:
    status: dict[str, str] = {}
    for receipt in approval_receipts:
        _set_status(status, receipt.session_id, "approved")
    for receipt in rejection_receipts:
        _set_status(status, receipt.session_id, "rejected")
    for entry in decision_entries:
        if entry.operator_action in {"approved", "rejected"}:
            _set_status(status, entry.session_id, entry.operator_action)
    return status


def _set_status(status: dict[str, str], session_id: str, value: str) -> None:
    if value not in _VALID_QUEUE_STATUSES:
        raise ValueError("invalid_queue_status")
    existing = status.get(session_id)
    if existing is not None and existing != value:
        raise ValueError("conflicting_session_status")
    status[session_id] = value


def _with_item_hash(item: OperatorWorkQueueItem) -> OperatorWorkQueueItem:
    if item.queue_status not in _VALID_QUEUE_STATUSES:
        raise ValueError("invalid_queue_status")
    if not strict_digest(item.review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(item.promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")
    return OperatorWorkQueueItem(
        session_id=item.session_id,
        run_id=item.run_id,
        task_id=item.task_id,
        review_packet_hash=item.review_packet_hash,
        promotion_receipt_hash=item.promotion_receipt_hash,
        queue_status=item.queue_status,
        policy_version=item.policy_version,
        code_version=item.code_version,
        content_hash=digest_payload(item.deterministic_material()),
        observed_at=item.observed_at,
    )


def _with_queue_hash(queue: OperatorWorkQueue) -> OperatorWorkQueue:
    return OperatorWorkQueue(
        queue_id=queue.queue_id,
        items=queue.items,
        pending_review_count=queue.pending_review_count,
        approved_count=queue.approved_count,
        rejected_count=queue.rejected_count,
        blocked_count=queue.blocked_count,
        policy_version=queue.policy_version,
        code_version=queue.code_version,
        content_hash=digest_payload(queue.deterministic_material()),
        observed_at=queue.observed_at,
    )


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
