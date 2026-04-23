"""
Tracer-bullet test: bridged real-fix sealed Revision → ReplayAnchor closure.

Proves that ``RealFixEvidenceClosureBridge`` takes exactly one
``RealFixRevisionSealBridgeOutcome`` that already came from the verified
real-fix path and produces exactly one schema-valid ``ReplayAnchor`` row
via ``EvidenceService.close_evidence``, with an audit cross-reference
that binds the replay anchor to the originating ``Revision``,
``SnapshotRoot``, ``ApprovalArtifact``, ``ReviewArtifact``,
``ValidationReceipt``, ``PatchProposal``, AND upstream
``InferenceArtifact`` (plus ``context_artifact_id``). Also proves that
every non-admissible input is rejected fail-closed with no replay anchor
row written by the bridge and no bridge attestation emitted, and that
the service's own ``evidence_closure`` audit record is preserved
unchanged on the success path.

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
)
from kernel.lifecycle.real_fix_evidence_closure_bridge import (
    RealFixEvidenceClosureBridge,
    RealFixEvidenceClosureBridgeOutcome,
    RealFixEvidenceClosureBridgeRejected,
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
)
from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridge,
)
from kernel.services.approval_service import ApprovalService
from kernel.services.evidence_service import EvidenceService
from kernel.services.review_service import ReviewService
from kernel.services.revision_seal_service import RevisionSealService
from kernel.services.validation_service import ValidationService
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
    JournalEntryRepository,
    PatchProposalRepository,
    ReplayAnchorRepository,
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
            "id": "msg_fix_evidence_bridge_test",
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


class RealFixEvidenceClosureBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.context_repo = ContextArtifactRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.patch_repo = PatchProposalRepository(self.conn)
        self.receipt_repo = ValidationReceiptRepository(self.conn)
        self.review_repo = ReviewArtifactRepository(self.conn)
        self.approval_repo = ApprovalArtifactRepository(self.conn)
        self.revision_repo = RevisionRepository(self.conn)
        self.snapshot_repo = SnapshotRootRepository(self.conn)
        self.journal_repo = JournalEntryRepository(self.conn)
        self.replay_anchor_repo = ReplayAnchorRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_evidence_closure_bridge_test",
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
        self.evidence_service = EvidenceService(
            replay_anchor_repo=self.replay_anchor_repo,
            revision_repo=self.revision_repo,
            context_repo=self.context_repo,
            inference_repo=self.inference_repo,
            audit_repo=self.audit_repo,
            audit_ledger=self.audit,
        )
        self.evidence_bridge = RealFixEvidenceClosureBridge(
            evidence_service=self.evidence_service,
            revision_reader=self.revision_repo,
            snapshot_reader=self.snapshot_repo,
            approval_reader=self.approval_repo,
            review_reader=self.review_repo,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            inference_reader=self.inference_repo,
            replay_anchor_reader=self.replay_anchor_repo,
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

    def _bridge_to_seal(self, task_id: str) -> RealFixRevisionSealBridgeOutcome:
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
        ap_outcome = self.approval_bridge.bridge(outcome=rb_outcome)
        return self.seal_bridge.bridge(
            outcome=ap_outcome,
            intent_id=f"real-fix::intent::{task_id}",
        )

    # ------------------------------------------------------------------
    # Success: bridged sealed revision → exactly one schema-valid ReplayAnchor
    # ------------------------------------------------------------------

    def test_bridge_produces_one_replay_anchor_linked_to_all_sides(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)

        outcome = self.evidence_bridge.bridge(outcome=seal_outcome)

        self.assertIsInstance(outcome, RealFixEvidenceClosureBridgeOutcome)
        self.assertTrue(outcome.replay_anchor_id.startswith("ra-"))
        self.assertEqual(outcome.revision_id, seal_outcome.revision_id)
        self.assertEqual(outcome.snapshot_root_id, seal_outcome.snapshot_root_id)
        self.assertEqual(
            outcome.approval_artifact_id, seal_outcome.approval_artifact_id
        )
        self.assertEqual(outcome.review_artifact_id, seal_outcome.review_artifact_id)
        self.assertEqual(
            outcome.validation_receipt_id, seal_outcome.validation_receipt_id
        )
        self.assertEqual(outcome.patch_proposal_id, seal_outcome.patch_proposal_id)
        self.assertEqual(
            outcome.inference_artifact_id, seal_outcome.inference_artifact_id
        )
        self.assertEqual(
            outcome.context_artifact_id, seal_outcome.context_artifact_id
        )
        self.assertEqual(outcome.task_id, task_id)
        self.assertEqual(outcome.root_revision_id, seal_outcome.root_revision_id)

        # Exactly one replay anchor row, bound to the task and the sealed
        # revision id surface.
        self.assertEqual(self._count("replay_anchors"), 1)
        anchor = self.replay_anchor_repo.fetch(outcome.replay_anchor_id)
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor["task_id"], task_id)
        self.assertEqual(anchor["root_revision_id"], seal_outcome.revision_id)

        # The existing EvidenceService's own evidence_closure audit record
        # is preserved unchanged: one per successful closure, carrying the
        # anchor and revision ids.
        closures = self._records_of("evidence_closure")
        self.assertEqual(len(closures), 1)
        self.assertEqual(closures[0]["task_id"], task_id)
        self.assertIn(outcome.replay_anchor_id, closures[0]["artifact_refs"])
        self.assertIn(outcome.revision_id, closures[0]["artifact_refs"])

        # Exactly one bridge attestation audit event, carrying all eight ids
        # plus the originating durable ``intent_anchor_records.intent_id``
        # (AUDIT-003 / §22.1): a reviewer reading only this attestation can
        # recover the originating intent-anchor id without a second fetch
        # on ``revisions.intent_id``.
        attested = self._records_of("real_fix_evidence_closure_bridge_attested")
        self.assertEqual(len(attested), 1)
        a = attested[0]
        self.assertEqual(a["task_id"], task_id)
        self.assertEqual(a["root_revision_id"], seal_outcome.root_revision_id)
        expected_intent_id = f"real-fix::intent::{task_id}"
        self.assertEqual(
            sorted(a["artifact_refs"]),
            sorted(
                [
                    outcome.replay_anchor_id,
                    seal_outcome.revision_id,
                    seal_outcome.snapshot_root_id,
                    seal_outcome.approval_artifact_id,
                    seal_outcome.review_artifact_id,
                    seal_outcome.validation_receipt_id,
                    seal_outcome.patch_proposal_id,
                    seal_outcome.inference_artifact_id,
                    expected_intent_id,
                ]
            ),
        )
        self.assertEqual(
            a["payload"]["replay_anchor_id"], outcome.replay_anchor_id
        )
        self.assertEqual(a["payload"]["revision_id"], seal_outcome.revision_id)
        self.assertEqual(
            a["payload"]["snapshot_root_id"], seal_outcome.snapshot_root_id
        )
        self.assertEqual(
            a["payload"]["approval_artifact_id"],
            seal_outcome.approval_artifact_id,
        )
        self.assertEqual(
            a["payload"]["review_artifact_id"], seal_outcome.review_artifact_id
        )
        self.assertEqual(
            a["payload"]["validation_receipt_id"],
            seal_outcome.validation_receipt_id,
        )
        self.assertEqual(
            a["payload"]["patch_proposal_id"], seal_outcome.patch_proposal_id
        )
        self.assertEqual(
            a["payload"]["inference_artifact_id"],
            seal_outcome.inference_artifact_id,
        )
        self.assertEqual(
            a["payload"]["context_artifact_id"],
            seal_outcome.context_artifact_id,
        )
        self.assertEqual(
            a["payload"]["originating_root_revision_id"],
            seal_outcome.root_revision_id,
        )
        self.assertEqual(
            a["payload"]["anchor_root_revision_id"], seal_outcome.revision_id
        )
        self.assertEqual(a["payload"]["intent_id"], expected_intent_id)
        self.assertEqual(a["payload"]["source"], "real_fix_tracer")

    def test_bridge_audit_chain_is_complete(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.evidence_bridge.bridge(outcome=seal_outcome)

        # A reviewer can walk the end-to-end chain from a single ordered
        # audit trail: tracer → inference row → verified pass → patch
        # proposal → validation receipt → validation bridge → review
        # artifact → review bridge → approval artifact → approval bridge
        # → revision sealed → seal bridge → evidence closure → evidence
        # closure bridge attestation.
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
                "evidence_closure",
                "real_fix_evidence_closure_bridge_attested",
            ],
        )

    # ------------------------------------------------------------------
    # Fail-closed: non-admissible inputs must not produce a replay anchor
    # ------------------------------------------------------------------

    def test_bridge_rejects_wrong_outcome_type(self) -> None:
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome="not-an-outcome")  # type: ignore[arg-type]
        self.assertEqual(self._count("replay_anchors"), 0)
        self.assertEqual(
            self._records_of("real_fix_evidence_closure_bridge_attested"), []
        )

    def _tamper(
        self, base: RealFixRevisionSealBridgeOutcome, **overrides: Any
    ) -> RealFixRevisionSealBridgeOutcome:
        return RealFixRevisionSealBridgeOutcome(
            revision_id=overrides.get("revision_id", base.revision_id),
            snapshot_root_id=overrides.get(
                "snapshot_root_id", base.snapshot_root_id
            ),
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

    def _anchors_before(self) -> int:
        return self._count("replay_anchors")

    def _assert_no_anchor_and_no_attestation(self, prior: int) -> None:
        self.assertEqual(self._count("replay_anchors"), prior)
        self.assertEqual(
            self._records_of("real_fix_evidence_closure_bridge_attested"), []
        )

    def test_bridge_refuses_unknown_revision_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(seal_outcome, revision_id="rev-does-not-exist")
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_non_sealed_revision_state(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        # Forcibly flip the persisted state to 'pending' to simulate a
        # non-sealed row. Because the append-only triggers protect sealed
        # rows, we insert a pending ghost and point the outcome at it.
        ghost_rev_id = "rev-ghost-pending"
        self.revision_repo.insert_pending(
            {
                "revision_id": ghost_rev_id,
                "parent_revision_id": None,
                "project_id": "phase1_default",
                "task_id": seal_outcome.task_id,
                "root_hash": "sha256:ghost",
                "snapshot_root_id": seal_outcome.snapshot_root_id,
                "intent_id": "intent-ghost",
                "originating_context_artifact_id": seal_outcome.context_artifact_id,
                "approval_id": seal_outcome.approval_artifact_id,
                "logical_sequence_at_seal": 0,
                "version_tuple_hash": "vth:ghost",
                "taint_set": [],
                "created_at": "2025-01-01T00:00:00+00:00",
            }
        )
        tampered = self._tamper(seal_outcome, revision_id=ghost_rev_id)
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_task_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(seal_outcome, task_id="fix-other-task")
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_approval_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(
            seal_outcome, approval_artifact_id="ap-does-not-exist"
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_context_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(seal_outcome, context_artifact_id="ctx-forged")
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_snapshot_root_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(
            seal_outcome, snapshot_root_id="snap-does-not-exist"
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_non_approved_approval_state(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.approval_repo.mark_state(
            approval_id=seal_outcome.approval_artifact_id,
            new_state="pending",
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=seal_outcome)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_invalidated_approval(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.assertTrue(
            self.approval_repo.mark_invalidated(
                approval_id=seal_outcome.approval_artifact_id,
                invalidation_reason="test_invalidation",
            )
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=seal_outcome)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_invalidated_receipt(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.assertTrue(
            self.receipt_repo.mark_invalidated(
                validation_receipt_id=seal_outcome.validation_receipt_id,
                invalidation_reason="test_invalidation",
            )
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=seal_outcome)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_required_receipt_ids(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.conn.execute(
            "UPDATE approval_artifacts SET required_receipt_ids = ? "
            "WHERE approval_id = ?;",
            (
                json.dumps(
                    [seal_outcome.validation_receipt_id, "vr-extra"]
                ),
                seal_outcome.approval_artifact_id,
            ),
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=seal_outcome)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_review_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(
            seal_outcome, review_artifact_id="rv-does-not-exist"
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_mismatched_inference_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        tampered = self._tamper(
            seal_outcome, inference_artifact_id="inf-tampered"
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=tampered)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_missing_inference_row(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.conn.execute(
            "DELETE FROM inference_artifacts WHERE inference_artifact_id = ?;",
            (seal_outcome.inference_artifact_id,),
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=seal_outcome)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_refuses_non_realfix_target_file_label(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        seal_outcome = self._bridge_to_seal(task_id)
        self.conn.execute(
            "UPDATE patch_proposals SET target_file_ids = ? "
            "WHERE patch_proposal_id = ?;",
            (
                json.dumps(["not-a-real-fix-label.py"]),
                seal_outcome.patch_proposal_id,
            ),
        )
        prior = self._anchors_before()
        with self.assertRaises(RealFixEvidenceClosureBridgeRejected):
            self.evidence_bridge.bridge(outcome=seal_outcome)
        self._assert_no_anchor_and_no_attestation(prior)

    def test_bridge_does_not_touch_unrelated_rows(self) -> None:
        # Bridge two independent real-fix runs through to sealed
        # revisions. Only close-evidence the first. The second's rows
        # must be untouched: no replay anchor for them, and no
        # closure-bridge attestation naming them.
        first_task = f"fix-{uuid4().hex[:8]}"
        second_task = f"fix-{uuid4().hex[:8]}"
        seal_a = self._bridge_to_seal(first_task)
        seal_b = self._bridge_to_seal(second_task)

        self.evidence_bridge.bridge(outcome=seal_a)

        # Exactly one replay anchor row exists, and it is bound to task A.
        self.assertEqual(self._count("replay_anchors"), 1)
        rows = self.conn.execute(
            "SELECT task_id FROM replay_anchors;"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [first_task])

        # Revision, snapshot, approval, review, receipt, patch, and
        # inference rows for task B remain intact.
        self.assertIsNotNone(self.revision_repo.fetch(seal_b.revision_id))
        self.assertIsNotNone(self.snapshot_repo.fetch(seal_b.snapshot_root_id))
        self.assertIsNotNone(self.approval_repo.fetch(seal_b.approval_artifact_id))
        self.assertIsNotNone(self.review_repo.fetch(seal_b.review_artifact_id))
        self.assertIsNotNone(
            self.receipt_repo.fetch(seal_b.validation_receipt_id)
        )
        self.assertIsNotNone(self.patch_repo.fetch(seal_b.patch_proposal_id))
        self.assertIsNotNone(
            self.inference_repo.fetch(seal_b.inference_artifact_id)
        )

        attested = self._records_of("real_fix_evidence_closure_bridge_attested")
        self.assertEqual(len(attested), 1)
        self.assertEqual(attested[0]["task_id"], first_task)
        self.assertNotIn(seal_b.revision_id, attested[0]["artifact_refs"])
        self.assertNotIn(seal_b.snapshot_root_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            seal_b.approval_artifact_id, attested[0]["artifact_refs"]
        )
        self.assertNotIn(seal_b.review_artifact_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            seal_b.validation_receipt_id, attested[0]["artifact_refs"]
        )
        self.assertNotIn(seal_b.patch_proposal_id, attested[0]["artifact_refs"])
        self.assertNotIn(
            seal_b.inference_artifact_id, attested[0]["artifact_refs"]
        )


if __name__ == "__main__":
    unittest.main()
