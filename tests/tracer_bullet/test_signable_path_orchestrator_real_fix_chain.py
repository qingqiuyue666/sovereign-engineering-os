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
from kernel.services.context_service import ContextService
from kernel.services.evidence_service import EvidenceService
from kernel.services.review_service import ReviewService
from kernel.services.revision_seal_service import (
    RevisionSealService,
    SealRejected,
)
from kernel.services.validation_service import ValidationService
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
    IntentAnchorRepository,
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
        self.intent_repo = IntentAnchorRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="orchestrator_real_fix_chain_test",
        )
        self.recorder = RealFixNarrowPathRecorder(
            repository=self.inference_repo,
            audit_ledger=self.ledger,
        )
        # The real-fix chain entrypoint now mints one authority-bearing
        # ``ContextArtifact`` row via the already-wired ``ContextService``
        # before dispatching the tracer. The other seven eight-stage
        # services remain unreachable — ``run_real_fix_chain`` must not
        # touch any of them.
        self.context_service = ContextService(
            repository=self.context_repo,
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
            # AUDIT-003 / §22.1: wire the durable intent-anchor reader so
            # the orchestrator-driven seal path enforces the durable-row
            # verification the service already implements. The
            # orchestrator mints the row at ``_emit_intent_anchor`` above
            # and threads the same ``intent_id`` into the seal bridge;
            # this wiring promotes the linkage from opt-in to always-on
            # on every orchestrator composition.
            intent_anchor_reader=self.intent_repo,
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
            context_service=self.context_service,
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
            intent_anchor_repository=self.intent_repo,
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
        # One real ContextArtifact row is now minted by the chain before
        # the tracer dispatches. This is the authority-bearing upgrade
        # from the prior tracer-scoped synthetic id.
        self.assertEqual(self._count("context_artifacts"), 1)
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
        # ``root_revision_id`` remains the clearly-labelled
        # ``real-fix::root::<task_id>`` form — no ``Revision`` row is
        # minted for the real-fix chain in this increment. The label is
        # now the ``root_revision_id`` field of a real persisted
        # ``ContextArtifact`` row (verified below).
        self.assertEqual(outcome.root_revision_id, f"real-fix::root::{task_id}")
        # ``context_artifact_id`` is no longer synthetic: it now names a
        # real ``ContextArtifact`` row minted via ``ContextService``.
        self.assertTrue(outcome.context_artifact_id.startswith("ctx-"))
        ctx_row = self.context_repo.fetch(outcome.context_artifact_id)
        self.assertIsNotNone(ctx_row)
        self.assertEqual(ctx_row["task_id"], task_id)
        self.assertEqual(
            ctx_row["root_revision_id"], f"real-fix::root::{task_id}"
        )
        # The persisted ``InferenceArtifact`` row points at the real
        # ``ContextArtifact`` id (not the prior synthetic label) so the
        # downstream bridges propagate the authority-bearing id.
        inf_row = self.inference_repo.fetch(outcome.inference_artifact_id)
        self.assertIsNotNone(inf_row)
        self.assertEqual(
            inf_row["context_artifact_id"], outcome.context_artifact_id
        )
        self.assertEqual(
            inf_row["root_revision_id"], f"real-fix::root::{task_id}"
        )

        # End-to-end audit chain: every bridge attestation is present and
        # they appear in causal order, followed by the orchestrator
        # wrapper event. The tracer's own verified_pass + projector /
        # service records are present alongside.
        types = self._audit_types()
        for required in (
            "context_artifact_created",
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
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'real_fix_chain_completed';"
        ).fetchone()
        wrapper_payload = json.loads(wrapper[0])
        self.assertEqual(wrapper_payload["replay_ceiling"], "semantic")
        self.assertEqual(wrapper_payload["source"], "real_fix_tracer")
        self.assertEqual(
            wrapper_payload["replay_anchor_id"], outcome.replay_anchor_id
        )

        # AUDIT-003 / §22.1: the wrapper's own "every id from a single
        # hop" claim must include the originating durable intent-anchor
        # id — both in ``payload`` and in ``artifact_refs``. The id
        # pinned here is the exact label minted by
        # ``_emit_intent_anchor`` and persisted into
        # ``intent_anchor_records`` during the ContextArtifact hop, so a
        # reviewer reading only this one record can recover the full
        # AUDIT-003 linkage without an extra DB fetch on
        # ``revisions.intent_id``.
        expected_intent_id = f"real-fix::intent::{task_id}"
        self.assertEqual(wrapper_payload["intent_id"], expected_intent_id)
        wrapper_artifact_refs = json.loads(wrapper[1])
        self.assertIn(expected_intent_id, wrapper_artifact_refs)

        # AUDIT-003 / §22.1 (upstream-of-bridges): the
        # ``patch_proposal_created`` record emitted by the projector
        # when composed by ``run_real_fix_chain`` must also name the
        # same durable intent-anchor id in both ``payload`` and
        # ``artifact_refs``. Without this the projector's "cross-plane
        # evidence hook" audit would still require a second fetch (via
        # ``inference_artifact_id -> context_artifact_id ->
        # intent_anchor_records``) to recover the originating
        # intent-anchor id, leaving a one-hop asymmetry immediately
        # upstream of ``real_fix_validation_bridge_attested`` that the
        # mainline pattern already closed on every downstream bridge.
        ppc = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'patch_proposal_created';"
        ).fetchone()
        ppc_payload = json.loads(ppc[0])
        ppc_refs = json.loads(ppc[1])
        self.assertEqual(ppc_payload["intent_id"], expected_intent_id)
        self.assertIn(expected_intent_id, ppc_refs)

        # AUDIT-003 / §22.1 (upstream-of-projector): the
        # ``inference_artifact_created`` record emitted by the narrow-
        # path recorder when composed by ``run_real_fix_chain`` must
        # also name the same durable intent-anchor id in both
        # ``payload`` and ``artifact_refs``. Without this the recorder's
        # "cross-plane evidence hook" audit would still require a
        # second fetch (via ``context_artifact_id ->
        # intent_anchor_records``) to recover the originating
        # intent-anchor id, leaving the last one-hop asymmetry
        # immediately upstream of ``patch_proposal_created`` that the
        # mainline pattern already closed on every downstream hop.
        iac = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'inference_artifact_created';"
        ).fetchone()
        iac_payload = json.loads(iac[0])
        iac_refs = json.loads(iac[1])
        self.assertEqual(iac_payload["intent_id"], expected_intent_id)
        self.assertIn(expected_intent_id, iac_refs)

        # AUDIT-003 / §22.1 (upstream-of-recorder): the
        # ``context_artifact_created`` record emitted by ``ContextService``
        # when composed by ``run_real_fix_chain`` must also name the same
        # durable intent-anchor id in both ``payload`` and
        # ``artifact_refs``. Without this the service's "cross-plane
        # evidence hook" audit would still require a second fetch (via
        # ``context_artifact_id -> intent_anchor_records``) to recover the
        # originating intent-anchor id, leaving the last one-hop
        # asymmetry immediately upstream of ``inference_artifact_created``
        # that the mainline pattern already closed on every downstream
        # hop.
        cac = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'context_artifact_created';"
        ).fetchone()
        cac_payload = json.loads(cac[0])
        cac_refs = json.loads(cac[1])
        self.assertEqual(cac_payload["intent_id"], expected_intent_id)
        self.assertIn(expected_intent_id, cac_refs)

        # AUDIT-003 / §22.1 (evidence service-record parity): the
        # ``evidence_closure`` record emitted by ``EvidenceService`` must
        # also name the same durable intent-anchor id in both ``payload``
        # and ``artifact_refs``. The id is the one written onto
        # ``revisions.intent_id`` by ``RevisionSealService`` upstream;
        # reading it from the already-fetched sealed revision row and
        # naming it on the service record closes the evidence-stage
        # one-hop asymmetry next to the already-closed bridge-layer
        # ``real_fix_evidence_closure_bridge_attested``. Mirrors the
        # parity between ``revision_sealed`` (service) and
        # ``real_fix_revision_seal_bridge_attested`` (bridge).
        ec = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'evidence_closure';"
        ).fetchone()
        ec_payload = json.loads(ec[0])
        ec_refs = json.loads(ec[1])
        self.assertEqual(ec_payload["intent_id"], expected_intent_id)
        self.assertIn(expected_intent_id, ec_refs)

        # AUDIT-003 / §22.1 (approval service-record parity): the
        # ``approval_artifact_issued`` record emitted by
        # ``ApprovalService.evaluate_barrier`` must also name the same
        # durable intent-anchor id in both ``payload`` and
        # ``artifact_refs``. The id is threaded in from the orchestrator
        # (``state.intent_anchor.intent_id``) and from the real-fix
        # approval bridge; the service performs no independent
        # verification. Naming it on the service record closes the
        # approval-stage one-hop asymmetry next to the already-closed
        # bridge-layer ``real_fix_approval_bridge_attested``.
        ap = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'approval_artifact_issued';"
        ).fetchone()
        ap_payload = json.loads(ap[0])
        ap_refs = json.loads(ap[1])
        self.assertEqual(ap_payload["intent_id"], expected_intent_id)
        self.assertIn(expected_intent_id, ap_refs)

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

    # ------------------------------------------------------------------
    # Bridge into the eight-stage authority-bearing lifecycle frame.
    # ------------------------------------------------------------------

    def test_run_real_fix_chain_enters_eight_stage_frame(self) -> None:
        """A completed real-fix chain drives the eight-stage lifecycle
        state frame end-to-end: the in-memory ``TaskLifecycleState`` is
        populated with every stage's authority-bearing artifact id,
        ``stage_entered`` audit records are emitted for every stage in
        causal order, and ``signable_path_sealed`` marks the terminal
        state. The chain's durable authority and the eight-stage frame
        are no longer disjoint surfaces.
        """
        from kernel.lifecycle.stage_types import Stage

        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))

        outcome = orch.run_real_fix_chain(task)

        # Terminal state is SEALED — the eight-stage lifecycle frame
        # reflects the chain's real authority-bearing terminal state.
        self.assertEqual(orch.current_stage(task_id), Stage.SEALED)

        # Every stage's artifact id is bound on the in-memory frame.
        state = orch._tasks[task_id]
        self.assertEqual(
            state.artifact_ids[Stage.CONTEXT], outcome.context_artifact_id
        )
        self.assertEqual(
            state.artifact_ids[Stage.INFERENCE], outcome.inference_artifact_id
        )
        self.assertEqual(
            state.artifact_ids[Stage.PATCH_PROPOSAL],
            outcome.patch_proposal_id,
        )
        self.assertEqual(
            state.artifact_ids[Stage.VALIDATION],
            outcome.validation_receipt_id,
        )
        self.assertEqual(
            state.artifact_ids[Stage.REVIEW], outcome.review_artifact_id
        )
        self.assertEqual(
            state.artifact_ids[Stage.APPROVAL],
            outcome.approval_artifact_id,
        )
        self.assertEqual(
            state.artifact_ids[Stage.REVISION_SEAL], outcome.revision_id
        )
        self.assertEqual(
            state.artifact_ids[Stage.EVIDENCE], outcome.replay_anchor_id
        )

        # The intent-anchor audit record is emitted exactly once per
        # real-fix chain invocation, matching the eight-stage
        # ``admit_context`` admission pattern.
        types = self._audit_types()
        self.assertEqual(types.count("intent_anchor_created"), 1)

        # ``stage_entered`` audit rows name every stage in causal order.
        stage_order = [
            Stage.CONTEXT.value,
            Stage.INFERENCE.value,
            Stage.PATCH_PROPOSAL.value,
            Stage.VALIDATION.value,
            Stage.REVIEW.value,
            Stage.APPROVAL.value,
            Stage.REVISION_SEAL.value,
            Stage.EVIDENCE.value,
        ]
        rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'stage_entered' "
            "ORDER BY sequence;"
        ).fetchall()
        stages_in_order = [json.loads(r[0])["stage"] for r in rows]
        self.assertEqual(stages_in_order, stage_order)

        # ``signable_path_sealed`` marks the terminal; emitted exactly
        # once; its ``artifact_refs`` enumerates the frame's ids.
        sealed_rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'signable_path_sealed';"
        ).fetchall()
        self.assertEqual(len(sealed_rows), 1)
        self.assertEqual(
            json.loads(sealed_rows[0][0])["stage"], Stage.SEALED.value
        )

        # Causal ordering: every ``stage_entered`` for a given stage
        # precedes that stage's bridge attestation (when applicable)
        # except CONTEXT (no bridge) and INFERENCE (tracer records it),
        # and ``signable_path_sealed`` precedes ``real_fix_chain_completed``.
        def idx(record_type: str) -> int:
            return types.index(record_type)

        self.assertLess(idx("stage_entered"), idx("real_fix_attempt_started"))
        self.assertLess(
            idx("real_fix_validation_bridge_attested"),
            idx("real_fix_review_bridge_attested"),
        )
        self.assertLess(
            idx("signable_path_sealed"), idx("real_fix_chain_completed")
        )

    # ------------------------------------------------------------------
    # Durable intent-anchor row (AUDIT-003 / §22.1): the real-fix chain
    # mints a row into ``intent_anchor_records`` before emitting the
    # ``intent_anchor_created`` audit record. This promotes the
    # originating intent from an audit-payload-only label to a durable
    # authority-bearing row, making ``Revision.intent_id`` reference a
    # row that replay / recovery / §22.1 preconditions can consult.
    # ------------------------------------------------------------------

    def test_run_real_fix_chain_persists_durable_intent_anchor_row(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))

        outcome = orch.run_real_fix_chain(task)

        # Exactly one durable row, bound to the real task and in the
        # canonical ``admitted`` state. The row exists independently of
        # any audit payload.
        rows = self.conn.execute(
            "SELECT intent_id, task_id, state FROM intent_anchor_records;"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        intent_id, row_task_id, row_state = rows[0]
        self.assertEqual(intent_id, f"real-fix::intent::{task_id}")
        self.assertEqual(row_task_id, task_id)
        self.assertEqual(row_state, "admitted")

        # Audit-as-attestation ordering: the ``intent_anchor_created``
        # audit record references the same intent_id the durable row
        # already carries. Exactly one such audit record per chain.
        audit_rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'intent_anchor_created';"
        ).fetchall()
        self.assertEqual(len(audit_rows), 1)
        self.assertEqual(
            json.loads(audit_rows[0][0])["intent_id"], intent_id
        )

        # The sealed ``Revision.intent_id`` references the same durable
        # ``intent_anchor_records.intent_id`` rather than the seal
        # service's fallback ``intent-<task_id>`` label. This closes the
        # real-fix surface's half of the AUDIT-003 / §22.1 linkage that
        # was already closed on the eight-stage ``admit_revision_seal``
        # surface (see ``test_happy_path_context_to_evidence``:
        # ``self.assertEqual(rev["intent_id"], intent_id)``).
        rev = self.revision_repo.fetch(outcome.revision_id)
        self.assertIsNotNone(rev)
        self.assertEqual(rev["intent_id"], intent_id)
        self.assertNotEqual(rev["intent_id"], f"intent-{task_id}")

        # AUDIT-003 / §22.1: the authority-bearing ``revision_sealed``
        # service audit names the durable ``intent_id`` in both
        # ``artifact_refs`` and ``payload``. A reviewer reading only this
        # one record can recover the originating durable intent-anchor id
        # without a second fetch on ``revisions.intent_id``. Exactly one
        # such record per chain invocation.
        sealed_rows = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'revision_sealed';"
        ).fetchall()
        self.assertEqual(len(sealed_rows), 1)
        sealed_payload = json.loads(sealed_rows[0][0])
        self.assertEqual(sealed_payload["intent_id"], intent_id)
        sealed_refs = json.loads(sealed_rows[0][1])
        self.assertIn(intent_id, sealed_refs)

    def test_unverified_tracer_outcome_still_persists_intent_anchor(self) -> None:
        """Fail-closed honesty: the durable intent row is minted during
        the ContextArtifact admission hop, which runs before the tracer
        dispatches. An unverified tracer outcome must therefore still
        leave a durable originating-intent row behind (the task is
        abandonable from ``Stage.CONTEXT``) — there is no scenario where
        a ``Stage.CONTEXT`` frame exists without a matching durable
        ``intent_anchor_records`` row.
        """
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(BROKEN_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))

        result = orch.run_real_fix_chain(task)
        self.assertFalse(getattr(result, "verified", False))

        rows = self.conn.execute(
            "SELECT intent_id, task_id, state FROM intent_anchor_records;"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], f"real-fix::intent::{task_id}")
        self.assertEqual(rows[0][1], task_id)
        self.assertEqual(rows[0][2], "admitted")

    def test_unverified_leaves_frame_at_context(self) -> None:
        """On unverified tracer outcome, the eight-stage lifecycle frame
        remains at ``Stage.CONTEXT`` (the only stage that was actually
        earned by a real ContextArtifact). No downstream stage is
        entered without a bridge-produced authority-bearing artifact to
        bind to it. The task remains abandonable — fail-closed.
        """
        from kernel.lifecycle.stage_types import Stage

        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(BROKEN_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))

        result = orch.run_real_fix_chain(task)

        self.assertFalse(getattr(result, "verified", False))
        self.assertEqual(orch.current_stage(task_id), Stage.CONTEXT)

        # The frame is abandonable from CONTEXT.
        orch.abandon(task_id=task_id, reason="tracer_unverified")
        self.assertEqual(orch.current_stage(task_id), Stage.ABANDONED)

        types = self._audit_types()
        self.assertIn("stage_entered", types)
        self.assertNotIn("signable_path_sealed", types)
        self.assertIn("task_abandoned", types)

    # ------------------------------------------------------------------
    # AUDIT-003 / §22.1 seal-time durable-row verification on the
    # orchestrator composition.
    #
    # The ``RevisionSealService`` can refuse any ``intent_id`` that does
    # not resolve to a durable ``intent_anchor_records`` row, but only
    # when ``intent_anchor_reader`` is wired at construction. The
    # orchestrator-driving composition (``setUp`` above) now wires the
    # reader, promoting that check from opt-in (proven in
    # ``test_revision_seal_service_intent_id.py``) to always-on on every
    # orchestrator-composed seal call. The fail-closed floor for the
    # unwired back-compat path (missing/empty ``intent_id``) remains
    # unchanged.
    # ------------------------------------------------------------------
    def test_orchestrator_seal_service_enforces_durable_row_check(
        self,
    ) -> None:
        """Wiring proof: with the orchestrator-composed seal service,
        a direct ``seal_revision`` call with an ``intent_id`` that does
        not name a durable ``intent_anchor_records`` row is refused
        fail-closed with the durable-row error.

        The chain is driven first so a real approval + context exists.
        A new seal attempt is then dispatched directly against the same
        seal service using those authority-bearing ids but a freshly
        synthesized ``intent_id`` that was never minted as a durable
        row. This exercises the seal-time check end-to-end on the
        orchestrator composition rather than on an isolated unit
        harness.
        """
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))
        outcome = orch.run_real_fix_chain(task)

        # The chain minted exactly one durable row for its own
        # ``real-fix::intent::<task_id>`` label. Any other non-empty
        # string is a well-formed intent_id at the fail-closed floor
        # but names no durable row and must be refused by the
        # seal-time durable-row check.
        bogus_intent_id = f"real-fix::intent::bogus-{uuid4().hex[:8]}"
        self.assertIsNone(self.intent_repo.fetch(bogus_intent_id))

        with self.assertRaises(SealRejected) as raised:
            self.seal_service.seal_revision(
                task_id=task_id,
                approval_id=outcome.approval_artifact_id,
                context_artifact_id=outcome.context_artifact_id,
                intent_id=bogus_intent_id,
            )
        # The message names the durable-row surface so a reviewer can
        # distinguish this refusal from the missing/empty fail-closed
        # floor.
        self.assertIn("intent_anchor_records", str(raised.exception))

    def test_orchestrator_seal_service_enforces_task_id_binding(
        self,
    ) -> None:
        """Wiring proof: the orchestrator-composed seal service refuses
        an ``intent_id`` that resolves to a durable row whose
        ``task_id`` does not match the seal's ``task_id``. This is the
        second half of the durable-row verification and is what makes
        the linkage task-bound rather than merely durable.
        """
        task_id = f"fix-{uuid4().hex[:8]}"

        def transport(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        orch = self._orchestrator(self._tracer(transport))
        outcome = orch.run_real_fix_chain(task)

        # Mint a durable row bound to a DIFFERENT task_id. The row is
        # real, but its task_id mismatches the seal's task_id.
        other_task_id = f"fix-{uuid4().hex[:8]}"
        mismatched_intent_id = f"real-fix::intent::{other_task_id}"
        self.intent_repo.insert(
            intent_id=mismatched_intent_id,
            task_id=other_task_id,
            state="admitted",
        )

        with self.assertRaises(SealRejected) as raised:
            self.seal_service.seal_revision(
                task_id=task_id,
                approval_id=outcome.approval_artifact_id,
                context_artifact_id=outcome.context_artifact_id,
                intent_id=mismatched_intent_id,
            )
        self.assertIn("task_id", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
