"""Operator Review Session Host v1 — local manual review control plane.

The host receives a local runtime review packet hash, promotion result,
and optional rollback plan hash, then produces a deterministic audit-ready
human review session and generates approval or rejection receipts.

This is a LOCAL CONTROL PLANE only:
- No provider calls, network, subprocess, secrets, env, SQLite, or raw dumps.
- No production autonomy can be enabled.
- No real external actions can be executed.
- All outputs are deterministic.
- observed_at is excluded from all hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string
from kernel.runtime.operator_review_session import (
    OperatorReviewSession,
    build_operator_review_session,
    validate_review_session_material,
)
from kernel.runtime.operator_review_receipt import (
    ApprovalReceipt,
    build_approval_receipt,
    RejectionReceipt,
    build_rejection_receipt,
)

__all__ = [
    "ReviewSessionResult",
    "host_review_session",
    "process_operator_approval",
    "process_operator_rejection",
    "validate_review_session_result",
]

_POLICY_VERSION = "operator-review-host-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class ReviewSessionResult:
    """Deterministic result from the review session host.

    Bundles the session with optional approval or rejection receipt.
    Exactly one of approval_receipt or rejection_receipt will be populated
    when the operator has made an explicit decision; both are None when
    the session is pending.
    """

    session: OperatorReviewSession
    approval_receipt: ApprovalReceipt | None
    rejection_receipt: RejectionReceipt | None
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_receipt_hash": (
                self.approval_receipt.content_hash if self.approval_receipt is not None else None
            ),
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "rejection_receipt_hash": (
                self.rejection_receipt.content_hash if self.rejection_receipt is not None else None
            ),
            "session_content_hash": self.session.content_hash,
            "session_id": self.session.session_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def host_review_session(
    *,
    session_id: str,
    run_id: str,
    task_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    promotion_accepted: bool,
    promotion_decision: str,
    rollback_plan_hash: str | None = None,
    operator_action: str = "pending",
    decision_reason_code: str = "pending_human_review",
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> ReviewSessionResult:
    """Host a new operator review session. Fail-closed on all invalid inputs.

    If promotion_accepted is False, the session is created with
    operator_action='pending' (or 'rejected') but NEVER 'approved'.
    """

    _validate_host_inputs(
        session_id=session_id,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=promotion_receipt_hash,
        promotion_accepted=promotion_accepted,
        rollback_plan_hash=rollback_plan_hash,
        operator_action=operator_action,
    )

    observed = _observed_at(observed_at)

    # Build the session — build_operator_review_session will also enforce
    # fail-closed: no approved when promotion rejected
    session = build_operator_review_session(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=promotion_receipt_hash,
        promotion_decision=promotion_decision,
        promotion_accepted=promotion_accepted,
        rollback_plan_hash=rollback_plan_hash,
        operator_action=operator_action,
        decision_reason_code=decision_reason_code,
        observed_at=observed,
    )

    approval_receipt: ApprovalReceipt | None = None
    rejection_receipt: RejectionReceipt | None = None

    if operator_action == "approved":
        approval_receipt = build_approval_receipt(
            session_id=session_id,
            run_id=run_id,
            task_id=task_id,
            review_packet_hash=review_packet_hash,
            promotion_receipt_hash=promotion_receipt_hash,
            observed_at=observed,
        )
    elif operator_action == "rejected":
        rejection_receipt = build_rejection_receipt(
            session_id=session_id,
            run_id=run_id,
            task_id=task_id,
            review_packet_hash=review_packet_hash,
            promotion_receipt_hash=promotion_receipt_hash,
            rollback_plan_hash=rollback_plan_hash,
            observed_at=observed,
        )

    material = {
        "approval_receipt_hash": (
            approval_receipt.content_hash if approval_receipt is not None else None
        ),
        "code_version": code_version,
        "policy_version": policy_version,
        "rejection_receipt_hash": (
            rejection_receipt.content_hash if rejection_receipt is not None else None
        ),
        "session_content_hash": session.content_hash,
        "session_id": session_id,
    }
    return ReviewSessionResult(
        session=session,
        approval_receipt=approval_receipt,
        rejection_receipt=rejection_receipt,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def process_operator_approval(
    *,
    session_id: str,
    run_id: str,
    task_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    observed_at: str | None = None,
) -> ApprovalReceipt:
    """Process an explicit operator approval action.

    Returns an approval receipt that authorizes progression to the next
    manual stage only. Production autonomy and live execution are hard-disabled.
    """

    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")

    return build_approval_receipt(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=promotion_receipt_hash,
        observed_at=observed_at,
    )


def process_operator_rejection(
    *,
    session_id: str,
    run_id: str,
    task_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    rollback_plan_hash: str | None = None,
    observed_at: str | None = None,
) -> RejectionReceipt:
    """Process an explicit operator rejection action.

    Returns a rejection receipt that preserves the rollback plan hash.
    """

    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")

    return build_rejection_receipt(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=promotion_receipt_hash,
        rollback_plan_hash=rollback_plan_hash,
        observed_at=observed_at,
    )


def validate_review_session_result(result: ReviewSessionResult) -> bool:
    """Validate that the review session result is structurally sound."""

    if not isinstance(result, ReviewSessionResult):
        return False
    if not validate_review_session_material(result.session):
        return False
    if result.approval_receipt is not None:
        from kernel.runtime.operator_review_receipt import validate_approval_receipt
        if not validate_approval_receipt(result.approval_receipt):
            return False
        if result.rejection_receipt is not None:
            return False
    if result.rejection_receipt is not None:
        from kernel.runtime.operator_review_receipt import validate_rejection_receipt
        if not validate_rejection_receipt(result.rejection_receipt):
            return False
        if result.approval_receipt is not None:
            return False
    if not strict_nonempty_string(result.policy_version):
        return False
    if not strict_nonempty_string(result.code_version):
        return False
    return result.content_hash == digest_payload(result.deterministic_material())


def _validate_host_inputs(
    *,
    session_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    promotion_accepted: bool,
    rollback_plan_hash: str | None,
    operator_action: str,
) -> None:
    """Fail closed on any invalid host inputs."""

    if not strict_nonempty_string(session_id):
        raise ValueError("session_id_must_be_nonempty_string")
    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")
    if not strict_bool(promotion_accepted):
        raise ValueError("promotion_accepted_must_be_bool")
    if rollback_plan_hash is not None and not strict_digest(rollback_plan_hash):
        raise ValueError("rollback_plan_hash_must_be_valid_digest")
    if operator_action not in {"pending", "approved", "rejected"}:
        raise ValueError(f"operator_action_must_be_pending_approved_or_rejected_got_{operator_action}")
    # Fail closed: rejected promotion cannot yield approval
    if not promotion_accepted and operator_action == "approved":
        raise ValueError("operator_action_cannot_be_approved_when_promotion_rejected")


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
