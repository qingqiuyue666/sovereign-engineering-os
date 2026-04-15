"""
Tracer-bullet test: SignablePathOrchestrator.run_real_fix_chain end-to-end.

Proves that the orchestrator wires the already-merged real-fix bridge
chain in the correct causal order exactly once per verified-pass
tracer run:

    RealFixTracer.run
        -> RealFixNarrowPathRecorder.record    (via tracer injection)
        -> RealFixPatchProjector.project
        -> RealFixValidationBridge.bridge
        -> RealFixReviewBridge.bridge
        -> RealFixApprovalBridge.bridge
        -> RealFixRevisionSealBridge.bridge
        -> RealFixEvidenceClosureBridge.bridge
        -> orchestrator wrapper `real_fix_chain_completed` audit

Also proves fail-closed refusal when required wirings are missing and
when the caller tries to overlay the real-fix chain on a task_id that
has already entered the eight-stage signable-path frame. The existing
eight-stage admission surface is not changed.
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
from kernel.lifecycle.real_fix_approval_bridge import RealFixApprovalBridge
from kernel.lifecycle.real_fix_evidence_closure_bridge import (
    RealFixEvidenceClosureBridge,
    RealFixEvidenceClosureBridgeOutcome,
)
from kernel.lifecycle.real_fix_patch_projector import RealFixPatchProjector
from kernel.lifecycle.real_fix_recorder import RealFixNarrowPathRecorder
from kernel.lifecycle.real_fix_review_bridge import RealFixReviewBridge
from kernel.lifecycle.real_fix_revision_seal_bridge import (
    RealFixRevisionSealBridge,
)
from kernel.lifecycle.real_fix_validation_bridge import RealFixValidationBridge
from kernel.lifecycle.signable_path_orchestrator import (
    RealFixChainRejected,
    SignablePathOrchestrator,
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
from kernel.tracers.real_fix_tracer import RealFixTracer, make_add_fix_task


CORRECT_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
)

BROKEN_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a - b\n"
    "```\n"
)


def _messages_body(text: str, model: str = "claude-sonnet-4-5") -> bytes:
    return json.dumps(
        {
            "id": "msg_orch_real_fix_chain_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 18},
        }
    ).encode("utf-8")


class _Unreachable:
    """Any attribute access is a test failure — these services must not be touched."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"unexpected service call: {name}")


