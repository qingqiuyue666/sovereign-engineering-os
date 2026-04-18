"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``approval_invalidated`` cascade audit record emitted by
``InvalidationService._invalidate_approval_cascade``.

When the caller threads the durable
``intent_anchor_records.intent_id`` into
``InvalidationService.on_new_patch_proposal`` (as
``PatchProposalService.propose`` does), ``invalidate_receipt``
forwards ``intent_id`` into ``_invalidate_approval_cascade`` so the
``approval_invalidated`` cascade record names it in both
``artifact_refs`` and ``payload`` — the paired sibling of the
``validation_receipt_invalidated`` coverage landed in the prior
increment.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this service performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly on both records.

Driving this through the live ``InvalidationService`` is direct: seed
a stale ``ValidationReceipt`` and a live ``ApprovalArtifact`` that
references it, then call ``on_new_patch_proposal`` with a different
``new_patch_group_hash`` and the test's ``intent_id``. The cascade
fires deterministically on the single seeded approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.services.invalidation_service import (
    DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE,
    InvalidationService,
    REASON_REQUIRED_RECEIPT_INVALIDATED,
)
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    DriftEventRecordRepository,
    ValidationReceiptRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


def _derive_input_hash(patch_group_hash: str) -> str:
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


class TestApprovalInvalidatedNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 cascade-path parity for ``approval_invalidated``."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.vr_repo = ValidationReceiptRepository(self.conn)
        self.ap_repo = ApprovalArtifactRepository(self.conn)
        self.drift_repo = DriftEventRecordRepository(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="test_approval_invalidated_intent_id",
        )
        self.svc = InvalidationService(
            receipt_repo=self.vr_repo,
            approval_repo=self.ap_repo,
            drift_repo=self.drift_repo,
            audit_ledger=self.audit,
        )

    def tearDown(self) -> None:
        self.conn.close()

    def _seed_stale_receipt_and_live_approval(
        self,
        *,
        task_id: str,
        root: str,
        old_hash: str,
    ) -> tuple[str, str]:
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
            reviewed_context_artifact_id=f"ca-{uuid4().hex[:8]}",
            required_receipt_ids=[rid],
        )
        return rid, ap_id

    def test_approval_invalidated_names_intent_id_when_threaded(self) -> None:
        """An ``on_new_patch_proposal`` call carrying ``intent_id`` must
        cascade to emit an ``approval_invalidated`` audit row whose
        ``payload`` and ``artifact_refs`` both name the threaded
        ``intent_id`` while preserving the prior ``reason`` /
        ``drift_class`` / ``drift_event_id`` / ``invalidating_receipt_id``
        payload fields and the prior ``[approval_id,
        invalidating_receipt_id]`` refs contribution."""
        task_id = f"task-{uuid4().hex[:8]}"
        intent_id = f"intent-{uuid4().hex[:8]}"
        root = "rev-genesis-000"
        old_hash = "sha256:old-patch"
        new_hash = "sha256:new-patch"
        new_pp = f"pp-{uuid4().hex[:8]}"

        rid, ap_id = self._seed_stale_receipt_and_live_approval(
            task_id=task_id, root=root, old_hash=old_hash,
        )

        invalidated = self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash=new_hash,
            new_patch_proposal_id=new_pp,
            intent_id=intent_id,
        )
        self.assertEqual(invalidated, [rid])

        row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'approval_invalidated' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], intent_id)
        self.assertIn(intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["reason"], REASON_REQUIRED_RECEIPT_INVALIDATED)
        self.assertEqual(
            payload["drift_class"], DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE
        )
        self.assertIn("drift_event_id", payload)
        self.assertEqual(payload["invalidating_receipt_id"], rid)
        self.assertIn(ap_id, refs)
        self.assertIn(rid, refs)

    def test_absent_intent_id_preserves_prior_audit_shape(self) -> None:
        """An ``on_new_patch_proposal`` call without ``intent_id`` must
        cascade to emit an ``approval_invalidated`` audit row with the
        prior shape exactly: no ``intent_id`` field on ``payload`` and
        no extra entry on ``artifact_refs``."""
        task_id = f"task-{uuid4().hex[:8]}"
        root = "rev-genesis-000"
        old_hash = "sha256:old-patch"
        new_hash = "sha256:new-patch"
        new_pp = f"pp-{uuid4().hex[:8]}"

        rid, ap_id = self._seed_stale_receipt_and_live_approval(
            task_id=task_id, root=root, old_hash=old_hash,
        )

        invalidated = self.svc.on_new_patch_proposal(
            task_id=task_id,
            root_revision_id=root,
            new_patch_group_hash=new_hash,
            new_patch_proposal_id=new_pp,
        )
        self.assertEqual(invalidated, [rid])

        row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'approval_invalidated' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertNotIn("intent_id", payload)
        self.assertEqual(refs, [ap_id, rid])


if __name__ == "__main__":
    unittest.main()
