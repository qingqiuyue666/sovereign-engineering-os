"""
P0 transaction-boundary hardening (phase 1): capability + service-effect
atomicity through `KernelUnitOfWork`.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.6 Capability Token Lifecycle Contract
- foundation §6 (P0 sealing + crash-window proofs)

These tests prove the success-path commit and the unexpected-runtime-
failure rollback semantics of the orchestrator's admission boundary.
Expected-governance-rejection commit semantics (e.g. capability-consume
rejection, illegal-stage rejection, validation-quarantine rejection,
budget refusal) are covered by `test_kernel_unit_of_work_rejection_evidence.py`.
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

from kernel.lifecycle.stage_types import Stage
from kernel.services.inference_service import InferenceFailure
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestKernelUnitOfWorkCapabilityRollback(unittest.TestCase):
    """Success-path commit and unexpected-failure rollback for admit_inference."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_admit_inference_unexpected_failure_rolls_back_success_side_effects(
        self,
    ) -> None:
        """Unexpected service failure must roll back the entire admission.

        With a `RuntimeError` raised mid-way through `InferenceService.
        run_inference` (i.e. AFTER `cap_svc.consume` has updated the
        token row but BEFORE any `inference_artifacts` row or
        `stage_entered` audit lands), the kernel transaction boundary
        must roll back the consume update, the (absent) artifact row,
        and the (absent) stage_entered audit. The in-memory current
        stage must remain CONTEXT.
        """
        task_id = f"task-{uuid4().hex[:8]}"
        # Drive the path through CONTEXT so admit_inference is legal.
        self.harness.run_through_stage(task_id, Stage.CONTEXT)
        token = self.harness.issue_capability("invoke_inference", task_id)
        token_id = token["capability_token_id"]

        before_pre_consumed = self.harness.cap_repo.fetch(token_id)
        self.assertIsNone(before_pre_consumed["consumed_at"])

        # An unexpected RuntimeError is NOT in EXPECTED_GOVERNANCE_REJECTIONS,
        # so the UoW must ROLLBACK on it.
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

        # Capability consume must have rolled back.
        after = self.harness.cap_repo.fetch(token_id)
        self.assertIsNone(
            after["consumed_at"],
            "capability_tokens.consumed_at must be NULL after UoW rollback",
        )

        # No inference artifact persisted.
        inf_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM inference_artifacts WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(inf_count, 0)

        # No inference stage_entered audit.
        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertFalse(
            any('"stage":"inference"' in row["payload_json"] for row in stage_rows)
        )

        # No capability_token_consumed audit either (rolled back).
        consumed_audit_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'capability_token_consumed' "
            "AND artifact_refs LIKE ?;",
            (task_id, f"%{token_id}%"),
        ).fetchone()[0]
        self.assertEqual(consumed_audit_count, 0)

        # In-memory state remains at CONTEXT.
        self.assertEqual(
            self.harness.orch.current_stage(task_id),
            Stage.CONTEXT,
        )

    def test_admit_inference_success_commits_side_effects(self) -> None:
        """Happy path: every side effect must be durable after admission."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.CONTEXT)
        token = self.harness.issue_capability("invoke_inference", task_id)
        token_id = token["capability_token_id"]

        inference_artifact_id = self.harness.orch.admit_inference(
            task_id=task_id,
            capability_token=token,
            worker_profile="acceptance_worker",
            model_route_id="fake-model-v1",
        )
        self.assertTrue(inference_artifact_id)

        # Capability consumed.
        token_row = self.harness.cap_repo.fetch(token_id)
        self.assertIsNotNone(token_row["consumed_at"])

        # Inference artifact persisted.
        inf_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM inference_artifacts "
            "WHERE inference_artifact_id = ?;",
            (inference_artifact_id,),
        ).fetchone()[0]
        self.assertEqual(inf_count, 1)

        # capability_token_consumed audit exists.
        consumed_audit_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = 'capability_token_consumed' "
            "AND artifact_refs LIKE ?;",
            (task_id, f"%{token_id}%"),
        ).fetchone()[0]
        self.assertEqual(consumed_audit_count, 1)

        # Inference stage_entered audit exists.
        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertTrue(
            any('"stage":"inference"' in row["payload_json"] for row in stage_rows)
        )

        # In-memory state advanced.
        self.assertEqual(
            self.harness.orch.current_stage(task_id),
            Stage.INFERENCE,
        )


if __name__ == "__main__":
    unittest.main()
