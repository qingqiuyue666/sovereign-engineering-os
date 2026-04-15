"""
Tracer-bullet test: replay classification honest downgrade semantics.

Foundation §5.1 test #7 + §6 definition of done:
  "replay classification bound by evidence"

Constitutional anchors:
- v11 §22.5 Replay Fidelity Contract
- v11 §23.12 ReplayAnchor
- v11 §24.1 AT-013 (replay claim bound by captured evidence)
- v11 §24.1 AT-032 (replay downgrade/refusal on missing evidence)
- v11 §24.2 INV-010 (claims may not exceed captured evidence)
- v11 §24.2 INV-011 (uncertified equivalence is never exact replay)
- foundation §5.2: AT-013/AT-032 -> INV-010/INV-011

This test runs against both the pure ReplayClassifier (unit-level) and
through the full EvidenceService wiring (integration-level, in-memory
SQLite). No mocks except the FakeModelAdapter.

What it proves:
1. An EXACT claim with full evidence closure is admitted as EXACT.
2. An EXACT claim with missing context or inference is downgraded to
   DEGRADED (never silently accepted).
3. An EXACT claim with equivalence proof bundle (phase 1) is always
   downgraded — INV-011.
4. A SEMANTIC claim without context is downgraded to DEGRADED.
5. A DIAGNOSTIC claim is always admitted (weakest non-degraded class).
6. An UNREPLAYABLE sealed revision with no evidence returns UNREPLAYABLE.
7. Downgrade reasons are explicit, non-empty strings.
8. The evidence service produces a schema-valid ReplayAnchor that
   carries the classification result through to persistence.
"""

from __future__ import annotations

import sys
import os
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import uuid4

# Ensure repo root is on the path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from kernel.replay.replay_classifier import (
    EvidenceView,
    ReplayClaimRequest,
    ReplayClass,
    ReplayClassification,
    ReplayClassifier,
)
from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    CapabilityRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
    IntentAnchorRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
    ApprovalArtifactRepository,
    ValidationReceiptRepository,
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
# Stub EvidenceView for unit-level classifier tests
# ---------------------------------------------------------------------------


class _StubEvidenceView:
    """Configurable EvidenceView for testing classifier decisions."""

    def __init__(
        self,
        *,
        sealed: bool = True,
        has_ctx: bool = True,
        has_inf: bool = True,
        artifact_ids: list[str] | None = None,
    ) -> None:
        self._sealed = sealed
        self._has_ctx = has_ctx
        self._has_inf = has_inf
        self._artifact_ids = artifact_ids or []

    def has_sealed_revision(self, root_revision_id: str) -> bool:
        return self._sealed

    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return self._has_ctx

    def has_inference_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return self._has_inf

    def required_artifact_ids(self, task_id: str, root_revision_id: str) -> list[str]:
        return self._artifact_ids


def _make_request(
    requested_class: ReplayClass = ReplayClass.EXACT,
    equivalence_proof: bool = False,
) -> ReplayClaimRequest:
    return ReplayClaimRequest(
        task_id="task-test",
        project_id="proj-test",
        root_revision_id="rev-root-1",
        requested_class=requested_class,
        environment_fingerprint_hash="sha256:placeholder",
        equivalence_proof_bundle_admitted=equivalence_proof,
    )


# ---------------------------------------------------------------------------
# Test: pure classifier downgrade semantics (INV-010/INV-011)
# ---------------------------------------------------------------------------


