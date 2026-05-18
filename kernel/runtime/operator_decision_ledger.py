"""Deterministic append-only operator decision ledger.

Records operator review session decisions (pending / approved / rejected)
in a tamper-evident in-memory append-only ledger. Every entry links to the
previous entry via content_hash, forming a verifiable decision chain.

This is a LOCAL AUDIT CONTROL PLANE only:
- No provider calls, network, subprocess, secrets, env, SQLite, or raw dumps.
- No production autonomy can be enabled.
- No real external actions can be executed.
- All outputs are deterministic.
- observed_at is excluded from all hashes.
- Append-only: entries cannot be deleted, modified, or reordered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "OperatorDecisionLedgerEntry",
    "OperatorDecisionLedger",
    "build_ledger_entry",
    "validate_ledger_entry",
    "compute_decision_chain_head",
]

_POLICY_VERSION = "operator-decision-ledger-v1"
_CODE_VERSION = "0.1.0"

_VALID_OPERATOR_ACTIONS = frozenset({"pending", "approved", "rejected"})

_GENESIS_HASH = "sha256:" + ("0" * 64)


@dataclass(frozen=True)
class OperatorDecisionLedgerEntry:
    """Immutable entry in the operator decision ledger.

    Each entry records one operator decision event. Entries are linked
    via previous_entry_hash to form a deterministic hash chain.
    observed_at is metadata only and excluded from content_hash.
    """

    entry_id: str
    session_id: str
    run_id: str
    task_id: str
    operator_action: str
    review_session_hash: str
    approval_receipt_hash: str | None
    rejection_receipt_hash: str | None
    rollback_plan_hash: str | None
    previous_entry_hash: str | None
    sequence_number: int
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_receipt_hash": self.approval_receipt_hash,
            "code_version": self.code_version,
            "entry_id": self.entry_id,
            "operator_action": self.operator_action,
            "policy_version": self.policy_version,
            "previous_entry_hash": self.previous_entry_hash,
            "rejection_receipt_hash": self.rejection_receipt_hash,
            "review_session_hash": self.review_session_hash,
            "rollback_plan_hash": self.rollback_plan_hash,
            "run_id": self.run_id,
            "sequence_number": self.sequence_number,
            "session_id": self.session_id,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_ledger_entry(
    *,
    entry_id: str,
    session_id: str,
    run_id: str,
    task_id: str,
    operator_action: str,
    review_session_hash: str,
    approval_receipt_hash: str | None = None,
    rejection_receipt_hash: str | None = None,
    rollback_plan_hash: str | None = None,
    previous_entry_hash: str | None = None,
    sequence_number: int,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> OperatorDecisionLedgerEntry:
    """Build a deterministic ledger entry.

    Raises ValueError for invalid or missing required fields.
    """

    for field, value in (
        ("entry_id", entry_id),
        ("session_id", session_id),
        ("run_id", run_id),
        ("task_id", task_id),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")

    if not strict_digest(review_session_hash):
        raise ValueError("review_session_hash_must_be_valid_digest")

    if operator_action not in _VALID_OPERATOR_ACTIONS:
        raise ValueError(f"operator_action_must_be_pending_approved_or_rejected_got_{operator_action}")

    if operator_action == "pending":
        if approval_receipt_hash is not None:
            raise ValueError("pending_entry_must_not_have_approval_receipt_hash")
        if rejection_receipt_hash is not None:
            raise ValueError("pending_entry_must_not_have_rejection_receipt_hash")

    if operator_action == "approved":
        if approval_receipt_hash is None:
            raise ValueError("approved_entry_must_have_approval_receipt_hash")
        if not strict_digest(approval_receipt_hash):
            raise ValueError("approval_receipt_hash_must_be_valid_digest")
        if rejection_receipt_hash is not None:
            raise ValueError("approved_entry_must_not_have_rejection_receipt_hash")

    if operator_action == "rejected":
        if rejection_receipt_hash is None:
            raise ValueError("rejected_entry_must_have_rejection_receipt_hash")
        if not strict_digest(rejection_receipt_hash):
            raise ValueError("rejection_receipt_hash_must_be_valid_digest")
        if approval_receipt_hash is not None:
            raise ValueError("rejected_entry_must_not_have_approval_receipt_hash")

    if rollback_plan_hash is not None and not strict_digest(rollback_plan_hash):
        raise ValueError("rollback_plan_hash_must_be_valid_digest")

    if previous_entry_hash is not None and not strict_digest(previous_entry_hash):
        raise ValueError("previous_entry_hash_must_be_valid_digest")

    if not isinstance(sequence_number, int) or sequence_number < 1:
        raise ValueError("sequence_number_must_be_positive_integer")

    if approval_receipt_hash is not None and operator_action != "approved":
        raise ValueError("approval_receipt_hash_only_allowed_on_approved_entries")
    if rejection_receipt_hash is not None and operator_action != "rejected":
        raise ValueError("rejection_receipt_hash_only_allowed_on_rejected_entries")

    observed = _observed_at(observed_at)
    material = {
        "approval_receipt_hash": approval_receipt_hash,
        "code_version": code_version,
        "entry_id": entry_id,
        "operator_action": operator_action,
        "policy_version": policy_version,
        "previous_entry_hash": previous_entry_hash,
        "rejection_receipt_hash": rejection_receipt_hash,
        "review_session_hash": review_session_hash,
        "rollback_plan_hash": rollback_plan_hash,
        "run_id": run_id,
        "sequence_number": sequence_number,
        "session_id": session_id,
        "task_id": task_id,
    }
    return OperatorDecisionLedgerEntry(
        entry_id=entry_id,
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        operator_action=operator_action,
        review_session_hash=review_session_hash,
        approval_receipt_hash=approval_receipt_hash,
        rejection_receipt_hash=rejection_receipt_hash,
        rollback_plan_hash=rollback_plan_hash,
        previous_entry_hash=previous_entry_hash,
        sequence_number=sequence_number,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_ledger_entry(entry: OperatorDecisionLedgerEntry) -> bool:
    """Validate that the ledger entry content hash matches deterministic material."""

    if not isinstance(entry, OperatorDecisionLedgerEntry):
        return False
    if not strict_nonempty_string(entry.entry_id):
        return False
    if not strict_nonempty_string(entry.session_id):
        return False
    if not strict_nonempty_string(entry.run_id):
        return False
    if not strict_nonempty_string(entry.task_id):
        return False
    if not strict_digest(entry.review_session_hash):
        return False
    if entry.operator_action not in _VALID_OPERATOR_ACTIONS:
        return False
    if not strict_nonempty_string(entry.policy_version):
        return False
    if not strict_nonempty_string(entry.code_version):
        return False
    if not isinstance(entry.sequence_number, int) or entry.sequence_number < 1:
        return False
    if entry.previous_entry_hash is not None and not strict_digest(entry.previous_entry_hash):
        return False
    if entry.approval_receipt_hash is not None and not strict_digest(entry.approval_receipt_hash):
        return False
    if entry.rejection_receipt_hash is not None and not strict_digest(entry.rejection_receipt_hash):
        return False
    if entry.rollback_plan_hash is not None and not strict_digest(entry.rollback_plan_hash):
        return False

    if entry.operator_action == "approved" and entry.approval_receipt_hash is None:
        return False
    if entry.operator_action == "rejected" and entry.rejection_receipt_hash is None:
        return False
    if entry.operator_action == "pending":
        if entry.approval_receipt_hash is not None:
            return False
        if entry.rejection_receipt_hash is not None:
            return False
    if entry.operator_action == "approved" and entry.rejection_receipt_hash is not None:
        return False
    if entry.operator_action == "rejected" and entry.approval_receipt_hash is not None:
        return False

    return entry.content_hash == digest_payload(entry.deterministic_material())


class OperatorDecisionLedger:
    """Append-only in-memory operator decision ledger.

    Entries can only be appended. Deletion, modification, and reordering
    are not supported. The ledger enforces:
    - sequence_number continuity (1-based, monotonically increasing)
    - previous_entry_hash chaining
    - duplicate session/action prevention
    - fail-closed on all invalid inputs
    """

    def __init__(self) -> None:
        self._entries: list[OperatorDecisionLedgerEntry] = []
        self._session_states: dict[str, str] = {}
        self._entry_ids: set[str] = set()

    @property
    def entries(self) -> tuple[OperatorDecisionLedgerEntry, ...]:
        return tuple(self._entries)

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    @property
    def decision_chain_head(self) -> str:
        return _compute_chain_head(self._entries)

    def append(self, entry: OperatorDecisionLedgerEntry) -> OperatorDecisionLedgerEntry:
        """Append a validated entry to the ledger.

        Raises ValueError on any constraint violation.
        Returns the entry for chaining.
        """

        if not validate_ledger_entry(entry):
            raise ValueError("ledger_entry_validation_failed")

        # Enforce append-only: entry_id must be unique
        if entry.entry_id in self._entry_ids:
            raise ValueError(f"duplicate_entry_id_{entry.entry_id}")

        # Enforce sequence_number continuity
        expected_seq = len(self._entries) + 1
        if entry.sequence_number != expected_seq:
            raise ValueError(
                f"sequence_number_mismatch_expected_{expected_seq}_got_{entry.sequence_number}"
            )

        # Enforce previous_entry_hash chaining
        if self._entries:
            expected_prev = self._entries[-1].content_hash
            if entry.previous_entry_hash != expected_prev:
                raise ValueError("previous_entry_hash_does_not_match_last_entry_content_hash")
        else:
            if entry.previous_entry_hash is not None:
                raise ValueError("first_entry_must_have_none_previous_entry_hash")

        # Enforce session state transitions
        session_id = entry.session_id
        action = entry.operator_action
        current_state = self._session_states.get(session_id)

        if current_state == "approved":
            raise ValueError(f"session_{session_id}_already_approved")
        if current_state == "rejected" and action == "approved":
            raise ValueError(f"session_{session_id}_already_rejected_cannot_approve")
        if current_state == "approved" and action == "rejected":
            raise ValueError(f"session_{session_id}_already_approved_cannot_reject")

        self._session_states[session_id] = action
        self._entry_ids.add(entry.entry_id)
        self._entries.append(entry)
        return entry

    def pending_count(self) -> int:
        return sum(1 for e in self._entries if e.operator_action == "pending")

    def approved_count(self) -> int:
        return sum(1 for e in self._entries if e.operator_action == "approved")

    def rejected_count(self) -> int:
        return sum(1 for e in self._entries if e.operator_action == "rejected")

    def entry_hashes(self) -> tuple[str, ...]:
        return tuple(e.content_hash for e in self._entries)


def compute_decision_chain_head(entries: tuple[OperatorDecisionLedgerEntry, ...]) -> str:
    """Compute the deterministic decision chain head from a sequence of entries.

    The chain head is computed by hashing the concatenation of entry content
    hashes in sequence order. This is a public convenience function that
    delegates to the internal computation.
    """
    return _compute_chain_head(list(entries))


def _compute_chain_head(entries: list[OperatorDecisionLedgerEntry]) -> str:
    """Internal: compute decision chain head from a list of entries."""
    if not entries:
        return _GENESIS_HASH
    entry_hash_list = [e.content_hash for e in entries]
    return digest_payload({"entry_hashes": entry_hash_list})


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
