"""
P0 transaction-boundary hardening (phase 1): expected-governance-rejection
audit evidence must survive the admission boundary.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.6 Capability Token Lifecycle Contract
- v11 §22.3 Atomic Approval Barrier Contract
- v11 §24.1 AT-015 (forensic reconstructability)
- v11 §24.2 INV-026 (audit append-only)
- foundation §6 (P0 sealing + crash-window proofs)

`KernelUnitOfWork` commits the transaction on the orchestrator's
declared expected governance rejection types (`OrchestratorRejected`,
`CapabilityDenied`, `ValidationRejected`, `ReviewRejected`,
`ApprovalBarrierFailed`, `ApprovalRejected`, `InferenceBudgetExhausted`)
so emit-rejection-audit-then-raise patterns inside the wrapped admit_*
body keep their durable rejection evidence visible to AT-015. Truly
unexpected exceptions still trigger ROLLBACK and are exercised by
`test_kernel_unit_of_work_capability_rollback.py`.
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
from kernel.lifecycle.signable_path_orchestrator import OrchestratorRejected
from kernel.lifecycle.stage_types import Stage
from kernel.services.capability_service import CapabilityDenied
from kernel.services.inference_service import (
    InferencePolicy,
    InferenceService,
)
from kernel.services.validation_service import ValidationRejected
from validation.tests.acceptance.conftest import AcceptanceHarness


class _CountingAdapter:
    """Minimal model adapter that counts invocations (mirrors AT-027)."""

    def __init__(self, output_tokens: int = 20) -> None:
        self.calls: int = 0
        self._output_tokens = output_tokens

    def invoke(self, *, prompt_envelope, policy):
        self.calls += 1
        return {
            "output_text": "x" * self._output_tokens,
            "token_usage": {"input": 10, "output": self._output_tokens},
            "latency_ms": 1,
            "model_route_id": "fake-model-v1",
        }


class TestRejectionEvidenceSurvives(unittest.TestCase):
    """Each expected governance rejection's audit must be durable post-failure."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # 1. Illegal stage transition
    # ------------------------------------------------------------------

    def test_illegal_stage_transition_rejection_audit_survives(self) -> None:
        """`illegal_stage_transition_rejected` audit must persist after refusal."""
        task_id = f"task-{uuid4().hex[:8]}"
        # Drive only through CONTEXT; admit_patch_proposal from CONTEXT is illegal.
        self.harness.run_through_stage(task_id, Stage.CONTEXT)
        bad_token = self.harness.issue_capability("propose_patch", task_id)

        with self.assertRaises(OrchestratorRejected):
            self.harness.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=bad_token,
            )

        # in-memory current_stage stays at CONTEXT.
        self.assertEqual(
            self.harness.orch.current_stage(task_id), Stage.CONTEXT
        )

        # Rejection audit is durable.
        rejected_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'illegal_stage_transition_rejected';",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(rejected_count, 1)

        # No successful patch_proposal stage_entered audit was written.
        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertFalse(
            any(
                '"stage":"patch_proposal"' in row["payload_json"]
                for row in stage_rows
            )
        )

    # ------------------------------------------------------------------
    # 2. Capability consume rejection
    # ------------------------------------------------------------------

    def test_capability_consume_rejection_audit_survives(self) -> None:
        """`capability_token_consume_rejected` audit must persist after refusal."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.CONTEXT)
        token = self.harness.issue_capability("invoke_inference", task_id)
        token_id = token["capability_token_id"]
        # Pre-consume the token so the orchestrator's cap_svc.consume must fail.
        self.harness.cap_repo.atomic_consume(token_id)

        with self.assertRaises(CapabilityDenied):
            self.harness.orch.admit_inference(
                task_id=task_id,
                capability_token=token,
                worker_profile="acceptance_worker",
                model_route_id="fake-model-v1",
            )

        self.assertEqual(
            self.harness.orch.current_stage(task_id), Stage.CONTEXT
        )

        rejected_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'capability_token_consume_rejected' "
            "AND artifact_refs LIKE ?;",
            (task_id, f"%{token_id}%"),
        ).fetchone()[0]
        self.assertEqual(rejected_count, 1)

        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertFalse(
            any('"stage":"inference"' in row["payload_json"] for row in stage_rows)
        )

    # ------------------------------------------------------------------
    # 3. Validation quarantine rejection
    # ------------------------------------------------------------------

    def test_validation_quarantine_rejection_audit_survives(self) -> None:
        """`validation_quarantine_admission_rejected` audit must persist."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)
        token = self.harness.issue_capability(
            "run_validation_quarantine", task_id
        )

        with patch(
            "kernel.services.validation_service.assert_proposal_admissible",
            side_effect=QuarantineAdmissibilityError("injected"),
        ):
            with self.assertRaises(ValidationRejected):
                self.harness.orch.admit_validation(
                    task_id=task_id,
                    capability_token=token,
                )

        self.assertEqual(
            self.harness.orch.current_stage(task_id), Stage.PATCH_PROPOSAL
        )

        rejected_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'validation_quarantine_admission_rejected';",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(rejected_count, 1)

        # No successful validation stage_entered audit; no validation_receipts row.
        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertFalse(
            any('"stage":"validation"' in row["payload_json"] for row in stage_rows)
        )
        vr_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM validation_receipts WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(vr_count, 0)

    # ------------------------------------------------------------------
    # 4. Budget pre-flight refusal
    # ------------------------------------------------------------------

    def test_budget_rejection_evidence_survives(self) -> None:
        """Budget pre-flight refusal must persist its budget records and audits."""
        adapter = _CountingAdapter(output_tokens=20)
        harness = AcceptanceHarness(
            inference_policy=InferencePolicy(max_output_tokens=50),
            default_hard_budget_tokens=40,
        )
        # Re-wire inference with the counting adapter so we can assert
        # the adapter was never invoked under a pre-flight refusal.
        harness.inf_svc = InferenceService(
            repository=harness.inf_repo,
            audit_ledger=harness.audit_ledger,
            context_reader=harness.ctx_repo,
            adapter=adapter,
            policy=InferencePolicy(max_output_tokens=50),
            budget_governor=harness.budget_governor,
            failure_bundle_repository=harness.failure_repo,
        )
        harness.orch._inference = harness.inf_svc  # type: ignore[attr-defined]

        try:
            task_id = f"task-{uuid4().hex[:8]}"
            # Use a small `actual_tokens` so admit_context fits the
            # 40-token hard budget; default `run_through_stage` would
            # request 500 tokens and trip ContextArtifactRejected
            # before we reach the inference pre-flight refusal.
            intent_id = f"intent-{uuid4().hex[:8]}"
            cap_ctx = harness.issue_capability(
                "read_repository_snapshot", task_id
            )
            harness.orch.admit_context(
                task_id=task_id,
                intent_id=intent_id,
                capability_token=cap_ctx,
                root_revision_id="rev-genesis-000",
                request={
                    "repo_graph_version": "1.0",
                    "symbol_index_version": "1.0",
                    "candidate_file_ids": ["src/main.py"],
                    "symbol_frontier_ids": ["main"],
                    "packing_policy_version": "phase1_budget_policy_v1",
                    "actual_tokens": 10,
                },
            )
            token = harness.issue_capability("invoke_inference", task_id)

            # The pre-flight refusal raises through admit_inference.
            with self.assertRaises(Exception) as ctx:
                harness.orch.admit_inference(
                    task_id=task_id,
                    capability_token=token,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )
            # The concrete exception is `InferenceBudgetExhausted` (a
            # subclass of `InferenceFailure`); included in
            # EXPECTED_GOVERNANCE_REJECTIONS so durable evidence
            # commits.
            from kernel.services.inference_service import (
                InferenceBudgetExhausted,
            )
            self.assertIsInstance(ctx.exception, InferenceBudgetExhausted)

            # Adapter was never invoked.
            self.assertEqual(adapter.calls, 0)

            # Budget records show pre-flight transition (durable).
            budget_rows = harness.budget_repo.list_for_task(task_id)
            states = [row["budget_state"] for row in budget_rows]
            self.assertIn("exceeded", states)

            # No inference artifact persisted.
            inf_count = harness.conn.execute(
                "SELECT COUNT(*) FROM inference_artifacts WHERE task_id = ?;",
                (task_id,),
            ).fetchone()[0]
            self.assertEqual(inf_count, 0)

            # No inference stage_entered audit.
            stage_rows = harness.conn.execute(
                "SELECT payload_json FROM audit_records "
                "WHERE task_id = ? AND record_type = 'stage_entered';",
                (task_id,),
            ).fetchall()
            self.assertFalse(
                any(
                    '"stage":"inference"' in row["payload_json"]
                    for row in stage_rows
                )
            )

            # In-memory state stays at CONTEXT.
            self.assertEqual(harness.orch.current_stage(task_id), Stage.CONTEXT)
        finally:
            harness.close()


if __name__ == "__main__":
    unittest.main()
