"""
Durable task lifecycle recovery (P0-2 phase 1, read-side only).

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- v11 §23.14 AuditRecord
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

Design:

The orchestrator's `TaskLifecycleState` (in `self._tasks`) is the
authority for `current_stage` and `artifact_ids` while a process is
live. After a crash or restart that in-memory dict is empty. PR #125's
transaction boundary already guarantees that every successful stage
admission writes a durable `stage_entered` audit row inside the same
`KernelUnitOfWork` as the artifact insert and capability consume, that
unexpected runtime failure rolls back the entire admission (no row
left), and that expected-governance rejection commits the rejection
audit but leaves no `stage_entered`. Combined with `signable_path_sealed`
(terminal SEALED) and `task_abandoned` (terminal ABANDONED), the
existing `audit_records` stream plus `intent_anchor_records` is the
complete durable lifecycle authority.

This module reads those rows and reconstructs a `TaskLifecycleSnapshot`.
It writes nothing. It mutates nothing on the orchestrator. It does not
introduce a second lifecycle authority.

Out of scope for this phase:
- Mutating `SignablePathOrchestrator._tasks` from the snapshot.
- Adding any new schema, table, index, audit record_type, or migration.
- Changing `KernelUnitOfWork`, `EXPECTED_GOVERNANCE_REJECTIONS`, or any
  admit_* method.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol

from kernel.lifecycle.stage_types import Stage


class RecoveryClass(str, Enum):
    """Classifier verdict for a reconstructed task lifecycle snapshot."""

    SAFE_TO_RESUME = "safe_to_resume"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"
    UNRECOVERABLE = "unrecoverable"
    SEALED = "sealed"
    ABANDONED = "abandoned"


@dataclass(frozen=True)
class TaskLifecycleSnapshot:
    """Read-only durable snapshot of one task's lifecycle.

    Reconstructed from `intent_anchor_records` + `audit_records` rows
    of record_type 'stage_entered', 'signable_path_sealed',
    'task_abandoned', 'illegal_stage_transition_rejected'.

    `intent_anchor_count` exposes the number of durable
    `intent_anchor_records` rows that share this `task_id`. Phase-1
    invariant is exactly one. Any other value is a duplicate-identity
    anomaly that the classifier must surface as NEEDS_MANUAL_REVIEW.

    `malformed_event_count` counts lifecycle audit rows with an
    unparseable payload, an unknown stage value, or a missing /
    invalid first artifact_ref. Any non-zero value is an integrity
    anomaly that the classifier must surface as NEEDS_MANUAL_REVIEW
    (outranks terminal state).
    """

    task_id: str
    intent_id: str
    current_stage: Optional[Stage]
    artifact_ids: dict[Stage, str]
    terminal_state: Optional[Stage]
    last_event_sequence: Optional[int]
    lifecycle_record_count: int
    malformed_event_count: int = 0
    intent_anchor_count: int = 1
    intent_created_at: Optional[str] = None


class ArtifactExistenceResolver(Protocol):
    """Optional callable used by the classifier to detect dangling refs.

    A resolver returns `True` when the given (stage, artifact_id) pair
    refers to a row that exists in the corresponding artifact
    repository, and `False` otherwise. When no resolver is supplied,
    the classifier skips the dangling-reference check.
    """

    def __call__(self, stage: Stage, artifact_id: str) -> bool: ...


class TaskRecoveryReader:
    """Read-only durable lifecycle reconstructor.

    Constructor takes only the two repositories needed for read-side
    reconstruction. It deliberately does NOT take
    `SignablePathOrchestrator` or any artifact-creating service.
    """

    def __init__(
        self,
        *,
        audit_repository: Any,
        intent_anchor_repository: Any,
    ) -> None:
        self._audit_repo = audit_repository
        self._intent_repo = intent_anchor_repository

    def reconstruct(self, task_id: str) -> Optional[TaskLifecycleSnapshot]:
        """Reconstruct a `TaskLifecycleSnapshot` from durable rows.

        Returns `None` when no `intent_anchor_records` row exists for
        `task_id` (the durable proof that a task ever began).

        When more than one `intent_anchor_records` row shares the
        `task_id` (a duplicate-identity anomaly given that
        `intent_anchor_records.task_id` is not UNIQUE in migration
        0001), reconstruction continues using the earliest row's
        `intent_id` only as a diagnostic anchor and records the
        ambiguity in `intent_anchor_count`. The classifier surfaces
        this as `NEEDS_MANUAL_REVIEW` rather than silently picking one
        anchor.
        """
        intent_rows = self._intent_repo.list_for_task(task_id)
        if not intent_rows:
            return None

        # Earliest row supplies the diagnostic anchor (P0-2 behavior).
        # Duplicate-anchor anomaly is exposed via `intent_anchor_count`
        # and the classifier surfaces NEEDS_MANUAL_REVIEW; the same
        # earliest-row data is used for `intent_created_at` so P0-3
        # rehydration can reconstruct an `IntentCausalAnchor` faithful
        # to the durable row's timestamp.
        intent_id = str(intent_rows[0]["intent_id"])
        intent_anchor_count = len(intent_rows)
        intent_created_at_raw = intent_rows[0].get("created_at")
        intent_created_at: Optional[str]
        if isinstance(intent_created_at_raw, str) and intent_created_at_raw:
            intent_created_at = intent_created_at_raw
        else:
            intent_created_at = None

        rows = self._audit_repo.list_task_lifecycle_for_task(task_id)
        artifact_ids: dict[Stage, str] = {}
        current_stage: Optional[Stage] = None
        terminal_state: Optional[Stage] = None
        last_event_sequence: Optional[int] = None
        malformed_event_count: int = 0

        for row in rows:
            record_type = row.get("record_type")
            sequence = row.get("sequence")
            if isinstance(sequence, int):
                last_event_sequence = sequence

            if record_type == "stage_entered":
                stage = self._parse_stage_from_payload(row)
                if stage is None:
                    malformed_event_count += 1
                    continue
                artifact_id = self._first_artifact_ref(row)
                if artifact_id is None:
                    malformed_event_count += 1
                    continue
                artifact_ids[stage] = artifact_id
                current_stage = stage
            elif record_type == "signable_path_sealed":
                terminal_state = Stage.SEALED
                current_stage = Stage.SEALED
            elif record_type == "task_abandoned":
                terminal_state = Stage.ABANDONED
                current_stage = Stage.ABANDONED
            elif record_type == "illegal_stage_transition_rejected":
                # Rejection-only event; do not advance current_stage.
                # PR #125 commits this audit so it is durable here for
                # forensic visibility but never represents a successful
                # admission.
                continue
            else:
                # Defensive: any unexpected record_type from the
                # lifecycle filter is treated as malformed without
                # advancing state.
                malformed_event_count += 1

        return TaskLifecycleSnapshot(
            task_id=task_id,
            intent_id=intent_id,
            current_stage=current_stage,
            artifact_ids=artifact_ids,
            terminal_state=terminal_state,
            last_event_sequence=last_event_sequence,
            lifecycle_record_count=len(rows),
            malformed_event_count=malformed_event_count,
            intent_anchor_count=intent_anchor_count,
            intent_created_at=intent_created_at,
        )

    @staticmethod
    def _parse_stage_from_payload(row: dict[str, Any]) -> Optional[Stage]:
        payload_raw = row.get("payload_json")
        if payload_raw is None:
            return None
        try:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else dict(payload_raw)
        except (ValueError, TypeError):
            return None
        stage_value = payload.get("stage")
        if not isinstance(stage_value, str) or not stage_value:
            return None
        try:
            return Stage(stage_value)
        except ValueError:
            return None

    @staticmethod
    def _first_artifact_ref(row: dict[str, Any]) -> Optional[str]:
        refs_raw = row.get("artifact_refs")
        if refs_raw is None:
            return None
        try:
            refs = json.loads(refs_raw) if isinstance(refs_raw, str) else list(refs_raw)
        except (ValueError, TypeError):
            return None
        if not isinstance(refs, list) or not refs:
            return None
        first = refs[0]
        if not isinstance(first, str) or not first:
            return None
        return first


class TaskRecoveryClassifier:
    """Verdict layer over `TaskLifecycleSnapshot`.

    Constructor takes an optional `artifact_exists` callable to detect
    dangling artifact references. When omitted, the classifier returns
    SAFE_TO_RESUME for any non-terminal snapshot whose payloads parsed
    cleanly; supplying the resolver is recommended for production
    callers that need NEEDS_MANUAL_REVIEW on missing-row anomalies.
    """

    def __init__(
        self,
        *,
        artifact_exists: Optional[ArtifactExistenceResolver] = None,
    ) -> None:
        self._artifact_exists = artifact_exists

    def classify(
        self, snapshot: Optional[TaskLifecycleSnapshot]
    ) -> RecoveryClass:
        # Precedence: integrity anomalies outrank terminal state. A
        # SEALED or ABANDONED verdict on a snapshot whose intent
        # ambiguity, malformed lifecycle row, or dangling artifact
        # reference would otherwise hide a durable-evidence anomaly is
        # not safe to act on; the classifier must surface
        # NEEDS_MANUAL_REVIEW first.
        #
        # Order:
        # 1. snapshot is None                              -> UNRECOVERABLE
        # 2. duplicate / missing intent anchor count       -> NEEDS_MANUAL_REVIEW
        # 3. malformed_event_count > 0                     -> NEEDS_MANUAL_REVIEW
        # 4. resolver supplied AND any artifact dangling   -> NEEDS_MANUAL_REVIEW
        # 5. terminal_state == Stage.SEALED                -> SEALED
        # 6. terminal_state == Stage.ABANDONED             -> ABANDONED
        # 7. current_stage is None                         -> NEEDS_MANUAL_REVIEW
        # 8. otherwise                                     -> SAFE_TO_RESUME
        if snapshot is None:
            return RecoveryClass.UNRECOVERABLE
        if snapshot.intent_anchor_count != 1:
            return RecoveryClass.NEEDS_MANUAL_REVIEW
        if snapshot.malformed_event_count > 0:
            return RecoveryClass.NEEDS_MANUAL_REVIEW
        if self._artifact_exists is not None:
            for stage, artifact_id in snapshot.artifact_ids.items():
                if not self._artifact_exists(stage, artifact_id):
                    return RecoveryClass.NEEDS_MANUAL_REVIEW
        if snapshot.terminal_state is Stage.SEALED:
            return RecoveryClass.SEALED
        if snapshot.terminal_state is Stage.ABANDONED:
            return RecoveryClass.ABANDONED
        if snapshot.current_stage is None:
            return RecoveryClass.NEEDS_MANUAL_REVIEW
        return RecoveryClass.SAFE_TO_RESUME


class StageArtifactExistenceResolver:
    """Standard read-only artifact existence resolver for the eight
    artifact-bearing stages of the narrow signable path.

    Implements the callable protocol expected by
    `TaskRecoveryClassifier(artifact_exists=...)`. For each
    artifact-bearing stage in `TaskLifecycleSnapshot.artifact_ids`,
    this resolver delegates to the corresponding repository's
    `fetch(artifact_id)` and returns `True` only when the row exists.

    Out of scope:
    - Writing rows of any kind.
    - Calling services.
    - Importing `SignablePathOrchestrator`.

    Repositories may be passed as `None` for stages a caller does not
    wire (the resolver returns `False` for those stages — fail-closed,
    not silent SAFE_TO_RESUME).

    Terminal stages (`Stage.SEALED`, `Stage.ABANDONED`) are not
    artifact-bearing; resolver returns `False` for them so any
    snapshot that mistakenly indexed an "artifact id" under a
    terminal-state key is surfaced as NEEDS_MANUAL_REVIEW by the
    classifier.
    """

    __slots__ = ("_stage_repos",)

    _ARTIFACT_BEARING_STAGES: tuple[Stage, ...] = (
        Stage.CONTEXT,
        Stage.INFERENCE,
        Stage.PATCH_PROPOSAL,
        Stage.VALIDATION,
        Stage.REVIEW,
        Stage.APPROVAL,
        Stage.REVISION_SEAL,
        Stage.EVIDENCE,
    )

    def __init__(
        self,
        *,
        context_repository: Optional[Any] = None,
        inference_repository: Optional[Any] = None,
        patch_proposal_repository: Optional[Any] = None,
        validation_receipt_repository: Optional[Any] = None,
        review_repository: Optional[Any] = None,
        approval_repository: Optional[Any] = None,
        revision_repository: Optional[Any] = None,
        replay_anchor_repository: Optional[Any] = None,
    ) -> None:
        self._stage_repos: dict[Stage, Optional[Any]] = {
            Stage.CONTEXT: context_repository,
            Stage.INFERENCE: inference_repository,
            Stage.PATCH_PROPOSAL: patch_proposal_repository,
            Stage.VALIDATION: validation_receipt_repository,
            Stage.REVIEW: review_repository,
            Stage.APPROVAL: approval_repository,
            Stage.REVISION_SEAL: revision_repository,
            Stage.EVIDENCE: replay_anchor_repository,
        }

    def __call__(self, stage: Stage, artifact_id: str) -> bool:
        if not isinstance(artifact_id, str) or not artifact_id:
            return False
        if stage not in self._ARTIFACT_BEARING_STAGES:
            # Terminal stages and any unmapped stage value: not
            # artifact-bearing on the narrow signable path.
            return False
        repo = self._stage_repos.get(stage)
        if repo is None:
            return False
        row = repo.fetch(artifact_id)
        return row is not None
