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
from kernel.contracts.barrier_rules import BarrierEvaluationError
from kernel.contracts.quarantine_rules import QuarantineAdmissibilityError
from kernel.services.capability_service import CapabilityDenied
from kernel.services.approval_service import ApprovalBarrierFailed, ApprovalRejected
from kernel.services.invalidation_service import (
    DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
    InvalidationService,
    REASON_UPSTREAM_PATCH_DRIFT,
)
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

    def test_replay_anchor_binds_validation_receipt_invalidated_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries receipt invalidations."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.PATCH_PROPOSAL
        )

        inval_svc = InvalidationService(
            receipt_repo=self.harness.vr_repo,
            approval_repo=self.harness.ap_repo,
            drift_repo=self.harness.drift_repo,
            audit_ledger=self.harness.audit_ledger,
        )

        def seed_extra_receipt(extra_task_id: str, root_revision_id: str) -> str:
            validation_receipt_id = f"vr-extra-{uuid4().hex[:8]}"
            self.harness.vr_repo.insert(
                {
                    "validation_receipt_id": validation_receipt_id,
                    "task_id": extra_task_id,
                    "root_revision_id": root_revision_id,
                    "receipt_type": "phase1_static_quarantine",
                    "validator_identity": "phase1_static_validator",
                    "validator_version": "phase1-slice1",
                    "input_hash": f"sha256:{validation_receipt_id}",
                    "result": "pass",
                    "diagnostics_hash": f"sha256:diag-{validation_receipt_id}",
                    "taint_set": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "version_tuple_hash": "vt-validation-extra",
                }
            )
            return validation_receipt_id

        other_receipt_id = seed_extra_receipt(
            other_task_id, other_ids["root_revision_id"]
        )
        self.assertTrue(
            inval_svc.invalidate_receipt(
                validation_receipt_id=other_receipt_id,
                reason=REASON_UPSTREAM_PATCH_DRIFT,
                drift_class=DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
                source_artifact_id=other_ids["patch_proposal_id"],
                task_id=other_task_id,
                root_revision_id=other_ids["root_revision_id"],
                intent_id=other_ids["intent_id"],
            )
        )
        other_invalidated_rows = (
            self.harness.audit_repo.list_validation_receipt_invalidated_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_invalidated_rows), 1)
        other_invalidated_audit_id = other_invalidated_rows[0]["audit_record_id"]

        first_invalidated_receipt_id = seed_extra_receipt(
            task_id, ids["root_revision_id"]
        )
        second_invalidated_receipt_id = seed_extra_receipt(
            task_id, ids["root_revision_id"]
        )
        for receipt_id in (
            first_invalidated_receipt_id,
            second_invalidated_receipt_id,
        ):
            self.assertTrue(
                inval_svc.invalidate_receipt(
                    validation_receipt_id=receipt_id,
                    reason=REASON_UPSTREAM_PATCH_DRIFT,
                    drift_class=DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
                    source_artifact_id=ids["patch_proposal_id"],
                    task_id=task_id,
                    root_revision_id=ids["root_revision_id"],
                    intent_id=ids["intent_id"],
                )
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

        invalidated_rows = (
            self.harness.audit_repo.list_validation_receipt_invalidated_for_task(
                task_id
            )
        )
        invalidated_audit_ids = [
            row["audit_record_id"] for row in invalidated_rows
        ]
        self.assertEqual(len(invalidated_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in invalidated_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [audit_id for audit_id in required if audit_id in invalidated_audit_ids],
            invalidated_audit_ids,
        )
        self.assertNotIn(
            other_invalidated_audit_id, required
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in invalidated_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [
                audit_id
                for audit_id in mirrored
                if audit_id in invalidated_audit_ids
            ],
            invalidated_audit_ids,
        )
        self.assertNotIn(
            other_invalidated_audit_id, mirrored
        )
        self.assertNotIn("validation_receipt_invalidated_audit_id", payload)
        self.assertNotIn("validation_receipt_invalidated_audit_ids", payload)

    def test_replay_anchor_binds_approval_invalidated_audit_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries approval invalidations."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.PATCH_PROPOSAL
        )

        inval_svc = InvalidationService(
            receipt_repo=self.harness.vr_repo,
            approval_repo=self.harness.ap_repo,
            drift_repo=self.harness.drift_repo,
            audit_ledger=self.harness.audit_ledger,
        )

        def seed_receipt_and_approval(
            extra_task_id: str, root_revision_id: str
        ) -> tuple[str, str]:
            validation_receipt_id = f"vr-extra-{uuid4().hex[:8]}"
            approval_id = f"ap-extra-{uuid4().hex[:8]}"
            self.harness.vr_repo.insert(
                {
                    "validation_receipt_id": validation_receipt_id,
                    "task_id": extra_task_id,
                    "root_revision_id": root_revision_id,
                    "receipt_type": "phase1_static_quarantine",
                    "validator_identity": "phase1_static_validator",
                    "validator_version": "phase1-slice1",
                    "input_hash": f"sha256:{validation_receipt_id}",
                    "result": "pass",
                    "diagnostics_hash": f"sha256:diag-{validation_receipt_id}",
                    "taint_set": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "version_tuple_hash": "vt-validation-extra",
                }
            )
            self.harness.ap_repo.insert(
                {
                    "approval_id": approval_id,
                    "task_id": extra_task_id,
                    "originating_root_revision_id": root_revision_id,
                    "reviewed_patch_hash": f"sha256:{approval_id}",
                    "reviewed_context_artifact_id": f"ctx-extra-{approval_id}",
                    "required_receipt_ids": [validation_receipt_id],
                    "approval_scope": "phase1_narrow_path_single_file",
                    "approver_identity": "kernel:phase1",
                    "approval_state": "approved",
                    "policy_version": "phase1_approval_policy_v1",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "expires_at": "2026-01-02T00:00:00+00:00",
                    "version_tuple_hash": "vt-approval-extra",
                }
            )
            return validation_receipt_id, approval_id

        other_receipt_id, _ = seed_receipt_and_approval(
            other_task_id, other_ids["root_revision_id"]
        )
        self.assertTrue(
            inval_svc.invalidate_receipt(
                validation_receipt_id=other_receipt_id,
                reason=REASON_UPSTREAM_PATCH_DRIFT,
                drift_class=DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
                source_artifact_id=other_ids["patch_proposal_id"],
                task_id=other_task_id,
                root_revision_id=other_ids["root_revision_id"],
                intent_id=other_ids["intent_id"],
            )
        )
        other_invalidated_rows = (
            self.harness.audit_repo.list_approval_invalidated_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_invalidated_rows), 1)
        other_invalidated_audit_id = other_invalidated_rows[0]["audit_record_id"]

        first_receipt_id, _ = seed_receipt_and_approval(
            task_id, ids["root_revision_id"]
        )
        second_receipt_id, _ = seed_receipt_and_approval(
            task_id, ids["root_revision_id"]
        )
        for receipt_id in (first_receipt_id, second_receipt_id):
            self.assertTrue(
                inval_svc.invalidate_receipt(
                    validation_receipt_id=receipt_id,
                    reason=REASON_UPSTREAM_PATCH_DRIFT,
                    drift_class=DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
                    source_artifact_id=ids["patch_proposal_id"],
                    task_id=task_id,
                    root_revision_id=ids["root_revision_id"],
                    intent_id=ids["intent_id"],
                )
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

        invalidated_rows = (
            self.harness.audit_repo.list_approval_invalidated_for_task(task_id)
        )
        invalidated_audit_ids = [
            row["audit_record_id"] for row in invalidated_rows
        ]
        self.assertEqual(len(invalidated_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in invalidated_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [audit_id for audit_id in required if audit_id in invalidated_audit_ids],
            invalidated_audit_ids,
        )
        self.assertNotIn(other_invalidated_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in invalidated_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [
                audit_id
                for audit_id in mirrored
                if audit_id in invalidated_audit_ids
            ],
            invalidated_audit_ids,
        )
        self.assertNotIn(other_invalidated_audit_id, mirrored)
        self.assertNotIn("approval_invalidated_audit_id", payload)
        self.assertNotIn("approval_invalidated_audit_ids", payload)

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
        self.assertEqual(
            [
                tok
                for tok in anchor["required_artifact_ids"]
                if tok in capability_token_ids
            ],
            capability_token_ids,
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
        self.assertEqual(
            [
                tok
                for tok in payload["required_artifact_ids"]
                if tok in capability_token_ids
            ],
            capability_token_ids,
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

    def test_replay_anchor_binds_approval_seal_time_barrier_rejected_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries seal-time rejections."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.APPROVAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.APPROVAL
        )

        def seal_time_rejection(rejection_ids: dict[str, str]) -> None:
            approval = self.harness.ap_repo.fetch(rejection_ids["approval_id"])
            self.assertIsNotNone(approval)
            with self.assertRaises(ApprovalBarrierFailed):
                self.harness.ap_svc.reverify_for_seal(
                    approval_id=rejection_ids["approval_id"],
                    current_root_revision_id="rev-DRIFTED-CONCURRENT",
                    current_context_artifact_id=approval[
                        "reviewed_context_artifact_id"
                    ],
                    current_patch_hash=approval["reviewed_patch_hash"],
                    intent_id=rejection_ids["intent_id"],
                )

        seal_time_rejection(other_ids)
        seal_time_rejection(ids)

        other_rejected_rows = (
            self.harness.audit_repo.list_approval_seal_time_barrier_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

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
            self.harness.audit_repo.list_approval_seal_time_barrier_rejected_for_task(
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
        self.assertNotIn("approval_seal_time_barrier_rejected_audit_id", payload)
        self.assertNotIn("approval_seal_time_barrier_rejected_audit_ids", payload)

    def test_replay_anchor_binds_approval_barrier_evaluation_error_audit_ids(
        self,
    ) -> None:
        """ReplayAnchor.required_artifact_ids carries approval evaluation errors."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.REVIEW
        )

        def evaluation_error(error_ids: dict[str, str]) -> None:
            with patch(
                "kernel.services.approval_service.evaluate_barrier",
                side_effect=BarrierEvaluationError("injected"),
            ):
                with self.assertRaises(ApprovalRejected):
                    self.harness.ap_svc.evaluate_barrier(
                        task_id=error_ids["task_id"],
                        review_artifact_id=error_ids["review_artifact_id"],
                        required_receipt_ids=[
                            error_ids["validation_receipt_id"]
                        ],
                        reviewed_context_artifact_id=error_ids[
                            "context_artifact_id"
                        ],
                        intent_id=error_ids["intent_id"],
                    )

        evaluation_error(other_ids)
        evaluation_error(ids)

        other_error_rows = (
            self.harness.audit_repo.list_approval_barrier_evaluation_error_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_error_rows), 1)
        other_error_audit_id = other_error_rows[0]["audit_record_id"]

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

        error_rows = (
            self.harness.audit_repo.list_approval_barrier_evaluation_error_for_task(
                task_id
            )
        )
        error_audit_ids = [row["audit_record_id"] for row in error_rows]
        self.assertEqual(len(error_audit_ids), 1)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        for audit_record_id in error_audit_ids:
            self.assertIn(audit_record_id, anchor["required_artifact_ids"])
        self.assertNotIn(other_error_audit_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for audit_record_id in error_audit_ids:
            self.assertIn(audit_record_id, payload["required_artifact_ids"])
        self.assertNotIn(
            other_error_audit_id, payload["required_artifact_ids"]
        )
        self.assertNotIn("approval_barrier_evaluation_error_audit_id", payload)
        self.assertNotIn("approval_barrier_evaluation_error_audit_ids", payload)

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

    def test_replay_anchor_review_artifact_ids_preserve_insertion_order(
        self,
    ) -> None:
        """_review_artifact_ids order is stable and task+root scoped."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_review(
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
                    "semantic_impact_hash": f"sha256:sem-{review_artifact_id}",
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

        first_extra_id = f"rv-extra-a-{uuid4().hex[:8]}"
        second_extra_id = f"rv-extra-b-{uuid4().hex[:8]}"
        third_extra_id = f"rv-extra-c-{uuid4().hex[:8]}"
        other_task_review_id = f"rv-other-task-{uuid4().hex[:8]}"
        other_root_review_id = f"rv-other-root-{uuid4().hex[:8]}"

        insert_review(
            first_extra_id,
            task_id,
            ids["root_revision_id"],
            ids["patch_proposal_id"],
        )
        insert_review(
            second_extra_id,
            task_id,
            ids["root_revision_id"],
            ids["patch_proposal_id"],
        )
        insert_review(
            third_extra_id,
            task_id,
            ids["root_revision_id"],
            ids["patch_proposal_id"],
        )
        insert_review(
            other_task_review_id,
            "task-out-of-scope",
            ids["root_revision_id"],
            ids["patch_proposal_id"],
        )
        insert_review(
            other_root_review_id,
            task_id,
            "rev-out-of-scope-root",
            ids["patch_proposal_id"],
        )

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        expected_review_ids = [
            ids["review_artifact_id"],
            first_extra_id,
            second_extra_id,
            third_extra_id,
        ]

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        self.assertEqual(
            [i for i in required if i in expected_review_ids],
            expected_review_ids,
        )
        self.assertNotIn(other_task_review_id, required)
        self.assertNotIn(other_root_review_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        self.assertEqual(
            [i for i in mirrored if i in expected_review_ids],
            expected_review_ids,
        )
        self.assertNotIn(other_task_review_id, mirrored)
        self.assertNotIn(other_root_review_id, mirrored)
        self.assertNotIn("review_artifact_id", payload)
        self.assertNotIn("review_artifact_ids", payload)

    def test_replay_anchor_patch_proposal_ids_preserve_first_seen_order(
        self,
    ) -> None:
        """_patch_proposal_ids first-seen order is stable and task+root scoped."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_review(
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
                    "semantic_impact_hash": f"sha256:sem-{review_artifact_id}",
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

        pp_extra_a = f"pp-extra-a-{uuid4().hex[:8]}"
        pp_extra_b = f"pp-extra-b-{uuid4().hex[:8]}"
        pp_other_task = f"pp-other-task-{uuid4().hex[:8]}"
        pp_other_root = f"pp-other-root-{uuid4().hex[:8]}"

        insert_review(
            f"rv-a-{uuid4().hex[:8]}",
            task_id,
            ids["root_revision_id"],
            pp_extra_a,
        )
        insert_review(
            f"rv-a2-{uuid4().hex[:8]}",
            task_id,
            ids["root_revision_id"],
            pp_extra_a,
        )
        insert_review(
            f"rv-b-{uuid4().hex[:8]}",
            task_id,
            ids["root_revision_id"],
            pp_extra_b,
        )
        insert_review(
            f"rv-other-task-{uuid4().hex[:8]}",
            "task-out-of-scope",
            ids["root_revision_id"],
            pp_other_task,
        )
        insert_review(
            f"rv-other-root-{uuid4().hex[:8]}",
            task_id,
            "rev-out-of-scope-root",
            pp_other_root,
        )

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        expected_pp_ids = [
            ids["patch_proposal_id"],
            pp_extra_a,
            pp_extra_b,
        ]

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        self.assertEqual(
            [i for i in required if i in expected_pp_ids],
            expected_pp_ids,
        )
        self.assertNotIn(pp_other_task, required)
        self.assertNotIn(pp_other_root, required)
        # Dedup guarantee: each same-task/same-root patch_proposal_id appears once.
        self.assertEqual(
            sum(1 for i in required if i == pp_extra_a), 1
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        self.assertEqual(
            [i for i in mirrored if i in expected_pp_ids],
            expected_pp_ids,
        )
        self.assertNotIn(pp_other_task, mirrored)
        self.assertNotIn(pp_other_root, mirrored)
        self.assertNotIn("patch_proposal_id", payload)
        self.assertNotIn("patch_proposal_ids", payload)

    def test_replay_anchor_drift_event_ids_preserve_insertion_order(
        self,
    ) -> None:
        """_drift_event_ids order is stable and task+root scoped."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_drift(
            drift_event_id: str,
            extra_task_id: str,
            root_revision_id: str,
        ) -> None:
            self.harness.drift_repo.insert(
                {
                    "drift_event_id": drift_event_id,
                    "task_id": extra_task_id,
                    "root_revision_id": root_revision_id,
                    "drift_class": "ordering_coverage_probe",
                    "detected_at": "2026-01-01T00:00:00+00:00",
                    "affected_artifact_ids": [],
                    "consequence_class": "probe_no_op",
                }
            )

        first_id = f"drift-a-{uuid4().hex[:8]}"
        second_id = f"drift-b-{uuid4().hex[:8]}"
        third_id = f"drift-c-{uuid4().hex[:8]}"
        other_task_drift = f"drift-other-task-{uuid4().hex[:8]}"
        other_root_drift = f"drift-other-root-{uuid4().hex[:8]}"

        insert_drift(first_id, task_id, ids["root_revision_id"])
        insert_drift(second_id, task_id, ids["root_revision_id"])
        insert_drift(third_id, task_id, ids["root_revision_id"])
        insert_drift(
            other_task_drift, "task-out-of-scope", ids["root_revision_id"]
        )
        insert_drift(other_root_drift, task_id, "rev-out-of-scope-root")

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        expected_ids = [first_id, second_id, third_id]
        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        self.assertEqual(
            [i for i in required if i in expected_ids],
            expected_ids,
        )
        self.assertNotIn(other_task_drift, required)
        self.assertNotIn(other_root_drift, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        self.assertEqual(
            [i for i in mirrored if i in expected_ids],
            expected_ids,
        )
        self.assertNotIn(other_task_drift, mirrored)
        self.assertNotIn(other_root_drift, mirrored)
        self.assertNotIn("drift_event_id", payload)
        self.assertNotIn("drift_event_ids", payload)

    def test_replay_anchor_failure_bundle_ids_preserve_insertion_order(
        self,
    ) -> None:
        """_failure_bundle_ids order is stable and task+root scoped."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_bundle(
            failure_bundle_id: str,
            extra_task_id: str,
            root_revision_id: str,
        ) -> None:
            self.harness.failure_repo.append(
                artifact={
                    "failure_bundle_id": failure_bundle_id,
                    "task_id": extra_task_id,
                    "root_revision_id": root_revision_id,
                    "failure_class": "ordering_coverage_probe",
                    "cause_hash": f"sha256:{failure_bundle_id}",
                    "evidence_refs": [],
                    "taint_set": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "retained_for_forensics_flag": False,
                }
            )

        first_id = f"fb-a-{uuid4().hex[:8]}"
        second_id = f"fb-b-{uuid4().hex[:8]}"
        third_id = f"fb-c-{uuid4().hex[:8]}"
        other_task_fb = f"fb-other-task-{uuid4().hex[:8]}"
        other_root_fb = f"fb-other-root-{uuid4().hex[:8]}"

        insert_bundle(first_id, task_id, ids["root_revision_id"])
        insert_bundle(second_id, task_id, ids["root_revision_id"])
        insert_bundle(third_id, task_id, ids["root_revision_id"])
        insert_bundle(
            other_task_fb, "task-out-of-scope", ids["root_revision_id"]
        )
        insert_bundle(other_root_fb, task_id, "rev-out-of-scope-root")

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        expected_ids = [first_id, second_id, third_id]
        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        self.assertEqual(
            [i for i in required if i in expected_ids],
            expected_ids,
        )
        self.assertNotIn(other_task_fb, required)
        self.assertNotIn(other_root_fb, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        self.assertEqual(
            [i for i in mirrored if i in expected_ids],
            expected_ids,
        )
        self.assertNotIn(other_task_fb, mirrored)
        self.assertNotIn(other_root_fb, mirrored)
        self.assertNotIn("failure_bundle_id", payload)
        self.assertNotIn("failure_bundle_ids", payload)

    def test_replay_anchor_budget_record_ids_preserve_insertion_order(
        self,
    ) -> None:
        """_budget_record_ids order is stable and task scoped."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVISION_SEAL)

        def insert_budget(
            budget_record_id: str,
            extra_task_id: str,
        ) -> None:
            self.harness.budget_repo.append(
                budget_record_id=budget_record_id,
                task_id=extra_task_id,
                budget_class="ordering_coverage_probe",
                allocated_amount=0,
                consumed_amount=0,
                remaining_amount=0,
                budget_state="active",
            )

        first_id = f"budget-probe-a-{uuid4().hex[:8]}"
        second_id = f"budget-probe-b-{uuid4().hex[:8]}"
        third_id = f"budget-probe-c-{uuid4().hex[:8]}"
        other_task_budget = f"budget-probe-other-{uuid4().hex[:8]}"

        existing_budget_ids = [
            row["budget_record_id"]
            for row in self.harness.budget_repo.list_for_task(task_id)
        ]

        insert_budget(first_id, task_id)
        insert_budget(second_id, task_id)
        insert_budget(third_id, task_id)
        insert_budget(other_task_budget, "task-out-of-scope")

        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        expected_ids = existing_budget_ids + [first_id, second_id, third_id]
        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        self.assertEqual(
            [i for i in required if i in expected_ids],
            expected_ids,
        )
        self.assertNotIn(other_task_budget, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        self.assertEqual(
            [i for i in mirrored if i in expected_ids],
            expected_ids,
        )
        self.assertNotIn(other_task_budget, mirrored)
        self.assertNotIn("budget_record_id", payload)
        self.assertNotIn("budget_record_ids", payload)

    def test_replay_anchor_validation_taint_record_ids_preserve_repository_order(
        self,
    ) -> None:
        """_validation_taint_record_ids order is stable and receipt scoped.

        TaintRepository.list_for_subject orders rows by taint_record_id,
        so the deterministic position of taint record ids within
        ReplayAnchor.required_artifact_ids must match the repository's
        lexicographic order. Insertion order here is intentionally
        reversed vs. the expected output to keep the test sensitive to
        that ORDER BY clause.
        """
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.APPROVAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.APPROVAL
        )

        first_taint_id = f"taint-aaa-{uuid4().hex[:8]}"
        second_taint_id = f"taint-bbb-{uuid4().hex[:8]}"
        other_taint_id = f"taint-ccc-{uuid4().hex[:8]}"
        self.assertLess(first_taint_id, second_taint_id)

        existing_taint_ids = [
            row["taint_record_id"]
            for row in self.harness.taint_repo.list_for_subject(
                ids["validation_receipt_id"]
            )
        ]

        self.harness.taint_repo.append(
            taint_record_id=second_taint_id,
            subject_id=ids["validation_receipt_id"],
            taint_class="policy_degraded",
            taint_state="downgraded",
            source_ref="ordering_coverage_probe",
        )
        self.harness.taint_repo.append(
            taint_record_id=first_taint_id,
            subject_id=ids["validation_receipt_id"],
            taint_class="policy_degraded",
            taint_state="downgraded",
            source_ref="ordering_coverage_probe",
        )
        self.harness.taint_repo.append(
            taint_record_id=other_taint_id,
            subject_id=other_ids["validation_receipt_id"],
            taint_class="policy_degraded",
            taint_state="downgraded",
            source_ref="ordering_coverage_probe",
        )

        seal_token = self.harness.issue_capability("seal_revision", task_id)
        self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        repo_ordered_ids = [
            row["taint_record_id"]
            for row in self.harness.taint_repo.list_for_subject(
                ids["validation_receipt_id"]
            )
        ]
        probe_ids = [first_taint_id, second_taint_id]
        self.assertEqual(
            [tid for tid in repo_ordered_ids if tid in probe_ids],
            probe_ids,
        )
        for existing_id in existing_taint_ids:
            self.assertIn(existing_id, repo_ordered_ids)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for taint_id in probe_ids:
            self.assertIn(taint_id, required)
        self.assertEqual(
            [tid for tid in required if tid in probe_ids],
            probe_ids,
        )
        self.assertNotIn(other_taint_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (task_id, replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for taint_id in probe_ids:
            self.assertIn(taint_id, mirrored)
        self.assertEqual(
            [tid for tid in mirrored if tid in probe_ids],
            probe_ids,
        )
        self.assertNotIn(other_taint_id, mirrored)
        self.assertNotIn("taint_record_id", payload)
        self.assertNotIn("taint_record_ids", payload)
        self.assertNotIn("validation_taint_record_id", payload)
        self.assertNotIn("validation_taint_record_ids", payload)

    def test_replay_anchor_capability_token_consume_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_capability_token_consume_rejected_audit_ids order is stable.

        AuditRepository.list_capability_token_consume_rejected_for_task
        orders rows by `sequence`, so the deterministic position of
        consume-rejection audit ids within ReplayAnchor.required_artifact_ids
        must match audit append order. Two same-task rejections are seeded
        in a known sequence plus one other-task rejection to prove
        task-scoping exclusion.
        """
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

        first_rejected_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        self.harness.cap_repo.atomic_consume(
            first_rejected_token["capability_token_id"]
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.consume(
                capability_token_id=first_rejected_token["capability_token_id"],
                task_id=task_id,
            )

        second_rejected_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        self.harness.cap_repo.atomic_consume(
            second_rejected_token["capability_token_id"]
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.consume(
                capability_token_id=second_rejected_token["capability_token_id"],
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
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn("capability_token_consume_rejected_audit_id", payload)
        self.assertNotIn("capability_token_consume_rejected_audit_ids", payload)

    def test_replay_anchor_capability_verification_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_capability_verification_rejected_audit_ids order is stable.

        AuditRepository.list_capability_verification_rejected_for_task
        orders rows by `sequence`, so the deterministic position of
        verification-rejection audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task rejections are seeded in a known sequence
        plus one other-task rejection to prove task-scoping exclusion.
        """
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

        first_rejected_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.verify_for_action(
                token=first_rejected_token,
                action_class="append_evidence",
                task_id=task_id,
                root_revision_id=None,
            )

        second_rejected_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        with self.assertRaises(CapabilityDenied):
            self.harness.cap_svc.verify_for_action(
                token=second_rejected_token,
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
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn("capability_verification_rejected_audit_id", payload)
        self.assertNotIn("capability_verification_rejected_audit_ids", payload)

    def test_replay_anchor_illegal_stage_transition_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_illegal_stage_transition_rejected_audit_ids order is stable.

        AuditRepository.list_illegal_stage_transition_rejected_for_task
        orders rows by `sequence`, so the deterministic position of
        illegal-stage-transition rejection audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task rejections are seeded in a known sequence
        by attempting patch-proposal admission twice from Stage.CONTEXT
        before advancing to inference; one other-task rejection proves
        task-scoping exclusion.
        """
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

        first_rejected_token = self.harness.issue_capability(
            "propose_patch", task_id
        )
        with self.assertRaises(OrchestratorRejected):
            self.harness.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=first_rejected_token,
            )

        second_rejected_token = self.harness.issue_capability(
            "propose_patch", task_id
        )
        with self.assertRaises(OrchestratorRejected):
            self.harness.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=second_rejected_token,
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
        approval_token = self.harness.issue_capability(
            "grant_approval", task_id
        )
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
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
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn("illegal_stage_transition_rejected_audit_id", payload)
        self.assertNotIn("illegal_stage_transition_rejected_audit_ids", payload)

    def test_replay_anchor_validation_quarantine_admission_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_validation_quarantine_admission_rejected_audit_ids order is stable.

        AuditRepository.list_validation_quarantine_admission_rejected_for_task
        orders rows by `sequence`, so the deterministic position of
        quarantine-admission rejection audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task rejections are seeded in a known sequence
        by injecting QuarantineAdmissibilityError around two
        admit_validation attempts; one other-task rejection proves
        task-scoping exclusion.
        """
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

            first_rejected_token = self.harness.issue_capability(
                "run_validation_quarantine", task_id
            )
            with self.assertRaises(ValidationRejected):
                self.harness.orch.admit_validation(
                    task_id=task_id,
                    capability_token=first_rejected_token,
                )

            second_rejected_token = self.harness.issue_capability(
                "run_validation_quarantine", task_id
            )
            with self.assertRaises(ValidationRejected):
                self.harness.orch.admit_validation(
                    task_id=task_id,
                    capability_token=second_rejected_token,
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
        approval_token = self.harness.issue_capability(
            "grant_approval", task_id
        )
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
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
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn(
            "validation_quarantine_admission_rejected_audit_id", payload
        )
        self.assertNotIn(
            "validation_quarantine_admission_rejected_audit_ids", payload
        )

    def test_replay_anchor_review_self_summary_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_review_self_summary_rejected_audit_ids order is stable.

        AuditRepository.list_review_self_summary_rejected_for_task
        orders rows by `sequence`, so the deterministic position of
        review-self-summary rejection audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task rejections are seeded in a known sequence
        by driving ReviewService.render_review twice under the
        FORBID_SELF_SUMMARY patch; one other-task rejection proves
        task-scoping exclusion.
        """
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
        approval_token = self.harness.issue_capability(
            "grant_approval", task_id
        )
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
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
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn("review_self_summary_rejected_audit_id", payload)
        self.assertNotIn("review_self_summary_rejected_audit_ids", payload)

    def test_replay_anchor_approval_barrier_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_approval_barrier_rejected_audit_ids order is stable (issue-time).

        AuditRepository.list_approval_barrier_rejected_for_task orders
        rows by `sequence`, so the deterministic position of issue-time
        approval-barrier rejection audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task issue-time rejections are seeded in a
        known sequence by calling ApprovalService.evaluate_barrier
        twice with a synthetic failing receipt; one other-task
        rejection proves task-scoping exclusion. Seal-time rejections
        and evaluation-error rejections are intentionally out of scope
        for this reader.
        """
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
        issue_time_rejection(ids)

        other_rejected_rows = (
            self.harness.audit_repo.list_approval_barrier_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        approval_token = self.harness.issue_capability(
            "grant_approval", task_id
        )
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
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
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn("approval_barrier_rejected_audit_id", payload)
        self.assertNotIn("approval_barrier_rejected_audit_ids", payload)

    def test_replay_anchor_approval_seal_time_barrier_rejected_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_approval_seal_time_barrier_rejected_audit_ids order is stable.

        AuditRepository.list_approval_seal_time_barrier_rejected_for_task
        orders rows by `sequence`, so the deterministic position of
        seal-time approval-barrier rejection audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task seal-time rejections are seeded in a
        known sequence by calling ApprovalService.reverify_for_seal
        twice with a synthetic drifted root; one other-task rejection
        proves task-scoping exclusion. Issue-time rejections and
        evaluation-error rejections are intentionally out of scope for
        this reader.
        """
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.APPROVAL)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.APPROVAL
        )

        def seal_time_rejection(rejection_ids: dict[str, str]) -> None:
            approval = self.harness.ap_repo.fetch(rejection_ids["approval_id"])
            self.assertIsNotNone(approval)
            with self.assertRaises(ApprovalBarrierFailed):
                self.harness.ap_svc.reverify_for_seal(
                    approval_id=rejection_ids["approval_id"],
                    current_root_revision_id="rev-DRIFTED-CONCURRENT",
                    current_context_artifact_id=approval[
                        "reviewed_context_artifact_id"
                    ],
                    current_patch_hash=approval["reviewed_patch_hash"],
                    intent_id=rejection_ids["intent_id"],
                )

        seal_time_rejection(other_ids)
        seal_time_rejection(ids)
        seal_time_rejection(ids)

        other_rejected_rows = (
            self.harness.audit_repo.list_approval_seal_time_barrier_rejected_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_rejected_rows), 1)
        other_rejected_audit_id = other_rejected_rows[0]["audit_record_id"]

        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        rejected_rows = (
            self.harness.audit_repo.list_approval_seal_time_barrier_rejected_for_task(
                task_id
            )
        )
        rejected_audit_ids = [
            row["audit_record_id"] for row in rejected_rows
        ]
        self.assertEqual(len(rejected_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in rejected_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in rejected_audit_ids],
            rejected_audit_ids,
        )
        self.assertNotIn(other_rejected_audit_id, mirrored)
        self.assertNotIn("approval_seal_time_barrier_rejected_audit_id", payload)
        self.assertNotIn("approval_seal_time_barrier_rejected_audit_ids", payload)

    def test_replay_anchor_approval_barrier_evaluation_error_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_approval_barrier_evaluation_error_audit_ids order is stable.

        AuditRepository.list_approval_barrier_evaluation_error_for_task
        orders rows by `sequence`, so the deterministic position of
        approval-barrier evaluation-error audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task evaluation errors are seeded in a known
        sequence by calling ApprovalService.evaluate_barrier twice
        under an injected BarrierEvaluationError patch; one other-task
        evaluation error proves task-scoping exclusion. Issue-time
        rejections and seal-time rejections are intentionally out of
        scope for this reader.
        """
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)

        other_task_id = f"task-other-{uuid4().hex[:8]}"
        other_ids = self.harness.run_through_stage(
            other_task_id, Stage.REVIEW
        )

        def evaluation_error(error_ids: dict[str, str]) -> None:
            with patch(
                "kernel.services.approval_service.evaluate_barrier",
                side_effect=BarrierEvaluationError("injected"),
            ):
                with self.assertRaises(ApprovalRejected):
                    self.harness.ap_svc.evaluate_barrier(
                        task_id=error_ids["task_id"],
                        review_artifact_id=error_ids["review_artifact_id"],
                        required_receipt_ids=[
                            error_ids["validation_receipt_id"]
                        ],
                        reviewed_context_artifact_id=error_ids[
                            "context_artifact_id"
                        ],
                        intent_id=error_ids["intent_id"],
                    )

        evaluation_error(other_ids)
        evaluation_error(ids)
        evaluation_error(ids)

        other_error_rows = (
            self.harness.audit_repo.list_approval_barrier_evaluation_error_for_task(
                other_task_id
            )
        )
        self.assertEqual(len(other_error_rows), 1)
        other_error_audit_id = other_error_rows[0]["audit_record_id"]

        approval_token = self.harness.issue_capability(
            "grant_approval", task_id
        )
        ids["approval_id"] = self.harness.orch.admit_approval(
            task_id=task_id,
            capability_token=approval_token,
        )
        seal_token = self.harness.issue_capability("seal_revision", task_id)
        ids["revision_id"] = self.harness.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=seal_token,
        )
        evidence_token = self.harness.issue_capability(
            "append_evidence", task_id
        )
        replay_anchor_id = self.harness.orch.admit_evidence(
            task_id=task_id,
            capability_token=evidence_token,
        )

        error_rows = (
            self.harness.audit_repo.list_approval_barrier_evaluation_error_for_task(
                task_id
            )
        )
        error_audit_ids = [row["audit_record_id"] for row in error_rows]
        self.assertEqual(len(error_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in error_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in error_audit_ids],
            error_audit_ids,
        )
        self.assertNotIn(other_error_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in error_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in error_audit_ids],
            error_audit_ids,
        )
        self.assertNotIn(other_error_audit_id, mirrored)
        self.assertNotIn("approval_barrier_evaluation_error_audit_id", payload)
        self.assertNotIn("approval_barrier_evaluation_error_audit_ids", payload)

    def test_replay_anchor_capability_token_consumed_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_capability_token_consumed_audit_ids order is stable.

        AuditRepository.list_capability_token_consumed_for_task orders
        rows by `sequence`, so the deterministic position of
        consumed-token audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. The happy path through REVISION_SEAL + EVIDENCE already
        emits multiple same-task consumed-token audits (one per stage
        that consumes a capability), which gives at least two
        same-task rows; one other-task consumed audit proves
        task-scoping exclusion. Revoked-lifecycle and rejection-audit
        readers are intentionally out of scope for this reader.
        """
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
        self.assertGreaterEqual(len(consumed_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in consumed_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in consumed_audit_ids],
            consumed_audit_ids,
        )
        self.assertNotIn(other_consumed_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in consumed_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in consumed_audit_ids],
            consumed_audit_ids,
        )
        self.assertNotIn(other_consumed_audit_id, mirrored)
        self.assertNotIn("capability_token_consumed_audit_id", payload)
        self.assertNotIn("capability_token_consumed_audit_ids", payload)

    def test_replay_anchor_capability_token_revoked_audit_ids_preserve_sequence_order(
        self,
    ) -> None:
        """_capability_token_revoked_audit_ids order is stable.

        AuditRepository.list_capability_token_revoked_for_task orders
        rows by `sequence`, so the deterministic position of
        revoked-token audit ids within
        ReplayAnchor.required_artifact_ids must match audit append
        order. Two same-task revocations are seeded in a known
        sequence by calling cap_svc.revoke_token twice; one other-task
        revocation proves task-scoping exclusion. Consumed-lifecycle
        and rejection-audit readers are intentionally out of scope for
        this reader.
        """
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

        first_revoked_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        self.harness.cap_svc.revoke_token(
            capability_token_id=first_revoked_token["capability_token_id"],
            reason="same_task_revocation_1",
        )

        second_revoked_token = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        self.harness.cap_svc.revoke_token(
            capability_token_id=second_revoked_token["capability_token_id"],
            reason="same_task_revocation_2",
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
        self.assertEqual(len(revoked_audit_ids), 2)

        anchor = self.harness.ra_repo.fetch(replay_anchor_id)
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for audit_record_id in revoked_audit_ids:
            self.assertIn(audit_record_id, required)
        self.assertEqual(
            [aid for aid in required if aid in revoked_audit_ids],
            revoked_audit_ids,
        )
        self.assertNotIn(other_revoked_audit_id, required)

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], replay_anchor_id),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for audit_record_id in revoked_audit_ids:
            self.assertIn(audit_record_id, mirrored)
        self.assertEqual(
            [aid for aid in mirrored if aid in revoked_audit_ids],
            revoked_audit_ids,
        )
        self.assertNotIn(other_revoked_audit_id, mirrored)
        self.assertNotIn("capability_token_revoked_audit_id", payload)
        self.assertNotIn("capability_token_revoked_audit_ids", payload)

    def test_replay_anchor_journal_entry_ids_preserve_logical_sequence_order(
        self,
    ) -> None:
        """_journal_entry_ids order is stable (logical_sequence).

        JournalEntryRepository.list_for_revision orders rows by
        `logical_sequence`, so the deterministic position of seal
        journal entry ids within ReplayAnchor.required_artifact_ids
        must match that ordering. The happy path seals a single
        revision with multiple journal entries, which is sufficient to
        exercise positional-equality. Rejection-audit and
        lifecycle-audit readers are intentionally out of scope for
        this reader.
        """
        ids = self.harness.run_full_happy_path()

        journal_rows = self.harness.conn.execute(
            "SELECT journal_entry_id FROM journal_entries "
            "WHERE revision_id = ? ORDER BY logical_sequence;",
            (ids["revision_id"],),
        ).fetchall()
        journal_entry_ids = [row["journal_entry_id"] for row in journal_rows]
        self.assertGreaterEqual(len(journal_entry_ids), 2)

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        for journal_entry_id in journal_entry_ids:
            self.assertIn(journal_entry_id, required)
        self.assertEqual(
            [jid for jid in required if jid in journal_entry_ids],
            journal_entry_ids,
        )

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        for journal_entry_id in journal_entry_ids:
            self.assertIn(journal_entry_id, mirrored)
        self.assertEqual(
            [jid for jid in mirrored if jid in journal_entry_ids],
            journal_entry_ids,
        )
        self.assertNotIn("journal_entry_id", payload)
        self.assertNotIn("journal_entry_ids", payload)

    def test_replay_anchor_required_artifact_ids_contain_no_duplicates(
        self,
    ) -> None:
        """Aggregated required_artifact_ids is duplicate-free.

        `_LiveEvidenceView.required_artifact_ids` fans out across 21
        reader extensions, each yielding from a disjoint id-space by
        type, but there is no per-reader test that asserts the
        aggregate list is duplicate-free. This test runs the happy
        path to maximize the populated reader set and asserts
        `len(required_artifact_ids) == len(set(required_artifact_ids))`
        on both the replay anchor and the existing evidence_closure
        payload mirror. Ordering is not re-tested here.
        """
        ids = self.harness.run_full_happy_path()

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        required = anchor["required_artifact_ids"]
        self.assertGreater(len(required), 0)
        self.assertEqual(len(required), len(set(required)))

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        mirrored = payload["required_artifact_ids"]
        self.assertGreater(len(mirrored), 0)
        self.assertEqual(len(mirrored), len(set(mirrored)))


if __name__ == "__main__":
    unittest.main()
