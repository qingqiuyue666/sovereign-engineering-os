"""
Tracer-bullet test: bridged real-fix ApprovalArtifact → Revision seal.

Proves that ``RealFixRevisionSealBridge`` takes exactly one
``RealFixApprovalBridgeOutcome`` that already came from the verified
real-fix path and produces exactly one schema-valid ``Revision`` row
(sealed) via ``RevisionSealService.seal_revision``, with an audit
cross-reference that binds the revision and its snapshot root to the
originating ``ApprovalArtifact``, ``ReviewArtifact``,
``ValidationReceipt``, ``PatchProposal``, AND upstream
``InferenceArtifact``. Also proves that every non-admissible input is
rejected fail-closed with no revision row written and no bridge
attestation emitted, and that rows for unrelated task ids are not
touched.

Scope:
- Uses the real ``AnthropicMessagesAdapter`` with a fake transport —
  no network.
- Uses the canonical ``make_add_fix_task`` single-file fix task.
- Uses the real repositories, schemas, and services end-to-end.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import (
    AnthropicMessagesAdapter,
    _TransportResponse,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.real_fix_approval_bridge import (
    RealFixApprovalBridge,
    RealFixApprovalBridgeOutcome,
)
from kernel.lifecycle.real_fix_patch_projector import (
    RealFixPatchProjector,
)
from kernel.lifecycle.real_fix_recorder import (
    RealFixNarrowPathRecord,
    RealFixNarrowPathRecorder,
)
from kernel.lifecycle.real_fix_review_bridge import (
    RealFixReviewBridge,
)
from kernel.lifecycle.real_fix_revision_seal_bridge import (
    RealFixRevisionSealBridge,
    RealFixRevisionSealBridgeOutcome,
    RealFixRevisionSealBridgeRejected,
)
from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridge,
)
from kernel.services.approval_service import ApprovalService
from kernel.services.review_service import ReviewService
from kernel.services.revision_seal_service import RevisionSealService
from kernel.services.validation_service import ValidationService
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    InferenceArtifactRepository,
    JournalEntryRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
    RevisionRepository,
    SnapshotRootRepository,
    ValidationReceiptRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import (
    RealFixTracer,
    make_add_fix_task,
)


CORRECT_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
)


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _messages_body(text: str, model: str = "claude-sonnet-4-5") -> bytes:
    return _json_bytes(
        {
            "id": "msg_fix_seal_bridge_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 24},
        }
    )


class _AuditCapture:
    """Record every ledger append for assertion. Thin passthrough."""

    def __init__(self, ledger: AppendOnlyLedger) -> None:
        self._ledger = ledger
        self.records: list[dict[str, Any]] = []

    def append(
        self,
        *,
        record_type: str,
        task_id: str | None = None,
        root_revision_id: str | None = None,
        artifact_refs=None,
        payload=None,
        **kwargs: Any,
    ) -> None:
        self.records.append(
            {
                "record_type": record_type,
                "task_id": task_id,
                "root_revision_id": root_revision_id,
                "artifact_refs": list(artifact_refs or []),
                "payload": dict(payload or {}),
            }
        )
        self._ledger.append(
            record_type=record_type,
            task_id=task_id,
            root_revision_id=root_revision_id,
            artifact_refs=artifact_refs,
            payload=payload,
            **kwargs,
        )


class RealFixRevisionSealBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.patch_repo = PatchProposalRepository(self.conn)
        self.receipt_repo = ValidationReceiptRepository(self.conn)
        self.review_repo = ReviewArtifactRepository(self.conn)
        self.approval_repo = ApprovalArtifactRepository(self.conn)
        self.revision_repo = RevisionRepository(self.conn)
        self.snapshot_repo = SnapshotRootRepository(self.conn)
        self.journal_repo = JournalEntryRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_revision_seal_bridge_test",
        )
        self.audit = _AuditCapture(self.ledger)
        self.recorder = RealFixNarrowPathRecorder(
            repository=self.inference_repo,
            audit_ledger=self.audit,
        )
        self.projector = RealFixPatchProjector(
            repository=self.patch_repo,
            audit_ledger=self.audit,
        )
        self.validation_service = ValidationService(
            repository=self.receipt_repo,
            patch_reader=self.patch_repo,
            audit_ledger=self.audit,
        )
        self.validation_bridge = RealFixValidationBridge(
            validation_service=self.validation_service,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.audit,
        )
        self.review_service = ReviewService(
            repository=self.review_repo,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.audit,
        )
        self.review_bridge = RealFixReviewBridge(
            review_service=self.review_service,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            review_reader=self.review_repo,
            audit_ledger=self.audit,
        )
        self.approval_service = ApprovalService(
            repository=self.approval_repo,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            review_reader=self.review_repo,
            audit_ledger=self.audit,
        )
        self.approval_bridge = RealFixApprovalBridge(
            approval_service=self.approval_service,
            review_reader=self.review_repo,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            inference_reader=self.inference_repo,
            approval_reader=self.approval_repo,
            audit_ledger=self.audit,
        )
        self.seal_service = RevisionSealService(
            revision_repo=self.revision_repo,
            snapshot_repo=self.snapshot_repo,
            journal_repo=self.journal_repo,
            approval_repo=self.approval_repo,
            patch_reader=self.patch_repo,
            approval_service=self.approval_service,
            audit_ledger=self.audit,
        )
        self.seal_bridge = RealFixRevisionSealBridge(
            seal_service=self.seal_service,
            approval_reader=self.approval_repo,
            review_reader=self.review_repo,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            inference_reader=self.inference_repo,
            revision_reader=self.revision_repo,
            audit_ledger=self.audit,
        )

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------

    def _tracer(self, transport) -> RealFixTracer:
        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=transport)
        return RealFixTracer(
            adapter=adapter,
            audit_ledger=self.audit,
            narrow_path_recorder=self.recorder,
        )

    def _count(self, table: str) -> int:
        return self.conn.execute(
            f"SELECT COUNT(*) FROM {table};"
        ).fetchone()[0]

    def _records_of(self, record_type: str) -> list[dict[str, Any]]:
        return [r for r in self.audit.records if r["record_type"] == record_type]

    def _bridge_to_approval(self, task_id: str) -> RealFixApprovalBridgeOutcome:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        tracer = self._tracer(t)
        result = tracer.run(task)
        self.assertTrue(result.verified)
        inf = self.inference_repo.fetch(result.inference_artifact_id)
        self.assertIsNotNone(inf)
        record = RealFixNarrowPathRecord(
            inference_artifact_id=result.inference_artifact_id,
            context_artifact_id=inf["context_artifact_id"],
            root_revision_id=inf["root_revision_id"],
            output_hash=inf["output_hash"],
            replay_ceiling=result.replay_ceiling,
        )
        projection = self.projector.project(task=task, result=result, record=record)
        vb_outcome = self.validation_bridge.bridge(projection=projection)
        rb_outcome = self.review_bridge.bridge(outcome=vb_outcome)
        return self.approval_bridge.bridge(outcome=rb_outcome)

    # ------------------------------------------------------------------
    # Success: bridged approval → exactly one schema-valid sealed revision
    # ------------------------------------------------------------------

    def test_bridge_produces_one_sealed_revision_linked_to_all_sides(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)

        outcome = self.seal_bridge.bridge(
            outcome=ap_outcome,
            intent_id=f"real-fix::intent::{task_id}",
        )

        self.assertIsInstance(outcome, RealFixRevisionSealBridgeOutcome)
        self.assertTrue(outcome.revision_id.startswith("rev-"))
        self.assertTrue(outcome.snapshot_root_id.startswith("snap-"))
        self.assertEqual(
            outcome.approval_artifact_id, ap_outcome.approval_artifact_id
        )
        self.assertEqual(outcome.review_artifact_id, ap_outcome.review_artifact_id)
        self.assertEqual(
            outcome.validation_receipt_id, ap_outcome.validation_receipt_id
        )
        self.assertEqual(outcome.patch_proposal_id, ap_outcome.patch_proposal_id)
        self.assertEqual(
            outcome.inference_artifact_id, ap_outcome.inference_artifact_id
        )
        self.assertEqual(outcome.context_artifact_id, ap_outcome.context_artifact_id)
        self.assertEqual(outcome.task_id, task_id)
        self.assertEqual(outcome.root_revision_id, ap_outcome.root_revision_id)

        # Exactly one revision row, sealed, bound to the approval.
        self.assertEqual(self._count("revisions"), 1)
        revision = self.revision_repo.fetch(outcome.revision_id)
        self.assertIsNotNone(revision)
        self.assertEqual(revision["state"], "sealed")
        self.assertEqual(revision["task_id"], task_id)
        self.assertEqual(revision["approval_id"], ap_outcome.approval_artifact_id)
        self.assertEqual(
            revision["originating_context_artifact_id"],
            ap_outcome.context_artifact_id,
        )
        self.assertEqual(revision["snapshot_root_id"], outcome.snapshot_root_id)
        self.assertIsNotNone(revision["sealed_at"])

        # Exactly one snapshot root, bound to the revision.
        self.assertEqual(self._count("snapshot_roots"), 1)

        # Exactly one bridge attestation audit event, carrying all seven ids.
        attested = self._records_of("real_fix_revision_seal_bridge_attested")
        self.assertEqual(len(attested), 1)
        a = attested[0]
        self.assertEqual(a["task_id"], task_id)
        self.assertEqual(a["root_revision_id"], ap_outcome.root_revision_id)
        self.assertEqual(
            sorted(a["artifact_refs"]),
            sorted(
                [
                    outcome.revision_id,
                    outcome.snapshot_root_id,
                    ap_outcome.approval_artifact_id,
                    ap_outcome.review_artifact_id,
                    ap_outcome.validation_receipt_id,
                    ap_outcome.patch_proposal_id,
                    ap_outcome.inference_artifact_id,
                ]
            ),
        )
        self.assertEqual(a["payload"]["revision_id"], outcome.revision_id)
        self.assertEqual(
            a["payload"]["snapshot_root_id"], outcome.snapshot_root_id
        )
        self.assertEqual(
            a["payload"]["approval_artifact_id"], ap_outcome.approval_artifact_id
        )
        self.assertEqual(
            a["payload"]["review_artifact_id"], ap_outcome.review_artifact_id
        )
        self.assertEqual(
            a["payload"]["validation_receipt_id"],
            ap_outcome.validation_receipt_id,
        )
        self.assertEqual(
            a["payload"]["patch_proposal_id"], ap_outcome.patch_proposal_id
        )
        self.assertEqual(
            a["payload"]["inference_artifact_id"],
            ap_outcome.inference_artifact_id,
        )
        self.assertEqual(
            a["payload"]["context_artifact_id"], ap_outcome.context_artifact_id
        )
        self.assertEqual(a["payload"]["revision_state"], "sealed")
        self.assertEqual(a["payload"]["source"], "real_fix_tracer")

    def test_bridge_audit_chain_is_complete(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        self.seal_bridge.bridge(
            outcome=ap_outcome,
            intent_id=f"real-fix::intent::{task_id}",
        )

        # A reviewer can walk the end-to-end chain from a single
        # ordered audit trail: tracer → inference row → verified pass →
        # patch proposal → validation receipt → validation bridge →
        # review artifact → review bridge → approval artifact →
        # approval bridge → revision sealed → seal bridge attestation.
        types = [r["record_type"] for r in self.audit.records]
        self.assertEqual(
            types,
            [
                "real_fix_attempt_started",
                "inference_artifact_created",
                "real_fix_verified_pass",
                "patch_proposal_created",
                "validation_receipt_created",
                "real_fix_validation_bridge_attested",
                "review_artifact_created",
                "real_fix_review_bridge_attested",
                "approval_artifact_issued",
                "real_fix_approval_bridge_attested",
                "revision_sealed",
                "real_fix_revision_seal_bridge_attested",
            ],
        )

    # ------------------------------------------------------------------
    # Fail-closed: non-admissible inputs must not produce a sealed revision
    # ------------------------------------------------------------------

    def test_bridge_rejects_wrong_outcome_type(self) -> None:
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome="not-an-outcome")  # type: ignore[arg-type]
        self.assertEqual(self._count("revisions"), 0)
        self.assertEqual(
            self._records_of("real_fix_revision_seal_bridge_attested"), []
        )

    def _tamper(
        self, base: RealFixApprovalBridgeOutcome, **overrides: Any
    ) -> RealFixApprovalBridgeOutcome:
        return RealFixApprovalBridgeOutcome(
            approval_artifact_id=overrides.get(
                "approval_artifact_id", base.approval_artifact_id
            ),
            review_artifact_id=overrides.get(
                "review_artifact_id", base.review_artifact_id
            ),
            validation_receipt_id=overrides.get(
                "validation_receipt_id", base.validation_receipt_id
            ),
            patch_proposal_id=overrides.get(
                "patch_proposal_id", base.patch_proposal_id
            ),
            inference_artifact_id=overrides.get(
                "inference_artifact_id", base.inference_artifact_id
            ),
            context_artifact_id=overrides.get(
                "context_artifact_id", base.context_artifact_id
            ),
            task_id=overrides.get("task_id", base.task_id),
            root_revision_id=overrides.get(
                "root_revision_id", base.root_revision_id
            ),
        )

    def test_bridge_refuses_unknown_approval_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        tampered = self._tamper(
            ap_outcome, approval_artifact_id="ap-does-not-exist"
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=tampered)
        self.assertEqual(self._count("revisions"), 0)
        self.assertEqual(
            self._records_of("real_fix_revision_seal_bridge_attested"), []
        )

    def test_bridge_refuses_mismatched_task_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        tampered = self._tamper(ap_outcome, task_id="fix-other-task")
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=tampered)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_mismatched_root_revision_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        tampered = self._tamper(
            ap_outcome, root_revision_id="real-fix::root::forged"
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=tampered)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_mismatched_context_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        tampered = self._tamper(ap_outcome, context_artifact_id="ctx-forged")
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=tampered)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_non_approved_approval_state(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        self.approval_repo.mark_state(
            approval_id=ap_outcome.approval_artifact_id,
            new_state="pending",
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=ap_outcome)
        self.assertEqual(self._count("revisions"), 0)
        self.assertEqual(
            self._records_of("real_fix_revision_seal_bridge_attested"), []
        )

    def test_bridge_refuses_invalidated_approval(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        self.assertTrue(
            self.approval_repo.mark_invalidated(
                approval_id=ap_outcome.approval_artifact_id,
                invalidation_reason="test_invalidation",
            )
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=ap_outcome)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_invalidated_receipt(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        self.assertTrue(
            self.receipt_repo.mark_invalidated(
                validation_receipt_id=ap_outcome.validation_receipt_id,
                invalidation_reason="test_invalidation",
            )
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=ap_outcome)
        self.assertEqual(self._count("revisions"), 0)
        self.assertEqual(
            self._records_of("real_fix_revision_seal_bridge_attested"), []
        )

    def test_bridge_refuses_mismatched_required_receipt_ids(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        # Rewrite the persisted approval's required_receipt_ids so it no
        # longer matches the single-receipt narrow-path shape.
        self.conn.execute(
            "UPDATE approval_artifacts SET required_receipt_ids = ? "
            "WHERE approval_id = ?;",
            (
                json.dumps(
                    [ap_outcome.validation_receipt_id, "vr-extra"]
                ),
                ap_outcome.approval_artifact_id,
            ),
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=ap_outcome)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_mismatched_review_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        tampered = self._tamper(
            ap_outcome, review_artifact_id="rv-does-not-exist"
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=tampered)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_mismatched_inference_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        tampered = self._tamper(
            ap_outcome, inference_artifact_id="inf-tampered"
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=tampered)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_missing_inference_row(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        self.conn.execute(
            "DELETE FROM inference_artifacts WHERE inference_artifact_id = ?;",
            (ap_outcome.inference_artifact_id,),
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=ap_outcome)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_refuses_non_realfix_target_file_label(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        self.conn.execute(
            "UPDATE patch_proposals SET target_file_ids = ? "
            "WHERE patch_proposal_id = ?;",
            (
                json.dumps(["not-a-real-fix-label.py"]),
                ap_outcome.patch_proposal_id,
            ),
        )
        with self.assertRaises(RealFixRevisionSealBridgeRejected):
            self.seal_bridge.bridge(outcome=ap_outcome)
        self.assertEqual(self._count("revisions"), 0)

    def test_bridge_does_not_touch_unrelated_rows(self) -> None:
        # Bridge two independent real-fix runs to approvals. Only
        # seal-bridge the first. The second's rows must be untouched:
        # no revision for them, and no seal-bridge attestation naming
        # them.
        first_task = f"fix-{uuid4().hex[:8]}"
        second_task = f"fix-{uuid4().hex[:8]}"
        ap_a = self._bridge_to_approval(first_task)
        ap_b = self._bridge_to_approval(second_task)

        self.seal_bridge.bridge(
            outcome=ap_a,
            intent_id=f"real-fix::intent::{first_task}",
        )

        # Exactly one revision row exists, and it is bound to task A.
        self.assertEqual(self._count("revisions"), 1)
        rows = self.conn.execute(
            "SELECT task_id FROM revisions;"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [first_task])

        # Approval, review, receipt, patch, and inference rows for task B
        # remain intact.
        self.assertIsNotNone(self.approval_repo.fetch(ap_b.approval_artifact_id))
        self.assertIsNotNone(self.review_repo.fetch(ap_b.review_artifact_id))
        self.assertIsNotNone(
            self.receipt_repo.fetch(ap_b.validation_receipt_id)
        )
        self.assertIsNotNone(self.patch_repo.fetch(ap_b.patch_proposal_id))
        self.assertIsNotNone(
            self.inference_repo.fetch(ap_b.inference_artifact_id)
        )

        attested = self._records_of("real_fix_revision_seal_bridge_attested")
        self.assertEqual(len(attested), 1)
        self.assertEqual(attested[0]["task_id"], first_task)
        self.assertNotIn(ap_b.approval_artifact_id, attested[0]["artifact_refs"])
        self.assertNotIn(ap_b.review_artifact_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            ap_b.validation_receipt_id, attested[0]["artifact_refs"]
        )
        self.assertNotIn(ap_b.patch_proposal_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            ap_b.inference_artifact_id, attested[0]["artifact_refs"]
        )


if __name__ == "__main__":
    unittest.main()
