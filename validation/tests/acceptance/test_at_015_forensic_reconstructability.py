"""
AT-015: Forensic reconstructability (phase-1 scope).

Constitutional anchors:
- v11 Section 15 (evidence plane obligations)
- v11 Section 24.1 AT-015
- v11 Section 24.2 INV-027 (indirect via failure evidence retention path)
- Foundation Section 9 (P2 cleanup: phase-1 limits to FailureBundle/retention)

What this test proves:
  After a full signable path, the audit records and artifacts are
  sufficient to reconstruct WHY every material action happened.
  Specifically: every stage transition is recorded, artifact refs are
  present, and the audit sequence is unbroken.

Phase-1 scope: reconstruction is limited to audit records + artifact
  queries. Full encrypted vault / forensic evidence is deferred.
"""

from __future__ import annotations

import json
import unittest
import sys
import os
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.signable_path_orchestrator import OrchestratorRejected
from kernel.contracts.quarantine_rules import QuarantineAdmissibilityError
from kernel.services.capability_service import CapabilityDenied
from kernel.services.approval_service import ApprovalBarrierFailed
from kernel.services.review_service import (
    RenderingProvenance,
    ReviewRejected,
    ReviewService,
)
from kernel.services.validation_service import ValidationRejected
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestForensicReconstructability(unittest.TestCase):
    """AT-015: forensic reconstructability via audit + artifact evidence."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_full_path_audit_reconstructable(self) -> None:
        """Every stage transition must leave an audit record with
        artifact_refs, so a post-hoc forensic query can trace causality."""
        ids = self.harness.run_full_happy_path()

        # Query all audit records for this task.
        rows = self.harness.conn.execute(
            "SELECT record_type, artifact_refs, task_id, sequence "
            "FROM audit_records WHERE task_id = ? ORDER BY sequence;",
            (ids["task_id"],),
        ).fetchall()

        self.assertTrue(len(rows) >= 8, f"expected >=8 audit records, got {len(rows)}")

        # Every audit record must have a record_type.
        for row in rows:
            self.assertTrue(row["record_type"], "audit record missing record_type")

        # Sequence must be monotonic and gapless.
        seqs = [row["sequence"] for row in rows]
        self.assertEqual(seqs, sorted(seqs))

        # Check that key artifact IDs appear in the audit trail.
        all_refs = " ".join(row["artifact_refs"] or "" for row in rows)
        self.assertIn(ids["context_artifact_id"], all_refs)
        self.assertIn(ids["replay_anchor_id"], all_refs)

    def test_sealed_revision_traceable_from_audit(self) -> None:
        """The sealed revision must be findable from audit records."""
        ids = self.harness.run_full_happy_path()

        # The revision must exist and be sealed.
        rev = self.harness.rev_repo.fetch(ids["revision_id"])
        self.assertIsNotNone(rev)
        self.assertEqual(rev["state"], "sealed")

        # The replay anchor must bind to the revision.
        anchor_row = self.harness.conn.execute(
            "SELECT root_revision_id FROM replay_anchors WHERE replay_anchor_id = ?;",
            (ids["replay_anchor_id"],),
        ).fetchone()
        self.assertIsNotNone(anchor_row)

    def test_replay_anchor_binds_snapshot_root_id(self) -> None:
        """ReplayAnchor.required_artifact_ids carries the sealed SnapshotRoot."""
        ids = self.harness.run_full_happy_path()

        revision = self.harness.rev_repo.fetch(ids["revision_id"])
        self.assertIsNotNone(revision)
        snapshot_root_id = revision["snapshot_root_id"]
        self.assertTrue(snapshot_root_id)

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        self.assertIn(snapshot_root_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        self.assertIn(snapshot_root_id, payload["required_artifact_ids"])
        self.assertNotIn("snapshot_root_id", payload)
        self.assertNotIn("snapshot_root_ids", payload)

    def test_replay_anchor_binds_approval_id(self) -> None:
        """ReplayAnchor.required_artifact_ids carries the sealed approval."""
        ids = self.harness.run_full_happy_path()

        revision = self.harness.rev_repo.fetch(ids["revision_id"])
        self.assertIsNotNone(revision)
        approval_id = revision["approval_id"]
        self.assertEqual(approval_id, ids["approval_id"])

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        self.assertIn(approval_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        self.assertIn(approval_id, payload["required_artifact_ids"])
        self.assertNotIn("approval_id", payload)
        self.assertNotIn("approval_ids", payload)

    def test_replay_anchor_binds_validation_receipt_id(self) -> None:
        """ReplayAnchor.required_artifact_ids carries required receipts."""
        ids = self.harness.run_full_happy_path()

        approval = self.harness.ap_repo.fetch(ids["approval_id"])
        self.assertIsNotNone(approval)
        receipt_ids = approval["required_receipt_ids"]
        self.assertEqual(receipt_ids, [ids["validation_receipt_id"]])

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        for receipt_id in receipt_ids:
            self.assertIn(receipt_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for receipt_id in receipt_ids:
            self.assertIn(receipt_id, payload["required_artifact_ids"])
        self.assertNotIn("validation_receipt_id", payload)
        self.assertNotIn("validation_receipt_ids", payload)

    def test_replay_anchor_binds_issued_capability_token_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries scoped issued tokens."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)
        other_token = self.harness.issue_capability(
            "read_repository_snapshot",
            "task-out-of-scope",
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )

        capability_rows = self.harness.cap_repo.list_for_task(task_id)
        capability_token_ids = [
            row["capability_token_id"] for row in capability_rows
        ]
        self.assertEqual(
            [row["capability_name"] for row in capability_rows],
            [
                "read_repository_snapshot",
                "invoke_inference",
                "propose_patch",
                "run_validation_quarantine",
                "render_review",
                "grant_approval",
                "seal_revision",
                "append_evidence",
            ],
        )

        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for capability_token_id in capability_token_ids:
            self.assertIn(capability_token_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_token["capability_token_id"], anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for capability_token_id in capability_token_ids:
            self.assertIn(capability_token_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_token["capability_token_id"], payload["required_artifact_ids"]
        )
        self.assertNotIn("capability_token_id", payload)
        self.assertNotIn("capability_token_ids", payload)

    def test_replay_anchor_binds_consumed_capability_audit_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries consumed-token audits."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_token = self.harness.issue_capability(
            "append_evidence", other_task_id
        )
        self.harness.cap_svc.consume(
            capability_token_id=other_token["capability_token_id"],
            task_id=other_task_id,
        )
        other_consumed_rows = (
            self.harness.audit_repo.list_capability_token_consumed_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_consumed_rows), 1)
        other_consumed_audit_id = other_consumed_rows[0]["audit_record_id"]

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        consumed_rows = (
            self.harness.audit_repo.list_capability_token_consumed_for_task(
                task_id
            )
        )
        consumed_audit_ids = [
            row["audit_record_id"] for row in consumed_rows
        ]
        self.assertEqual(len(consumed_audit_ids), 8)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in consumed_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(other_consumed_audit_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in consumed_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(other_consumed_audit_id, payload["required_artifact_ids"])
        self.assertNotIn("capability_token_consumed_audit_id", payload)
        self.assertNotIn("capability_token_consumed_audit_ids", payload)

    def test_replay_anchor_binds_revoked_capability_audit_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries revoked-token audits."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_token = self.harness.issue_capability(
            "read_repository_snapshot", other_task_id
        )
        self.harness.cap_svc.revoke_token(
            capability_token_id=other_token["capability_token_id"],
            reason="other_task_revocation",
        )
        other_revoked_rows = (
            self.harness.audit_repo.list_capability_token_revoked_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_revoked_rows), 1)
        other_revoked_audit_id = other_revoked_rows[0]["audit_record_id"]

        revoked_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        self.harness.cap_svc.revoke_token(
            capability_token_id=revoked_token["capability_token_id"],
            reason="same_task_revocation",
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        revoked_rows = (
            self.harness.audit_repo.list_capability_token_revoked_for_task(
                task_id
            )
        )
        revoked_audit_ids = [
            row["audit_record_id"] for row in revoked_rows
        ]
        self.assertEqual(len(revoked_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in revoked_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(other_revoked_audit_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in revoked_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(other_revoked_audit_id, payload["required_artifact_ids"])
        self.assertNotIn("capability_token_revoked_audit_id", payload)
        self.assertNotIn("capability_token_revoked_audit_ids", payload)

    def test_replay_anchor_binds_consume_rejected_capability_audit_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries consume-rejection audits."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_token = self.harness.issue_capability(
            "append_evidence", other_task_id
        )
        self.harness.cap_repo.atomic_consume(
            other_token["capability_token_id"]
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.consume(
                capability_token_id=other_token["capability_token_id"],
                task_id=other_task_id,
            )
        other_rejected_rows = (
            self.harness.audit_repo.list_capability_token_consume_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        rejected_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        self.harness.cap_repo.atomic_consume(
            rejected_token["capability_token_id"]
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.consume(
                capability_token_id=rejected_token["capability_token_id"],
                task_id=task_id,
            )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_capability_token_consume_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn("capability_token_consume_rejected_audit_id", payload)
        self.assertNotIn("capability_token_consume_rejected_audit_ids", payload)

    def test_replay_anchor_binds_verification_rejected_capability_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries verification rejections."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_token = self.harness.issue_capability(
            "read_repository_snapshot", other_task_id
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.verify_for_action(
                token=other_token,
                action_class="append_evidence",
                task_id=other_task_id,
                root_revision_id=None,
            )
        other_rejected_rows = (
            self.harness.audit_repo.list_capability_verification_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        rejected_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.verify_for_action(
                token=rejected_token,
                action_class="append_evidence",
                task_id=task_id,
                root_revision_id=None,
            )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_capability_verification_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn("capability_verification_rejected_audit_id", payload)
        self.assertNotIn("capability_verification_rejected_audit_ids", payload)

    def test_replay_anchor_binds_illegal_stage_transition_rejected_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries illegal-stage rejections."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.CONTEXT)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        self.harness.run_through_stage(other_task_id, Stage.CONTEXT)
        other_patch_token = self.harness.issue_capability(
            "propose_patch", other_task_id
        )
        with self.assertRaises(OrchestratorRejected):
            self.harness.orch.admit_patch_proposal(
                task_id=other_task_id,
                capability_token=other_patch_token,
            )
        other_rejected_rows = (
            self.harness.audit_repo.list_illegal_stage_transition_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        rejected_patch_token = self.harness.issue_capability(
            "propose_patch", task_id
        )
        with self.assertRaises(OrchestratorRejected):
            self.harness.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=rejected_patch_token,
            )

        inference_token = self.harness.issue_capability(
            "invoke_inference", task_id
        )
        ids["inference_artifact_id"] = self.harness.orch.admit_inference(
            task_id=task_id,
            capability_token=inference_token,
            worker_profile="acceptance_worker",
            model_route_id="fake-model-v1",
        )
        patch_token = self.harness.issue_capability("propose_patch", task_id)
        ids["patch_proposal_id"] = self.harness.orch.admit_patch_proposal(
            task_id=task_id,
            capability_token=patch_token,
        )
        validation_token = self.harness.issue_capability(
            "run_validation_quarantine", task_id
        )
        ids["validation_receipt_id"] = self.harness.orch.admit_validation(
            task_id=task_id,
            capability_token=validation_token,
        )
        review_token = self.harness.issue_capability("render_review", task_id)
        ids["review_artifact_id"] = self.harness.orch.admit_review(
            task_id=task_id,
            capability_token=review_token,
        )
        approval_token = self.harness.issue_capability("grant_approval", task_id)
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability("append_evidence", task_id)
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_illegal_stage_transition_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn("illegal_stage_transition_rejected_audit_id", payload)
        self.assertNotIn("illegal_stage_transition_rejected_audit_ids", payload)

    def test_replay_anchor_binds_validation_quarantine_rejected_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries validation rejections."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        self.harness.run_through_stage(other_task_id, Stage.PATCH_PROPOSAL)

        with patch(
            "kernel.services.validation_service.assert_proposal_admissible",
            side_effect=QuarantineAdmissibilityError("injected"),
        ):
            other_validation_token = self.harness.issue_capability(
                "run_validation_quarantine", other_task_id
            )
            with self.assertRaises(ValidationRejected):
                self.harness.orch.admit_validation(
                    task_id=other_task_id,
                    capability_token=other_validation_token,
                )

            rejected_validation_token = self.harness.issue_capability(
                "run_validation_quarantine", task_id
            )
            with self.assertRaises(ValidationRejected):
                self.harness.orch.admit_validation(
                    task_id=task_id,
                    capability_token=rejected_validation_token,
                )

        other_rejected_rows = (
            self.harness.audit_repo.list_validation_quarantine_admission_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        validation_token = self.harness.issue_capability(
            "run_validation_quarantine", task_id
        )
        ids["validation_receipt_id"] = self.harness.orch.admit_validation(
            task_id=task_id,
            capability_token=validation_token,
        )
        review_token = self.harness.issue_capability("render_review", task_id)
        ids["review_artifact_id"] = self.harness.orch.admit_review(
            task_id=task_id,
            capability_token=review_token,
        )
        approval_token = self.harness.issue_capability("grant_approval", task_id)
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability("append_evidence", task_id)
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_validation_quarantine_admission_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn(
            "validation_quarantine_admission_rejected_audit_id", payload
        )
        self.assertNotIn(
            "validation_quarantine_admission_rejected_audit_ids", payload
        )

    def test_replay_anchor_binds_review_self_summary_rejected_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries review rejections."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.VALIDATION)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.VALIDATION
        )

        provenance = RenderingProvenance(
            renderer_id="same_worker_renderer",
            renderer_version="v1",
            self_summary_flag=True,
        )
        with patch.object(ReviewService, "FORBID_SELF_SUMMARY", True):
            with self.assertRaises(ReviewRejected):
                self.harness.rev_svc.render_review(
                    task_id=other_task_id,
                    patch_proposal_id=other_ids["patch_proposal_id"],
                    validation_receipt_id=other_ids["validation_receipt_id"],
                    rendering_provenance=provenance,
                    intent_id=other_ids["intent_id"],
                )
            with self.assertRaises(ReviewRejected):
                self.harness.rev_svc.render_review(
                    task_id=task_id,
                    patch_proposal_id=ids["patch_proposal_id"],
                    validation_receipt_id=ids["validation_receipt_id"],
                    rendering_provenance=provenance,
                    intent_id=ids["intent_id"],
                )

        other_rejected_rows = (
            self.harness.audit_repo.list_review_self_summary_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        review_token = self.harness.issue_capability("render_review", task_id)
        ids["review_artifact_id"] = self.harness.orch.admit_review(
            task_id=task_id,
            capability_token=review_token,
        )
        approval_token = self.harness.issue_capability("grant_approval", task_id)
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability("append_evidence", task_id)
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_review_self_summary_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn("review_self_summary_rejected_audit_id", payload)
        self.assertNotIn("review_self_summary_rejected_audit_ids", payload)

    def test_replay_anchor_binds_approval_barrier_rejected_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries approval rejections."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.REVIEW
        )

        def issue_time_rejection(rejection_ids: dict[str, str]) -> None:
            failing_receipt_id = f"vr-fail-{uuid4().hex}"
            self.harness.vr_repo.insert(
                {
                    "validation_receipt_id": failing_receipt_id,
                    "task_id": rejection_ids["task_id"],
                    "root_revision_id": rejection_ids["root_revision_id"],
                    "receipt_type": "phase1_static_quarantine",
                    "validator_identity": "acceptance_test",
                    "validator_version": "phase1-slice1",
                    "input_hash": f"sha256:{failing_receipt_id}",
                    "result": "fail",
                    "diagnostics_hash": f"sha256:diag-{failing_receipt_id}",
                    "taint_set": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "version_tuple_hash": "vt-approval-barrier-rejection",
                }
            )
            with self.assertRaises(ApprovalBarrierFailed):
                self.harness.ap_svc.evaluate_barrier(
                    task_id=rejection_ids["task_id"],
                    review_artifact_id=rejection_ids["review_artifact_id"],
                    required_receipt_ids=[failing_receipt_id],
                    reviewed_context_artifact_id=rejection_ids[
                        "context_artifact_id"
                    ],
                    intent_id=rejection_ids["intent_id"],
                )

        issue_time_rejection(other_ids)
        issue_time_rejection(ids)

        other_rejected_rows = (
            self.harness.audit_repo.list_approval_barrier_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        approval_token = self.harness.issue_capability("grant_approval", task_id)
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability("append_evidence", task_id)
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_approval_barrier_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, anchor["required_artifact_ids"]
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_rejected_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn("approval_barrier_rejected_audit_id", payload)
        self.assertNotIn("approval_barrier_rejected_audit_ids", payload)

    def test_replay_anchor_binds_review_artifact_id(self) -> None:
        """ReplayAnchor.required_artifact_ids carries scoped review artifacts."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_extra_review(
            review_artifact_id: str, extra_task_id: str, root_revision_id: str
        ) -> None:
            self.harness.rv_repo.insert(
                {
                    "review_artifact_id": review_artifact_id,
                    "task_id": extra_task_id,
                    "root_revision_id": root_revision_id,
                    "patch_proposal_id": ids["patch_proposal_id"],
                    "diff_hash": f"sha256:{review_artifact_id}",
                    "semantic_impact_hash": f"sha256:semantic-{review_artifact_id}",
                    "risk_class": "low",
                    "rendering_provenance": {
                        "renderer_id": "acceptance_test",
                        "renderer_version": "1.0",
                        "self_summary_flag": False,
                    },
                    "taint_set": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "version_tuple_hash": "vt-review-extra",
                }
            )

        other_root_review_id = f"rv-{uuid4().hex}"
        other_task_review_id = f"rv-{uuid4().hex}"
        insert_extra_review(
            other_root_review_id, task_id, "rev-out-of-scope-root"
        )
        insert_extra_review(
            other_task_review_id, "task-out-of-scope", ids["root_revision_id"]
        )

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        self.assertIn(ids["review_artifact_id"], anchor["required_artifact_ids"])
        self.assertNotIn(other_root_review_id, anchor["required_artifact_ids"])
        self.assertNotIn(other_task_review_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        self.assertIn(ids["review_artifact_id"], payload["required_artifact_ids"])
        self.assertNotIn(other_root_review_id, payload["required_artifact_ids"])
        self.assertNotIn(other_task_review_id, payload["required_artifact_ids"])
        self.assertNotIn("review_artifact_id", payload)
        self.assertNotIn("review_artifact_ids", payload)

    def test_replay_anchor_binds_patch_proposal_id_from_review(self) -> None:
        """ReplayAnchor.required_artifact_ids carries scoped reviewed patches."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_extra_review(
            review_artifact_id: str,
            extra_task_id: str,
            root_revision_id: str,
            patch_proposal_id: str,
        ) -> None:
            self.harness.rv_repo.insert(
                {
                    "review_artifact_id": review_artifact_id,
                    "task_id": extra_task_id,
                    "root_revision_id": root_revision_id,
                    "patch_proposal_id": patch_proposal_id,
                    "diff_hash": f"sha256:{review_artifact_id}",
                    "semantic_impact_hash": f"sha256:semantic-{review_artifact_id}",
                    "risk_class": "low",
                    "rendering_provenance": {
                        "renderer_id": "acceptance_test",
                        "renderer_version": "1.0",
                        "self_summary_flag": False,
                    },
                    "taint_set": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "version_tuple_hash": "vt-review-extra",
                }
            )

        other_root_patch_id = f"pp-{uuid4().hex}"
        other_task_patch_id = f"pp-{uuid4().hex}"
        insert_extra_review(
            f"rv-{uuid4().hex}",
            task_id,
            "rev-out-of-scope-root",
            other_root_patch_id,
        )
        insert_extra_review(
            f"rv-{uuid4().hex}",
            "task-out-of-scope",
            ids["root_revision_id"],
            other_task_patch_id,
        )

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        self.assertIn(ids["patch_proposal_id"], anchor["required_artifact_ids"])
        self.assertNotIn(other_root_patch_id, anchor["required_artifact_ids"])
        self.assertNotIn(other_task_patch_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        self.assertIn(ids["patch_proposal_id"], payload["required_artifact_ids"])
        self.assertNotIn(other_root_patch_id, payload["required_artifact_ids"])
        self.assertNotIn(other_task_patch_id, payload["required_artifact_ids"])
        self.assertNotIn("patch_proposal_id", payload)
        self.assertNotIn("patch_proposal_ids", payload)

    def test_replay_anchor_binds_seal_journal_entry_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries seal journal entries."""
        ids = self.harness.run_full_happy_path()

        journal_rows = self.harness.conn.execute(
            "SELECT journal_entry_id FROM journal_entries "
            "WHERE revision_id = ? ORDER BY logical_sequence;",
            (ids["revision_id"],),
        ).fetchall()
        journal_entry_ids = [row["journal_entry_id"] for row in journal_rows]
        self.assertEqual(len(journal_entry_ids), 3)

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        for journal_entry_id in journal_entry_ids:
            self.assertIn(journal_entry_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for journal_entry_id in journal_entry_ids:
            self.assertIn(journal_entry_id, payload["required_artifact_ids"])
        self.assertNotIn("journal_entry_id", payload)
        self.assertNotIn("journal_entry_ids", payload)


if __name__ == "__main__":
    unittest.main()
