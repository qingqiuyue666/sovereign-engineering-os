"""
AT-017: Incremental invalidation (phase-1 minimum honest scope).

Constitutional anchors:
- v11 Section 22.3 Atomic Approval Barrier (drift consequence invalidation)
- v11 Section 23.7 ValidationReceipt (`invalidated_at`, `invalidation_reason`)
- v11 Section 23.11 ApprovalArtifact (`approval_state='invalidated'`)
- v11 Section 23.19 DriftEventRecord
- v11 Section 24.1 AT-017 (incremental invalidation behavior)
- v11 Section 24.2 INV-017 (stale artifacts cannot silently remain admissible)
- Foundation Section 9 (AT-017 / INV-017 marked adjacent hardening,
  implemented here at phase-1 minimum honest scope)

What this test proves:
  The narrow signable path's minimum honest invalidation surface
  actually marks and enforces invalidation when governing upstream
  inputs drift:

  Case A (upstream patch drift -> receipt invalidation):
    When a new PatchProposal is persisted for the same
    (task_id, root_revision_id) whose patch_group_hash derives to a
    different input_hash than an existing live ValidationReceipt's
    input_hash, that receipt is marked invalidated_at / invalidation_reason
    and a DriftEventRecord is emitted.

  Case B (receipt invalidation -> approval cascade):
    When a ValidationReceipt is marked invalidated, every live
    ApprovalArtifact whose required_receipt_ids includes it is marked
    invalidated (approval_state='invalidated') and a DriftEventRecord is
    emitted.

  Idempotency:
    Re-invalidating the same receipt (or re-running on_new_patch_proposal
    with no new drift) MUST NOT duplicate audit/drift evidence.

  No-op safety:
    A new proposal whose derived input_hash matches an existing live
    receipt MUST NOT touch that receipt.

  Barrier integration:
    An approval invalidated by cascade fails the seal-time barrier
    (REASON_RECEIPT_INVALIDATED), matching the §22.3 rule set.
"""

from __future__ import annotations

import hashlib
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    DriftEventRecordRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ValidationReceiptRepository,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.services.invalidation_service import (
    CONSEQUENCE_APPROVAL_INVALIDATED,
    CONSEQUENCE_RECEIPT_INVALIDATED,
    DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE,
    DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
    InvalidationService,
    REASON_REQUIRED_RECEIPT_INVALIDATED,
    REASON_UPSTREAM_PATCH_DRIFT,
)
from kernel.services.patch_proposal_service import (
    PatchProposalRequest,
    PatchProposalService,
)
from kernel.contracts.barrier_rules import (
    BarrierInputs,
    REASON_RECEIPT_INVALIDATED,
    evaluate_barrier,
)


def _derive_input_hash(patch_group_hash: str) -> str:
    """Mirror ValidationService / InvalidationService derivation."""
    return "sha256:" + hashlib.sha256(patch_group_hash.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_receipt(
    repo: ValidationReceiptRepository,
    *,
    task_id: str,
    root_revision_id: str,
    patch_group_hash: str,
) -> str:
    """Insert a minimum viable ValidationReceipt row for a test subject."""
    rid = f"vr-{uuid4().hex[:8]}"
    repo.insert(
        {
            "validation_receipt_id": rid,
            "task_id": task_id,
            "root_revision_id": root_revision_id,
            "receipt_type": "phase1_static_quarantine",
            "validator_identity": "phase1_static_validator",
            "validator_version": "phase1-slice1",
            "input_hash": _derive_input_hash(patch_group_hash),
            "result": "pass",
            "diagnostics_hash": "sha256:deadbeef",
            "taint_set": [],
            "created_at": _now_iso(),
            "version_tuple_hash": "vt:test",
        }
    )
    return rid


def _seed_approval(
    repo: ApprovalArtifactRepository,
    *,
    task_id: str,
    root_revision_id: str,
    reviewed_patch_hash: str,
    reviewed_context_artifact_id: str,
    required_receipt_ids: list[str],
) -> str:
    ap_id = f"ap-{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    repo.insert(
        {
            "approval_id": ap_id,
            "task_id": task_id,
            "originating_root_revision_id": root_revision_id,
            "reviewed_patch_hash": reviewed_patch_hash,
            "reviewed_context_artifact_id": reviewed_context_artifact_id,
            "required_receipt_ids": list(required_receipt_ids),
            "approval_scope": "phase1_narrow_path_single_file",
            "approver_identity": "kernel:phase1",
            "approval_state": "approved",
            "policy_version": "phase1_approval_policy_v1",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "version_tuple_hash": "vt:test",
        }
    )
    return ap_id


