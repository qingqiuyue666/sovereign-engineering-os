"""
Tracer-bullet test: full eight-stage signable path, context to evidence.

Foundation §5.1 test #1: the minimum end-to-end proof that all stages
wire correctly, that the audit ledger captures every transition, that
the replay anchor is produced, and that the state machine reaches SEALED.

This test runs against an in-memory SQLite database (`:memory:`) to
avoid any filesystem side effects. It wires the orchestrator to the real
service modules — no mocks, no stubs (except the ModelAdapter, which is
a fake that produces deterministic output).

What it proves:
1. Migrations apply cleanly.
2. Context -> Inference -> PatchProposal -> Validation -> Review ->
   Approval -> RevisionSeal -> Evidence completes without error.
3. The orchestrator reaches SEALED terminal state.
4. A sealed revision exists in the database.
5. A ReplayAnchor exists in the database.
6. The audit ledger has monotonically-sequenced records.
7. The nine-step seal ordering was enforced (journal entries present).
8. The §22.3 barrier passed at approval time.
9. Taint propagation is explicit (empty in the happy path).
"""

from __future__ import annotations

import json
import sys
import os
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import uuid4

# Ensure repo root is on the path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    CapabilityRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
    IntentAnchorRepository,
    PatchProposalRepository,
    ValidationReceiptRepository,
    ReviewArtifactRepository,
    ApprovalArtifactRepository,
    RevisionRepository,
    SnapshotRootRepository,
    JournalEntryRepository,
    ReplayAnchorRepository,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.services.capability_service import CapabilityService
from kernel.services.context_service import ContextService
from kernel.services.inference_service import (
    InferenceService,
    InferencePolicy,
    ModelAdapter,
)
from kernel.services.patch_proposal_service import PatchProposalService
from kernel.services.validation_service import ValidationService
from kernel.services.review_service import ReviewService
from kernel.services.approval_service import ApprovalService
from kernel.services.revision_seal_service import RevisionSealService
from kernel.services.evidence_service import EvidenceService
from kernel.lifecycle.signable_path_orchestrator import SignablePathOrchestrator
from kernel.lifecycle.stage_types import Stage


# ---------------------------------------------------------------------------
# Fake model adapter: deterministic output for the tracer.
# ---------------------------------------------------------------------------


