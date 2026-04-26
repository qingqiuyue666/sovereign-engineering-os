"""
P0-5 phase 1 — recovery gate / restore coordinator.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the explicit semantics of `RecoveryGate`:

- `evaluate(task_id)` is read-only; it never mutates the orchestrator
  and never writes a durable row.
- `restore_if_allowed(task_id, orchestrator)` only invokes
  `restore_task_from_snapshot` for `SAFE_TO_RESUME` / `SEALED` /
  `ABANDONED` snapshots; `UNRECOVERABLE` / `NEEDS_MANUAL_REVIEW`
  produce `restored=False` without touching the orchestrator.
- The orchestrator's `restore_task_from_snapshot` retains final
  authority on snapshot integrity guards.
- The standard composition built by `build_standard_recovery_gate`
  uses `StageArtifactExistenceResolver` so dangling artifact
  references surface as `NEEDS_MANUAL_REVIEW` and the gate refuses to
  restore.
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

from kernel.lifecycle.recovery_gate import (
    RecoveryGate,
    RecoveryGateResult,
    build_standard_recovery_gate,
)
from kernel.lifecycle.signable_path_orchestrator import (
    OrchestratorRejected,
    SignablePathOrchestrator,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import RecoveryClass
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


def _gate_from_harness(harness: AcceptanceHarness, **overrides) -> RecoveryGate:
    """Build a standard recovery gate from harness repositories.

    `overrides` may pass `inference_repository=None` (or any other
    stage repository) to simulate an unwired-stage anomaly.
    """
    kwargs = dict(
        audit_repository=harness.audit_repo,
        intent_anchor_repository=harness.intent_repo,
        context_repository=harness.ctx_repo,
        inference_repository=harness.inf_repo,
        patch_proposal_repository=harness.pp_repo,
        validation_receipt_repository=harness.vr_repo,
        review_repository=harness.rv_repo,
        approval_repository=harness.ap_repo,
        revision_repository=harness.rev_repo,
        replay_anchor_repository=harness.ra_repo,
    )
    kwargs.update(overrides)
    return build_standard_recovery_gate(**kwargs)


def _audit_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM audit_records;"
    ).fetchone()[0]


def _intent_anchor_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM intent_anchor_records;"
    ).fetchone()[0]


class TestRecoveryGateRestoreCoordinator(unittest.TestCase):
    """`RecoveryGate.evaluate` and `restore_if_allowed` semantics."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()
        self.gate = _gate_from_harness(self.harness)

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # A
    # ------------------------------------------------------------------

    def test_evaluate_unknown_task_returns_unrecoverable_without_restore(
        self,
    ) -> None:
        result = self.gate.evaluate("task-never-existed")
        self.assertIsInstance(result, RecoveryGateResult)
        self.assertEqual(result.recovery_class, RecoveryClass.UNRECOVERABLE)
        self.assertIsNone(result.snapshot)
        self.assertFalse(result.restored)
        self.assertEqual(result.reason, "unrecoverable")

    # ------------------------------------------------------------------
    # B
    # ------------------------------------------------------------------

    def test_evaluate_safe_to_resume_without_restore_does_not_mutate_orchestrator(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        result = self.gate.evaluate(task_id)
        self.assertEqual(result.recovery_class, RecoveryClass.SAFE_TO_RESUME)
        self.assertFalse(result.restored)
        self.assertIsNone(fresh_orch.current_stage(task_id))

    # ------------------------------------------------------------------
    # C
    # ------------------------------------------------------------------

    def test_restore_if_allowed_restores_safe_to_resume_task(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        result = self.gate.restore_if_allowed(
            task_id=task_id, orchestrator=fresh_orch
        )
        self.assertEqual(result.recovery_class, RecoveryClass.SAFE_TO_RESUME)
        self.assertTrue(result.restored)
        self.assertEqual(fresh_orch.current_stage(task_id), Stage.INFERENCE)

    # ------------------------------------------------------------------
    # D
    # ------------------------------------------------------------------

    def test_restore_if_allowed_restored_task_can_continue_next_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        result = self.gate.restore_if_allowed(
            task_id=task_id, orchestrator=fresh_orch
        )
        self.assertTrue(result.restored)

        patch_token = self.harness.issue_capability("propose_patch", task_id)
        proposal_id = fresh_orch.admit_patch_proposal(
            task_id=task_id,
            capability_token=patch_token,
        )
        self.assertTrue(proposal_id)
        self.assertEqual(
            fresh_orch.current_stage(task_id), Stage.PATCH_PROPOSAL
        )

    # ------------------------------------------------------------------
    # E
    # ------------------------------------------------------------------

    def test_restore_if_allowed_refuses_needs_manual_review(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        # Inject a duplicate intent anchor row to force NEEDS_MANUAL_REVIEW.
        self.harness.intent_repo.insert(
            intent_id=f"intent-dup-{uuid4().hex[:8]}",
            task_id=task_id,
            state="admitted",
        )

        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        before_audit = _audit_count(self.harness)
        before_intent = _intent_anchor_count(self.harness)

        result = self.gate.restore_if_allowed(
            task_id=task_id, orchestrator=fresh_orch
        )
        self.assertEqual(
            result.recovery_class, RecoveryClass.NEEDS_MANUAL_REVIEW
        )
        self.assertFalse(result.restored)
        self.assertIsNone(fresh_orch.current_stage(task_id))

        # Gate must not write any durable row.
        self.assertEqual(_audit_count(self.harness), before_audit)
        self.assertEqual(_intent_anchor_count(self.harness), before_intent)

    # ------------------------------------------------------------------
    # F
    # ------------------------------------------------------------------

    def test_restore_if_allowed_restores_sealed_for_introspection(
        self,
    ) -> None:
        ids = self.harness.run_full_happy_path()
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        result = self.gate.restore_if_allowed(
            task_id=ids["task_id"], orchestrator=fresh_orch
        )
        self.assertEqual(result.recovery_class, RecoveryClass.SEALED)
        self.assertTrue(result.restored)
        self.assertEqual(
            fresh_orch.current_stage(ids["task_id"]), Stage.SEALED
        )

    # ------------------------------------------------------------------
    # G
    # ------------------------------------------------------------------

    def test_restore_if_allowed_restores_abandoned_for_introspection(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.orch.abandon(
            task_id=task_id, reason="recovery_gate_test_abandon"
        )
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        result = self.gate.restore_if_allowed(
            task_id=task_id, orchestrator=fresh_orch
        )
        self.assertEqual(result.recovery_class, RecoveryClass.ABANDONED)
        self.assertTrue(result.restored)
        self.assertEqual(fresh_orch.current_stage(task_id), Stage.ABANDONED)

        # Further admission against ABANDONED must be refused.
        bogus_token = self.harness.issue_capability("invoke_inference", task_id)
        with self.assertRaises(OrchestratorRejected):
            fresh_orch.admit_inference(
                task_id=task_id,
                capability_token=bogus_token,
                worker_profile="acceptance_worker",
                model_route_id="fake-model-v1",
            )

    # ------------------------------------------------------------------
    # H
    # ------------------------------------------------------------------

    def test_restore_gate_has_no_durable_side_effects(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        before_audit = _audit_count(self.harness)
        before_intent = _intent_anchor_count(self.harness)

        result = self.gate.restore_if_allowed(
            task_id=task_id, orchestrator=fresh_orch
        )
        self.assertTrue(result.restored)

        self.assertEqual(_audit_count(self.harness), before_audit)
        self.assertEqual(_intent_anchor_count(self.harness), before_intent)

    # ------------------------------------------------------------------
    # I
    # ------------------------------------------------------------------

    def test_build_standard_recovery_gate_uses_artifact_resolver(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        # Build a gate with inference_repository=None so the resolver
        # must classify any inference artifact id as missing.
        unwired_gate = _gate_from_harness(
            self.harness, inference_repository=None
        )
        fresh_orch = fresh_orchestrator_from_harness(self.harness)

        verdict = unwired_gate.evaluate(task_id)
        self.assertEqual(
            verdict.recovery_class, RecoveryClass.NEEDS_MANUAL_REVIEW
        )
        self.assertFalse(verdict.restored)

        result = unwired_gate.restore_if_allowed(
            task_id=task_id, orchestrator=fresh_orch
        )
        self.assertEqual(
            result.recovery_class, RecoveryClass.NEEDS_MANUAL_REVIEW
        )
        self.assertFalse(result.restored)
        self.assertIsNone(fresh_orch.current_stage(task_id))


if __name__ == "__main__":
    unittest.main()