class TestIncrementalInvalidation(unittest.TestCase):
    """AT-017 / INV-017: incremental invalidation (phase-1 minimum scope)."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.vr_repo = ValidationReceiptRepository(self.conn)
        self.ap_repo = ApprovalArtifactRepository(self.conn)
        self.drift_repo = DriftEventRecordRepository(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="test_at_017"
        )
        self.svc = InvalidationService(
            receipt_repo=self.vr_repo,
            approval_repo=self.ap_repo,
            drift_repo=self.drift_repo,
            audit_ledger=self.audit,
        )

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Case A: upstream patch drift -> receipt invalidation
    # ------------------------------------------------------------------

    def test_upstream_patch_drift_invalidates_receipt(self) -> None:
        task_id = "task-A"
        root = "rev-R1"
        old_hash = "sha256:old-patch"
        new_hash = "sha256:new-patch"
        new_pp = "pp-new"

        rid = _seed_receipt(
            self.vr_repo,
            task_id=task_id,
            root_revision_id=root,
            patch_group_hash=old_hash,
        )

        invalidated = self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash=new_hash,
            new_patch_proposal_id=new_pp,
        )

        self.assertEqual(invalidated, [rid])
        receipt = self.vr_repo.fetch(rid)
        self.assertIsNotNone(receipt["invalidated_at"])
        self.assertEqual(
            receipt["invalidation_reason"], REASON_UPSTREAM_PATCH_DRIFT
        )

        # DriftEventRecord emitted with correct class/consequence.
        drift_rows = self.conn.execute(
            "SELECT * FROM drift_event_records WHERE task_id = ?;", (task_id,)
        ).fetchall()
        self.assertEqual(len(drift_rows), 1)
        self.assertEqual(drift_rows[0]["drift_class"], DRIFT_CLASS_UPSTREAM_PATCH_DRIFT)
        self.assertEqual(
            drift_rows[0]["consequence_class"], CONSEQUENCE_RECEIPT_INVALIDATED
        )

        # AuditRecord appended.
        audit_rows = self.conn.execute(
            "SELECT record_type FROM audit_records WHERE task_id = ?;", (task_id,)
        ).fetchall()
        types = [r["record_type"] for r in audit_rows]
        self.assertIn("validation_receipt_invalidated", types)

    def test_same_hash_is_noop(self) -> None:
        """A proposal matching an existing receipt's hash must NOT invalidate."""
        task_id = "task-noop"
        root = "rev-R1"
        hash_x = "sha256:same"
        rid = _seed_receipt(
            self.vr_repo,
            task_id=task_id,
            root_revision_id=root,
            patch_group_hash=hash_x,
        )
        invalidated = self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash=hash_x,
            new_patch_proposal_id="pp-x",
        )
        self.assertEqual(invalidated, [])
        receipt = self.vr_repo.fetch(rid)
        self.assertIsNone(receipt["invalidated_at"])
        drift_rows = self.conn.execute(
            "SELECT COUNT(*) FROM drift_event_records WHERE task_id = ?;",
            (task_id,),
        ).fetchone()
        self.assertEqual(drift_rows[0], 0)

    def test_scoped_to_task_and_root(self) -> None:
        """Receipts bound to a different task or root MUST NOT be touched."""
        rid_other_task = _seed_receipt(
            self.vr_repo,
            task_id="task-other",
            root_revision_id="rev-R1",
            patch_group_hash="sha256:old",
        )
        rid_other_root = _seed_receipt(
            self.vr_repo,
            task_id="task-A",
            root_revision_id="rev-R2",
            patch_group_hash="sha256:old",
        )
        self.svc.on_new_patch_proposal(
            task_id="task-A",
            root_revision_id="rev-R1",
            new_patch_group_hash="sha256:new",
            new_patch_proposal_id="pp-new",
        )
        self.assertIsNone(self.vr_repo.fetch(rid_other_task)["invalidated_at"])
        self.assertIsNone(self.vr_repo.fetch(rid_other_root)["invalidated_at"])

    # ------------------------------------------------------------------
    # Case B: receipt invalidation -> approval cascade
    # ------------------------------------------------------------------

    def test_approval_cascade_on_receipt_invalidation(self) -> None:
        task_id = "task-B"
        root = "rev-R1"
        old_hash = "sha256:old-patch"
        new_hash = "sha256:new-patch"

        rid = _seed_receipt(
            self.vr_repo,
            task_id=task_id,
            root_revision_id=root,
            patch_group_hash=old_hash,
        )
        ap_id = _seed_approval(
            self.ap_repo,
            task_id=task_id,
            root_revision_id=root,
            reviewed_patch_hash=old_hash,
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=[rid],
        )

        self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash=new_hash,
            new_patch_proposal_id="pp-2",
        )

        approval = self.ap_repo.fetch(ap_id)
        self.assertEqual(approval["approval_state"], "invalidated")
        self.assertIsNotNone(approval["invalidated_at"])
        self.assertEqual(
            approval["invalidation_reason"], REASON_REQUIRED_RECEIPT_INVALIDATED
        )

        # Two drift records: one for the receipt, one for the approval cascade.
        drift_classes = [
            r["drift_class"]
            for r in self.conn.execute(
                "SELECT drift_class FROM drift_event_records WHERE task_id = ?;",
                (task_id,),
            ).fetchall()
        ]
        self.assertIn(DRIFT_CLASS_UPSTREAM_PATCH_DRIFT, drift_classes)
        self.assertIn(DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE, drift_classes)

        # Drift record for the approval must carry consequence=approval_invalidated.
        cascade_row = self.conn.execute(
            """
            SELECT consequence_class, approval_id
              FROM drift_event_records
             WHERE task_id = ? AND drift_class = ?;
            """,
            (task_id, DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE),
        ).fetchone()
        self.assertEqual(
            cascade_row["consequence_class"], CONSEQUENCE_APPROVAL_INVALIDATED
        )
        self.assertEqual(cascade_row["approval_id"], ap_id)

        # AuditRecord for approval_invalidated must reference approval_id.
        audit_row = self.conn.execute(
            "SELECT approval_id FROM audit_records WHERE record_type = 'approval_invalidated';"
        ).fetchone()
        self.assertEqual(audit_row["approval_id"], ap_id)

    def test_cascade_invalidated_approval_fails_barrier(self) -> None:
        """An invalidated approval's receipt fails §22.3 at seal time."""
        task_id = "task-C"
        root = "rev-R1"
        rid = _seed_receipt(
            self.vr_repo,
            task_id=task_id,
            root_revision_id=root,
            patch_group_hash="sha256:old",
        )
        _seed_approval(
            self.ap_repo,
            task_id=task_id,
            root_revision_id=root,
            reviewed_patch_hash="sha256:old",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=[rid],
        )
        self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash="sha256:new",
            new_patch_proposal_id="pp-new",
        )
        # Receipt is now invalidated; feed it back through the §22.3
        # barrier rule set exactly as the seal-time reverify would.
        receipt = self.vr_repo.fetch(rid)
        now = datetime.now(timezone.utc)
        inputs = BarrierInputs(
            approval_id="ap-any",
            approval_state="approved",
            approval_policy_version="phase1_approval_policy_v1",
            originating_root_revision_id=root,
            reviewed_patch_hash="sha256:old",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=[rid],
            approval_expires_at=(now + timedelta(hours=1)).isoformat(),
            current_root_revision_id=root,
            current_context_artifact_id="ctx-1",
            current_patch_hash="sha256:old",
            current_policy_version="phase1_approval_policy_v1",
            receipts_live={rid: receipt},
            task_superseded=False,
            now_iso=now.isoformat(),
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, REASON_RECEIPT_INVALIDATED)

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_idempotent_second_call_emits_no_new_evidence(self) -> None:
        task_id = "task-D"
        root = "rev-R1"
        rid = _seed_receipt(
            self.vr_repo,
            task_id=task_id,
            root_revision_id=root,
            patch_group_hash="sha256:old",
        )
        ap_id = _seed_approval(
            self.ap_repo,
            task_id=task_id,
            root_revision_id=root,
            reviewed_patch_hash="sha256:old",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=[rid],
        )
        self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash="sha256:new",
            new_patch_proposal_id="pp-new",
        )
        drifts_first = self.conn.execute(
            "SELECT COUNT(*) FROM drift_event_records WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        audits_first = self.conn.execute(
            """
            SELECT COUNT(*) FROM audit_records
             WHERE task_id = ?
               AND record_type IN
                 ('validation_receipt_invalidated','approval_invalidated');
            """,
            (task_id,),
        ).fetchone()[0]

        # Second call on already-drifted state: no new rows.
        self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash="sha256:new",
            new_patch_proposal_id="pp-new",
        )
        drifts_second = self.conn.execute(
            "SELECT COUNT(*) FROM drift_event_records WHERE task_id = ?;",
            (task_id,),
        ).fetchone()[0]
        audits_second = self.conn.execute(
            """
            SELECT COUNT(*) FROM audit_records
             WHERE task_id = ?
               AND record_type IN
                 ('validation_receipt_invalidated','approval_invalidated');
            """,
            (task_id,),
        ).fetchone()[0]
        self.assertEqual(drifts_first, drifts_second)
        self.assertEqual(audits_first, audits_second)

        # The approval remains invalidated exactly once.
        approval = self.ap_repo.fetch(ap_id)
        self.assertEqual(approval["approval_state"], "invalidated")


