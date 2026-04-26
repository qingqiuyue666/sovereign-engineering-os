"""
P0-3 phase 1 — controlled task rehydration: explicit in-memory restore
from a previously reconstructed `TaskLifecycleSnapshot`.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the explicit, fail-closed semantics of
`SignablePathOrchestrator.restore_task_from_snapshot`:

- Only `SAFE_TO_RESUME`, `SEALED`, `ABANDONED` are admissible recovery
  classes; `UNRECOVERABLE` and `NEEDS_MANUAL_REVIEW` are refused.
- Snapshot integrity guards (intent fields, malformed-event-count,
  intent-anchor-count) must hold.
- Restore performs zero durable writes (no audit_records, no
  intent_anchor_records, no artifact rows, no `KernelUnitOfWork`).
- After restore, `current_stage()` reflects the snapshot, and the
  orchestrator can continue admitting subsequent stages or refuse
  further admission for terminal-state restores.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any
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
    TaskRecoveryClassifier,
    TaskRecoveryReader,
)
from validation.tests.acceptance.conftest import AcceptanceHarness


def fresh_orchestrator_from_harness(
    harness: AcceptanceHarness,
) -> SignablePathOrchestrator:
    """Build a fresh `SignablePathOrchestrator` over the harness's
    services / repositories / connection.

    The fresh orchestrator's `_tasks` dict starts empty, simulating a
    process restart that retained the durable substrate but lost
    in-memory lifecycle state. Used by P0-3 rehydration tests.
    """
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


def _audit_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM audit_records;"
    ).fetchone()[0]


def _intent_anchor_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM intent_anchor_records;"
    ).fetchone()[0]


class TestControlledTaskRehydration(unittest.TestCase):
    """`restore_task_from_snapshot` semantics: P0-3 phase 1."""

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

    def test_restore_safe_to_resume_snapshot_rehydrates_current_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.SAFE_TO_RESUME)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        # Pre-restore: no in-memory state on the fresh orchestrator.
        self.assertIsNone(fresh_orch.current_stage(task_id))

        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )

        self.assertEqual(fresh_orch.current_stage(task_id), Stage.INFERENCE)

    # ------------------------------------------------------------------
    # B
    # ------------------------------------------------------------------

    def test_restored_safe_to_resume_task_can_continue_next_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        snapshot = self.reader.reconstruct(task_id)
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.SAFE_TO_RESUME)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )
        self.assertEqual(fresh_orch.current_stage(task_id), Stage.INFERENCE)

        # Next stage admission must succeed against the restored state.
        patch_token = self.harness.issue_capability("propose_patch", task_id)
        proposal_id = fresh_orch.admit_patch_proposal(
            task_id=task_id,
            capability_token=patch_token,
        )
        self.assertTrue(proposal_id)

        # Durable artifact row exists.
        pp_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM patch_proposals WHERE patch_proposal_id = ?;",
            (proposal_id,),
        ).fetchone()[0]
        self.assertEqual(pp_count, 1)

        # In-memory state advanced.
        self.assertEqual(
            fresh_orch.current_stage(task_id), Stage.PATCH_PROPOSAL
        )

    # ------------------------------------------------------------------
    # C
    # ------------------------------------------------------------------

    def test_restore_has_no_durable_side_effects(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        snapshot = self.reader.reconstruct(task_id)
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.SAFE_TO_RESUME)

        before_audit = _audit_count(self.harness)
        before_intent = _intent_anchor_count(self.harness)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )

        after_audit = _audit_count(self.harness)
        after_intent = _intent_anchor_count(self.harness)
        self.assertEqual(
            after_audit,
            before_audit,
            "restore must not append any audit_records row",
        )
        self.assertEqual(
            after_intent,
            before_intent,
            "restore must not insert any intent_anchor_records row",
        )

    # ------------------------------------------------------------------
    # D
    # ------------------------------------------------------------------

    def test_restore_rejects_needs_manual_review_snapshot(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.CONTEXT)
        # Inject duplicate intent anchor row to force NEEDS_MANUAL_REVIEW.
        self.harness.intent_repo.insert(
            intent_id=f"intent-dup-{uuid4().hex[:8]}",
            task_id=task_id,
            state="admitted",
        )
        snapshot = self.reader.reconstruct(task_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.intent_anchor_count, 2)
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.NEEDS_MANUAL_REVIEW)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        with self.assertRaises(OrchestratorRejected):
            fresh_orch.restore_task_from_snapshot(
                snapshot=snapshot, recovery_class=verdict
            )
        self.assertIsNone(fresh_orch.current_stage(task_id))

    # ------------------------------------------------------------------
    # E
    # ------------------------------------------------------------------

    def test_restore_rejects_duplicate_in_memory_task(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        snapshot = self.reader.reconstruct(task_id)
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.SAFE_TO_RESUME)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )
        self.assertEqual(fresh_orch.current_stage(task_id), Stage.INFERENCE)

        with self.assertRaises(OrchestratorRejected):
            fresh_orch.restore_task_from_snapshot(
                snapshot=snapshot, recovery_class=verdict
            )
        # Original restored stage is preserved; not overwritten.
        self.assertEqual(fresh_orch.current_stage(task_id), Stage.INFERENCE)

    # ------------------------------------------------------------------
    # F
    # ------------------------------------------------------------------

    def test_restore_sealed_terminal_snapshot_for_introspection(self) -> None:
        ids = self.harness.run_full_happy_path()
        snapshot = self.reader.reconstruct(ids["task_id"])
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.SEALED)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )
        self.assertEqual(
            fresh_orch.current_stage(ids["task_id"]), Stage.SEALED
        )

    # ------------------------------------------------------------------
    # Pin: SEALED-restored tasks must refuse any further admission.
    # ABANDONED-restored already covered above (G); SEALED needs the
    # same protection. No implementation change should be required —
    # `Stage.SEALED` is a terminal stage with no successors per
    # `kernel.lifecycle.stage_types`, so `_advance` from SEALED
    # to any next stage raises `IllegalStageTransitionRejected`
    # (subclass of `OrchestratorRejected`) and emits the durable
    # `illegal_stage_transition_rejected` audit row inside the
    # KernelUnitOfWork from PR #125.
    # ------------------------------------------------------------------

    def test_restore_sealed_terminal_snapshot_refuses_further_admission(
        self,
    ) -> None:
        ids = self.harness.run_full_happy_path()
        snapshot = self.reader.reconstruct(ids["task_id"])
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.SEALED)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )
        self.assertEqual(
            fresh_orch.current_stage(ids["task_id"]), Stage.SEALED
        )

        # Snapshot the count of stage_entered audits for this task
        # before attempting an impossible post-seal admission.
        before_stage_entered_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (ids["task_id"],),
        ).fetchone()[0]

        # Any admit_* against a SEALED task is illegal: SEALED has no
        # successors. Issue an inference capability and attempt to
        # admit it; admission must be refused fail-closed.
        bogus_token = self.harness.issue_capability(
            "invoke_inference", ids["task_id"]
        )
        with self.assertRaises(OrchestratorRejected):
            fresh_orch.admit_inference(
                task_id=ids["task_id"],
                capability_token=bogus_token,
                worker_profile="acceptance_worker",
                model_route_id="fake-model-v1",
            )

        # In-memory state must remain SEALED.
        self.assertEqual(
            fresh_orch.current_stage(ids["task_id"]), Stage.SEALED
        )

        # No new stage_entered audit row was written for the refused
        # admission. (The illegal_stage_transition_rejected row IS
        # written and durable per PR #125, but stage_entered count
        # must be unchanged.)
        after_stage_entered_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (ids["task_id"],),
        ).fetchone()[0]
        self.assertEqual(
            after_stage_entered_count,
            before_stage_entered_count,
            "refused post-seal admission must not write a stage_entered audit",
        )

    # ------------------------------------------------------------------
    # G
    # ------------------------------------------------------------------

    def test_restore_abandoned_terminal_snapshot_for_introspection(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.orch.abandon(
            task_id=task_id, reason="rehydration_test_abandon"
        )
        snapshot = self.reader.reconstruct(task_id)
        verdict = self.classifier.classify(snapshot)
        self.assertEqual(verdict, RecoveryClass.ABANDONED)

        fresh_orch = fresh_orchestrator_from_harness(self.harness)
        fresh_orch.restore_task_from_snapshot(
            snapshot=snapshot, recovery_class=verdict
        )
        self.assertEqual(fresh_orch.current_stage(task_id), Stage.ABANDONED)

        # Abandoned tasks must refuse further admission. _get_task
        # raises OrchestratorRejected when state.abandoned is True;
        # admit_inference unwraps that into the same exception class.
        bogus_token = self.harness.issue_capability("invoke_inference", task_id)
        with self.assertRaises(OrchestratorRejected):
            fresh_orch.admit_inference(
                task_id=task_id,
                capability_token=bogus_token,
                worker_profile="acceptance_worker",
                model_route_id="fake-model-v1",
            )


if __name__ == "__main__":
    unittest.main()
