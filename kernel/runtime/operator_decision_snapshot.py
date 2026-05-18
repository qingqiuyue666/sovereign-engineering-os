"""Deterministic snapshot of the operator decision ledger.

Produces a tamper-evident snapshot of the ledger state at a point in time,
including entry hashes, decision chain head, and aggregate counts.
The snapshot does NOT modify the ledger and does NOT execute any actions.

This is a LOCAL AUDIT CONTROL PLANE only:
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
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string
from kernel.runtime.operator_decision_ledger import (
    OperatorDecisionLedger,
    OperatorDecisionLedgerEntry,
)

__all__ = [
    "OperatorDecisionLedgerSnapshot",
    "build_ledger_snapshot",
    "validate_ledger_snapshot",
]

_POLICY_VERSION = "operator-decision-snapshot-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class OperatorDecisionLedgerSnapshot:
    """Immutable snapshot of the operator decision ledger.

    The snapshot captures the full ledger state at a point in time.
    observed_at is metadata only and excluded from content_hash.
    """

    ledger_id: str
    entry_hashes: tuple[str, ...]
    decision_chain_head: str
    total_entries: int
    pending_count: int
    approved_count: int
    rejected_count: int
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approved_count": self.approved_count,
            "code_version": self.code_version,
            "decision_chain_head": self.decision_chain_head,
            "entry_hashes": list(self.entry_hashes),
            "ledger_id": self.ledger_id,
            "pending_count": self.pending_count,
            "policy_version": self.policy_version,
            "rejected_count": self.rejected_count,
            "total_entries": self.total_entries,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_ledger_snapshot(
    *,
    ledger_id: str,
    ledger: OperatorDecisionLedger,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> OperatorDecisionLedgerSnapshot:
    """Build a deterministic snapshot of the ledger.

    The snapshot captures the current state of the ledger without modifying it.
    Raises ValueError for invalid inputs.
    """

    for field, value in (
        ("ledger_id", ledger_id),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")

    if not isinstance(ledger, OperatorDecisionLedger):
        raise ValueError("ledger_must_be_OperatorDecisionLedger")

    observed = _observed_at(observed_at)
    entry_hashes = ledger.entry_hashes()
    decision_chain_head = ledger.decision_chain_head
    total_entries = ledger.total_entries
    pending_count = ledger.pending_count()
    approved_count = ledger.approved_count()
    rejected_count = ledger.rejected_count()

    for h in entry_hashes:
        if not strict_digest(h):
            raise ValueError("entry_hash_in_ledger_is_invalid")

    if total_entries != len(entry_hashes):
        raise ValueError("total_entries_does_not_match_entry_hashes_count")

    if total_entries != (pending_count + approved_count + rejected_count):
        raise ValueError("total_entries_does_not_match_action_counts")

    material = {
        "approved_count": approved_count,
        "code_version": code_version,
        "decision_chain_head": decision_chain_head,
        "entry_hashes": list(entry_hashes),
        "ledger_id": ledger_id,
        "pending_count": pending_count,
        "policy_version": policy_version,
        "rejected_count": rejected_count,
        "total_entries": total_entries,
    }
    return OperatorDecisionLedgerSnapshot(
        ledger_id=ledger_id,
        entry_hashes=entry_hashes,
        decision_chain_head=decision_chain_head,
        total_entries=total_entries,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_ledger_snapshot(snapshot: OperatorDecisionLedgerSnapshot) -> bool:
    """Validate that the snapshot content hash matches its deterministic material."""

    if not isinstance(snapshot, OperatorDecisionLedgerSnapshot):
        return False
    if not strict_nonempty_string(snapshot.ledger_id):
        return False
    if not isinstance(snapshot.entry_hashes, tuple):
        return False
    for h in snapshot.entry_hashes:
        if not strict_digest(h):
            return False
    if not strict_digest(snapshot.decision_chain_head):
        return False
    if not isinstance(snapshot.total_entries, int) or snapshot.total_entries < 0:
        return False
    if snapshot.total_entries != len(snapshot.entry_hashes):
        return False
    if not isinstance(snapshot.pending_count, int) or snapshot.pending_count < 0:
        return False
    if not isinstance(snapshot.approved_count, int) or snapshot.approved_count < 0:
        return False
    if not isinstance(snapshot.rejected_count, int) or snapshot.rejected_count < 0:
        return False
    if snapshot.total_entries != (snapshot.pending_count + snapshot.approved_count + snapshot.rejected_count):
        return False
    if not strict_nonempty_string(snapshot.policy_version):
        return False
    if not strict_nonempty_string(snapshot.code_version):
        return False
    return snapshot.content_hash == digest_payload(snapshot.deterministic_material())


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