class TestPatchProposalServiceTriggersInvalidation(unittest.TestCase):
    """Prove the PatchProposalService wire-in actually enforces Case A."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.pp_repo = PatchProposalRepository(self.conn)
        self.vr_repo = ValidationReceiptRepository(self.conn)
        self.ap_repo = ApprovalArtifactRepository(self.conn)
        self.drift_repo = DriftEventRecordRepository(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inf_repo = InferenceArtifactRepository(self.conn)

        self.audit = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="test_at_017_wired"
        )
        self.inval = InvalidationService(
            receipt_repo=self.vr_repo,
            approval_repo=self.ap_repo,
            drift_repo=self.drift_repo,
            audit_ledger=self.audit,
        )
        self.pp_svc = PatchProposalService(
            repository=self.pp_repo,
            inference_reader=self.inf_repo,
            audit_ledger=self.audit,
            invalidation_service=self.inval,
        )

    def tearDown(self) -> None:
        self.conn.close()

    def _seed_inference(self, task_id: str, root: str) -> str:
        inf_id = f"inf-{uuid4().hex[:8]}"
        self.inf_repo.insert(
            {
                "inference_artifact_id": inf_id,
                "task_id": task_id,
                "root_revision_id": root,
                "context_artifact_id": "ctx-1",
                "worker_run_id": "wr-1",
                "worker_profile": "tp",
                "model_route_id": "mr-1",
                "output_hash": "sha256:out",
                "provenance_refs": [],
                "taint_set": [],
                "created_at": _now_iso(),
                "version_tuple_hash": "vt:test",
            }
        )
        return inf_id

    def test_new_proposal_invalidates_stale_receipt(self) -> None:
        task_id = "task-wired"
        root = "rev-R1"
        inf_id = self._seed_inference(task_id, root)

        # First proposal: define the initial patch_group_hash.
        pp1 = self.pp_svc.propose(
            task_id=task_id,
            inference_artifact_id=inf_id,
            request=PatchProposalRequest(
                target_file_ids=("src/a.py",),
                patch_body_hash="sha256:body-v1",
            ),
        )
        proposal1 = self.pp_repo.fetch(pp1)
        # Seed a receipt pinned to this first proposal's patch_group_hash.
        rid = _seed_receipt(
            self.vr_repo,
            task_id=task_id,
            root_revision_id=root,
            patch_group_hash=proposal1["patch_group_hash"],
        )

        # Now persist a NEW proposal with a different patch body hash.
        self.pp_svc.propose(
            task_id=task_id,
            inference_artifact_id=inf_id,
            request=PatchProposalRequest(
                target_file_ids=("src/a.py",),
                patch_body_hash="sha256:body-v2",
            ),
        )

        receipt = self.vr_repo.fetch(rid)
        self.assertIsNotNone(receipt["invalidated_at"])
        self.assertEqual(
            receipt["invalidation_reason"], REASON_UPSTREAM_PATCH_DRIFT
        )


if __name__ == "__main__":
    unittest.main()
