"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``validation_receipt_invalidated`` audit record emitted by
``InvalidationService.invalidate_receipt``.

When the caller threads the durable
``intent_anchor_records.intent_id`` into
``InvalidationService.on_new_patch_proposal`` (as
``PatchProposalService.propose`` does from its own ``intent_id``
parameter, which the orchestrator forwards from
``state.intent_anchor.intent_id``), the
``validation_receipt_invalidated`` audit record must name the same id
in both ``artifact_refs`` and ``payload`` so a reviewer reading only
that record can recover the AUDIT-003 / §22.1 linkage without a
second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this service performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly. The cascaded ``approval_invalidated``
record is intentionally not in scope of this increment and is emitted
with its prior shape unchanged.

Driving this through the live ``InvalidationService`` is direct: seed
a stale ``ValidationReceipt`` for a given ``(task_id,
root_revision_id)``, then call ``on_new_patch_proposal`` with a
different ``new_patch_group_hash`` and the test's ``intent_id``. No
patching required.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.services.invalidation_service import (
    InvalidationService,
    REASON_UPSTREAM_PATCH_DRIFT,
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


class TestValidationReceiptInvalidatedNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 parity for ``validation_receipt_invalidated``."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.vr_repo = ValidationReceiptRepository(self.conn)
        self.ap_repo = ApprovalArtifactRepository(self.conn)
        self.drift_repo = DriftEventRecordRepository(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="test_validation_receipt_invalidated_intent_id",
        )
        self.svc = InvalidationService(
            receipt_repo=self.vr_repo,
            approval_repo=self.ap_repo,
            drift_repo=self.drift_repo,
            audit_ledger=self.audit,
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_validation_receipt_invalidated_names_intent_id_when_threaded(
        self,
    ) -> None:
        """An ``on_new_patch_proposal`` call carrying ``intent_id`` must
        emit a ``validation_receipt_invalidated`` audit row whose
        ``payload`` and ``artifact_refs`` both name the threaded
        ``intent_id`` while preserving the prior ``reason`` /
        ``drift_class`` / ``drift_event_id`` / ``source_artifact_id``
        payload fields and the prior ``[validation_receipt_id,
        source_artifact_id]`` refs contribution."""
        task_id = f"task-{uuid4().hex[:8]}"
        intent_id = f"intent-{uuid4().hex[:8]}"
        root = "rev-genesis-000"
        old_hash = "sha256:old-patch"
        new_hash = "sha256:new-patch"
        new_pp = f"pp-{uuid4().hex[:8]}"

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
            intent_id=intent_id,
        )
        self.assertEqual(invalidated, [rid])

        row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'validation_receipt_invalidated' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], intent_id)
        self.assertIn(intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["reason"], REASON_UPSTREAM_PATCH_DRIFT)
        self.assertIn("drift_class", payload)
        self.assertIn("drift_event_id", payload)
        self.assertEqual(payload["source_artifact_id"], new_pp)
        self.assertIn(rid, refs)
        self.assertIn(new_pp, refs)

    def test_absent_intent_id_preserves_prior_audit_shape(self) -> None:
        """An ``on_new_patch_proposal`` call without ``intent_id`` must
        emit a ``validation_receipt_invalidated`` audit row with the
        prior shape exactly: no ``intent_id`` field on ``payload`` and
        no extra entry on ``artifact_refs``."""
        task_id = f"task-{uuid4().hex[:8]}"
        root = "rev-genesis-000"
        old_hash = "sha256:old-patch"
        new_hash = "sha256:new-patch"
        new_pp = f"pp-{uuid4().hex[:8]}"

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

        row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'validation_receipt_invalidated' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertNotIn("intent_id", payload)
        self.assertEqual(refs, [rid, new_pp])


if __name__ == "__main__":
    unittest.main()
