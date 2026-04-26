"""
P0-5 phase 1 — recovery gate / restore coordinator.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

Composes the existing P0-2 / P0-3 / P0-4 recovery surfaces into a
single explicit runtime entry point:

  TaskRecoveryReader.reconstruct(task_id)
    -> TaskRecoveryClassifier.classify(snapshot)
       -> SignablePathOrchestrator.restore_task_from_snapshot(...)

The gate is read-side / in-memory only. It writes nothing. It does
not duplicate restore safety logic — `restore_task_from_snapshot`
remains the authority on whether a snapshot is admissible. The gate's
job is to filter unsafe recovery classes BEFORE the restore call so
the orchestrator never sees `UNRECOVERABLE` / `NEEDS_MANUAL_REVIEW`
inputs in the normal coordinator path.

Out of scope:
- Auto-restore on orchestrator construction.
- Multi-task scheduling.
- Re-running admit_* methods.
- Mutating durable rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    StageArtifactExistenceResolver,
    TaskLifecycleSnapshot,
    TaskRecoveryClassifier,
    TaskRecoveryReader,
)


_REASON_BY_CLASS: dict[RecoveryClass, str] = {
    RecoveryClass.UNRECOVERABLE: "unrecoverable",
    RecoveryClass.NEEDS_MANUAL_REVIEW: "needs_manual_review",
    RecoveryClass.SAFE_TO_RESUME: "safe_to_resume",
    RecoveryClass.SEALED: "sealed",
    RecoveryClass.ABANDONED: "abandoned",
}


_RESTORE_ALLOWED: frozenset[RecoveryClass] = frozenset(
    {
        RecoveryClass.SAFE_TO_RESUME,
        RecoveryClass.SEALED,
        RecoveryClass.ABANDONED,
    }
)


@dataclass(frozen=True)
class RecoveryGateResult:
    """Read-only verdict + outcome of a `RecoveryGate` evaluation."""

    task_id: str
    recovery_class: RecoveryClass
    snapshot: Optional[TaskLifecycleSnapshot]
    restored: bool
    reason: str


class RestorableOrchestrator(Protocol):
    """Minimal protocol the gate uses for restore.

    Avoids a hard import of `SignablePathOrchestrator` so the gate
    stays decoupled from the runtime class. Concrete callers pass
    their `SignablePathOrchestrator` instance directly.
    """

    def restore_task_from_snapshot(
        self,
        *,
        snapshot: TaskLifecycleSnapshot,
        recovery_class: RecoveryClass,
    ) -> None: ...


class RecoveryGate:
    """Explicit recovery evaluation + optional in-memory restore.

    `evaluate(task_id)` returns the read-only verdict and never calls
    the orchestrator. `restore_if_allowed(task_id, orchestrator)` is
    the only gate path that mutates the orchestrator's in-memory
    `_tasks`; the orchestrator's `restore_task_from_snapshot` retains
    final authority over the restore guards.
    """

    __slots__ = ("_reader", "_classifier")

    def __init__(
        self,
        *,
        reader: TaskRecoveryReader,
        classifier: TaskRecoveryClassifier,
    ) -> None:
        self._reader = reader
        self._classifier = classifier

    def evaluate(self, task_id: str) -> RecoveryGateResult:
        """Reconstruct + classify a task; do not restore."""
        snapshot = self._reader.reconstruct(task_id)
        recovery_class = self._classifier.classify(snapshot)
        return RecoveryGateResult(
            task_id=task_id,
            recovery_class=recovery_class,
            snapshot=snapshot,
            restored=False,
            reason=_REASON_BY_CLASS[recovery_class],
        )

    def restore_if_allowed(
        self,
        *,
        task_id: str,
        orchestrator: RestorableOrchestrator,
    ) -> RecoveryGateResult:
        """Evaluate; restore only if the recovery class is admissible.

        Allowed classes: `SAFE_TO_RESUME`, `SEALED`, `ABANDONED`.
        Refused classes (no orchestrator call): `UNRECOVERABLE`,
        `NEEDS_MANUAL_REVIEW`. The orchestrator's
        `restore_task_from_snapshot` is the final authority and may
        still raise on snapshot integrity / duplicate-task guards;
        such exceptions propagate.
        """
        verdict = self.evaluate(task_id)
        if verdict.snapshot is None:
            return verdict
        if verdict.recovery_class not in _RESTORE_ALLOWED:
            return verdict
        orchestrator.restore_task_from_snapshot(
            snapshot=verdict.snapshot,
            recovery_class=verdict.recovery_class,
        )
        return RecoveryGateResult(
            task_id=verdict.task_id,
            recovery_class=verdict.recovery_class,
            snapshot=verdict.snapshot,
            restored=True,
            reason=verdict.reason,
        )


def build_standard_recovery_gate(
    *,
    audit_repository: Any,
    intent_anchor_repository: Any,
    context_repository: Optional[Any] = None,
    inference_repository: Optional[Any] = None,
    patch_proposal_repository: Optional[Any] = None,
    validation_receipt_repository: Optional[Any] = None,
    review_repository: Optional[Any] = None,
    approval_repository: Optional[Any] = None,
    revision_repository: Optional[Any] = None,
    replay_anchor_repository: Optional[Any] = None,
) -> RecoveryGate:
    """Construct a RecoveryGate composed with the standard P0-2/P0-4
    artifact existence resolver.

    Wraps `TaskRecoveryReader` + `StageArtifactExistenceResolver` +
    `TaskRecoveryClassifier(artifact_exists=resolver)`. Stage-bearing
    repositories are individually optional; unwired stages produce a
    fail-closed `False` from the resolver and surface as
    `NEEDS_MANUAL_REVIEW` from the classifier (P0-4 semantics).
    """
    reader = TaskRecoveryReader(
        audit_repository=audit_repository,
        intent_anchor_repository=intent_anchor_repository,
    )
    resolver = StageArtifactExistenceResolver(
        context_repository=context_repository,
        inference_repository=inference_repository,
        patch_proposal_repository=patch_proposal_repository,
        validation_receipt_repository=validation_receipt_repository,
        review_repository=review_repository,
        approval_repository=approval_repository,
        revision_repository=revision_repository,
        replay_anchor_repository=replay_anchor_repository,
    )
    classifier = TaskRecoveryClassifier(artifact_exists=resolver)
    return RecoveryGate(reader=reader, classifier=classifier)
