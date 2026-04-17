"""
Tracer-bullet test: bridged real-fix ReviewArtifact → ApprovalArtifact.

Proves that ``RealFixApprovalBridge`` takes exactly one
``RealFixReviewBridgeOutcome`` that already came from the verified
real-fix path and produces exactly one schema-valid ``ApprovalArtifact``,
with an audit cross-reference that binds the approval to the
originating ``ReviewArtifact``, ``ValidationReceipt``, ``PatchProposal``,
AND the upstream ``InferenceArtifact``. Also proves that every
non-admissible input is rejected fail-closed with no approval row
written and no bridge attestation emitted, and that rows for unrelated
task ids are not touched.

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
    RealFixApprovalBridgeRejected,
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
    RealFixReviewBridgeOutcome,
)
from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridge,
    RealFixValidationBridgeOutcome,
)
from kernel.services.approval_service import ApprovalService
from kernel.services.review_service import ReviewService
from kernel.services.validation_service import ValidationService
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
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
            "id": "msg_fix_approval_bridge_test",
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


class RealFixApprovalBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.patch_repo = PatchProposalRepository(self.conn)
        self.receipt_repo = ValidationReceiptRepository(self.conn)
        self.review_repo = ReviewArtifactRepository(self.conn)
        self.approval_repo = ApprovalArtifactRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_approval_bridge_test",
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

    def _bridge_to_review(self, task_id: str) -> RealFixReviewBridgeOutcome:
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
        return self.review_bridge.bridge(outcome=vb_outcome)

    # ------------------------------------------------------------------
    # Success: bridged review → exactly one schema-valid approval
    # ------------------------------------------------------------------

    def test_bridge_produces_one_schema_valid_approval_linked_to_all_sides(
        self,
    ) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        outcome = self.approval_bridge.bridge(
            outcome=rb_outcome,
            intent_id=f"real-fix::intent::{task_id}",
        )

        self.assertIsInstance(outcome, RealFixApprovalBridgeOutcome)
        self.assertTrue(outcome.approval_artifact_id.startswith("ap-"))
        self.assertEqual(outcome.review_artifact_id, rb_outcome.review_artifact_id)
        self.assertEqual(
            outcome.validation_receipt_id, rb_outcome.validation_receipt_id
        )
        self.assertEqual(outcome.patch_proposal_id, rb_outcome.patch_proposal_id)
        self.assertEqual(
            outcome.inference_artifact_id, rb_outcome.inference_artifact_id
        )
        self.assertEqual(outcome.task_id, task_id)
        self.assertEqual(outcome.root_revision_id, rb_outcome.root_revision_id)

        # Exactly one approval row, in state 'approved'.
        self.assertEqual(self._count("approval_artifacts"), 1)
        approval = self.approval_repo.fetch(outcome.approval_artifact_id)
        self.assertIsNotNone(approval)
        self.assertEqual(approval["task_id"], task_id)
        self.assertEqual(
            approval["originating_root_revision_id"], rb_outcome.root_revision_id
        )
        self.assertEqual(approval["approval_state"], "approved")
        self.assertEqual(
            approval["required_receipt_ids"],
            [rb_outcome.validation_receipt_id],
        )
        self.assertEqual(
            approval["reviewed_context_artifact_id"], outcome.context_artifact_id
        )

        # Causal linkage: approval's reviewed_patch_hash comes from the
        # upstream patch proposal. Transitive linkage to the originating
        # InferenceArtifact is preserved via PatchProposal.inference_artifact_id.
        patch_row = self.patch_repo.fetch(rb_outcome.patch_proposal_id)
        self.assertIsNotNone(patch_row)
        self.assertEqual(
            approval["reviewed_patch_hash"], patch_row["patch_group_hash"]
        )
        self.assertEqual(
            patch_row["inference_artifact_id"], rb_outcome.inference_artifact_id
        )

        # Exactly one bridge attestation audit event, carrying all five
        # upstream ids plus the originating durable intent-anchor id
        # (AUDIT-003 / §22.1): a reviewer reading only this record can
        # recover the originating ``intent_anchor_records.intent_id``
        # without a second fetch.
        expected_intent_id = f"real-fix::intent::{task_id}"
        attested = self._records_of("real_fix_approval_bridge_attested")
        self.assertEqual(len(attested), 1)
        a = attested[0]
        self.assertEqual(a["task_id"], task_id)
        self.assertEqual(a["root_revision_id"], rb_outcome.root_revision_id)
        self.assertEqual(
            sorted(a["artifact_refs"]),
            sorted(
                [
                    outcome.approval_artifact_id,
                    rb_outcome.review_artifact_id,
                    rb_outcome.validation_receipt_id,
                    rb_outcome.patch_proposal_id,
                    rb_outcome.inference_artifact_id,
                    expected_intent_id,
                ]
            ),
        )
        self.assertIn(expected_intent_id, a["artifact_refs"])
        self.assertEqual(
            a["payload"]["approval_artifact_id"], outcome.approval_artifact_id
        )
        self.assertEqual(
            a["payload"]["review_artifact_id"], rb_outcome.review_artifact_id
        )
        self.assertEqual(
            a["payload"]["validation_receipt_id"],
            rb_outcome.validation_receipt_id,
        )
        self.assertEqual(
            a["payload"]["patch_proposal_id"], rb_outcome.patch_proposal_id
        )
        self.assertEqual(
            a["payload"]["inference_artifact_id"],
            rb_outcome.inference_artifact_id,
        )
        self.assertEqual(
            a["payload"]["reviewed_context_artifact_id"],
            outcome.context_artifact_id,
        )
        self.assertEqual(a["payload"]["intent_id"], expected_intent_id)
        self.assertEqual(a["payload"]["approval_state"], "approved")
        self.assertEqual(a["payload"]["source"], "real_fix_tracer")

    def test_bridge_audit_chain_is_complete(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)
        self.approval_bridge.bridge(outcome=rb_outcome)

        # A reviewer can walk the end-to-end chain from a single
        # ordered audit trail: tracer → inference row → verified pass →
        # patch proposal created → validation receipt created →
        # validation bridge attestation → review artifact created →
        # review bridge attestation → approval artifact issued →
        # approval bridge attestation.
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
            ],
        )

    # ------------------------------------------------------------------
    # Fail-closed: non-admissible inputs must not produce an approval row
    # ------------------------------------------------------------------

    def test_bridge_rejects_wrong_outcome_type(self) -> None:
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome="not-an-outcome")  # type: ignore[arg-type]
        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_unknown_review_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id="rv-does-not-exist",
            validation_receipt_id=rb_outcome.validation_receipt_id,
            patch_proposal_id=rb_outcome.patch_proposal_id,
            inference_artifact_id=rb_outcome.inference_artifact_id,
            task_id=rb_outcome.task_id,
            root_revision_id=rb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )
        self.assertEqual(self._records_of("approval_artifact_issued"), [])

    def test_bridge_refuses_mismatched_task_id_on_review(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id=rb_outcome.review_artifact_id,
            validation_receipt_id=rb_outcome.validation_receipt_id,
            patch_proposal_id=rb_outcome.patch_proposal_id,
            inference_artifact_id=rb_outcome.inference_artifact_id,
            task_id="fix-other-task",
            root_revision_id=rb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_mismatched_root_revision_id_on_review(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id=rb_outcome.review_artifact_id,
            validation_receipt_id=rb_outcome.validation_receipt_id,
            patch_proposal_id=rb_outcome.patch_proposal_id,
            inference_artifact_id=rb_outcome.inference_artifact_id,
            task_id=rb_outcome.task_id,
            root_revision_id="real-fix::root::forged",
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_mismatched_patch_proposal_on_review(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id=rb_outcome.review_artifact_id,
            validation_receipt_id=rb_outcome.validation_receipt_id,
            patch_proposal_id="pp-forged",
            inference_artifact_id=rb_outcome.inference_artifact_id,
            task_id=rb_outcome.task_id,
            root_revision_id=rb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_unknown_validation_receipt_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id=rb_outcome.review_artifact_id,
            validation_receipt_id="vr-does-not-exist",
            patch_proposal_id=rb_outcome.patch_proposal_id,
            inference_artifact_id=rb_outcome.inference_artifact_id,
            task_id=rb_outcome.task_id,
            root_revision_id=rb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_invalidated_receipt(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        # Simulate an upstream drift consequence: the receipt was
        # invalidated after review was rendered. The approval bridge
        # must re-check and refuse fail-closed.
        self.assertTrue(
            self.receipt_repo.mark_invalidated(
                validation_receipt_id=rb_outcome.validation_receipt_id,
                invalidation_reason="test_invalidation",
            )
        )

        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=rb_outcome)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )
        self.assertEqual(self._records_of("approval_artifact_issued"), [])

    def test_bridge_refuses_mismatched_inference_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id=rb_outcome.review_artifact_id,
            validation_receipt_id=rb_outcome.validation_receipt_id,
            patch_proposal_id=rb_outcome.patch_proposal_id,
            inference_artifact_id="inf-tampered",
            task_id=rb_outcome.task_id,
            root_revision_id=rb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_unknown_patch_proposal_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        # Rewrite the review row's patch_proposal_id to something that
        # doesn't exist, keeping the outcome consistent with the review
        # row. The patch fetch then fails.
        bogus_pp = "pp-does-not-exist"
        self.conn.execute(
            "UPDATE review_artifacts SET patch_proposal_id = ? "
            "WHERE review_artifact_id = ?;",
            (bogus_pp, rb_outcome.review_artifact_id),
        )
        tampered = RealFixReviewBridgeOutcome(
            review_artifact_id=rb_outcome.review_artifact_id,
            validation_receipt_id=rb_outcome.validation_receipt_id,
            patch_proposal_id=bogus_pp,
            inference_artifact_id=rb_outcome.inference_artifact_id,
            task_id=rb_outcome.task_id,
            root_revision_id=rb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_non_realfix_target_file_label(self) -> None:
        # Tamper the persisted patch row so its target label is no
        # longer the real-fix narrow-path synthetic id. Every other
        # identity still matches, but the bridge must refuse.
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        self.conn.execute(
            "UPDATE patch_proposals SET target_file_ids = ? "
            "WHERE patch_proposal_id = ?;",
            (json.dumps(["not-a-real-fix-label.py"]), rb_outcome.patch_proposal_id),
        )

        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=rb_outcome)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_refuses_missing_inference_row(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        rb_outcome = self._bridge_to_review(task_id)

        # Drop the inference row after review was rendered. The
        # approval bridge must refuse because it cannot resolve the
        # reviewed_context_artifact_id.
        self.conn.execute(
            "DELETE FROM inference_artifacts WHERE inference_artifact_id = ?;",
            (rb_outcome.inference_artifact_id,),
        )

        with self.assertRaises(RealFixApprovalBridgeRejected):
            self.approval_bridge.bridge(outcome=rb_outcome)

        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_approval_bridge_attested"), []
        )

    def test_bridge_does_not_touch_unrelated_rows(self) -> None:
        # Bridge two independent real-fix runs to reviews. Only
        # approval-bridge the first. The second's review, receipt,
        # patch, and inference rows must be untouched: no approval for
        # them, and no bridge attestation naming them.
        first_task = f"fix-{uuid4().hex[:8]}"
        second_task = f"fix-{uuid4().hex[:8]}"
        rb_a = self._bridge_to_review(first_task)
        rb_b = self._bridge_to_review(second_task)

        self.approval_bridge.bridge(outcome=rb_a)

        # Exactly one approval row exists, and it is bound to task A.
        self.assertEqual(self._count("approval_artifacts"), 1)
        rows = self.conn.execute(
            "SELECT task_id FROM approval_artifacts;"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [first_task])

        # Review, receipt, patch, and inference rows for task B remain intact.
        self.assertIsNotNone(self.review_repo.fetch(rb_b.review_artifact_id))
        self.assertIsNotNone(
            self.receipt_repo.fetch(rb_b.validation_receipt_id)
        )
        self.assertIsNotNone(self.patch_repo.fetch(rb_b.patch_proposal_id))
        self.assertIsNotNone(
            self.inference_repo.fetch(rb_b.inference_artifact_id)
        )

        attested = self._records_of("real_fix_approval_bridge_attested")
        self.assertEqual(len(attested), 1)
        self.assertEqual(attested[0]["task_id"], first_task)
        self.assertNotIn(rb_b.review_artifact_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            rb_b.validation_receipt_id, attested[0]["artifact_refs"]
        )
        self.assertNotIn(rb_b.patch_proposal_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            rb_b.inference_artifact_id, attested[0]["artifact_refs"]
        )


if __name__ == "__main__":
    unittest.main()
