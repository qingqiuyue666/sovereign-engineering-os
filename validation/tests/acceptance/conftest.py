"""
Shared fixtures for acceptance tests.

All acceptance tests share the same database bootstrap and service
wiring pattern. This conftest provides reusable helpers so each test
file stays focused on its specific AT-ID obligation.

Constitutional reference: foundation Section 5 (Acceptance Test Plan).
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import uuid4

# Ensure repo root is on the path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    BudgetRepository,
    CapabilityRepository,
    ContextArtifactRepository,
    DriftEventRecordRepository,
    FailureBundleRepository,
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
    TaintRepository,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.services.capability_service import CapabilityService
from kernel.services.context_service import ContextService
from kernel.services.inference_service import (
    InferenceService,
    InferencePolicy,
    ModelAdapter,
)
from kernel.services.budget_governor import BudgetGovernor
from kernel.services.patch_proposal_service import PatchProposalService
from kernel.services.validation_service import ValidationService
from kernel.services.review_service import ReviewService
from kernel.services.approval_service import ApprovalService
from kernel.services.revision_seal_service import RevisionSealService
from kernel.services.evidence_service import EvidenceService
from kernel.lifecycle.signable_path_orchestrator import SignablePathOrchestrator
from kernel.lifecycle.stage_types import Stage


class FakeModelAdapter:
    """Deterministic ModelAdapter for acceptance tests."""

    def invoke(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> Mapping[str, Any]:
        return {
            "output_text": "acceptance-test output text",
            "token_usage": {"input": 100, "output": 20},
            "latency_ms": 42,
            "model_route_id": "fake-model-v1",
        }


class AcceptanceHarness:
    """Fully-wired acceptance test harness.

    Creates an in-memory SQLite database, applies migrations, and wires
    all kernel services and the orchestrator. Tests use this to drive
    the narrow signable path end-to-end.
    """

    def __init__(
        self,
        actor_identity: str = "acceptance_test",
        *,
        inference_policy: InferencePolicy | None = None,
        default_hard_budget_tokens: int = 96_000,
    ) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)

        # Repositories.
        self.audit_repo = AuditRepository(self.conn)
        self.budget_repo = BudgetRepository(self.conn)
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
        self.taint_repo = TaintRepository(self.conn)
        self.drift_repo = DriftEventRecordRepository(self.conn)
        self.failure_repo = FailureBundleRepository(self.conn)

        # Audit ledger.
        self.audit_ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity=actor_identity,
        )

        # Services.
        self.cap_svc = CapabilityService(
            repository=self.cap_repo,
            audit_ledger=self.audit_ledger,
        )
        # AT-027 / INV-021: the phase-1 static budget policy values on
        # `ContextService` are constructor-overridable, so the
        # orchestrator's runtime allocation (which reads
        # `hard_budget_tokens` off the persisted ContextArtifact) picks
        # up the same number tests want to drive without forking a
        # parallel budget surface.
        self.ctx_svc = ContextService(
            repository=self.ctx_repo,
            audit_ledger=self.audit_ledger,
            hard_budget_tokens=default_hard_budget_tokens,
            effective_budget_tokens=min(
                default_hard_budget_tokens,
                # 96k effective is the phase-1 default; clamp to the
                # tighter hard budget when tests pick a smaller one.
                96_000 if default_hard_budget_tokens >= 96_000 else default_hard_budget_tokens,
            ),
        )
        # Per-task token-budget governor, wired into the inference
        # boundary. The orchestrator (not this harness) is responsible
        # for calling `allocate` at `admit_context`.
        self.budget_governor = BudgetGovernor(
            audit_ledger=self.audit_ledger,
            default_hard_budget_tokens=default_hard_budget_tokens,
            budget_repository=self.budget_repo,
        )
        self.inf_svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit_ledger,
            context_reader=self.ctx_repo,
            adapter=FakeModelAdapter(),
            policy=inference_policy or InferencePolicy(),
            budget_governor=self.budget_governor,
            failure_bundle_repository=self.failure_repo,
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
            taint_repository=self.taint_repo,
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
            # the production orchestrator-driven seal path enforces the
            # "intent_id must name a real intent_anchor_records row whose
            # task_id matches" check. The orchestrator already mints the
            # durable row at ``_emit_intent_anchor`` and threads the same
            # ``intent_id`` into ``seal_revision``; wiring the reader
            # promotes that linkage from opt-in (proven in
            # ``test_revision_seal_service_intent_id.py``) to always-on
            # in the production composition root.
            intent_anchor_reader=self.intent_repo,
        )
        self.evidence_svc = EvidenceService(
            replay_anchor_repo=self.ra_repo,
            revision_repo=self.rev_repo,
            context_repo=self.ctx_repo,
            inference_repo=self.inf_repo,
            approval_repo=self.ap_repo,
            taint_repo=self.taint_repo,
            budget_repo=self.budget_repo,
            drift_repo=self.drift_repo,
            failure_repo=self.failure_repo,
            journal_repo=self.je_repo,
            review_repo=self.rv_repo,
            capability_repo=self.cap_repo,
            audit_repo=self.audit_repo,
            audit_ledger=self.audit_ledger,
        )

        # Orchestrator. The budget governor and context repository are
        # passed in so the orchestrator can perform real runtime budget
        # allocation at `admit_context` (AT-027 / INV-021).
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
            budget_governor=self.budget_governor,
            context_repository=self.ctx_repo,
            intent_anchor_repository=self.intent_repo,
            connection=self.conn,
        )

    def close(self) -> None:
        self.conn.close()

    def issue_capability(
        self,
        name: str,
        task_id: str,
        *,
        single_use: bool = True,
        ttl_hours: int = 1,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return self.cap_svc.issue_token(
            subject_identity="acceptance_test",
            capability_name=name,
            scope_hash="scope:acceptance",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
            single_use=single_use,
            bound_task_id=task_id,
        )

    def run_full_happy_path(self, task_id: str | None = None) -> dict[str, str]:
        """Run the full eight-stage signable path, returning artifact IDs."""
        task_id = task_id or f"task-{uuid4().hex[:8]}"
        intent_id = f"intent-{uuid4().hex[:8]}"
        root_rev_id = "rev-genesis-000"

        # NOTE: budget allocation happens inside `admit_context` via the
        # orchestrator (AT-027 / INV-021). The harness intentionally
        # does NOT pre-seed budget state, so AT-027 tests exercise the
        # real runtime path.
        cap_ctx = self.issue_capability("read_repository_snapshot", task_id)
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

        cap_inf = self.issue_capability("invoke_inference", task_id)
        inf_id = self.orch.admit_inference(
            task_id=task_id,
            capability_token=cap_inf,
            worker_profile="acceptance_worker",
            model_route_id="fake-model-v1",
        )

        cap_patch = self.issue_capability("propose_patch", task_id)
        pp_id = self.orch.admit_patch_proposal(
            task_id=task_id,
            capability_token=cap_patch,
        )
        cap_validation = self.issue_capability("run_validation_quarantine", task_id)
        vr_id = self.orch.admit_validation(
            task_id=task_id,
            capability_token=cap_validation,
        )
        cap_review = self.issue_capability("render_review", task_id)
        rv_id = self.orch.admit_review(
            task_id=task_id,
            capability_token=cap_review,
        )
        cap_approval = self.issue_capability("grant_approval", task_id)
        ap_id = self.orch.admit_approval(
            task_id=task_id,
            capability_token=cap_approval,
        )
        cap_seal = self.issue_capability("seal_revision", task_id)
        rev_id = self.orch.admit_revision_seal(
            task_id=task_id,
            capability_token=cap_seal,
        )
        cap_evidence = self.issue_capability("append_evidence", task_id)
        ra_id = self.orch.admit_evidence(
            task_id=task_id,
            capability_token=cap_evidence,
        )

        return {
            "task_id": task_id,
            "intent_id": intent_id,
            "root_revision_id": root_rev_id,
            "context_artifact_id": ctx_id,
            "inference_artifact_id": inf_id,
            "patch_proposal_id": pp_id,
            "validation_receipt_id": vr_id,
            "review_artifact_id": rv_id,
            "approval_id": ap_id,
            "revision_id": rev_id,
            "replay_anchor_id": ra_id,
        }

    def run_through_stage(self, task_id: str, target_stage: Stage) -> dict[str, str]:
        """Run the signable path up to (and including) the target stage."""
        intent_id = f"intent-{uuid4().hex[:8]}"
        root_rev_id = "rev-genesis-000"
        ids: dict[str, str] = {
            "task_id": task_id,
            "intent_id": intent_id,
            "root_revision_id": root_rev_id,
        }
        # See `run_full_happy_path` re: runtime budget allocation.

        stage_order = [
            Stage.CONTEXT, Stage.INFERENCE, Stage.PATCH_PROPOSAL,
            Stage.VALIDATION, Stage.REVIEW, Stage.APPROVAL,
            Stage.REVISION_SEAL, Stage.EVIDENCE,
        ]

        for stage in stage_order:
            if stage == Stage.CONTEXT:
                cap = self.issue_capability("read_repository_snapshot", task_id)
                ids["context_artifact_id"] = self.orch.admit_context(
                    task_id=task_id,
                    intent_id=intent_id,
                    capability_token=cap,
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
            elif stage == Stage.INFERENCE:
                cap = self.issue_capability("invoke_inference", task_id)
                ids["inference_artifact_id"] = self.orch.admit_inference(
                    task_id=task_id,
                    capability_token=cap,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )
            elif stage == Stage.PATCH_PROPOSAL:
                cap = self.issue_capability("propose_patch", task_id)
                ids["patch_proposal_id"] = self.orch.admit_patch_proposal(
                    task_id=task_id,
                    capability_token=cap,
                )
            elif stage == Stage.VALIDATION:
                cap = self.issue_capability("run_validation_quarantine", task_id)
                ids["validation_receipt_id"] = self.orch.admit_validation(
                    task_id=task_id,
                    capability_token=cap,
                )
            elif stage == Stage.REVIEW:
                cap = self.issue_capability("render_review", task_id)
                ids["review_artifact_id"] = self.orch.admit_review(
                    task_id=task_id,
                    capability_token=cap,
                )
            elif stage == Stage.APPROVAL:
                cap = self.issue_capability("grant_approval", task_id)
                ids["approval_id"] = self.orch.admit_approval(
                    task_id=task_id,
                    capability_token=cap,
                )
            elif stage == Stage.REVISION_SEAL:
                cap = self.issue_capability("seal_revision", task_id)
                ids["revision_id"] = self.orch.admit_revision_seal(
                    task_id=task_id,
                    capability_token=cap,
                )
            elif stage == Stage.EVIDENCE:
                cap = self.issue_capability("append_evidence", task_id)
                ids["replay_anchor_id"] = self.orch.admit_evidence(
                    task_id=task_id,
                    capability_token=cap,
                )

            if stage == target_stage:
                break

        return ids
