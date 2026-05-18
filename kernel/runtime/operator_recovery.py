"""Read-only recovery helpers for the operator control plane."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string
from kernel.runtime.operator_decision_store import OperatorDecisionStore
from kernel.runtime.operator_review_store import OperatorReviewStore

__all__ = ["OperatorControlPlaneRecoveryReceipt", "recover_operator_control_plane"]

_POLICY_VERSION = "operator-control-plane-recovery-v1"
_CODE_VERSION = "0.1.0"
_GENESIS_HASH = "sha256:" + ("0" * 64)


@dataclass(frozen=True)
class OperatorControlPlaneRecoveryReceipt:
    """Deterministic receipt for read-only operator control-plane recovery."""

    recovery_id: str
    decision_store_verification_hash: str
    review_store_verification_hash: str | None
    reconstructed_decision_chain_head: str
    total_decision_records: int
    total_review_records: int | None
    session_action_summary: tuple[dict[str, object], ...]
    recovered: bool
    reasons: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "decision_store_verification_hash": self.decision_store_verification_hash,
            "policy_version": self.policy_version,
            "reasons": list(self.reasons),
            "reconstructed_decision_chain_head": self.reconstructed_decision_chain_head,
            "recovered": self.recovered,
            "recovery_id": self.recovery_id,
            "review_store_verification_hash": self.review_store_verification_hash,
            "session_action_summary": list(self.session_action_summary),
            "total_decision_records": self.total_decision_records,
            "total_review_records": self.total_review_records,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def recover_operator_control_plane(
    *,
    recovery_id: str,
    decision_store_path: str | Path,
    decision_store_id: str,
    review_store_path: str | Path | None = None,
    review_store_id: str | None = None,
    observed_at: str | None = None,
) -> OperatorControlPlaneRecoveryReceipt:
    """Recover operator state from durable stores without mutating them."""

    for field, value in (
        ("recovery_id", recovery_id),
        ("decision_store_id", decision_store_id),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if review_store_path is not None and not strict_nonempty_string(review_store_id):
        raise ValueError("review_store_id_must_be_nonempty_string")

    observed = _observed_at(observed_at)
    reasons: list[str] = []
    decision_store = OperatorDecisionStore(decision_store_path, store_id=decision_store_id)
    decision_verification = decision_store.verify_store(observed_at=observed)
    decision_hash = decision_verification.content_hash
    chain_head = decision_verification.decision_chain_head
    total_decision_records = decision_verification.total_records
    session_action_summary: tuple[dict[str, object], ...] = ()

    if not decision_verification.valid:
        reasons.extend(decision_verification.reasons)
        return _with_hash(
            OperatorControlPlaneRecoveryReceipt(
                recovery_id=recovery_id,
                decision_store_verification_hash=decision_hash,
                review_store_verification_hash=None,
                reconstructed_decision_chain_head=chain_head,
                total_decision_records=total_decision_records,
                total_review_records=None,
                session_action_summary=session_action_summary,
                recovered=False,
                reasons=tuple(reasons),
                content_hash="",
                observed_at=observed,
            )
        )

    try:
        ledger = decision_store.rebuild_ledger()
        snapshot = decision_store.export_snapshot()
        if snapshot.decision_chain_head != ledger.decision_chain_head:
            raise ValueError("decision_chain_head_mismatch")
        if not strict_digest(snapshot.decision_chain_head):
            raise ValueError("decision_chain_head_must_be_valid_digest")
        chain_head = ledger.decision_chain_head
        session_action_summary = tuple(
            {
                "operator_action": entry.operator_action,
                "run_id": entry.run_id,
                "sequence_number": entry.sequence_number,
                "session_id": entry.session_id,
                "task_id": entry.task_id,
            }
            for entry in ledger.entries
        )
    except ValueError as exc:
        reasons.append(str(exc))
        return _with_hash(
            OperatorControlPlaneRecoveryReceipt(
                recovery_id=recovery_id,
                decision_store_verification_hash=decision_hash,
                review_store_verification_hash=None,
                reconstructed_decision_chain_head=_GENESIS_HASH,
                total_decision_records=0,
                total_review_records=None,
                session_action_summary=(),
                recovered=False,
                reasons=tuple(reasons),
                content_hash="",
                observed_at=observed,
            )
        )

    review_hash: str | None = None
    total_review_records: int | None = None
    if review_store_path is not None:
        review_store = OperatorReviewStore(review_store_path, store_id=review_store_id or "")
        review_verification = review_store.verify_store(observed_at=observed)
        review_hash = review_verification.content_hash
        total_review_records = review_verification.total_records
        if not review_verification.valid:
            reasons.extend(review_verification.reasons)

    recovered = not reasons
    return _with_hash(
        OperatorControlPlaneRecoveryReceipt(
            recovery_id=recovery_id,
            decision_store_verification_hash=decision_hash,
            review_store_verification_hash=review_hash,
            reconstructed_decision_chain_head=chain_head,
            total_decision_records=total_decision_records,
            total_review_records=total_review_records,
            session_action_summary=session_action_summary,
            recovered=recovered,
            reasons=tuple(reasons),
            content_hash="",
            observed_at=observed,
        )
    )


def _with_hash(
    receipt: OperatorControlPlaneRecoveryReceipt,
) -> OperatorControlPlaneRecoveryReceipt:
    return OperatorControlPlaneRecoveryReceipt(
        recovery_id=receipt.recovery_id,
        decision_store_verification_hash=receipt.decision_store_verification_hash,
        review_store_verification_hash=receipt.review_store_verification_hash,
        reconstructed_decision_chain_head=receipt.reconstructed_decision_chain_head,
        total_decision_records=receipt.total_decision_records,
        total_review_records=receipt.total_review_records,
        session_action_summary=receipt.session_action_summary,
        recovered=receipt.recovered,
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
