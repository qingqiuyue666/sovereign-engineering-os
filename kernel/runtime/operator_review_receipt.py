"""Deterministic human approval and rejection receipts.

These receipts capture the operator's explicit decision in an auditable,
deterministic format. They can never enable production autonomy or live
execution — they only authorize progression to the next manual review stage.

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
    "ApprovalReceipt",
    "build_approval_receipt",
    "validate_approval_receipt",
    "RejectionReceipt",
    "build_rejection_receipt",
    "validate_rejection_receipt",
]

_POLICY_VERSION = "operator-review-receipt-v1"
_CODE_VERSION = "0.1.0"

# These flags are hard-frozen to False — no production autonomy or live
# execution can ever be enabled through an operator review receipt.
_PRODUCTION_AUTONOMY_ENABLED = False
_LIVE_EXECUTION_ENABLED = False


# ── Approval Receipt ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ApprovalReceipt:
    """Immutable receipt for an operator's explicit approval decision.

    The receipt authorizes progression to the next manual review stage ONLY.
    It does not enable production autonomy or live execution.
    """

    session_id: str
    run_id: str
    task_id: str
    review_packet_hash: str
    promotion_receipt_hash: str
    operator_action: str
    approval_scope: str
    approval_reason_code: str
    approved_for_next_stage: bool
    production_autonomy_enabled: bool = _PRODUCTION_AUTONOMY_ENABLED
    live_execution_enabled: bool = _LIVE_EXECUTION_ENABLED
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_reason_code": self.approval_reason_code,
            "approval_scope": self.approval_scope,
            "approved_for_next_stage": self.approved_for_next_stage,
            "code_version": self.code_version,
            "live_execution_enabled": self.live_execution_enabled,
            "operator_action": self.operator_action,
            "policy_version": self.policy_version,
            "production_autonomy_enabled": self.production_autonomy_enabled,
            "promotion_receipt_hash": self.promotion_receipt_hash,
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


def build_approval_receipt(
    *,
    session_id: str,
    run_id: str,
    task_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    approval_scope: str = "manual_next_stage_only",
    approval_reason_code: str = "operator_approved",
    approved_for_next_stage: bool = True,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> ApprovalReceipt:
    """Build a deterministic operator approval receipt.

    The receipt hard-freezes production_autonomy_enabled=False and
    live_execution_enabled=False. These can never be changed.
    """

    for field, value in (
        ("session_id", session_id),
        ("run_id", run_id),
        ("task_id", task_id),
        ("approval_scope", approval_scope),
        ("approval_reason_code", approval_reason_code),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")
    if not strict_bool(approved_for_next_stage):
        raise ValueError("approved_for_next_stage_must_be_bool")

    observed = _observed_at(observed_at)
    material = {
        "approval_reason_code": approval_reason_code,
        "approval_scope": approval_scope,
        "approved_for_next_stage": approved_for_next_stage,
        "code_version": code_version,
        "live_execution_enabled": _LIVE_EXECUTION_ENABLED,
        "operator_action": "approved",
        "policy_version": policy_version,
        "production_autonomy_enabled": _PRODUCTION_AUTONOMY_ENABLED,
        "promotion_receipt_hash": promotion_receipt_hash,
        "review_packet_hash": review_packet_hash,
        "run_id": run_id,
        "session_id": session_id,
        "task_id": task_id,
    }
    return ApprovalReceipt(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=promotion_receipt_hash,
        operator_action="approved",
        approval_scope=approval_scope,
        approval_reason_code=approval_reason_code,
        approved_for_next_stage=approved_for_next_stage,
        production_autonomy_enabled=_PRODUCTION_AUTONOMY_ENABLED,
        live_execution_enabled=_LIVE_EXECUTION_ENABLED,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_approval_receipt(receipt: ApprovalReceipt) -> bool:
    """Validate that the approval receipt is structurally and materially sound."""

    if not isinstance(receipt, ApprovalReceipt):
        return False
    if not strict_nonempty_string(receipt.session_id):
        return False
    if not strict_nonempty_string(receipt.run_id):
        return False
    if not strict_nonempty_string(receipt.task_id):
        return False
    if not strict_digest(receipt.review_packet_hash):
        return False
    if not strict_digest(receipt.promotion_receipt_hash):
        return False
    if receipt.operator_action != "approved":
        return False
    if not strict_nonempty_string(receipt.approval_scope):
        return False
    if not strict_nonempty_string(receipt.approval_reason_code):
        return False
    if not strict_bool(receipt.approved_for_next_stage):
        return False
    if receipt.production_autonomy_enabled is not False:
        return False
    if receipt.live_execution_enabled is not False:
        return False
    if not strict_nonempty_string(receipt.policy_version):
        return False
    if not strict_nonempty_string(receipt.code_version):
        return False
    return receipt.content_hash == digest_payload(receipt.deterministic_material())


# ── Rejection Receipt ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class RejectionReceipt:
    """Immutable receipt for an operator's explicit rejection decision.

    The receipt always references a rollback plan hash so the rejection
    can be traced back to the deterministic recovery plan.
    """

    session_id: str
    run_id: str
    task_id: str
    review_packet_hash: str
    promotion_receipt_hash: str
    operator_action: str
    rejection_reason_code: str
    rollback_plan_hash: str | None
    approved_for_next_stage: bool = False
    production_autonomy_enabled: bool = _PRODUCTION_AUTONOMY_ENABLED
    live_execution_enabled: bool = _LIVE_EXECUTION_ENABLED
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approved_for_next_stage": self.approved_for_next_stage,
            "code_version": self.code_version,
            "live_execution_enabled": self.live_execution_enabled,
            "operator_action": self.operator_action,
            "policy_version": self.policy_version,
            "production_autonomy_enabled": self.production_autonomy_enabled,
            "promotion_receipt_hash": self.promotion_receipt_hash,
            "rejection_reason_code": self.rejection_reason_code,
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


def build_rejection_receipt(
    *,
    session_id: str,
    run_id: str,
    task_id: str,
    review_packet_hash: str,
    promotion_receipt_hash: str,
    rejection_reason_code: str = "operator_rejected",
    rollback_plan_hash: str | None = None,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> RejectionReceipt:
    """Build a deterministic operator rejection receipt.

    rollback_plan_hash is preserved when provided. When None, the receipt
    still records the rejection without a rollback reference but the
    host layer should ensure a rollback plan exists on rejection.
    """

    for field, value in (
        ("session_id", session_id),
        ("run_id", run_id),
        ("task_id", task_id),
        ("rejection_reason_code", rejection_reason_code),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if not strict_digest(promotion_receipt_hash):
        raise ValueError("promotion_receipt_hash_must_be_valid_digest")
    if rollback_plan_hash is not None and not strict_digest(rollback_plan_hash):
        raise ValueError("rollback_plan_hash_must_be_valid_digest")

    observed = _observed_at(observed_at)
    material = {
        "approved_for_next_stage": False,
        "code_version": code_version,
        "live_execution_enabled": _LIVE_EXECUTION_ENABLED,
        "operator_action": "rejected",
        "policy_version": policy_version,
        "production_autonomy_enabled": _PRODUCTION_AUTONOMY_ENABLED,
        "promotion_receipt_hash": promotion_receipt_hash,
        "rejection_reason_code": rejection_reason_code,
        "review_packet_hash": review_packet_hash,
        "rollback_plan_hash": rollback_plan_hash,
        "run_id": run_id,
        "session_id": session_id,
        "task_id": task_id,
    }
    return RejectionReceipt(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=promotion_receipt_hash,
        operator_action="rejected",
        rejection_reason_code=rejection_reason_code,
        rollback_plan_hash=rollback_plan_hash,
        approved_for_next_stage=False,
        production_autonomy_enabled=_PRODUCTION_AUTONOMY_ENABLED,
        live_execution_enabled=_LIVE_EXECUTION_ENABLED,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_rejection_receipt(receipt: RejectionReceipt) -> bool:
    """Validate that the rejection receipt is structurally and materially sound."""

    if not isinstance(receipt, RejectionReceipt):
        return False
    if not strict_nonempty_string(receipt.session_id):
        return False
    if not strict_nonempty_string(receipt.run_id):
        return False
    if not strict_nonempty_string(receipt.task_id):
        return False
    if not strict_digest(receipt.review_packet_hash):
        return False
    if not strict_digest(receipt.promotion_receipt_hash):
        return False
    if receipt.operator_action != "rejected":
        return False
    if not strict_nonempty_string(receipt.rejection_reason_code):
        return False
    if receipt.approved_for_next_stage is not False:
        return False
    if receipt.production_autonomy_enabled is not False:
        return False
    if receipt.live_execution_enabled is not False:
        return False
    if not strict_nonempty_string(receipt.policy_version):
        return False
    if not strict_nonempty_string(receipt.code_version):
        return False
    if receipt.rollback_plan_hash is not None and not strict_digest(receipt.rollback_plan_hash):
        return False
    return receipt.content_hash == digest_payload(receipt.deterministic_material())


# ── Shared helpers ──────────────────────────────────────────────────────────


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
