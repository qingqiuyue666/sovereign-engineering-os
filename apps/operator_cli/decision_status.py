"""Read-only status helpers for durable operator decision stores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_decision_store import OperatorDecisionStore

__all__ = [
    "DecisionStoreStatus",
    "summarize_decision_store",
    "render_decision_status_text",
]

_POLICY_VERSION = "operator-decision-status-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class DecisionStoreStatus:
    store_id: str
    total_records: int
    pending_count: int
    approved_count: int
    rejected_count: int
    decision_chain_head: str
    verification_hash: str
    snapshot_hash: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approved_count": self.approved_count,
            "code_version": self.code_version,
            "decision_chain_head": self.decision_chain_head,
            "pending_count": self.pending_count,
            "policy_version": self.policy_version,
            "rejected_count": self.rejected_count,
            "snapshot_hash": self.snapshot_hash,
            "store_id": self.store_id,
            "total_records": self.total_records,
            "verification_hash": self.verification_hash,
        }


def summarize_decision_store(path: str | Path, *, store_id: str) -> DecisionStoreStatus:
    """Summarize a durable decision store without mutating it."""

    store = OperatorDecisionStore(path, store_id=store_id)
    verification = store.verify_store()
    if not verification.valid:
        raise ValueError("decision_store_invalid")
    snapshot = store.export_snapshot()
    status = DecisionStoreStatus(
        store_id=store_id,
        total_records=verification.total_records,
        pending_count=snapshot.pending_count,
        approved_count=snapshot.approved_count,
        rejected_count=snapshot.rejected_count,
        decision_chain_head=verification.decision_chain_head,
        verification_hash=verification.content_hash,
        snapshot_hash=verification.snapshot_hash,
        content_hash="",
    )
    return DecisionStoreStatus(
        store_id=status.store_id,
        total_records=status.total_records,
        pending_count=status.pending_count,
        approved_count=status.approved_count,
        rejected_count=status.rejected_count,
        decision_chain_head=status.decision_chain_head,
        verification_hash=status.verification_hash,
        snapshot_hash=status.snapshot_hash,
        policy_version=status.policy_version,
        code_version=status.code_version,
        content_hash=digest_payload(status.deterministic_material()),
    )


def render_decision_status_text(status: DecisionStoreStatus) -> str:
    """Render a concise read-only decision-store status line."""

    if not isinstance(status, DecisionStoreStatus):
        raise ValueError("status_must_be_decision_store_status")
    return (
        f"decision_store={status.store_id} records={status.total_records} "
        f"pending={status.pending_count} approved={status.approved_count} "
        f"rejected={status.rejected_count} chain_head={status.decision_chain_head}"
    )
