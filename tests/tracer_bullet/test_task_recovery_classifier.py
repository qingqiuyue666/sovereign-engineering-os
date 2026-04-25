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

    # ------------------------------------------------------------------
    # Anomaly-precedence checks (integrity outranks terminal state).
    # ------------------------------------------------------------------

    def test_classify_sealed_with_dangling_artifact_returns_needs_manual_review(
        self,
    ) -> None:
        """SEALED + dangling artifact must surface as NEEDS_MANUAL_REVIEW."""
        snapshot = TaskLifecycleSnapshot(
            task_id="task-sealed-dangling",
            intent_id="intent-sealed-dangling",
            current_stage=Stage.SEALED,
            artifact_ids={
                Stage.CONTEXT: "ctx-ok",
                Stage.EVIDENCE: "ev-dangling",
            },
            terminal_state=Stage.SEALED,
            last_event_sequence=99,
            lifecycle_record_count=9,
            malformed_event_count=0,
            intent_anchor_count=1,
        )

        def artifact_exists(stage: Stage, artifact_id: str) -> bool:
            return stage is not Stage.EVIDENCE

        classifier = TaskRecoveryClassifier(artifact_exists=artifact_exists)
        self.assertEqual(
            classifier.classify(snapshot), RecoveryClass.NEEDS_MANUAL_REVIEW
        )

    def test_classify_sealed_with_malformed_event_returns_needs_manual_review(
        self,
    ) -> None:
        """SEALED + malformed_event_count > 0 must surface as NEEDS_MANUAL_REVIEW."""
        snapshot = TaskLifecycleSnapshot(
            task_id="task-sealed-malformed",
            intent_id="intent-sealed-malformed",
            current_stage=Stage.SEALED,
            artifact_ids={Stage.CONTEXT: "ctx-ok"},
            terminal_state=Stage.SEALED,
            last_event_sequence=10,
            lifecycle_record_count=10,
            malformed_event_count=1,
            intent_anchor_count=1,
        )
        classifier = TaskRecoveryClassifier()
        self.assertEqual(
            classifier.classify(snapshot), RecoveryClass.NEEDS_MANUAL_REVIEW
        )

    def test_classify_abandoned_with_dangling_artifact_returns_needs_manual_review(
        self,
    ) -> None:
        """ABANDONED + dangling artifact must surface as NEEDS_MANUAL_REVIEW."""
        snapshot = TaskLifecycleSnapshot(
            task_id="task-abandoned-dangling",
            intent_id="intent-abandoned-dangling",
            current_stage=Stage.ABANDONED,
            artifact_ids={
                Stage.CONTEXT: "ctx-ok",
                Stage.INFERENCE: "inf-dangling",
            },
            terminal_state=Stage.ABANDONED,
            last_event_sequence=5,
            lifecycle_record_count=3,
            malformed_event_count=0,
            intent_anchor_count=1,
        )

        def artifact_exists(stage: Stage, artifact_id: str) -> bool:
            return stage is not Stage.INFERENCE

        classifier = TaskRecoveryClassifier(artifact_exists=artifact_exists)
        self.assertEqual(
            classifier.classify(snapshot), RecoveryClass.NEEDS_MANUAL_REVIEW
        )

    # ------------------------------------------------------------------
    # Duplicate intent anchor anomaly (Fix 2).
    # ------------------------------------------------------------------

    def test_duplicate_intent_anchors_classify_as_needs_manual_review(
        self,
    ) -> None:
        """Two intent_anchor_records rows with same task_id must surface anomaly."""
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            harness.run_through_stage(task_id, Stage.CONTEXT)
            # Inject a second durable intent_anchor_records row for the
            # same task_id with a distinct intent_id. This is a
            # synthetic representation of a duplicate-identity anomaly
            # (intent_anchor_records.task_id is not UNIQUE).
            harness.intent_repo.insert(
                intent_id=f"intent-dup-{uuid4().hex[:8]}",
                task_id=task_id,
                state="admitted",
            )

            reader = TaskRecoveryReader(
                audit_repository=harness.audit_repo,
                intent_anchor_repository=harness.intent_repo,
            )
            snapshot = reader.reconstruct(task_id)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.intent_anchor_count, 2)

            classifier = TaskRecoveryClassifier()
            self.assertEqual(
                classifier.classify(snapshot),
                RecoveryClass.NEEDS_MANUAL_REVIEW,
            )
        finally:
            harness.close()

    def test_duplicate_intent_anchors_do_not_classify_as_safe_or_terminal(
        self,
    ) -> None:
        """Duplicates outrank SAFE_TO_RESUME, SEALED, ABANDONED verdicts."""
        # SAFE_TO_RESUME shape with duplicate intent anchors.
        non_terminal_dup = TaskLifecycleSnapshot(
            task_id="task-dup-non-terminal",
            intent_id="intent-dup-1",
            current_stage=Stage.CONTEXT,
            artifact_ids={Stage.CONTEXT: "ctx-1"},
            terminal_state=None,
            last_event_sequence=1,
            lifecycle_record_count=1,
            malformed_event_count=0,
            intent_anchor_count=2,
        )

        # SEALED shape with duplicate intent anchors.
        sealed_dup = TaskLifecycleSnapshot(
            task_id="task-dup-sealed",
            intent_id="intent-dup-1",
            current_stage=Stage.SEALED,
            artifact_ids={
                Stage.CONTEXT: "ctx-1",
                Stage.EVIDENCE: "ev-1",
            },
            terminal_state=Stage.SEALED,
            last_event_sequence=99,
            lifecycle_record_count=9,
            malformed_event_count=0,
            intent_anchor_count=3,
        )

        # ABANDONED shape with duplicate intent anchors.
        abandoned_dup = TaskLifecycleSnapshot(
            task_id="task-dup-abandoned",
            intent_id="intent-dup-1",
            current_stage=Stage.ABANDONED,
            artifact_ids={Stage.CONTEXT: "ctx-1"},
            terminal_state=Stage.ABANDONED,
            last_event_sequence=5,
            lifecycle_record_count=3,
            malformed_event_count=0,
            intent_anchor_count=4,
        )

        classifier = TaskRecoveryClassifier()
        for snapshot in (non_terminal_dup, sealed_dup, abandoned_dup):
            verdict = classifier.classify(snapshot)
            self.assertEqual(
                verdict,
                RecoveryClass.NEEDS_MANUAL_REVIEW,
                f"intent_anchor_count={snapshot.intent_anchor_count} "
                f"current_stage={snapshot.current_stage} "
                f"terminal_state={snapshot.terminal_state} "
                f"-> expected NEEDS_MANUAL_REVIEW, got {verdict}",
            )
            self.assertNotIn(
                verdict,
                (
                    RecoveryClass.SAFE_TO_RESUME,
                    RecoveryClass.SEALED,
                    RecoveryClass.ABANDONED,
                ),
            )

    def test_unknown_task_still_returns_none_and_unrecoverable_after_fix(
        self,
    ) -> None:
        """Fix 2 must not regress the unknown-task path."""
        harness = AcceptanceHarness()
        try:
            reader = TaskRecoveryReader(
                audit_repository=harness.audit_repo,
                intent_anchor_repository=harness.intent_repo,
            )
            snapshot = reader.reconstruct("task-never-existed")
            self.assertIsNone(snapshot)
            classifier = TaskRecoveryClassifier()
            self.assertEqual(
                classifier.classify(snapshot), RecoveryClass.UNRECOVERABLE
            )
        finally:
            harness.close()


if __name__ == "__main__":
    unittest.main()
