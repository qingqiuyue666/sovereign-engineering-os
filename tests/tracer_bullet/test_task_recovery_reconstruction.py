"""
P0-2 phase 1 — durable task lifecycle recovery: read-side reconstruction.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.10 invariant binding
- v11 §23.14 AuditRecord
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests prove that `TaskRecoveryReader.reconstruct(task_id)` returns
a `TaskLifecycleSnapshot` faithful to the durable evidence written by
the orchestrator, and that the snapshot remains correct under PR #125
unexpected-rollback and expected-governance-rejection cases.

Read-only: no orchestrator behavior is mutated; no schema is touched.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.contracts.quarantine_rules import QuarantineAdmissibilityError
from kernel.lifecycle.signable_path_orchestrator import (
    IllegalStageTransitionRejected,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    TaskRecoveryClassifier,
    TaskRecoveryReader,
)
from kernel.services.validation_service import ValidationRejected
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestTaskRecoveryReconstruction(unittest.TestCase):
    """`TaskRecoveryReader.reconstruct` faithfully derives lifecycle state."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()
        self.reader = TaskRecoveryReader(
            audit_repository=self.harness.audit_repo,
            intent_anchor_repository=self.harness.intent_repo,
        )
        self.classifier = TaskRecoveryClassifier()

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # A
    # ------------------------------------------------------------------

    def test_reconstruct_returns_none_for_unknown_task(self) -> None:
        snapshot = self.reader.reconstruct("task-does-not-exist")
        self.assertIsNone(snapshot)
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.UNRECOVERABLE
        )

    # ------------------------------------------------------------------
    # B
    # ------------------------------------------------------------------

    def test_reconstruct_after_context_admission_yields_context_stage(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.CONTEXT)

        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.task_id, task_id)
        self.assertEqual(snapshot.intent_id, ids["intent_id"])
        self.assertEqual(snapshot.current_stage, Stage.CONTEXT)
        self.assertIsNone(snapshot.terminal_state)
        self.assertEqual(
            snapshot.artifact_ids[Stage.CONTEXT], ids["context_artifact_id"]
        )
        self.assertNotIn(Stage.INFERENCE, snapshot.artifact_ids)
        self.assertEqual(snapshot.malformed_event_count, 0)
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
        )

    # ------------------------------------------------------------------
    # C
    # ------------------------------------------------------------------

    def test_reconstruct_after_inference_admission_yields_inference_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.INFERENCE)

        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.current_stage, Stage.INFERENCE)
        self.assertIn(Stage.CONTEXT, snapshot.artifact_ids)
        self.assertIn(Stage.INFERENCE, snapshot.artifact_ids)
        self.assertEqual(
            snapshot.artifact_ids[Stage.CONTEXT], ids["context_artifact_id"]
        )
        self.assertEqual(
            snapshot.artifact_ids[Stage.INFERENCE], ids["inference_artifact_id"]
        )
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
        )

    # ------------------------------------------------------------------
    # D
    # ------------------------------------------------------------------

    def test_reconstruct_after_full_happy_path_yields_sealed_terminal(
        self,
    ) -> None:
        ids = self.harness.run_full_happy_path()
        snapshot = self.reader.reconstruct(ids["task_id"])
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.terminal_state, Stage.SEALED)
        self.assertEqual(snapshot.current_stage, Stage.SEALED)
        # All eight successful stage artifacts must be reconstructed.
        for stage in (
            Stage.CONTEXT,
            Stage.INFERENCE,
            Stage.PATCH_PROPOSAL,
            Stage.VALIDATION,
            Stage.REVIEW,
            Stage.APPROVAL,
            Stage.REVISION_SEAL,
            Stage.EVIDENCE,
        ):
            self.assertIn(stage, snapshot.artifact_ids)
        self.assertEqual(
            snapshot.artifact_ids[Stage.CONTEXT], ids["context_artifact_id"]
        )
        self.assertEqual(
            snapshot.artifact_ids[Stage.EVIDENCE], ids["replay_anchor_id"]
        )
        self.assertEqual(self.classifier.classify(snapshot), RecoveryClass.SEALED)

    # ------------------------------------------------------------------
    # E
    # ------------------------------------------------------------------

    def test_reconstruct_after_abandon_yields_abandoned_terminal(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.orch.abandon(task_id=task_id, reason="acceptance_test_abandon")

        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.terminal_state, Stage.ABANDONED)
        self.assertEqual(snapshot.current_stage, Stage.ABANDONED)
        # Pre-abandon artifacts remain visible in the snapshot.
        self.assertIn(Stage.CONTEXT, snapshot.artifact_ids)
        self.assertIn(Stage.INFERENCE, snapshot.artifact_ids)
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.ABANDONED
        )

    # ------------------------------------------------------------------
    # F
    # ------------------------------------------------------------------

    def test_reconstruct_after_unexpected_rollback_yields_prior_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.CONTEXT)
        token = self.harness.issue_capability("invoke_inference", task_id)

        # PR #125: RuntimeError is unexpected -> ROLLBACK; no
        # `stage_entered` for inference is committed.
        with patch.object(
            self.harness.inf_svc,
            "run_inference",
            side_effect=RuntimeError("simulated unexpected mid-call failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.harness.orch.admit_inference(
                    task_id=task_id,
                    capability_token=token,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )

        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.current_stage, Stage.CONTEXT)
        self.assertNotIn(Stage.INFERENCE, snapshot.artifact_ids)
        self.assertEqual(
            snapshot.artifact_ids[Stage.CONTEXT], ids["context_artifact_id"]
        )
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
        )

    # ------------------------------------------------------------------
    # G
    # ------------------------------------------------------------------

    def test_reconstruct_after_expected_governance_rejection_yields_prior_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)
        token = self.harness.issue_capability(
            "run_validation_quarantine", task_id
        )

        # PR #125: ValidationRejected is in EXPECTED_GOVERNANCE_REJECTIONS
        # so the validation_quarantine_admission_rejected audit commits,
        # but no `stage_entered` for VALIDATION is written.
        with patch(
            "kernel.services.validation_service.assert_proposal_admissible",
            side_effect=QuarantineAdmissibilityError("injected"),
        ):
            with self.assertRaises(ValidationRejected):
                self.harness.orch.admit_validation(
                    task_id=task_id,
                    capability_token=token,
                )

        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.current_stage, Stage.PATCH_PROPOSAL)
        self.assertNotIn(Stage.VALIDATION, snapshot.artifact_ids)
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
        )

    # ------------------------------------------------------------------
    # H
    # ------------------------------------------------------------------

    def test_reconstruct_after_illegal_stage_rejection_yields_prior_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.CONTEXT)
        bad_token = self.harness.issue_capability("propose_patch", task_id)

        with self.assertRaises(IllegalStageTransitionRejected):
            self.harness.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=bad_token,
            )

        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.current_stage, Stage.CONTEXT)
        self.assertNotIn(Stage.PATCH_PROPOSAL, snapshot.artifact_ids)
        # The illegal_stage_transition_rejected row IS in the lifecycle
        # ledger but does not advance current_stage.
        self.assertGreaterEqual(snapshot.lifecycle_record_count, 2)
        self.assertEqual(
            self.classifier.classify(snapshot), RecoveryClass.SAFE_TO_RESUME
        )


if __name__ == "__main__":
    unittest.main()
