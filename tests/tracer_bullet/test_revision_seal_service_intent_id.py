"""
Tracer-bullet test: ``RevisionSealService.seal_revision`` fails closed
when no originating ``intent_id`` is supplied.

Proves that the seal service no longer silently fabricates an
``intent-<task_id>`` label when the caller omits ``intent_id``.  The
§22.1 precondition is that "a valid originating intent exists" before
the seal transaction runs.  Both production callers (the eight-stage
``admit_revision_seal`` and the real-fix ``run_real_fix_chain``) already
supply the durable ``intent_anchor_records.intent_id`` they minted at
intent emission (PRs #27 and #28); this test pins that contract at the
service's own surface so any future direct caller that forgets the
argument is rejected fail-closed rather than producing a Revision whose
``intent_id`` references no durable row.

Scope:
- Exercises ``RevisionSealService.seal_revision`` directly through the
  real-fix approval-bridge path (so the approval / review / receipt /
  patch / inference rows the service reads all exist and are admissible).
- Uses the real ``AnthropicMessagesAdapter`` with a fake transport — no
  network.
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
from kernel.lifecycle.real_fix_patch_projector import RealFixPatchProjector
from kernel.lifecycle.real_fix_recorder import (
    RealFixNarrowPathRecord,
    RealFixNarrowPathRecorder,
)
from kernel.lifecycle.real_fix_review_bridge import RealFixReviewBridge
from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridge,
)
from kernel.services.approval_service import ApprovalService
from kernel.services.review_service import ReviewService
from kernel.services.revision_seal_service import (
    RevisionSealService,
    SealRejected,
)
from kernel.services.validation_service import ValidationService
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    InferenceArtifactRepository,
    IntentAnchorRepository,
    JournalEntryRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
    RevisionRepository,
    SnapshotRootRepository,
    ValidationReceiptRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import RealFixTracer, make_add_fix_task


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
            "id": "msg_seal_intent_id_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 24},
        }
    )


class _AuditCapture:
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


class RevisionSealServiceIntentIdFailClosedTest(unittest.TestCase):
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
            actor_identity="revision_seal_service_intent_id_test",
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
        self.intent_anchor_repo = IntentAnchorRepository(self.conn)
        self.seal_service = RevisionSealService(
            revision_repo=self.revision_repo,
            snapshot_repo=self.snapshot_repo,
            journal_repo=self.journal_repo,
            approval_repo=self.approval_repo,
            patch_reader=self.patch_repo,
            approval_service=self.approval_service,
            audit_ledger=self.audit,
            intent_anchor_reader=self.intent_anchor_repo,
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

    def _bridge_to_approval(
        self, task_id: str
    ) -> RealFixApprovalBridgeOutcome:
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
        projection = self.projector.project(
            task=task, result=result, record=record
        )
        vb_outcome = self.validation_bridge.bridge(projection=projection)
        rb_outcome = self.review_bridge.bridge(outcome=vb_outcome)
        return self.approval_bridge.bridge(outcome=rb_outcome)

    # ------------------------------------------------------------------
    # Fail-closed: seal_revision refuses when intent_id is missing
    # ------------------------------------------------------------------

    def _assert_no_seal_side_effects(self) -> None:
        self.assertEqual(self._count("revisions"), 0)
        self.assertEqual(self._count("snapshot_roots"), 0)
        # journal_entries has no seal_prepare / seal_mutation / seal_confirmed
        # rows — the service aborts before step 2.
        rows = self.conn.execute(
            "SELECT entry_type FROM journal_entries;"
        ).fetchall()
        for r in rows:
            self.assertNotIn(
                r[0],
                ("seal_prepare", "seal_mutation", "seal_confirmed"),
            )
        self.assertEqual(self._records_of("revision_sealed"), [])

    def test_seal_revision_rejects_missing_intent_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)

        with self.assertRaises(SealRejected) as raised:
            self.seal_service.seal_revision(
                task_id=ap_outcome.task_id,
                approval_id=ap_outcome.approval_artifact_id,
                context_artifact_id=ap_outcome.context_artifact_id,
                intent_id=None,
            )
        self.assertIn("intent_id", str(raised.exception))
        self._assert_no_seal_side_effects()

    def test_seal_revision_rejects_empty_intent_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)

        with self.assertRaises(SealRejected):
            self.seal_service.seal_revision(
                task_id=ap_outcome.task_id,
                approval_id=ap_outcome.approval_artifact_id,
                context_artifact_id=ap_outcome.context_artifact_id,
                intent_id="",
            )
        self._assert_no_seal_side_effects()

    def test_seal_revision_rejects_whitespace_only_intent_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)

        with self.assertRaises(SealRejected):
            self.seal_service.seal_revision(
                task_id=ap_outcome.task_id,
                approval_id=ap_outcome.approval_artifact_id,
                context_artifact_id=ap_outcome.context_artifact_id,
                intent_id="   ",
            )
        self._assert_no_seal_side_effects()

    def test_seal_revision_accepts_explicit_intent_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        intent_id = f"real-fix::intent::{task_id}"
        # The durable ``intent_anchor_records`` row must exist before
        # the seal (AUDIT-003 / §22.1). Both production callers
        # mint this row at intent emission; the test mirrors that
        # production sequence explicitly.
        self.intent_anchor_repo.insert(
            intent_id=intent_id, task_id=task_id, state="admitted"
        )

        revision_id = self.seal_service.seal_revision(
            task_id=ap_outcome.task_id,
            approval_id=ap_outcome.approval_artifact_id,
            context_artifact_id=ap_outcome.context_artifact_id,
            intent_id=intent_id,
        )
        self.assertTrue(revision_id.startswith("rev-"))
        self.assertEqual(self._count("revisions"), 1)
        revision = self.revision_repo.fetch(revision_id)
        self.assertIsNotNone(revision)
        self.assertEqual(revision["state"], "sealed")
        self.assertEqual(revision["intent_id"], intent_id)
        # No silently-fabricated ``intent-<task_id>`` label written.
        self.assertNotEqual(revision["intent_id"], f"intent-{task_id}")

        # AUDIT-003 / §22.1: the authority-bearing ``revision_sealed``
        # audit record names the durable ``intent_id`` in both
        # ``artifact_refs`` and ``payload`` so a reviewer reading only
        # this one record can recover the originating intent-anchor id
        # without a second fetch on ``revisions.intent_id``.
        sealed_records = self._records_of("revision_sealed")
        self.assertEqual(len(sealed_records), 1)
        sealed = sealed_records[0]
        self.assertEqual(sealed["payload"]["intent_id"], intent_id)
        self.assertIn(intent_id, sealed["artifact_refs"])

    # ------------------------------------------------------------------
    # Fail-closed: seal_revision refuses when intent_id names no durable
    # intent_anchor_records row, or resolves to a row whose task_id does
    # not match the seal's task_id (AUDIT-003 / §22.1).
    # ------------------------------------------------------------------

    def test_seal_revision_rejects_unknown_intent_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        # Intentionally do NOT insert a matching anchor row: the
        # supplied label is non-empty but names no durable row.
        unknown_intent_id = f"real-fix::intent::{task_id}"

        with self.assertRaises(SealRejected) as raised:
            self.seal_service.seal_revision(
                task_id=ap_outcome.task_id,
                approval_id=ap_outcome.approval_artifact_id,
                context_artifact_id=ap_outcome.context_artifact_id,
                intent_id=unknown_intent_id,
            )
        self.assertIn("intent_anchor_records", str(raised.exception))
        self._assert_no_seal_side_effects()

    def test_seal_revision_rejects_task_id_mismatch_on_anchor_row(
        self,
    ) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        ap_outcome = self._bridge_to_approval(task_id)
        other_task_id = f"fix-{uuid4().hex[:8]}"
        intent_id = f"real-fix::intent::{other_task_id}"
        # Durable row exists but is bound to a different task_id than
        # the one being sealed: must be refused.
        self.intent_anchor_repo.insert(
            intent_id=intent_id,
            task_id=other_task_id,
            state="admitted",
        )

        with self.assertRaises(SealRejected) as raised:
            self.seal_service.seal_revision(
                task_id=ap_outcome.task_id,
                approval_id=ap_outcome.approval_artifact_id,
                context_artifact_id=ap_outcome.context_artifact_id,
                intent_id=intent_id,
            )
        self.assertIn("task_id", str(raised.exception))
        self._assert_no_seal_side_effects()


if __name__ == "__main__":
    unittest.main()