class _FakeModelAdapter:
    """A deterministic ModelAdapter that returns fixed output."""

    def invoke(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> Mapping[str, Any]:
        return {
            "output_text": "tracer-bullet output text",
            "token_usage": {"input": 100, "output": 20},
            "latency_ms": 42,
            "model_route_id": "fake-model-v1",
        }


# ---------------------------------------------------------------------------
# Test case
# ---------------------------------------------------------------------------


class TestHappyPathContextToEvidence(unittest.TestCase):
    """Foundation §5.1 test #1: full happy-path narrow signable path."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)

        # Repositories.
        self.audit_repo = AuditRepository(self.conn)
        self.cap_repo = CapabilityRepository(self.conn)
        self.ctx_repo = ContextArtifactRepository(self.conn)
        self.inf_repo = InferenceArtifactRepository(self.conn)
        self.intent_repo = IntentAnchorRepository(self.conn)
        self.pp_repo = PatchProposalRepository(self.conn)
        self.vr_repo = ValidationReceiptRepository(self.conn)
        self.rv_repo = ReviewArtifactRepository(self.conn)
        self.ap_repo = ApprovalArtifactRepository(self.conn)
        self.rev_repo = RevisionRepository(self.conn)
        self.snap_repo = SnapshotRootRepository(self.conn)
        self.je_repo = JournalEntryRepository(self.conn)
        self.ra_repo = ReplayAnchorRepository(self.conn)

        # Audit ledger.
        self.audit_ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="tracer_test",
        )

        # Services.
        self.cap_svc = CapabilityService(
            repository=self.cap_repo,
            audit_ledger=self.audit_ledger,
        )
        self.ctx_svc = ContextService(
            repository=self.ctx_repo,
            audit_ledger=self.audit_ledger,
        )
        self.inf_svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit_ledger,
            context_reader=self.ctx_repo,
            adapter=_FakeModelAdapter(),
            policy=InferencePolicy(),
        )
        self.pp_svc = PatchProposalService(
            repository=self.pp_repo,
            inference_reader=self.inf_repo,
            audit_ledger=self.audit_ledger,
        )
        self.val_svc = ValidationService(
            repository=self.vr_repo,
            patch_reader=self.pp_repo,
            audit_ledger=self.audit_ledger,
        )
        self.rev_svc = ReviewService(
            repository=self.rv_repo,
            patch_reader=self.pp_repo,
            receipt_reader=self.vr_repo,
            audit_ledger=self.audit_ledger,
        )
        self.ap_svc = ApprovalService(
            repository=self.ap_repo,
            patch_reader=self.pp_repo,
            receipt_reader=self.vr_repo,
            review_reader=self.rv_repo,
            audit_ledger=self.audit_ledger,
        )
        self.seal_svc = RevisionSealService(
            revision_repo=self.rev_repo,
            snapshot_repo=self.snap_repo,
            journal_repo=self.je_repo,
            approval_repo=self.ap_repo,
            patch_reader=self.pp_repo,
            approval_service=self.ap_svc,
            audit_ledger=self.audit_ledger,
            # AUDIT-003 / §22.1: wire the durable intent-anchor reader so
            # the orchestrator-driven happy path enforces the durable-row
            # verification. The orchestrator mints the row at
            # ``_emit_intent_anchor`` and threads the same ``intent_id``
            # into the seal; wiring the reader makes the linkage check
            # fire on this end-to-end path rather than silently accept.
            intent_anchor_reader=self.intent_repo,
        )
        self.evidence_svc = EvidenceService(
            replay_anchor_repo=self.ra_repo,
            revision_repo=self.rev_repo,
            context_repo=self.ctx_repo,
            inference_repo=self.inf_repo,
            audit_ledger=self.audit_ledger,
        )

        # Orchestrator.
        self.orch = SignablePathOrchestrator(
            capability_service=self.cap_svc,
            context_service=self.ctx_svc,
            inference_service=self.inf_svc,
            patch_proposal_service=self.pp_svc,
            validation_service=self.val_svc,
            review_service=self.rev_svc,
            approval_service=self.ap_svc,
            revision_seal_service=self.seal_svc,
            evidence_service=self.evidence_svc,
            audit_ledger=self.audit_ledger,
            intent_anchor_repository=self.intent_repo,
        )

    def tearDown(self) -> None:
        self.conn.close()

    def _issue_capability(self, name: str, task_id: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return self.cap_svc.issue_token(
            subject_identity="tracer_test",
            capability_name=name,
            scope_hash="scope:tracer",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            single_use=True,
            bound_task_id=task_id,
        )

    def test_full_happy_path(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        intent_id = f"intent-{uuid4().hex[:8]}"
        root_rev_id = "rev-genesis-000"

        # Stage 1: Context.
        cap_ctx = self._issue_capability("read_repository_snapshot", task_id)
        ctx_id = self.orch.admit_context(
            task_id=task_id,
            intent_id=intent_id,
            capability_token=cap_ctx,
            root_revision_id=root_rev_id,
            request={
                "repo_graph_version": "1.0",
                "symbol_index_version": "1.0",
                "candidate_file_ids": ["src/main.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 500,
            },
        )
        self.assertTrue(ctx_id.startswith("ctx-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.CONTEXT)

        # Stage 2: Inference (via fake adapter).
        cap_inf = self._issue_capability("invoke_inference", task_id)
        inf_id = self.orch.admit_inference(
            task_id=task_id,
            capability_token=cap_inf,
            worker_profile="tracer_worker",
            model_route_id="fake-model-v1",
        )
        self.assertTrue(inf_id.startswith("inf-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.INFERENCE)

        # Stage 3: PatchProposal (phase-1 single-file default).
        cap_patch = self._issue_capability("propose_patch", task_id)
        pp_id = self.orch.admit_patch_proposal(
            task_id=task_id,
            capability_token=cap_patch,
        )
        self.assertTrue(pp_id.startswith("pp-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.PATCH_PROPOSAL)

        # Stage 4: Validation.
        cap_validation = self._issue_capability(
            "run_validation_quarantine", task_id
        )
        vr_id = self.orch.admit_validation(
            task_id=task_id,
            capability_token=cap_validation,
        )
        self.assertTrue(vr_id.startswith("vr-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.VALIDATION)

        # Stage 5: Review.
        rv_id = self.orch.admit_review(task_id=task_id)
        self.assertTrue(rv_id.startswith("rv-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.REVIEW)

        # Stage 6: Approval (§22.3 barrier check).
        ap_id = self.orch.admit_approval(task_id=task_id)
        self.assertTrue(ap_id.startswith("ap-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.APPROVAL)

        # Stage 7: Revision Seal (nine-step §22.2 ordering).
        rev_id = self.orch.admit_revision_seal(task_id=task_id)
        self.assertTrue(rev_id.startswith("rev-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.REVISION_SEAL)

        # Stage 8: Evidence closure (replay anchor).
        ra_id = self.orch.admit_evidence(task_id=task_id)
        self.assertTrue(ra_id.startswith("ra-"))
        self.assertEqual(self.orch.current_stage(task_id), Stage.SEALED)

        # ---- post-condition assertions ----

        # Sealed revision exists.
        rev = self.rev_repo.fetch(rev_id)
        self.assertIsNotNone(rev)
        self.assertEqual(rev["state"], "sealed")
        self.assertIsNotNone(rev["sealed_at"])

        # Replay anchor exists with correct task.
        anchor_row = self.conn.execute(
            "SELECT * FROM replay_anchors WHERE replay_anchor_id = ?;",
            (ra_id,),
        ).fetchone()
        self.assertIsNotNone(anchor_row)
        self.assertEqual(anchor_row["task_id"], task_id)

        # Audit records have monotonic sequence.
        audit_rows = self.conn.execute(
            "SELECT sequence FROM audit_records ORDER BY sequence;"
        ).fetchall()
        seqs = [r[0] for r in audit_rows]
        self.assertTrue(len(seqs) >= 8, f"expected >=8 audit records, got {len(seqs)}")
        self.assertEqual(seqs, sorted(seqs), "audit sequence not monotonic")
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)), "audit sequence has gaps")

        # Journal entries present (seal_prepare, seal_mutation, seal_confirmed).
        journal_rows = self.conn.execute(
            "SELECT entry_type FROM journal_entries ORDER BY logical_sequence;"
        ).fetchall()
        entry_types = [r[0] for r in journal_rows]
        self.assertIn("seal_prepare", entry_types)
        self.assertIn("seal_mutation", entry_types)
        self.assertIn("seal_confirmed", entry_types)

        # Approval artifact is in 'approved' state.
        approval = self.ap_repo.fetch(ap_id)
        self.assertIsNotNone(approval)
        self.assertEqual(approval["approval_state"], "approved")

        # Validation receipt result is 'pass'.
        receipt = self.vr_repo.fetch(vr_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["result"], "pass")

        # No taint on the happy path.
        self.assertEqual(receipt.get("taint_set", []), [])

        # Durable intent-anchor row exists (AUDIT-003 / §22.1). Revision
        # ``intent_id`` now references a row in ``intent_anchor_records``
        # rather than an audit-payload-only label.
        intent_rows = self.conn.execute(
            "SELECT intent_id, task_id, state "
            "FROM intent_anchor_records WHERE task_id = ?;",
            (task_id,),
        ).fetchall()
        self.assertEqual(len(intent_rows), 1)
        self.assertEqual(intent_rows[0]["intent_id"], intent_id)
        self.assertEqual(intent_rows[0]["state"], "admitted")
        self.assertEqual(rev["intent_id"], intent_id)

        # AUDIT-003 / §22.1 (approval service-record parity): the
        # ``approval_artifact_issued`` record emitted by
        # ``ApprovalService.evaluate_barrier`` must name the same durable
        # intent-anchor id in both ``payload`` and ``artifact_refs``. The
        # id is threaded in from the orchestrator
        # (``state.intent_anchor.intent_id``); the service performs no
        # independent verification. Naming it on the service record
        # closes the approval-stage one-hop asymmetry on the eight-stage
        # path.
        ap_row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'approval_artifact_issued';"
        ).fetchone()
        self.assertIsNotNone(ap_row)
        ap_payload = json.loads(ap_row["payload_json"])
        ap_refs = json.loads(ap_row["artifact_refs"])
        self.assertEqual(ap_payload["intent_id"], intent_id)
        self.assertIn(intent_id, ap_refs)

        # AUDIT-003 / §22.1 (review service-record parity): the
        # ``review_artifact_created`` record emitted by
        # ``ReviewService.render_review`` must name the same durable
        # intent-anchor id in both ``payload`` and ``artifact_refs``. The
        # id is threaded in from the orchestrator
        # (``state.intent_anchor.intent_id``); the service performs no
        # independent verification. Naming it on the service record
        # closes the review-stage one-hop asymmetry on the eight-stage
        # path.
        rv_row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'review_artifact_created';"
        ).fetchone()
        self.assertIsNotNone(rv_row)
        rv_payload = json.loads(rv_row["payload_json"])
        rv_refs = json.loads(rv_row["artifact_refs"])
        self.assertEqual(rv_payload["intent_id"], intent_id)
        self.assertIn(intent_id, rv_refs)

        # AUDIT-003 / §22.1 (validation service-record parity): the
        # ``validation_receipt_created`` record emitted by
        # ``ValidationService.validate`` must name the same durable
        # intent-anchor id in both ``payload`` and ``artifact_refs``. The
        # id is threaded in from the orchestrator
        # (``state.intent_anchor.intent_id``); the service performs no
        # independent verification. Naming it on the service record
        # closes the validation-stage one-hop asymmetry on the
        # eight-stage path.
        vr_row = self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE record_type = 'validation_receipt_created';"
        ).fetchone()
        self.assertIsNotNone(vr_row)
        vr_payload = json.loads(vr_row["payload_json"])
        vr_refs = json.loads(vr_row["artifact_refs"])
        self.assertEqual(vr_payload["intent_id"], intent_id)
        self.assertIn(intent_id, vr_refs)


class TestIllegalTransitionRejected(unittest.TestCase):
    """Verify the orchestrator refuses an out-of-order stage skip."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        audit_repo = AuditRepository(self.conn)
        self.audit_ledger = AppendOnlyLedger(
            repository=audit_repo, actor_identity="test"
        )
        cap_repo = CapabilityRepository(self.conn)
        ctx_repo = ContextArtifactRepository(self.conn)
        self.cap_svc = CapabilityService(
            repository=cap_repo, audit_ledger=self.audit_ledger
        )
        self.ctx_svc = ContextService(
            repository=ctx_repo, audit_ledger=self.audit_ledger
        )

        # Dummy services that should never be called.
        class _Unreachable:
            def __getattr__(self, name: str):
                raise AssertionError(f"unexpected service call: {name}")

        dummy = _Unreachable()
        self.orch = SignablePathOrchestrator(
            capability_service=self.cap_svc,
            context_service=self.ctx_svc,
            inference_service=dummy,
            patch_proposal_service=dummy,
            validation_service=dummy,
            review_service=dummy,
            approval_service=dummy,
            revision_seal_service=dummy,
            evidence_service=dummy,
            audit_ledger=self.audit_ledger,
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_skip_inference_raises(self) -> None:
        from kernel.lifecycle.signable_path_orchestrator import OrchestratorRejected

        task_id = f"task-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        cap = self.cap_svc.issue_token(
            subject_identity="test",
            capability_name="read_repository_snapshot",
            scope_hash="scope:test",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            bound_task_id=task_id,
        )
        self.orch.admit_context(
            task_id=task_id,
            intent_id="i1",
            capability_token=cap,
            root_revision_id="rev-0",
            request={
                "repo_graph_version": "1",
                "symbol_index_version": "1",
                "candidate_file_ids": ["a.py"],
                "symbol_frontier_ids": [],
                "packing_policy_version": "p1",
                "actual_tokens": 10,
            },
        )
        cap_patch = self.cap_svc.issue_token(
            subject_identity="test",
            capability_name="propose_patch",
            scope_hash="scope:test",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            bound_task_id=task_id,
        )
        with self.assertRaises(OrchestratorRejected):
            self.orch.admit_patch_proposal(
                task_id=task_id,
                capability_token=cap_patch,
            )


class TestSealedRevisionImmutable(unittest.TestCase):
    """INV-005: sealed revision cannot be updated or deleted at SQL layer."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_update_sealed_raises(self) -> None:
        import sqlite3 as _sqlite3

        rev_repo = RevisionRepository(self.conn)
        rev_repo.insert_pending(
            {
                "revision_id": "rev-test",
                "parent_revision_id": None,
                "project_id": "p1",
                "task_id": "t1",
                "root_hash": "rh1",
                "snapshot_root_id": "snap-1",
                "intent_id": "i1",
                "originating_context_artifact_id": "ctx-1",
                "approval_id": None,
                "logical_sequence_at_seal": 0,
                "version_tuple_hash": "vth1:test",
                "taint_set": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        rev_repo.transition_to_sealed(
            revision_id="rev-test",
            sealed_at=datetime.now(timezone.utc).isoformat(),
            logical_sequence_at_seal=1,
            approval_id="ap-1",
        )
        # Sealed rows are immutable; SQLite RAISE(ABORT) may surface as
        # either OperationalError or IntegrityError depending on the
        # driver version, so we catch both.
        with self.assertRaises((_sqlite3.OperationalError, _sqlite3.IntegrityError)):
            self.conn.execute(
                "UPDATE revisions SET root_hash = 'tampered' WHERE revision_id = 'rev-test';"
            )


if __name__ == "__main__":
    unittest.main()
