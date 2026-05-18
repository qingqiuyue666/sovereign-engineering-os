"""Deterministic operator review session contract for manual human review.

An OperatorReviewSession binds a local runtime review packet, promotion
gate result, and optional rollback plan into a single auditable human
decision loop.

No provider calls, network access, secrets, env reads, subprocess,
SQLite mutations, or execution happen here.

Observation timestamps are metadata only and are excluded from content hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "OperatorReviewSession",
    "build_operator_review_session",
    "validate_review_session_material",
]

_POLICY_VERSION = "operator-review-session-v1"
_CODE_VERSION = "0.1.0"

_VALID_OPERATOR_ACTIONS = frozenset({"pending", "approved", "rejected"})


@dataclass(frozen=True)
class OperatorReviewSession:
    """Immutable operator review session binding review packet + promotion gate.

    The session captures the full context the human operator needs to make
    an approval or rejection decision. observation timestamps are metadata
    and excluded from content_hash.
    """

    session_id: str
    run_id: str
    task_id: str
    review_packet_hash: str
    promotion_receipt_hash: str
    promotion_decision: str
    promotion_accepted: bool
    rollback_plan_hash: str | None
    operator_action: str
    decision_reason_code: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "decision_reason_code": self.decision_reason_code,
            "operator_action": self.operator_action,
            "policy_version": self.policy_version,
            "promotion_accepted": self.promotion_accepted,
            "promotion_decision": self.promotion_decision,
            "promotion_receipt_hash": self.promotion_receipt_hash,
            "review_packet_hash": self.review_packet_hash,
            "rollback_plan_hash": self.rollback_plan_hash,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_review_session(
    *,
    session_id: str,
    run_id: str,
    task_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    promotion_decision: str,
    promotion_accepted: bool,
    rollback_plan_hash: str | None = None,
    operator_action: str = "pending",
    decision_reason_code: str = "pending_human_review",
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> OperatorReviewSession:
    """Build a deterministic operator review session.

    Raises ValueError for invalid or missing required fields.
    """

    for field, value in (
        ("session_id", session_id),
        ("run_id", run_id),
        ("task_id", task_id),
        ("policy_version", policy_version),
        ("code_version", code_version),
        ("promotion_decision", promotion_decision),
        ("decision_reason_code", decision_reason_code),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")
    if not strict_bool(promotion_accepted):
        raise ValueError("promotion_accepted_must_be_bool")
    if operator_action not in _VALID_OPERATOR_ACTIONS:
        raise ValueError(f"operator_action_must_be_pending_approved_or_rejected_got_{operator_action}")
    if rollback_plan_hash is not None and not strict_digest(rollback_plan_hash):
        raise ValueError("rollback_plan_hash_must_be_valid_digest")

    # Fail closed: if promotion gate rejected, operator_action cannot be approved
    if not promotion_accepted and operator_action == "approved":
        raise ValueError("operator_action_cannot_be_approved_when_promotion_rejected")

    observed = _observed_at(observed_at)
    material = {
        "code_version": code_version,
        "decision_reason_code": decision_reason_code,
        "operator_action": operator_action,
        "policy_version": policy_version,
        "promotion_accepted": promotion_accepted,
        "promotion_decision": promotion_decision,
        "promotion_receipt_hash": promotion_receipt_hash,
        "review_packet_hash": review_packet_hash,
        "rollback_plan_hash": rollback_plan_hash,
        "run_id": run_id,
        "session_id": session_id,
        "task_id": task_id,
    }
    return OperatorReviewSession(
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
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_review_session_material(session: OperatorReviewSession) -> bool:
    """Validate that the session content hash matches deterministic material."""

    if not isinstance(session, OperatorReviewSession):
        return False
    if not strict_nonempty_string(session.session_id):
        return False
    if not strict_nonempty_string(session.run_id):
        return False
    if not strict_nonempty_string(session.task_id):
        return False
    if not strict_digest(session.review_packet_hash):
        return False
    if not strict_digest(session.promotion_receipt_hash):
        return False
    if not strict_nonempty_string(session.promotion_decision):
        return False
    if not strict_bool(session.promotion_accepted):
        return False
    if session.operator_action not in _VALID_OPERATOR_ACTIONS:
        return False
    if not strict_nonempty_string(session.decision_reason_code):
        return False
    if not strict_nonempty_string(session.policy_version):
        return False
    if not strict_nonempty_string(session.code_version):
        return False
    if session.rollback_plan_hash is not None and not strict_digest(session.rollback_plan_hash):
        return False
    if not session.promotion_accepted and session.operator_action == "approved":
        return False
    return session.content_hash == digest_payload(session.deterministic_material())


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
