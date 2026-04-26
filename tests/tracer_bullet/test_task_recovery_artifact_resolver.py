"""
P0-4 phase 1 — recovery artifact integrity resolver.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the read-only behavior of
`StageArtifactExistenceResolver`:

- For an existing happy-path snapshot, every artifact-bearing stage
  resolves True; the classifier (with resolver wired) verdicts SEALED.
- For a synthetic snapshot whose artifact id has no durable row, the
  resolver returns False and the classifier verdicts NEEDS_MANUAL_REVIEW.
- Missing repositories (None) -> resolver returns False -> classifier
  verdicts NEEDS_MANUAL_REVIEW.
- Terminal stages (`Stage.SEALED`, `Stage.ABANDONED`) are
  non-artifact-bearing -> resolver returns False.
- A snapshot classified as NEEDS_MANUAL_REVIEW must be refused by
  `restore_task_from_snapshot`.

Read-only: no orchestrator behavior is mutated; no schema is touched;
no durable row is written by the resolver.
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

from kernel.lifecycle.signable_path_orchestrator import (
    OrchestratorRejected,
    SignablePathOrchestrator,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    StageArtifactExistenceResolver,
    TaskLifecycleSnapshot,
    TaskRecoveryClassifier,
    TaskRecoveryReader,
)
from validation.tests.acceptance.conftest import AcceptanceHarness


def fresh_orchestrator_from_harness(
    harness: AcceptanceHarness,
) -> SignablePathOrchestrator:
    return SignablePathOrchestrator(
        capability_service=harness.cap_svc,
        context_service=harness.ctx_svc,
        inference_service=harness.inf_svc,
        patch_proposal_service=harness.pp_svc,
        validation_service=harness.val_svc,
        review_service=harness.rev_svc,
        approval_service=harness.ap_svc,
        revision_seal_service=harness.seal_svc,
        evidence_service=harness.evidence_svc,
        audit_ledger=harness.audit_ledger,
        budget_governor=harness.budget_governor,
        context_repository=harness.ctx_repo,
        intent_anchor_repository=harness.intent_repo,
        connection=harness.conn,
    )


def _resolver_from_harness(
    harness: AcceptanceHarness,
    *,
    inference_repository=None,
    use_default_inference: bool = True,
) -> StageArtifactExistenceResolver:
    return StageArtifactExistenceResolver(
        context_repository=harness.ctx_repo,
        inference_repository=(
            harness.inf_repo if use_default_inference else inference_repository
        ),
        patch_proposal_repository=harness.pp_repo,
        validation_receipt_repository=harness.vr_repo,
        review_repository=harness.rv_repo,
        approval_repository=harness.ap_repo,
        revision_repository=harness.rev_repo,
        replay_anchor_repository=harness.ra_repo,
    )


def _audit_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM audit_records;"
    ).fetchone()[0]


def _intent_anchor_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM intent_anchor_records;"
    ).fetchone()[0]


class TestStageArtifactExistenceResolver(unittest.TestCase):
    """`StageArtifactExistenceResolver` read-only verdict matrix."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()
        self.reader = TaskRecoveryReader(
            audit_repository=self.harness.audit_repo,
            intent_anchor_repository=self.harness.intent_repo,
        )

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # A
    # ------------------------------------------------------------------

    def test_resolver_returns_true_for_existing_happy_path_artifacts(
        self,
    ) -> None:
        ids = self.harness.run_full_happy_path()
        snapshot = self.reader.reconstruct(ids["task_id"])
        self.assertIsNotNone(snapshot)

        resolver = _resolver_from_harness(self.harness)
        classifier = TaskRecoveryClassifier(artifact_exists=resolver)
        self.assertEqual(classifier.classify(snapshot), RecoveryClass.SEALED)

        # Every artifact-bearing stage in the snapshot resolves True.
        for stage, artifact_id in snapshot.artifact_ids.items():
            with self.subTest(stage=stage):
                self.assertTrue(
                    resolver(stage, artifact_id),
                    f"resolver({stage}, {artifact_id!r}) must return True",
                )

    # ------------------------------------------------------------------
    # B
    # ------------------------------------------------------------------

    def test_resolver_returns_false_for_missing_artifact_id(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        resolver = _resolver_from_harness(self.harness)
        self.assertFalse(
            resolver(Stage.INFERENCE, "missing-inference-artifact")
        )

        # Synthetic snapshot referencing a missing inference artifact id.
        synthetic = TaskLifecycleSnapshot(
            task_id="task-synthetic",
            intent_id="intent-synthetic",
            current_stage=Stage.INFERENCE,
            artifact_ids={
                Stage.CONTEXT: "ctx-also-missing",
                Stage.INFERENCE: "missing-inference-artifact",
            },
            terminal_state=None,
            last_event_sequence=2,
            lifecycle_record_count=2,
            malformed_event_count=0,
            intent_anchor_count=1,
            intent_created_at="2026-01-01T00:00:00+00:00",
        )
        classifier = TaskRecoveryClassifier(artifact_exists=resolver)
        self.assertEqual(
            classifier.classify(synthetic), RecoveryClass.NEEDS_MANUAL_REVIEW
        )

    # ------------------------------------------------------------------
    # C
    # ------------------------------------------------------------------

    def test_resolver_returns_false_when_stage_repository_missing(
        self,
    ) -> None:
        # Build a resolver with inference_repository = None.
        resolver = _resolver_from_harness(
            self.harness,
            inference_repository=None,
            use_default_inference=False,
        )
        self.assertFalse(resolver(Stage.INFERENCE, "any-inference-id"))

        snapshot = TaskLifecycleSnapshot(
            task_id="task-no-inf-repo",
            intent_id="intent-no-inf-repo",
            current_stage=Stage.INFERENCE,
            artifact_ids={Stage.INFERENCE: "any-inference-id"},
            terminal_state=None,
            last_event_sequence=1,
            lifecycle_record_count=1,
            malformed_event_count=0,
            intent_anchor_count=1,
            intent_created_at="2026-01-01T00:00:00+00:00",
        )
        classifier = TaskRecoveryClassifier(artifact_exists=resolver)
        self.assertEqual(
            classifier.classify(snapshot), RecoveryClass.NEEDS_MANUAL_REVIEW
        )

    # ------------------------------------------------------------------
    # D
    # ------------------------------------------------------------------

    def test_rehydration_rejects_snapshot_classified_with_dangling_artifact(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.INFERENCE)
        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)

        # Synthetic snapshot with the inference artifact id replaced
        # by a dangling reference.
        bad_artifacts = dict(snapshot.artifact_ids)
        bad_artifacts[Stage.INFERENCE] = "missing-inference-artifact"
        bad_snapshot = TaskLifecycleSnapshot(
            task_id=snapshot.task_id,
            intent_id=snapshot.intent_id,
            current_stage=snapshot.current_stage,
            artifact_ids=bad_artifacts,
            terminal_state=snapshot.terminal_state,
            last_event_sequence=snapshot.last_event_sequence,
            lifecycle_record_count=snapshot.lifecycle_record_count,
            malformed_event_count=snapshot.malformed_event_count,
            intent_anchor_count=snapshot.intent_anchor_count,
            intent_created_at=snapshot.intent_created_at,
        )

        resolver = _resolver_from_harness(self.harness)
        verdict = TaskRecoveryClassifier(artifact_exists=resolver).classify(
            bad_snapshot
        )
        self.assertEqual(verdict, RecoveryClass.NEEDS_MANUAL_REVIEW)

        before_audit = _audit_count(self.harness)
        before_intent = _intent_anchor_count(self.harness)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        with self.assertRaises(OrchestratorRejected):
            fresh_orch.restore_task_from_snapshot(
                snapshot=bad_snapshot, recovery_class=verdict
            )
        self.assertIsNone(fresh_orch.current_stage(task_id))

        # Failed restore must not have written any durable row.
        self.assertEqual(_audit_count(self.harness), before_audit)
        self.assertEqual(_intent_anchor_count(self.harness), before_intent)

    # ------------------------------------------------------------------
    # E
    # ------------------------------------------------------------------

    def test_resolver_returns_false_for_terminal_stages(self) -> None:
        resolver = _resolver_from_harness(self.harness)
        self.assertFalse(resolver(Stage.SEALED, "anything"))
        self.assertFalse(resolver(Stage.ABANDONED, "anything"))


if __name__ == "__main__":
    unittest.main()