class SignablePathOrchestratorRealFixChainTest(unittest.TestCase):
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
            actor_identity="orchestrator_real_fix_chain_test",
        )
        self.recorder = RealFixNarrowPathRecorder(
            repository=self.inference_repo,
            audit_ledger=self.ledger,
        )
        self.projector = RealFixPatchProjector(
            repository=self.patch_repo,
            audit_ledger=self.ledger,
        )
        self.validation_service = ValidationService(
            repository=self.receipt_repo,
            patch_reader=self.patch_repo,
            audit_ledger=self.ledger,
        )
        self.validation_bridge = RealFixValidationBridge(
            validation_service=self.validation_service,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.ledger,
        )
        self.review_service = ReviewService(
            repository=self.review_repo,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.ledger,
        )
        self.review_bridge = RealFixReviewBridge(
            review_service=self.review_service,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            review_reader=self.review_repo,
            audit_ledger=self.ledger,
        )
        self.approval_service = ApprovalService(
            repository=self.approval_repo,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            review_reader=self.review_repo,
            audit_ledger=self.ledger,
        )
        self.approval_bridge = RealFixApprovalBridge(
            approval_service=self.approval_service,
            review_reader=self.review_repo,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            inference_reader=self.inference_repo,
            approval_reader=self.approval_repo,
            audit_ledger=self.ledger,
        )
        self.seal_service = RevisionSealService(
            revision_repo=self.revision_repo,
            snapshot_repo=self.snapshot_repo,
            journal_repo=self.journal_repo,
            approval_repo=self.approval_repo,
            patch_reader=self.patch_repo,
            approval_service=self.approval_service,
            audit_ledger=self.ledger,
        )
        self.seal_bridge = RealFixRevisionSealBridge(
            seal_service=self.seal_service,
            approval_reader=self.approval_repo,
            review_reader=self.review_repo,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            inference_reader=self.inference_repo,
            revision_reader=self.revision_repo,
            audit_ledger=self.ledger,
        )
        self.evidence_service = EvidenceService(
            replay_anchor_repo=self.replay_anchor_repo,
            revision_repo=self.revision_repo,
            context_repo=self.context_repo,
            inference_repo=self.inference_repo,
            audit_ledger=self.ledger,
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
            audit_ledger=self.ledger,
        )

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------

    def _tracer(self, transport) -> RealFixTracer:
        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=transport)
        return RealFixTracer(
            adapter=adapter,
            audit_ledger=self.ledger,
            narrow_path_recorder=self.recorder,
        )

    def _orchestrator(self, tracer: RealFixTracer) -> SignablePathOrchestrator:
        # The eight-stage services are unreachable in this test. They
        # exist because the orchestrator constructor requires them;
        # run_real_fix_chain must not touch any of them.
        dummy = _Unreachable()
        return SignablePathOrchestrator(
            capability_service=dummy,
            context_service=dummy,
            inference_service=dummy,
            patch_proposal_service=dummy,
            validation_service=dummy,
            review_service=dummy,
            approval_service=dummy,
            revision_seal_service=dummy,
            evidence_service=dummy,
            audit_ledger=self.ledger,
            real_fix_tracer=tracer,
            real_fix_patch_projector=self.projector,
            real_fix_validation_bridge=self.validation_bridge,
            real_fix_review_bridge=self.review_bridge,
            real_fix_approval_bridge=self.approval_bridge,
            real_fix_revision_seal_bridge=self.seal_bridge,
            real_fix_evidence_closure_bridge=self.evidence_bridge,
        )

    def _count(self, table: str) -> int:
        return self.conn.execute(
            f"SELECT COUNT(*) FROM {table};"
        ).fetchone()[0]

    def _audit_types(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT record_type FROM audit_records ORDER BY sequence;"
        ).fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Success: verified pass drives the full chain end-to-end.
    # ------------------------------------------------------------------

    def test_run_real_fix_chain_end_to_end(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))

        outcome = orch.run_real_fix_chain(task)

        # One and only one row of each kind produced by the chain.
        self.assertIsInstance(outcome, RealFixEvidenceClosureBridgeOutcome)
        self.assertEqual(self._count("inference_artifacts"), 1)
        self.assertEqual(self._count("patch_proposals"), 1)
        self.assertEqual(self._count("validation_receipts"), 1)
        self.assertEqual(self._count("review_artifacts"), 1)
        self.assertEqual(self._count("approval_artifacts"), 1)
        self.assertEqual(self._count("revisions"), 1)
        self.assertEqual(self._count("snapshot_roots"), 1)
        self.assertEqual(self._count("replay_anchors"), 1)

        # The sealed revision carries the authority-bearing terminal state.
        rev = self.revision_repo.fetch(outcome.revision_id)
        self.assertIsNotNone(rev)
        self.assertEqual(rev["state"], "sealed")

        # Replay anchor is bound to the task and the sealed revision.
        anchor = self.replay_anchor_repo.fetch(outcome.replay_anchor_id)
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor["task_id"], task_id)
        self.assertEqual(anchor["root_revision_id"], outcome.revision_id)

        # Outcome ids are all populated and internally consistent.
        self.assertTrue(outcome.inference_artifact_id.startswith("inf-"))
        self.assertTrue(outcome.patch_proposal_id.startswith("pp-"))
        self.assertTrue(outcome.validation_receipt_id.startswith("vr-"))
        self.assertTrue(outcome.review_artifact_id.startswith("rv-"))
        self.assertTrue(outcome.approval_artifact_id.startswith("ap-"))
        self.assertTrue(outcome.revision_id.startswith("rev-"))
        self.assertTrue(outcome.replay_anchor_id.startswith("ra-"))
        self.assertEqual(outcome.task_id, task_id)
        self.assertEqual(outcome.root_revision_id, f"real-fix::root::{task_id}")
        self.assertEqual(
            outcome.context_artifact_id, f"real-fix::context::{task_id}"
        )

        # End-to-end audit chain: every bridge attestation is present and
        # they appear in causal order, followed by the orchestrator
        # wrapper event. The tracer's own verified_pass + projector /
        # service records are present alongside.
        types = self._audit_types()
        for required in (
            "real_fix_attempt_started",
            "inference_artifact_created",
            "real_fix_verified_pass",
            "patch_proposal_created",
            "real_fix_validation_bridge_attested",
            "real_fix_review_bridge_attested",
            "real_fix_approval_bridge_attested",
            "real_fix_revision_seal_bridge_attested",
            "evidence_closure",
            "real_fix_evidence_closure_bridge_attested",
            "real_fix_chain_completed",
        ):
            self.assertIn(required, types, f"missing audit type: {required}")

        # Causal order: each bridge attestation precedes the next.
        def idx(record_type: str) -> int:
            return types.index(record_type)

        self.assertLess(
            idx("real_fix_validation_bridge_attested"),
            idx("real_fix_review_bridge_attested"),
        )
        self.assertLess(
            idx("real_fix_review_bridge_attested"),
            idx("real_fix_approval_bridge_attested"),
        )
        self.assertLess(
            idx("real_fix_approval_bridge_attested"),
            idx("real_fix_revision_seal_bridge_attested"),
        )
        self.assertLess(
            idx("real_fix_revision_seal_bridge_attested"),
            idx("real_fix_evidence_closure_bridge_attested"),
        )
        self.assertLess(
            idx("real_fix_evidence_closure_bridge_attested"),
            idx("real_fix_chain_completed"),
        )

        # Replay-ceiling honesty: the tracer tag and the orchestrator
        # wrapper both carry "semantic". Real-provider output admits no
        # stronger ceiling.
        wrapper = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'real_fix_chain_completed';"
        ).fetchone()
        wrapper_payload = json.loads(wrapper[0])
        self.assertEqual(wrapper_payload["replay_ceiling"], "semantic")
        self.assertEqual(wrapper_payload["source"], "real_fix_tracer")
        self.assertEqual(
            wrapper_payload["replay_anchor_id"], outcome.replay_anchor_id
        )

        # Audit sequence is gap-free.
        seqs = [
            r[0]
            for r in self.conn.execute(
                "SELECT sequence FROM audit_records ORDER BY sequence;"
            ).fetchall()
        ]
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)))

    # ------------------------------------------------------------------
    # Fail-closed: unverified tracer outcome returns early with no chain.
    # ------------------------------------------------------------------

    def test_unverified_tracer_outcome_does_not_chain(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(BROKEN_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))

        result = orch.run_real_fix_chain(task)

        # The tracer returns its unverified result surface; no downstream
        # bridge is dispatched, so no narrow-path rows exist.
        self.assertFalse(getattr(result, "verified", False))
        self.assertEqual(self._count("inference_artifacts"), 0)
        self.assertEqual(self._count("patch_proposals"), 0)
        self.assertEqual(self._count("validation_receipts"), 0)
        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(self._count("approval_artifacts"), 0)
        self.assertEqual(self._count("revisions"), 0)
        self.assertEqual(self._count("replay_anchors"), 0)

        types = self._audit_types()
        self.assertNotIn("real_fix_chain_completed", types)
        self.assertNotIn("real_fix_validation_bridge_attested", types)

    # ------------------------------------------------------------------
    # Fail-closed: partial wiring is rejected.
    # ------------------------------------------------------------------

    def test_partial_wiring_rejected_fail_closed(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        tracer = self._tracer(transport)
        dummy = _Unreachable()
        # Omit the evidence closure bridge on purpose.
        orch = SignablePathOrchestrator(
            capability_service=dummy,
            context_service=dummy,
            inference_service=dummy,
            patch_proposal_service=dummy,
            validation_service=dummy,
            review_service=dummy,
            approval_service=dummy,
            revision_seal_service=dummy,
            evidence_service=dummy,
            audit_ledger=self.ledger,
            real_fix_tracer=tracer,
            real_fix_patch_projector=self.projector,
            real_fix_validation_bridge=self.validation_bridge,
            real_fix_review_bridge=self.review_bridge,
            real_fix_approval_bridge=self.approval_bridge,
            real_fix_revision_seal_bridge=self.seal_bridge,
            # real_fix_evidence_closure_bridge intentionally absent
        )
        task = make_add_fix_task(task_id=task_id)

        with self.assertRaises(RealFixChainRejected) as ctx:
            orch.run_real_fix_chain(task)
        self.assertIn("real_fix_evidence_closure_bridge", str(ctx.exception))

        # No artifacts were produced; the tracer itself must not have
        # been dispatched because the wiring check is the first thing
        # the chain does.
        self.assertEqual(self._count("inference_artifacts"), 0)
        self.assertNotIn("real_fix_attempt_started", self._audit_types())

    # ------------------------------------------------------------------
    # Fail-closed: cannot overlay the chain on an eight-stage frame.
    # ------------------------------------------------------------------

    def test_refuses_overlay_on_eight_stage_frame(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        tracer = self._tracer(transport)
        orch = self._orchestrator(tracer)

        # Manually seed the in-memory bookkeeping as if the eight-stage
        # surface had admitted this task already. We deliberately do
        # not go through admit_context (its dummy services would fail);
        # directly populating ``_tasks`` is sufficient for the overlay
        # guard and is the minimum reproducible case.
        from kernel.lifecycle.signable_path_orchestrator import (
            IntentCausalAnchor,
            TaskLifecycleState,
        )
        from kernel.lifecycle.stage_types import Stage

        orch._tasks[task_id] = TaskLifecycleState(
            task_id=task_id,
            intent_anchor=IntentCausalAnchor(
                intent_id="intent-x",
                task_id=task_id,
                state="admitted",
                created_at="2026-04-15T00:00:00+00:00",
            ),
            current_stage=Stage.CONTEXT,
        )

        task = make_add_fix_task(task_id=task_id)
        with self.assertRaises(RealFixChainRejected) as ctx:
            orch.run_real_fix_chain(task)
        self.assertIn("eight-stage", str(ctx.exception))

        # Nothing was produced.
        self.assertEqual(self._count("inference_artifacts"), 0)


if __name__ == "__main__":
    unittest.main()
