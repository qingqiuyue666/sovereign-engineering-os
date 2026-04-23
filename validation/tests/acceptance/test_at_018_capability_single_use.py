"""
AT-018: Capability token single-use lifecycle.

Constitutional anchors:
- v11 Section 22.6 Capability Token Lifecycle Contract
- v11 Section 24.1 AT-018
- v11 Section 24.2 INV-012 (single-use token consumed once)
- v11 Section 24.2 INV-013 (admissibility check before effect)
- Foundation Section 5.1 test #8 (capability token lifecycle)

What this test proves:
  A single-use capability token can be consumed exactly once. The
  second consumption attempt must fail closed with deterministic
  rejection evidence.
"""

from __future__ import annotations

import unittest
import sys
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.lifecycle.stage_types import Stage
from kernel.services.capability_service import CapabilityDenied


class TestCapabilitySingleUse(unittest.TestCase):
    """AT-018 / INV-012: single-use token consumed exactly once."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def _context_request(self) -> dict:
        return {
            "repo_graph_version": "1.0",
            "symbol_index_version": "1.0",
            "candidate_file_ids": ["src/main.py"],
            "symbol_frontier_ids": ["main"],
            "packing_policy_version": "phase1_budget_policy_v1",
            "actual_tokens": 500,
        }

    def _count_audit(self, task_id: str, record_type: str) -> int:
        row = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records "
            "WHERE task_id = ? AND record_type = ?;",
            (task_id, record_type),
        ).fetchone()
        return int(row[0])

    def test_single_use_consumed_once(self) -> None:
        """First consume succeeds; second must fail."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        # First consume: must succeed.
        result = self.harness.cap_repo.atomic_consume(token_id)
        self.assertTrue(result.winner)

        # Second consume: must fail.
        result2 = self.harness.cap_repo.atomic_consume(token_id)
        self.assertFalse(result2.winner)
        self.assertEqual(result2.reason, "already_consumed")

    def test_expired_token_cannot_be_consumed(self) -> None:
        """An expired token must not be consumable."""
        task_id = f"task-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        token = self.harness.cap_svc.issue_token(
            subject_identity="test",
            capability_name="read_repository_snapshot",
            scope_hash="scope:test",
            issued_at=(now - timedelta(hours=2)).isoformat(),
            expires_at=(now - timedelta(hours=1)).isoformat(),
            single_use=True,
            bound_task_id=task_id,
        )
        result = self.harness.cap_repo.atomic_consume(token["capability_token_id"])
        self.assertFalse(result.winner)

    def test_revoked_token_cannot_be_consumed(self) -> None:
        """A revoked token must not be consumable."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        # Revoke.
        self.harness.cap_repo.revoke(
            capability_token_id=token_id,
            reason="test_revocation",
        )

        # Consume attempt must fail.
        result = self.harness.cap_repo.atomic_consume(token_id)
        self.assertFalse(result.winner)
        self.assertEqual(result.reason, "revoked")

    def test_orchestrator_consumes_context_and_inference_tokens(self) -> None:
        """Live context and inference admissions consume issued tokens."""
        task_id = f"task-{uuid4().hex[:8]}"
        context_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        inference_token = self.harness.issue_capability(
            "invoke_inference", task_id, single_use=True,
        )

        self.harness.orch.admit_context(
            task_id=task_id,
            intent_id=f"intent-{uuid4().hex[:8]}",
            capability_token=context_token,
            root_revision_id="rev-genesis-000",
            request=self._context_request(),
        )
        self.harness.orch.admit_inference(
            task_id=task_id,
            capability_token=inference_token,
            worker_profile="acceptance_worker",
            model_route_id="fake-model-v1",
        )

        for token in (context_token, inference_token):
            row = self.harness.cap_repo.fetch(token["capability_token_id"])
            self.assertIsNotNone(row)
            self.assertIsNotNone(row["consumed_at"])
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consumed"),
            2,
        )

    def test_orchestrator_consumes_patch_proposal_token(self) -> None:
        """Live patch-proposal admission consumes its propose_patch token."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        patch_token = self.harness.issue_capability(
            "propose_patch", task_id, single_use=True,
        )

        proposal_id = self.harness.orch.admit_patch_proposal(
            task_id=task_id,
            capability_token=patch_token,
        )

        self.assertTrue(proposal_id.startswith("pp-"))
        row = self.harness.cap_repo.fetch(patch_token["capability_token_id"])
        self.assertIsNotNone(row)
        self.assertIsNotNone(row["consumed_at"])
        self.assertEqual(
            self.harness.orch.current_stage(task_id), Stage.PATCH_PROPOSAL
        )
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consumed"),
            3,
        )

    def test_orchestrator_consumes_validation_token(self) -> None:
        """Live validation admission consumes its quarantine token."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)
        validation_token = self.harness.issue_capability(
            "run_validation_quarantine", task_id, single_use=True,
        )

        receipt_id = self.harness.orch.admit_validation(
            task_id=task_id,
            capability_token=validation_token,
        )

        self.assertTrue(receipt_id.startswith("vr-"))
        row = self.harness.cap_repo.fetch(
            validation_token["capability_token_id"]
        )
        self.assertIsNotNone(row)
        self.assertIsNotNone(row["consumed_at"])
        self.assertEqual(self.harness.orch.current_stage(task_id), Stage.VALIDATION)
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consumed"),
            4,
        )

    def test_context_consume_failure_blocks_artifact_and_stage(self) -> None:
        """A pre-consumed context token rejects before durable path progress."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        self.harness.cap_repo.atomic_consume(token["capability_token_id"])

        with self.assertRaises(CapabilityDenied):
            self.harness.orch.admit_context(
                task_id=task_id,
                intent_id=f"intent-{uuid4().hex[:8]}",
                capability_token=token,
                root_revision_id="rev-genesis-000",
                request=self._context_request(),
            )

        context_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM context_artifacts WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(context_count, 0)
        self.assertIsNone(self.harness.orch.current_stage(task_id))
        self.assertEqual(self._count_audit(task_id, "stage_entered"), 0)
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consume_rejected"),
            1,
        )

    def test_inference_consume_failure_blocks_artifact_and_stage(self) -> None:
        """A pre-consumed inference token rejects before inference effects."""
        task_id = f"task-{uuid4().hex[:8]}"
        context_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        self.harness.orch.admit_context(
            task_id=task_id,
            intent_id=f"intent-{uuid4().hex[:8]}",
            capability_token=context_token,
            root_revision_id="rev-genesis-000",
            request=self._context_request(),
        )
        inference_token = self.harness.issue_capability(
            "invoke_inference", task_id, single_use=True,
        )
        self.harness.cap_repo.atomic_consume(
            inference_token["capability_token_id"]
        )

        with self.assertRaises(CapabilityDenied):
            self.harness.orch.admit_inference(
                task_id=task_id,
                capability_token=inference_token,
                worker_profile="acceptance_worker",
                model_route_id="fake-model-v1",
            )

        inference_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM inference_artifacts WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(inference_count, 0)
        self.assertEqual(self.harness.orch.current_stage(task_id), Stage.CONTEXT)
        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertFalse(
            any('"stage":"inference"' in row["payload_json"] for row in stage_rows)
        )
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consume_rejected"),
            1,
        )

    def test_patch_proposal_consume_failure_blocks_artifact_and_stage(self) -> None:
        """A pre-consumed propose_patch token rejects before patch effects."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        patch_token = self.harness.issue_capability(
            "propose_patch", task_id, single_use=True,
        )
        self.harness.cap_repo.atomic_consume(
            patch_token["capability_token_id"]
        )

        with self.assertRaises(CapabilityDenied):
            self.harness.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=patch_token,
            )

        patch_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM patch_proposals WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(patch_count, 0)
        self.assertEqual(self.harness.orch.current_stage(task_id), Stage.INFERENCE)
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
        self.assertEqual(self._count_audit(task_id, "patch_proposal_created"), 0)
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consume_rejected"),
            1,
        )

    def test_validation_consume_failure_blocks_artifact_taint_and_stage(self) -> None:
        """A pre-consumed validation token rejects before validation effects."""
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)
        validation_token = self.harness.issue_capability(
            "run_validation_quarantine", task_id, single_use=True,
        )
        self.harness.cap_repo.atomic_consume(
            validation_token["capability_token_id"]
        )

        with self.assertRaises(CapabilityDenied):
            self.harness.orch.admit_validation(
                task_id=task_id,
                capability_token=validation_token,
            )

        validation_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM validation_receipts WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        taint_count = self.harness.conn.execute(
            "SELECT COUNT(*) FROM taint_records;"
        ).fetchone()[0]
        self.assertEqual(validation_count, 0)
        self.assertEqual(taint_count, 0)
        self.assertEqual(
            self.harness.orch.current_stage(task_id), Stage.PATCH_PROPOSAL
        )
        stage_rows = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'stage_entered';",
            (task_id,),
        ).fetchall()
        self.assertFalse(
            any(
                '"stage":"validation"' in row["payload_json"]
                for row in stage_rows
            )
        )
        self.assertEqual(self._count_audit(task_id, "validation_receipt_created"), 0)
        self.assertEqual(
            self._count_audit(task_id, "capability_token_consume_rejected"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
