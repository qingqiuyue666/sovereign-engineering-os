"""
Seal Transaction Ordering contract rules (C22.1 / C22.2).

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.2 Seal Transaction Ordering Contract
- v11 §23.1 Revision, §23.2 JournalEntry, §23.3 SnapshotRoot
- v11 §24.1 AT-001 / AT-002 / AT-003 (crash at each seal ordering window)
- v11 §24.2 INV-004 (journal monotonic), INV-005 (sealed immutability)
- foundation §6 step 9 (P1 revision seal ordered transition)

This module encodes the nine-step seal ordering rule set from §22.2 as a
small state machine over named steps. It does not acquire any database
transaction; the `RevisionSealService` owns the transaction and calls
these helpers to record and enforce legal progression.

Phase-1 posture:
- The ordered steps are named constants; the service must invoke them in
  the exact order below. Any attempt to skip or reorder raises
  `SealOrderingViolation` fail-closed.
- `SealExecutionLog` records the timestamps of each step as a durable
  forensic view for the caller; the service persists the crossing of
  the durability boundary as the atomic seal point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence


class SealOrderingViolation(Exception):
    """Raised when seal steps are executed out of §22.2 order."""


class SealStep(str, Enum):
    # §22.2 exact ordering.
    PREPARE_METADATA = "prepare_seal_metadata"                  # 1
    WRITE_PENDING_PAYLOAD = "write_pending_mutation_payload"    # 2
    PERSIST_SNAPSHOT_ROOT = "persist_snapshot_root_candidate"   # 3
    JOURNAL_PREPARE_ENTRY = "append_journal_prepare_entry"      # 4
    WAL_MUTATION_AND_SEAL = "append_wal_mutation_and_seal"      # 5
    CROSS_DURABILITY = "cross_durability_boundary"              # 6
    STATE_PENDING_TO_SEALED = "transition_pending_to_sealed"    # 7
    JOURNAL_SEAL_CONFIRM = "append_seal_confirmation_entry"     # 8
    EXPOSE_AS_CURRENT = "expose_sealed_as_current_truth"        # 9


SEAL_STEP_ORDER: tuple[SealStep, ...] = (
    SealStep.PREPARE_METADATA,
    SealStep.WRITE_PENDING_PAYLOAD,
    SealStep.PERSIST_SNAPSHOT_ROOT,
    SealStep.JOURNAL_PREPARE_ENTRY,
    SealStep.WAL_MUTATION_AND_SEAL,
    SealStep.CROSS_DURABILITY,
    SealStep.STATE_PENDING_TO_SEALED,
    SealStep.JOURNAL_SEAL_CONFIRM,
    SealStep.EXPOSE_AS_CURRENT,
)


@dataclass
class SealExecutionLog:
    """Caller-owned mutable record of each step completion."""

    started: list[tuple[SealStep, str]] = field(default_factory=list)

    def record(self, step: SealStep) -> None:
        expected_index = len(self.started)
        if expected_index >= len(SEAL_STEP_ORDER):
            raise SealOrderingViolation(
                f"attempted to record step {step.value!r} past end of seal order"
            )
        expected = SEAL_STEP_ORDER[expected_index]
        if step is not expected:
            raise SealOrderingViolation(
                f"expected seal step {expected.value!r}, got {step.value!r}"
            )
        self.started.append((step, _now_iso()))

    def ensure_complete(self) -> None:
        if len(self.started) != len(SEAL_STEP_ORDER):
            missing = [
                s.value for s in SEAL_STEP_ORDER[len(self.started):]
            ]
            raise SealOrderingViolation(
                f"seal incomplete: missing steps {missing}"
            )

    def as_tuples(self) -> Sequence[tuple[str, str]]:
        return tuple((s.value, ts) for s, ts in self.started)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SealPreconditions:
    """§22.2 preconditions the caller must have satisfied before step 1."""

    intent_executable: bool
    current_root_matches_validated_root: bool
    required_receipts_valid: bool
    approval_valid_and_not_expired: bool
    barrier_checks_passed: bool

    def assert_satisfied(self) -> None:
        unmet: list[str] = []
        if not self.intent_executable:
            unmet.append("intent_executable")
        if not self.current_root_matches_validated_root:
            unmet.append("current_root_matches_validated_root")
        if not self.required_receipts_valid:
            unmet.append("required_receipts_valid")
        if not self.approval_valid_and_not_expired:
            unmet.append("approval_valid_and_not_expired")
        if not self.barrier_checks_passed:
            unmet.append("barrier_checks_passed")
        if unmet:
            raise SealOrderingViolation(
                f"seal preconditions not met: {unmet}"
            )