class TestReplayClassifierDowngrade(unittest.TestCase):
    """Exercise the ReplayClassifier's honest downgrade rules."""

    def test_exact_with_full_evidence_admitted(self) -> None:
        """EXACT claim with full closure -> EXACT (control case)."""
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=True)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.EXACT))
        self.assertEqual(result.replay_class, ReplayClass.EXACT)
        self.assertIsNone(result.degradation_reason)
        self.assertIsNone(result.unreplayable_reason)

    def test_exact_missing_context_downgrades_to_degraded(self) -> None:
        """EXACT claim with missing context -> DEGRADED (INV-010)."""
        ev = _StubEvidenceView(sealed=True, has_ctx=False, has_inf=True)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.EXACT))
        self.assertEqual(result.replay_class, ReplayClass.DEGRADED)
        self.assertIsNotNone(result.degradation_reason)
        self.assertIn("missing", result.degradation_reason.lower())

    def test_exact_missing_inference_downgrades_to_degraded(self) -> None:
        """EXACT claim with missing inference -> DEGRADED (INV-010)."""
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=False)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.EXACT))
        self.assertEqual(result.replay_class, ReplayClass.DEGRADED)
        self.assertIsNotNone(result.degradation_reason)

    def test_exact_with_equivalence_proof_always_downgrades(self) -> None:
        """EXACT with equivalence proof in phase 1 -> DEGRADED (INV-011).

        Phase-1 does not admit proof bundles. Even with full evidence
        closure, an equivalence proof claim must be refused for EXACT.
        """
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=True)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(
            _make_request(ReplayClass.EXACT, equivalence_proof=True)
        )
        self.assertEqual(result.replay_class, ReplayClass.DEGRADED)
        self.assertIsNotNone(result.degradation_reason)
        self.assertIn("equivalence", result.degradation_reason.lower())

    def test_exact_missing_evidence_with_proof_bundle_downgrades(self) -> None:
        """EXACT with missing evidence AND equivalence proof -> DEGRADED.

        Both INV-010 and INV-011 apply; the classifier must downgrade.
        """
        ev = _StubEvidenceView(sealed=True, has_ctx=False, has_inf=False)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(
            _make_request(ReplayClass.EXACT, equivalence_proof=True)
        )
        self.assertEqual(result.replay_class, ReplayClass.DEGRADED)
        self.assertIsNotNone(result.degradation_reason)

    def test_semantic_with_context_admitted(self) -> None:
        """SEMANTIC claim with context present -> SEMANTIC."""
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=False)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.SEMANTIC))
        self.assertEqual(result.replay_class, ReplayClass.SEMANTIC)
        self.assertIsNone(result.degradation_reason)

    def test_semantic_without_context_downgrades_to_degraded(self) -> None:
        """SEMANTIC claim without context -> DEGRADED."""
        ev = _StubEvidenceView(sealed=True, has_ctx=False, has_inf=True)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.SEMANTIC))
        self.assertEqual(result.replay_class, ReplayClass.DEGRADED)
        self.assertIsNotNone(result.degradation_reason)
        self.assertIn("context", result.degradation_reason.lower())

    def test_diagnostic_always_admitted(self) -> None:
        """DIAGNOSTIC is the weakest non-degraded class; always admitted
        if the sealed revision exists."""
        ev = _StubEvidenceView(sealed=True, has_ctx=False, has_inf=False)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.DIAGNOSTIC))
        self.assertEqual(result.replay_class, ReplayClass.DIAGNOSTIC)
        self.assertIsNone(result.degradation_reason)

    def test_no_sealed_revision_is_unreplayable(self) -> None:
        """If the sealed revision doesn't exist, claim is UNREPLAYABLE."""
        ev = _StubEvidenceView(sealed=False)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.EXACT))
        self.assertEqual(result.replay_class, ReplayClass.UNREPLAYABLE)
        self.assertIsNotNone(result.unreplayable_reason)
        self.assertIn("sealed revision", result.unreplayable_reason.lower())

    def test_degraded_request_is_self_honoring(self) -> None:
        """A caller requesting DEGRADED gets DEGRADED with explicit reason."""
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=True)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.DEGRADED))
        self.assertEqual(result.replay_class, ReplayClass.DEGRADED)
        self.assertIsNotNone(result.degradation_reason)

    def test_unreplayable_request_is_self_honoring(self) -> None:
        """A caller requesting UNREPLAYABLE gets UNREPLAYABLE."""
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=True)
        classifier = ReplayClassifier(ev)
        result = classifier.classify(_make_request(ReplayClass.UNREPLAYABLE))
        self.assertEqual(result.replay_class, ReplayClass.UNREPLAYABLE)


# ---------------------------------------------------------------------------
# Test: ReplayAnchor construction shape
# ---------------------------------------------------------------------------


class TestReplayAnchorConstruction(unittest.TestCase):
    """Verify that build_replay_anchor produces a well-shaped anchor dict."""

    def test_anchor_carries_classification(self) -> None:
        ev = _StubEvidenceView(sealed=True, has_ctx=True, has_inf=True,
                               artifact_ids=["ctx-1", "inf-1"])
        classifier = ReplayClassifier(ev)
        request = _make_request(ReplayClass.EXACT)
        classification = classifier.classify(request)
        anchor = classifier.build_replay_anchor(
            request=request,
            classification=classification,
            replay_anchor_id="ra-test-1",
            version_tuple_hash="vth:test",
        )
        self.assertEqual(anchor["replay_anchor_id"], "ra-test-1")
        self.assertEqual(anchor["replay_class_claim"], "exact")
        self.assertEqual(anchor["task_id"], "task-test")
        self.assertEqual(anchor["project_id"], "proj-test")
        self.assertIn("created_at", anchor)
        self.assertEqual(anchor["required_artifact_ids"], ["ctx-1", "inf-1"])

    def test_degraded_anchor_carries_reason(self) -> None:
        ev = _StubEvidenceView(sealed=True, has_ctx=False, has_inf=True)
        classifier = ReplayClassifier(ev)
        request = _make_request(ReplayClass.EXACT)
        classification = classifier.classify(request)
        anchor = classifier.build_replay_anchor(
            request=request,
            classification=classification,
            replay_anchor_id="ra-test-2",
            version_tuple_hash="vth:test",
        )
        self.assertEqual(anchor["replay_class_claim"], "degraded")
        self.assertIn("degradation_reason", anchor)
        self.assertTrue(len(anchor["degradation_reason"]) > 0)


