"""
P0-2 phase 1 — durable task lifecycle recovery: classifier verdicts.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

Tests pin the verdict semantics of `TaskRecoveryClassifier.classify`:
- None snapshot -> UNRECOVERABLE
- terminal SEALED  -> SEALED
- terminal ABANDONED -> ABANDONED
- non-terminal valid snapshot -> SAFE_TO_RESUME
- dangling artifact ref under an artifact_exists resolver -> NEEDS_MANUAL_REVIEW

Read-only: no orchestrator behavior is mutated; no schema is touched.
"""

from __future__ import annotations

import os
import sys
import unittest
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    TaskLifecycleSnapshot,
    TaskRecoveryClassifier,
    TaskRecoveryReader,
)
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestTaskRecoveryClassifier(unittest.TestCase):
    """`TaskRecoveryClassifier.classify` verdict matrix."""

    # ------------------------------------------------------------------
    # A
    # ------------------------------------------------------------------

    def test_classify_unknown_task_returns_unrecoverable(self) -> None:
        classifier = TaskRecoveryClassifier()
        self.assertEqual(
            classifier.classify(None), RecoveryClass.UNRECOVERABLE
        )

    # ------------------------------------------------------------------
    # B
    # ------------------------------------------------------------------

    def test_classify_after_context_returns_safe_to_resume(self) -> None:
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            harness.run_through_stage(task_id, Stage.CONTEXT)
            reader = TaskRecoveryReader(
                audit_repository=harness.audit_repo,
                intent_anchor_repository=harness.intent_repo,
            )
            snapshot = reader.reconstruct(task_id)
            classifier = TaskRecoveryClassifier()
            self.assertEqual(
                classifier.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
            )
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # C
    # ------------------------------------------------------------------

    def test_classify_after_seal_returns_sealed(self) -> None:
        harness = AcceptanceHarness()
        try:
            ids = harness.run_full_happy_path()
            reader = TaskRecoveryReader(
                audit_repository=harness.audit_repo,
                intent_anchor_repository=harness.intent_repo,
            )
            snapshot = reader.reconstruct(ids["task_id"])
            classifier = TaskRecoveryClassifier()
            self.assertEqual(
                classifier.classify(snapshot), RecoveryClass.SEALED
            )
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # D
    # ------------------------------------------------------------------

    def test_classify_after_abandon_returns_abandoned(self) -> None:
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            harness.run_through_stage(task_id, Stage.INFERENCE)
            harness.orch.abandon(
                task_id=task_id, reason="classifier_test_abandon"
            )
            reader = TaskRecoveryReader(
                audit_repository=harness.audit_repo,
                intent_anchor_repository=harness.intent_repo,
            )
            snapshot = reader.reconstruct(task_id)
            classifier = TaskRecoveryClassifier()
            self.assertEqual(
                classifier.classify(snapshot), RecoveryClass.ABANDONED
            )
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # E
    # ------------------------------------------------------------------

    def test_classify_with_dangling_artifact_id_returns_needs_manual_review(
        self,
    ) -> None:
        # Manually constructed snapshot with a dangling artifact ref.
        snapshot = TaskLifecycleSnapshot(
            task_id="task-synthetic",
            intent_id="intent-synthetic",
            current_stage=Stage.INFERENCE,
            artifact_ids={
                Stage.CONTEXT: "ctx-real",
                Stage.INFERENCE: "inf-dangling",
            },
            terminal_state=None,
            last_event_sequence=2,
            lifecycle_record_count=2,
            malformed_event_count=0,
        )

        def artifact_exists(stage: Stage, artifact_id: str) -> bool:
            # Treat the inference artifact as missing from its repo.
            if stage is Stage.INFERENCE:
                return False
            return True

        classifier = TaskRecoveryClassifier(artifact_exists=artifact_exists)
        self.assertEqual(
            classifier.classify(snapshot), RecoveryClass.NEEDS_MANUAL_REVIEW
        )

        # Same snapshot with a resolver that finds everything: SAFE_TO_RESUME.
        permissive = TaskRecoveryClassifier(
            artifact_exists=lambda _stage, _aid: True
        )
        self.assertEqual(
            permissive.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
        )


if __name__ == "__main__":
    unittest.main()
