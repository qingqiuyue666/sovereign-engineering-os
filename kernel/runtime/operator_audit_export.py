"""Deterministic read-only audit export report for operator stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string
from kernel.runtime.operator_decision_store import (
    OperatorDecisionStore,
    OperatorDecisionStoreVerificationReceipt,
)
from kernel.runtime.operator_recovery import OperatorControlPlaneRecoveryReceipt
from kernel.runtime.operator_review_store import (
    OperatorReviewStore,
    OperatorReviewStoreVerificationReceipt,
)

__all__ = ["OperatorAuditExportReport", "build_operator_audit_export_report"]

_POLICY_VERSION = "operator-audit-export-v1"
_CODE_VERSION = "0.1.0"
_FORBIDDEN_FIELD_MARKERS = (
    "raw_prompt",
    "raw_response",
    "raw_provider_response",
    "raw_exception",
    "raw_traceback",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)


@dataclass(frozen=True)
class OperatorAuditExportReport:
    """Deterministic local audit export report."""

    export_id: str
    decision_store_verification_hash: str
    review_store_verification_hash: str | None
    recovery_receipt_hash: str | None
    decision_chain_head: str
    total_decisions: int
    pending_count: int
    approved_count: int
    rejected_count: int
    session_count: int | None
    approval_count: int | None
    rejection_count: int | None
    export_sections: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_count": self.approval_count,
            "approved_count": self.approved_count,
            "code_version": self.code_version,
            "decision_chain_head": self.decision_chain_head,
            "decision_store_verification_hash": self.decision_store_verification_hash,
            "export_id": self.export_id,
            "export_sections": list(self.export_sections),
            "pending_count": self.pending_count,
            "policy_version": self.policy_version,
            "recovery_receipt_hash": self.recovery_receipt_hash,
            "rejected_count": self.rejected_count,
            "rejection_count": self.rejection_count,
            "review_store_verification_hash": self.review_store_verification_hash,
            "session_count": self.session_count,
            "total_decisions": self.total_decisions,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_audit_export_report(
    *,
    export_id: str,
    decision_store_path: str | Path,
    decision_store_id: str,
    review_store_path: str | Path | None = None,
    review_store_id: str | None = None,
    recovery_receipt: OperatorControlPlaneRecoveryReceipt | None = None,
    decision_store_verification: OperatorDecisionStoreVerificationReceipt | None = None,
    review_store_verification: OperatorReviewStoreVerificationReceipt | None = None,
    extra_export_material: dict[str, object] | None = None,
    observed_at: str | None = None,
) -> OperatorAuditExportReport:
    """Build a deterministic report from local durable stores."""

    for field, value in (
        ("export_id", export_id),
        ("decision_store_id", decision_store_id),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if review_store_path is not None and not strict_nonempty_string(review_store_id):
        raise ValueError("review_store_id_must_be_nonempty_string")
    _reject_forbidden_fields(extra_export_material or {})

    observed = _observed_at(observed_at)
    decision_store = OperatorDecisionStore(decision_store_path, store_id=decision_store_id)
    decision_verification = decision_store_verification or decision_store.verify_store(observed_at=observed)
    _validate_decision_verification(decision_verification)
    if not decision_verification.valid:
        raise ValueError("decision_store_verification_invalid")

    snapshot = decision_store.export_snapshot()
    if decision_verification.decision_chain_head != snapshot.decision_chain_head:
        raise ValueError("decision_chain_head_mismatch")
    if not strict_digest(snapshot.decision_chain_head):
        raise ValueError("decision_chain_head_missing_or_invalid")

    review_hash: str | None = None
    session_count: int | None = None
    approval_count: int | None = None
    rejection_count: int | None = None
    sections = ["decision_store_verification", "decision_ledger_snapshot"]

    if review_store_path is not None:
        review_store = OperatorReviewStore(review_store_path, store_id=review_store_id or "")
        review_verification = review_store_verification or review_store.verify_store(observed_at=observed)
        _validate_review_verification(review_verification)
        if not review_verification.valid:
            raise ValueError("review_store_verification_invalid")
        review_hash = review_verification.content_hash
        session_count = review_verification.session_count
        approval_count = review_verification.approval_count
        rejection_count = review_verification.rejection_count
        sections.append("review_store_verification")

    recovery_hash: str | None = None
    if recovery_receipt is not None:
        _validate_recovery_receipt(recovery_receipt)
        if not recovery_receipt.recovered:
            raise ValueError("recovery_receipt_invalid")
        recovery_hash = recovery_receipt.content_hash
        sections.append("recovery_receipt")

    report = OperatorAuditExportReport(
        export_id=export_id,
        decision_store_verification_hash=decision_verification.content_hash,
        review_store_verification_hash=review_hash,
        recovery_receipt_hash=recovery_hash,
        decision_chain_head=snapshot.decision_chain_head,
        total_decisions=snapshot.total_entries,
        pending_count=snapshot.pending_count,
        approved_count=snapshot.approved_count,
        rejected_count=snapshot.rejected_count,
        session_count=session_count,
        approval_count=approval_count,
        rejection_count=rejection_count,
        export_sections=tuple(sections),
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def _validate_decision_verification(receipt: OperatorDecisionStoreVerificationReceipt) -> None:
    if not isinstance(receipt, OperatorDecisionStoreVerificationReceipt):
        raise ValueError("decision_store_verification_must_be_receipt")
    if receipt.content_hash != digest_payload(receipt.deterministic_material()):
        raise ValueError("decision_store_verification_hash_mismatch")
    if not strict_digest(receipt.decision_chain_head):
        raise ValueError("decision_chain_head_missing_or_invalid")
    if not strict_digest(receipt.snapshot_hash):
        raise ValueError("snapshot_hash_missing_or_invalid")


def _validate_review_verification(receipt: OperatorReviewStoreVerificationReceipt) -> None:
    if not isinstance(receipt, OperatorReviewStoreVerificationReceipt):
        raise ValueError("review_store_verification_must_be_receipt")
    if receipt.content_hash != digest_payload(receipt.deterministic_material()):
        raise ValueError("review_store_verification_hash_mismatch")
    if not strict_digest(receipt.review_history_hash):
        raise ValueError("review_history_hash_missing_or_invalid")


def _validate_recovery_receipt(receipt: OperatorControlPlaneRecoveryReceipt) -> None:
    if not isinstance(receipt, OperatorControlPlaneRecoveryReceipt):
        raise ValueError("recovery_receipt_must_be_receipt")
    if receipt.content_hash != digest_payload(receipt.deterministic_material()):
        raise ValueError("recovery_receipt_hash_mismatch")
    if not strict_digest(receipt.reconstructed_decision_chain_head):
        raise ValueError("recovery_chain_head_missing_or_invalid")


def _with_hash(report: OperatorAuditExportReport) -> OperatorAuditExportReport:
    return OperatorAuditExportReport(
        export_id=report.export_id,
        decision_store_verification_hash=report.decision_store_verification_hash,
        review_store_verification_hash=report.review_store_verification_hash,
        recovery_receipt_hash=report.recovery_receipt_hash,
        decision_chain_head=report.decision_chain_head,
        total_decisions=report.total_decisions,
        pending_count=report.pending_count,
        approved_count=report.approved_count,
        rejected_count=report.rejected_count,
        session_count=report.session_count,
        approval_count=report.approval_count,
        rejection_count=report.rejection_count,
        export_sections=report.export_sections,
        policy_version=report.policy_version,
        code_version=report.code_version,
        content_hash=digest_payload(report.deterministic_material()),
        observed_at=report.observed_at,
    )


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError("forbidden_field_present")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)
    elif isinstance(value, tuple):
        for nested in value:
            _reject_forbidden_fields(nested)


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