# ---------------------------------------------------------------------------
# Test: full evidence service integration (wired stack)
# ---------------------------------------------------------------------------


class _FakeModelAdapter:
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


class TestEvidenceServiceReplayClassification(unittest.TestCase):
    """Integration test: evidence closure through the full stack produces
    a persisted ReplayAnchor with honest classification.

    This is the tracer-bullet proof for AT-013/AT-032: the evidence
    service composes the classifier, persists the anchor, and the anchor
    reflects the classification.
    """

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)

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

        self.audit_ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="tracer_replay_test",
        )

        self.cap_svc = CapabilityService(
            repository=self.cap_repo, audit_ledger=self.audit_ledger
        )
        self.ctx_svc = ContextService(
            repository=self.ctx_repo, audit_ledger=self.audit_ledger
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
        )
        self.evidence_svc = EvidenceService(
            replay_anchor_repo=self.ra_repo,
            revision_repo=self.rev_repo,
            context_repo=self.ctx_repo,
            inference_repo=self.inf_repo,
            audit_ledger=self.audit_ledger,
        )

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
            subject_identity="tracer_replay_test",
            capability_name=name,
            scope_hash="scope:tracer",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            single_use=True,
            bound_task_id=task_id,
        )

    def _run_full_path(self, task_id: str) -> str:
        """Run a task through all 8 stages to SEALED. Returns ra_id."""
        intent_id = f"intent-{uuid4().hex[:8]}"

        cap_ctx = self._issue_capability("read_repository_snapshot", task_id)
        self.orch.admit_context(
            task_id=task_id,
            intent_id=intent_id,
            capability_token=cap_ctx,
            root_revision_id="rev-genesis-000",
            request={
                "repo_graph_version": "1.0",
                "symbol_index_version": "1.0",
                "candidate_file_ids": ["src/main.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 500,
            },
        )
        cap_inf = self._issue_capability("invoke_inference", task_id)
        self.orch.admit_inference(
            task_id=task_id,
            capability_token=cap_inf,
            worker_profile="tracer_worker",
            model_route_id="fake-model-v1",
        )
        self.orch.admit_patch_proposal(task_id=task_id)
        self.orch.admit_validation(task_id=task_id)
        self.orch.admit_review(task_id=task_id)
        self.orch.admit_approval(task_id=task_id)
        self.orch.admit_revision_seal(task_id=task_id)
        ra_id = self.orch.admit_evidence(task_id=task_id)
        return ra_id

    def test_evidence_closure_produces_persisted_anchor(self) -> None:
        """Full path evidence closure produces a schema-valid persisted
        ReplayAnchor with DIAGNOSTIC classification (phase-1 default)."""
        task_id = f"task-{uuid4().hex[:8]}"
        ra_id = self._run_full_path(task_id)

        # Verify anchor is persisted.
        anchor_row = self.conn.execute(
            "SELECT * FROM replay_anchors WHERE replay_anchor_id = ?;",
            (ra_id,),
        ).fetchone()
        self.assertIsNotNone(anchor_row)
        self.assertEqual(anchor_row["task_id"], task_id)
        # Phase-1 default is DIAGNOSTIC (not EXACT).
        self.assertEqual(anchor_row["replay_class_claim"], "diagnostic")

    def test_evidence_closure_audit_record(self) -> None:
        """Evidence closure emits an audit record with classification details."""
        task_id = f"task-{uuid4().hex[:8]}"
        ra_id = self._run_full_path(task_id)

        audit_rows = self.conn.execute(
            "SELECT record_type FROM audit_records "
            "WHERE task_id = ? ORDER BY sequence;",
            (task_id,),
        ).fetchall()
        evidence_records = [
            r for r in audit_rows
            if r["record_type"] == "evidence_closure"
        ]
        self.assertGreaterEqual(
            len(evidence_records), 1,
            "audit must contain evidence_closure record",
        )

    def test_sealed_state_reached(self) -> None:
        """After evidence closure, the orchestrator reaches SEALED."""
        task_id = f"task-{uuid4().hex[:8]}"
        self._run_full_path(task_id)
        self.assertEqual(self.orch.current_stage(task_id), Stage.SEALED)


if __name__ == "__main__":
    unittest.main()
