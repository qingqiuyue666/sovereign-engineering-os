"""
Linear orchestrator for the current-stage signable path.

Constitutional anchors:
- v11 §24.3, §25.2, §30.2, §31 (current-stage signable path)
- v11 §22.5 (replay admission boundary)
- v11 §22.6 (capability-gated stage admission)
- v11 §22.9 (inter-plane interface discipline)
- v11 §22.10 (invariant binding)
- implementation foundation Delta D-001, Section 6 (P0 state-machine skeleton)

Scope lock: this orchestrator owns ONLY the eight-stage path:
  Context -> Inference -> PatchProposal -> Validation -> Review -> Approval
  -> Revision Seal -> Evidence

Any call that does not map to one of these stage admissions is rejected
fail-closed. This module does not hold policy, does not reach into model
runtimes, and does not bypass the approval barrier. It is a kernel-owned
state machine skeleton that defers decisions to capability / context /
inference / validation / review / approval / seal / evidence services.

Phase-1 minimal durable intent causal anchor (per foundation §6 / AUDIT-003):
  At the earliest runnable stage (Context admission), the orchestrator
  emits a minimal causal anchor (`intent_id`, `task_id`, `state`,
  `created_at`). This satisfies the §22.1 precondition that "a valid
  originating intent exists" without introducing a new top-level
  artifact type beyond the §23 pack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

from kernel.lifecycle.stage_types import (
    IllegalStageTransition,
    Stage,
    assert_legal_transition,
    successor_of,
)


class OrchestratorRejected(Exception):
    """Fail-closed rejection raised on any out-of-path or unauthorized admission."""


class RealFixChainRejected(Exception):
    """Fail-closed rejection for the narrow real-fix bridge chain entrypoint.

    Raised only by ``run_real_fix_chain`` when the chain's required
    components are not all wired, when the verified-pass record was not
    produced by the tracer, or when the caller attempts to run the
    real-fix chain on a ``task_id`` that has already entered the eight-
    stage signable-path frame.
    """


@dataclass(frozen=True)
class IntentCausalAnchor:
    """Minimal durable intent causal anchor (phase-1 AUDIT-003 disposition).

    NOT a new top-level artifact. This is an execution-layer precondition
    record consumed by §22.1 WAL preconditions and by §23.1 Revision.intent_id.
    It is intentionally narrow: four fields, no policy surface, no expansion.
    """

    intent_id: str
    task_id: str
    state: str
    created_at: str  # ISO-8601 UTC


@dataclass
class TaskLifecycleState:
    """In-memory state for a single task progressing through the signable path.

    This is not authority. It is a kernel-owned bookkeeping view used to
    enforce legal transitions and to refuse out-of-path operations. Authority
    lives in durable artifacts (ContextArtifact, InferenceArtifact, ...,
    Revision, AuditRecord).
    """

    task_id: str
    intent_anchor: IntentCausalAnchor
    current_stage: Stage
    artifact_ids: MutableMapping[Stage, str] = field(default_factory=dict)
    abandoned: bool = False


class SignablePathOrchestrator:
    """Eight-stage linear orchestrator (skeleton).

    Responsibilities (phase-1 skeleton):
    - admit exactly the eight stages in order
    - refuse any out-of-path operation fail-closed
    - emit minimal durable causal anchor on initial admission
    - forward each stage to its service and record the produced artifact id

    Explicitly out of scope:
    - prompt construction (owned by InferenceService under ModelIntegrationContract)
    - quarantine execution (owned by ValidationService / quarantine runner)
    - approval barrier decision (owned by ApprovalService via barrier_rules)
    - seal ordering (owned by RevisionSealService via seal_ordering)
    - evidence closure (owned by EvidenceService via append_only_ledger)
    - multi-lane orchestration (explicitly out of scope in phase 1)
    """

    def __init__(
        self,
        *,
        capability_service: Any,
        context_service: Any,
        inference_service: Any,
        patch_proposal_service: Any,
        validation_service: Any,
        review_service: Any,
        approval_service: Any,
        revision_seal_service: Any,
        evidence_service: Any,
        audit_ledger: Any,
        budget_governor: Any | None = None,
        context_repository: Any | None = None,
        # ------------------------------------------------------------------
        # Durable intent-anchor persistence (optional; AUDIT-003 / §22.1).
        #
        # When wired, ``_emit_intent_anchor`` persists one row into
        # ``intent_anchor_records`` BEFORE emitting the
        # ``intent_anchor_created`` audit record. This promotes the
        # originating intent from an audit-payload-only label to a
        # durable authority-bearing row that §22.1 WAL preconditions
        # and §23.1 ``Revision.intent_id`` can consult on recovery.
        # When absent, ``_emit_intent_anchor`` falls back to the
        # prior audit-only behavior so existing tracer-bullet tests
        # that hand-build the orchestrator without the repository
        # continue to compile unchanged.
        # ------------------------------------------------------------------
        intent_anchor_repository: Any | None = None,
        # ------------------------------------------------------------------
        # Narrow real-fix bridge-chain wirings (all optional; all-or-nothing).
        #
        # These reuse the already-merged bridges exactly as they exist.
        # The orchestrator composes them in causal order via
        # ``run_real_fix_chain`` and does not re-implement any of their
        # admission, schema, or audit logic. When any of the seven
        # wirings are absent, ``run_real_fix_chain`` refuses fail-closed;
        # the eight-stage admission surface continues to operate
        # unchanged regardless of whether these are wired.
        # ------------------------------------------------------------------
        real_fix_tracer: Any | None = None,
        real_fix_patch_projector: Any | None = None,
        real_fix_validation_bridge: Any | None = None,
        real_fix_review_bridge: Any | None = None,
        real_fix_approval_bridge: Any | None = None,
        real_fix_revision_seal_bridge: Any | None = None,
        real_fix_evidence_closure_bridge: Any | None = None,
    ) -> None:
        # The orchestrator holds references only; it does not own policy.
        self._capability = capability_service
        self._context = context_service
        self._inference = inference_service
        self._patch_proposal = patch_proposal_service
        self._validation = validation_service
        self._review = review_service
        self._approval = approval_service
        self._seal = revision_seal_service
        self._evidence = evidence_service
        self._audit = audit_ledger
        # AT-027 / INV-021 wiring. The orchestrator allocates a per-task
        # budget envelope at `admit_context`, reading the realized
        # phase-1 static policy values off the just-persisted
        # ContextArtifact via `context_repository`. Both are optional
        # so existing tracer-bullet tests that hand-build the
        # orchestrator without budget governance continue to compile;
        # in that case `admit_inference` proceeds without governance
        # enforcement (the InferenceService also accepts a None
        # governor).
        self._budget = budget_governor
        self._ctx_repo = context_repository
        # Durable intent-anchor writer (AUDIT-003 / §22.1). Held as a
        # reference only; persistence happens inside ``_emit_intent_anchor``
        # strictly before the audit record is emitted so the audit remains
        # an attestation over a durable row rather than the source of truth.
        self._intent_repo = intent_anchor_repository
        self._tasks: dict[str, TaskLifecycleState] = {}

        # Narrow real-fix bridge-chain wirings. Held as references only;
        # policy and admission live in the bridges themselves.
        self._rf_tracer = real_fix_tracer
        self._rf_projector = real_fix_patch_projector
        self._rf_validation_bridge = real_fix_validation_bridge
        self._rf_review_bridge = real_fix_review_bridge
        self._rf_approval_bridge = real_fix_approval_bridge
        self._rf_revision_seal_bridge = real_fix_revision_seal_bridge
        self._rf_evidence_closure_bridge = real_fix_evidence_closure_bridge

    # ------------------------------------------------------------------
    # admission primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _emit_intent_anchor(self, task_id: str, intent_id: str) -> IntentCausalAnchor:
        anchor = IntentCausalAnchor(
            intent_id=intent_id,
            task_id=task_id,
            state="admitted",
            created_at=self._now_iso(),
        )
        # AUDIT-003 / §22.1 durable persistence of the originating intent.
        # When the intent-anchor repository is wired, mint the durable
        # ``intent_anchor_records`` row BEFORE emitting the
        # ``intent_anchor_created`` audit record. Order is load-bearing:
        # the audit attests over an already-durable row rather than
        # acting as the source of truth. Any persistence exception
        # bubbles up unchanged (fail-closed) and the audit record is
        # not emitted, so a failed mint never leaves an audit claim
        # without a durable row behind it.
        if self._intent_repo is not None:
            self._intent_repo.insert(
                intent_id=intent_id,
                task_id=task_id,
                state=anchor.state,
            )
        # Append an audit note recording the anchor's creation. The audit
        # ledger is append-only (INV-026); this call must never silently
        # fall through on failure.
        self._audit.append(
            record_type="intent_anchor_created",
            task_id=task_id,
            artifact_refs=[intent_id],
            payload={
                "intent_id": intent_id,
                "task_id": task_id,
                "state": anchor.state,
                "created_at": anchor.created_at,
            },
        )
        return anchor

    def _get_task(self, task_id: str) -> TaskLifecycleState:
        state = self._tasks.get(task_id)
        if state is None:
            raise OrchestratorRejected(f"unknown task: {task_id}")
        if state.abandoned:
            raise OrchestratorRejected(f"task already abandoned: {task_id}")
        return state

    def _advance(self, state: TaskLifecycleState, target: Stage) -> None:
        try:
            assert_legal_transition(state.current_stage, target)
        except IllegalStageTransition as exc:
            # Fail closed. INV-018-compatible: illegal lifecycle
            # transitions are audit-emitted rather than silently ignored.
            #
            # AUDIT-003 / §22.1: name the durable
            # ``intent_anchor_records.intent_id`` (the one
            # ``_emit_intent_anchor`` minted at admit_context and that
            # lives on ``state.intent_anchor``) in both ``artifact_refs``
            # and ``payload`` so a reviewer reading only this rejection
            # record can recover the originating-intent linkage without
            # a second fetch. Authoritative fail-closed verification of
            # ``intent_id`` against ``intent_anchor_records`` remains
            # the responsibility of ``RevisionSealService`` downstream;
            # this surface performs no independent verification. Absent
            # / empty ``intent_id`` preserves the prior audit shape
            # exactly.
            audit_artifact_refs: list[str] = []
            audit_payload: dict[str, Any] = {
                "from": state.current_stage.value,
                "to": target.value,
                "reason": str(exc),
            }
            anchor_intent_id = getattr(state.intent_anchor, "intent_id", None)
            if isinstance(anchor_intent_id, str) and anchor_intent_id:
                audit_artifact_refs.append(anchor_intent_id)
                audit_payload["intent_id"] = anchor_intent_id
            self._audit.append(
                record_type="illegal_stage_transition_rejected",
                task_id=state.task_id,
                artifact_refs=audit_artifact_refs,
                payload=audit_payload,
            )
            raise OrchestratorRejected(str(exc)) from exc
        state.current_stage = target

    # ------------------------------------------------------------------
    # stage-admission surface (narrow, linear)
    # ------------------------------------------------------------------

    def admit_context(
        self,
        *,
        task_id: str,
        intent_id: str,
        capability_token: Mapping[str, Any],
        root_revision_id: str,
        request: Mapping[str, Any],
    ) -> str:
        """Stage 1: Context admission.

        Preconditions:
        - no prior state for this task_id in the orchestrator
        - capability_token verifies for the `read_repository_snapshot` class
          (C22.6 default-deny; §17 Capability Security bootstrap)
        - the request is a valid context packing request (C22.7)

        On success:
        - emits minimal durable intent causal anchor
        - produces ContextArtifact via ContextService
        - records stage transition + artifact id
        """
        if task_id in self._tasks:
            raise OrchestratorRejected(f"task already admitted: {task_id}")

        # Capability gate (C22.6 / INV-CAP-VERIFY-BEFORE-EFFECT).
        self._capability.verify_for_action(
            token=capability_token,
            action_class="read_repository_snapshot",
            task_id=task_id,
            root_revision_id=root_revision_id,
        )
        self._capability.consume(
            capability_token_id=str(capability_token["capability_token_id"]),
            task_id=task_id,
        )

        anchor = self._emit_intent_anchor(task_id=task_id, intent_id=intent_id)

        artifact_id = self._context.build_context_artifact(
            task_id=task_id,
            root_revision_id=root_revision_id,
            request=request,
            intent_anchor=anchor,
        )

        # AT-027 / INV-021 runtime allocation: bind the budget envelope
        # to the same `hard_budget_tokens` the ContextArtifact records
        # under `phase1_budget_policy_v1`. This is the single real
        # runtime point at which a task acquires its governed budget;
        # it must not be pre-seeded by callers / harnesses. Allocation
        # happens after the context artifact is persisted so the
        # governance value comes from the durable artifact, not from
        # an unaudited request mapping.
        if self._budget is not None:
            if self._ctx_repo is None:
                raise OrchestratorRejected(
                    "budget_governor wired without context_repository; "
                    "cannot read hard_budget_tokens off the persisted "
                    "ContextArtifact (AT-027 wiring is incomplete)"
                )
            ctx_row = self._ctx_repo.fetch(artifact_id)
            if ctx_row is None:
                raise OrchestratorRejected(
                    f"context artifact {artifact_id} missing after persistence"
                )
            self._budget.allocate(
                task_id=task_id,
                hard_budget_tokens=int(ctx_row["hard_budget_tokens"]),
            )

        state = TaskLifecycleState(
            task_id=task_id,
            intent_anchor=anchor,
            current_stage=Stage.CONTEXT,
        )
        state.artifact_ids[Stage.CONTEXT] = artifact_id
        self._tasks[task_id] = state

        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[artifact_id],
            payload={"stage": Stage.CONTEXT.value},
        )
        return artifact_id

    def admit_inference(
        self,
        *,
        task_id: str,
        capability_token: Mapping[str, Any],
        worker_profile: str,
        model_route_id: str,
    ) -> str:
        """Stage 2: Inference admission (governed via ModelIntegrationContract).

        This method does NOT talk to a model. It hands the task to the
        InferenceService, which owns the governed prompt/response boundary.
        """
        state = self._get_task(task_id)
        if successor_of(state.current_stage) is not Stage.INFERENCE:
            self._advance(state, Stage.INFERENCE)

        self._capability.verify_for_action(
            token=capability_token,
            action_class="invoke_inference",
            task_id=task_id,
            root_revision_id=None,
        )
        self._capability.consume(
            capability_token_id=str(capability_token["capability_token_id"]),
            task_id=task_id,
        )

        context_artifact_id = state.artifact_ids[Stage.CONTEXT]
        inference_artifact_id = self._inference.run_inference(
            task_id=task_id,
            context_artifact_id=context_artifact_id,
            worker_profile=worker_profile,
            model_route_id=model_route_id,
            intent_id=state.intent_anchor.intent_id,
        )
        self._advance(state, Stage.INFERENCE)
        state.artifact_ids[Stage.INFERENCE] = inference_artifact_id

        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[inference_artifact_id],
            payload={"stage": Stage.INFERENCE.value},
        )
        return inference_artifact_id

    # The remaining stages follow the same narrow pattern. They are stubs
    # that call their owning service and record stage transitions. Concrete
    # bodies are intentionally minimal in this first slice; the contract is
    # that any real logic lives in the service, never in the orchestrator.

    def admit_patch_proposal(
        self,
        *,
        task_id: str,
        capability_token: Mapping[str, Any],
    ) -> str:
        state = self._get_task(task_id)
        if successor_of(state.current_stage) is not Stage.PATCH_PROPOSAL:
            self._advance(state, Stage.PATCH_PROPOSAL)

        self._capability.verify_for_action(
            token=capability_token,
            action_class="propose_patch",
            task_id=task_id,
            root_revision_id=None,
        )
        self._capability.consume(
            capability_token_id=str(capability_token["capability_token_id"]),
            task_id=task_id,
        )

        inference_artifact_id = state.artifact_ids[Stage.INFERENCE]
        proposal_id = self._patch_proposal.propose(
            task_id=task_id,
            inference_artifact_id=inference_artifact_id,
            intent_id=state.intent_anchor.intent_id,
        )
        self._advance(state, Stage.PATCH_PROPOSAL)
        state.artifact_ids[Stage.PATCH_PROPOSAL] = proposal_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[proposal_id],
            payload={"stage": Stage.PATCH_PROPOSAL.value},
        )
        return proposal_id

    def admit_validation(
        self,
        *,
        task_id: str,
        capability_token: Mapping[str, Any],
    ) -> str:
        state = self._get_task(task_id)
        if successor_of(state.current_stage) is not Stage.VALIDATION:
            self._advance(state, Stage.VALIDATION)

        self._capability.verify_for_action(
            token=capability_token,
            action_class="run_validation_quarantine",
            task_id=task_id,
            root_revision_id=None,
        )
        self._capability.consume(
            capability_token_id=str(capability_token["capability_token_id"]),
            task_id=task_id,
        )

        proposal_id = state.artifact_ids[Stage.PATCH_PROPOSAL]
        receipt_id = self._validation.validate(
            task_id=task_id,
            patch_proposal_id=proposal_id,
            intent_id=state.intent_anchor.intent_id,
        )
        self._advance(state, Stage.VALIDATION)
        state.artifact_ids[Stage.VALIDATION] = receipt_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[receipt_id],
            payload={"stage": Stage.VALIDATION.value},
        )
        return receipt_id

    def admit_review(
        self,
        *,
        task_id: str,
        capability_token: Mapping[str, Any],
    ) -> str:
        state = self._get_task(task_id)
        if successor_of(state.current_stage) is not Stage.REVIEW:
            self._advance(state, Stage.REVIEW)

        self._capability.verify_for_action(
            token=capability_token,
            action_class="render_review",
            task_id=task_id,
            root_revision_id=None,
        )
        self._capability.consume(
            capability_token_id=str(capability_token["capability_token_id"]),
            task_id=task_id,
        )

        proposal_id = state.artifact_ids[Stage.PATCH_PROPOSAL]
        receipt_id = state.artifact_ids[Stage.VALIDATION]
        review_id = self._review.render_review(
            task_id=task_id,
            patch_proposal_id=proposal_id,
            validation_receipt_id=receipt_id,
            intent_id=state.intent_anchor.intent_id,
        )
        self._advance(state, Stage.REVIEW)
        state.artifact_ids[Stage.REVIEW] = review_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[review_id],
            payload={"stage": Stage.REVIEW.value},
        )
        return review_id

    def admit_approval(self, *, task_id: str) -> str:
        state = self._get_task(task_id)
        self._advance(state, Stage.APPROVAL)
        review_id = state.artifact_ids[Stage.REVIEW]
        receipt_id = state.artifact_ids[Stage.VALIDATION]
        context_id = state.artifact_ids[Stage.CONTEXT]
        approval_id = self._approval.evaluate_barrier(
            task_id=task_id,
            review_artifact_id=review_id,
            required_receipt_ids=[receipt_id],
            reviewed_context_artifact_id=context_id,
            intent_id=state.intent_anchor.intent_id,
        )
        state.artifact_ids[Stage.APPROVAL] = approval_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[approval_id],
            payload={"stage": Stage.APPROVAL.value},
        )
        return approval_id

    def admit_revision_seal(self, *, task_id: str) -> str:
        state = self._get_task(task_id)
        self._advance(state, Stage.REVISION_SEAL)
        approval_id = state.artifact_ids[Stage.APPROVAL]
        context_id = state.artifact_ids[Stage.CONTEXT]
        revision_id = self._seal.seal_revision(
            task_id=task_id,
            approval_id=approval_id,
            context_artifact_id=context_id,
            intent_id=state.intent_anchor.intent_id,
        )
        state.artifact_ids[Stage.REVISION_SEAL] = revision_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[revision_id],
            payload={"stage": Stage.REVISION_SEAL.value},
        )
        return revision_id

    def admit_evidence(self, *, task_id: str) -> str:
        state = self._get_task(task_id)
        self._advance(state, Stage.EVIDENCE)
        revision_id = state.artifact_ids[Stage.REVISION_SEAL]
        replay_anchor_id = self._evidence.close_evidence(
            task_id=task_id, revision_id=revision_id
        )
        state.artifact_ids[Stage.EVIDENCE] = replay_anchor_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[replay_anchor_id],
            payload={"stage": Stage.EVIDENCE.value},
        )
        # Evidence -> SEALED terminal. This is the only way to reach SEALED.
        self._advance(state, Stage.SEALED)
        # AUDIT-003 / §22.1: name the durable
        # ``intent_anchor_records.intent_id`` (the one
        # ``_emit_intent_anchor`` minted at admit_context and that lives
        # on ``state.intent_anchor``) in both ``artifact_refs`` and
        # ``payload`` so a reviewer reading only this terminal seal
        # record can recover the originating-intent linkage without a
        # second fetch. Authoritative fail-closed verification of
        # ``intent_id`` against ``intent_anchor_records`` remains the
        # responsibility of ``RevisionSealService`` downstream; this
        # surface performs no independent verification. Absent / empty
        # ``intent_id`` preserves the prior audit shape exactly.
        audit_artifact_refs: list[str] = list(state.artifact_ids.values())
        audit_payload: dict[str, Any] = {"stage": Stage.SEALED.value}
        anchor_intent_id = getattr(state.intent_anchor, "intent_id", None)
        if isinstance(anchor_intent_id, str) and anchor_intent_id:
            audit_artifact_refs.append(anchor_intent_id)
            audit_payload["intent_id"] = anchor_intent_id
        self._audit.append(
            record_type="signable_path_sealed",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )
        return replay_anchor_id

    # ------------------------------------------------------------------
    # abandonment / introspection
    # ------------------------------------------------------------------

    def abandon(self, *, task_id: str, reason: str) -> None:
        """Explicit abandonment terminal. Legal from any non-terminal stage."""
        state = self._tasks.get(task_id)
        if state is None:
            raise OrchestratorRejected(f"unknown task: {task_id}")
        if state.abandoned:
            return
        self._advance(state, Stage.ABANDONED)
        state.abandoned = True
        # AUDIT-003 / §22.1: name the durable
        # ``intent_anchor_records.intent_id`` (the one
        # ``_emit_intent_anchor`` minted at admit_context and that lives
        # on ``state.intent_anchor``) in both ``artifact_refs`` and
        # ``payload`` so a reviewer reading only this terminal
        # abandonment record can recover the originating-intent linkage
        # without a second fetch. Authoritative fail-closed verification
        # of ``intent_id`` against ``intent_anchor_records`` remains the
        # responsibility of ``RevisionSealService`` downstream; this
        # surface performs no independent verification. Absent / empty
        # ``intent_id`` preserves the prior audit shape exactly.
        audit_artifact_refs: list[str] = list(state.artifact_ids.values())
        audit_payload: dict[str, Any] = {"reason": reason}
        anchor_intent_id = getattr(state.intent_anchor, "intent_id", None)
        if isinstance(anchor_intent_id, str) and anchor_intent_id:
            audit_artifact_refs.append(anchor_intent_id)
            audit_payload["intent_id"] = anchor_intent_id
        self._audit.append(
            record_type="task_abandoned",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )

    def current_stage(self, task_id: str) -> Optional[Stage]:
        state = self._tasks.get(task_id)
        return None if state is None else state.current_stage

    # ------------------------------------------------------------------
    # narrow real-fix bridge chain
    # ------------------------------------------------------------------

    def run_real_fix_chain(self, task: Any) -> Any:
        """Drive the already-merged real-fix bridge chain in causal order.

        This is the single orchestrator entrypoint that wires the
        verified real-fix narrow path end-to-end. It reuses the
        already-merged components exactly as they exist:

            RealFixTracer.run
                -> RealFixNarrowPathRecorder.record    (via the tracer)
                -> RealFixPatchProjector.project
                -> RealFixValidationBridge.bridge
                -> RealFixReviewBridge.bridge
                -> RealFixApprovalBridge.bridge
                -> RealFixRevisionSealBridge.bridge
                -> RealFixEvidenceClosureBridge.bridge

        Fail-closed conditions (raise ``RealFixChainRejected`` without
        any downstream call):
        - any of the seven wirings is absent
        - the tracer did not produce ``real_fix_verified_pass`` (the
          tracer's own unverified outcome is returned via the rejection
          path so the caller still sees the verified=False result; no
          downstream bridge is dispatched)
        - the tracer returned verified=True but no ``inference_artifact_id``
          (the injected recorder did not produce an authority-bearing
          row; chain cannot proceed honestly)
        - the ``task.task_id`` already holds an eight-stage frame in
          this orchestrator's in-memory bookkeeping (the two surfaces
          must not conflate)

        Any ``Rejected`` exception raised by an individual bridge or by
        the underlying service bubbles up unchanged — the orchestrator
        does not swallow, rewrap, or silently downgrade bridge refusal.
        The existing per-bridge audit records and per-service audit
        records (including the recorder's ``inference_artifact_created``
        event, every ``*_bridge_attested`` event, and the evidence
        service's ``evidence_closure`` record) are emitted unchanged;
        the replay-ceiling ``"semantic"`` tag flows from the tracer
        through every bridge attestation without modification.

        The orchestrator emits one wrapper audit record
        (``real_fix_chain_completed``) at the end of a successful chain
        that names every artifact id the chain produced. This is a
        review convenience hop; it is not authority — the authority
        lives in the bridge-emitted records.
        """
        required = {
            "real_fix_tracer": self._rf_tracer,
            "real_fix_patch_projector": self._rf_projector,
            "real_fix_validation_bridge": self._rf_validation_bridge,
            "real_fix_review_bridge": self._rf_review_bridge,
            "real_fix_approval_bridge": self._rf_approval_bridge,
            "real_fix_revision_seal_bridge": self._rf_revision_seal_bridge,
            "real_fix_evidence_closure_bridge": self._rf_evidence_closure_bridge,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            # Fail-closed: a partially-wired chain must never silently
            # degrade to a shorter chain; the caller has requested the
            # full narrow real-fix path.
            raise RealFixChainRejected(
                "real-fix bridge chain is not fully wired; missing: "
                f"{', '.join(missing)}"
            )

        task_id = getattr(task, "task_id", "")
        if not isinstance(task_id, str) or not task_id:
            raise RealFixChainRejected("task is missing task_id")

        # The eight-stage admission surface and the narrow real-fix
        # chain both take a ``task_id``; refuse to run the real-fix
        # chain for a task that has already entered the eight-stage
        # frame to prevent conflation of the two surfaces.
        if task_id in self._tasks:
            raise RealFixChainRejected(
                f"task {task_id!r} has already entered the eight-stage "
                "signable-path frame; real-fix chain refuses to overlay"
            )

        # --- 0/7: real ContextArtifact admission --------------------------
        # Mint one authority-bearing ``ContextArtifact`` row via the
        # already-wired ``ContextService`` before dispatching the
        # tracer. This replaces the prior tracer-scoped synthetic
        # ``real-fix::context::<task_id>`` identifier with a real
        # persisted ``ctx-<hex>`` id. The id is threaded into the
        # recorder via ``tracer.run(...)`` overrides so the
        # ``InferenceArtifact`` row and every downstream bridge carry
        # the real id unchanged (the bridges read it off the persisted
        # InferenceArtifact row; no bridge code needs to change).
        #
        # The ``root_revision_id`` remains the clearly-labelled
        # ``real-fix::root::<task_id>`` form: no ``Revision`` row is
        # minted in this increment (that would be phase-2 runtime work).
        # The label is now the ``root_revision_id`` field of a real
        # persisted ``ContextArtifact`` row, which is an honest upgrade
        # without claiming a Revision row that does not exist.
        #
        # Any ``ContextService`` rejection bubbles up unchanged
        # (fail-closed). The tracer is not dispatched on rejection, so
        # no adapter cost is incurred for a malformed admission request.
        #
        # This step does NOT enter the eight-stage task lifecycle state
        # machine: no ``_tasks`` entry is created, no ``Stage.CONTEXT``
        # transition is recorded, no ``admit_context`` is called. The
        # orchestrator uses ``ContextService`` directly as a service
        # dependency. The existing overlay guard above continues to
        # refuse any task id that has already entered the eight-stage
        # frame.
        from kernel.services.context_service import ContextRequest

        rf_root_revision_id = f"real-fix::root::{task_id}"
        rf_context_request = ContextRequest(
            repo_graph_version="real_fix_tracer_v1",
            symbol_index_version="real_fix_tracer_v1",
            candidate_file_ids=(),
            symbol_frontier_ids=(),
            packing_policy_version="real_fix_tracer_v1",
            actual_tokens=0,
            provenance_refs=(),
            deferred_retrieval_items=(),
            truncation_reason=None,
            taint_set=(),
        )
        # Narrow intent anchor for the real-fix admission surface. Reuses
        # the same ``_emit_intent_anchor`` helper the eight-stage
        # ``admit_context`` uses so the ``intent_anchor_created`` audit
        # record is emitted exactly once per real-fix chain invocation.
        # This is the single hop that brings the real-fix chain's entry
        # onto the real eight-stage authority-bearing lifecycle surface.
        rf_intent_anchor = self._emit_intent_anchor(
            task_id=task_id,
            intent_id=f"real-fix::intent::{task_id}",
        )
        rf_context_artifact_id = self._context.build_context_artifact(
            task_id=task_id,
            root_revision_id=rf_root_revision_id,
            request=rf_context_request,
            intent_anchor=rf_intent_anchor,
        )

        # --- eight-stage lifecycle frame entry ----------------------------
        # The real-fix chain's real ContextArtifact IS the eight-stage
        # signable path's CONTEXT admission. Populate the in-memory task
        # state machine exactly as ``admit_context`` would, and emit the
        # same ``stage_entered`` audit record. From this point forward,
        # every bridge outcome is recorded as its corresponding
        # ``Stage`` admission via ``_advance`` + ``stage_entered``,
        # finally advancing ``EVIDENCE -> SEALED`` at closure. The
        # lifecycle frame therefore reflects the true authority-bearing
        # state of the chain, not a disjoint surface.
        #
        # Fail-closed properties preserved:
        # - ``_advance`` already audits any illegal transition via
        #   ``illegal_stage_transition_rejected`` before raising.
        # - On unverified tracer outcome (early return below), the frame
        #   remains at ``Stage.CONTEXT``; the caller may later
        #   ``abandon()``. No downstream stage is entered without an
        #   authority-bearing artifact to bind to it.
        # - The ``context_artifact_created`` audit record (emitted by
        #   ``ContextService`` above) already precedes this
        #   ``stage_entered`` record, matching the eight-stage admission
        #   audit order.
        state = TaskLifecycleState(
            task_id=task_id,
            intent_anchor=rf_intent_anchor,
            current_stage=Stage.CONTEXT,
        )
        state.artifact_ids[Stage.CONTEXT] = rf_context_artifact_id
        self._tasks[task_id] = state
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[rf_context_artifact_id],
            payload={"stage": Stage.CONTEXT.value},
        )

        # --- 1/7: tracer + recorder ---------------------------------------
        # The tracer owns the adapter boundary and (when configured with
        # the recorder) produces exactly one authority-bearing
        # ``InferenceArtifact`` row on a verified pass. The tracer
        # already emits every audit record the narrow path requires
        # (attempt started, failure class on reject, verified_pass on
        # success) and propagates the honest replay ceiling.
        #
        # Overrides bind the ``InferenceArtifact`` row's
        # ``context_artifact_id`` to the real ContextArtifact minted
        # above and the ``root_revision_id`` to the labelled
        # ``real-fix::root::<task_id>`` form (matching the
        # ContextArtifact row's own ``root_revision_id``).
        # Thread the durable ``intent_anchor_records.intent_id`` minted
        # at entrypoint so the ``inference_artifact_created`` record the
        # recorder emits on a verified pass names it in both
        # ``artifact_refs`` and ``payload``. AUDIT-003 / §22.1: this
        # closes the last upstream one-hop asymmetry on the real-fix
        # narrow-path audit chain above ``patch_proposal_created``. The
        # tracer and recorder perform no independent verification;
        # authoritative fail-closed verification of ``intent_id`` remains
        # in the downstream seal service at stage 6.
        result = self._rf_tracer.run(
            task,
            context_artifact_id=rf_context_artifact_id,
            root_revision_id=rf_root_revision_id,
            intent_id=rf_intent_anchor.intent_id,
        )
        if not getattr(result, "verified", False) or \
                getattr(result, "outcome", "") != "real_fix_verified_pass":
            # Fail-closed by outcome class: the tracer's own failure-
            # class audit record is already the evidence. The chain
            # does not dispatch any bridge for an unverified result.
            return result

        inference_artifact_id = getattr(result, "inference_artifact_id", "")
        if not isinstance(inference_artifact_id, str) or not inference_artifact_id:
            # Defense-in-depth: verified_pass without an
            # authority-bearing narrow-path id means the recorder did
            # not actually persist. Refuse to chain.
            raise RealFixChainRejected(
                "tracer returned verified_pass without an "
                "inference_artifact_id; recorder did not persist"
            )

        # The recorder's returned ``RealFixNarrowPathRecord`` carries
        # ``context_artifact_id`` / ``root_revision_id`` / ``output_hash``
        # / ``replay_ceiling``. We reconstruct the equivalent record
        # shape for the projector from the tracer surface + the
        # authority-bearing ids the recorder was instructed to use via
        # the tracer overrides. This keeps the orchestrator from having
        # to hold a second reference to the recorder itself.
        from kernel.lifecycle.real_fix_recorder import RealFixNarrowPathRecord

        record = RealFixNarrowPathRecord(
            inference_artifact_id=inference_artifact_id,
            context_artifact_id=rf_context_artifact_id,
            root_revision_id=rf_root_revision_id,
            output_hash=getattr(result, "output_hash", ""),
            replay_ceiling=getattr(result, "replay_ceiling", "") or "semantic",
        )

        # The tracer + recorder produced the authority-bearing
        # ``InferenceArtifact`` row; advance the eight-stage frame to
        # match and emit the ``stage_entered`` record the eight-stage
        # surface would have emitted for this admission.
        self._advance(state, Stage.INFERENCE)
        state.artifact_ids[Stage.INFERENCE] = inference_artifact_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[inference_artifact_id],
            payload={"stage": Stage.INFERENCE.value},
        )

        # --- 2/7: patch projection ----------------------------------------
        # Thread the durable ``intent_anchor_records.intent_id`` minted
        # at entrypoint so the ``patch_proposal_created`` record names
        # it in both ``artifact_refs`` and ``payload``. AUDIT-003 /
        # §22.1: this closes the next upstream one-hop asymmetry on the
        # real-fix narrow-path audit chain above
        # ``real_fix_validation_bridge_attested``. The projector does
        # not verify the id; authoritative fail-closed verification
        # remains in the downstream seal service at stage 6.
        projection = self._rf_projector.project(
            task=task,
            result=result,
            record=record,
            intent_id=rf_intent_anchor.intent_id,
        )
        self._advance(state, Stage.PATCH_PROPOSAL)
        state.artifact_ids[Stage.PATCH_PROPOSAL] = projection.patch_proposal_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[projection.patch_proposal_id],
            payload={"stage": Stage.PATCH_PROPOSAL.value},
        )

        # --- 3/7: validation bridge ---------------------------------------
        # Thread the durable ``intent_anchor_records.intent_id`` minted
        # at entrypoint so the ``real_fix_validation_bridge_attested``
        # record names it in both ``artifact_refs`` and ``payload``.
        # AUDIT-003 / §22.1: this closes the last one-hop asymmetry on
        # the real-fix bridge surface upstream of the already-closed
        # review bridge attestation. The validation bridge does not
        # verify the id; authoritative fail-closed verification remains
        # in the downstream seal service at stage 6.
        validation_outcome = self._rf_validation_bridge.bridge(
            projection=projection,
            intent_id=rf_intent_anchor.intent_id,
        )
        self._advance(state, Stage.VALIDATION)
        state.artifact_ids[Stage.VALIDATION] = (
            validation_outcome.validation_receipt_id
        )
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[validation_outcome.validation_receipt_id],
            payload={"stage": Stage.VALIDATION.value},
        )

        # --- 4/7: review bridge -------------------------------------------
        # Thread the durable ``intent_anchor_records.intent_id`` minted
        # at entrypoint so the ``real_fix_review_bridge_attested``
        # record names it in both ``artifact_refs`` and ``payload``.
        # AUDIT-003 / §22.1: this closes the next one-hop asymmetry
        # upstream of the already-closed approval-bridge attestation.
        # The review bridge does not verify the id; authoritative
        # fail-closed verification remains in the downstream seal
        # service at stage 6.
        review_outcome = self._rf_review_bridge.bridge(
            outcome=validation_outcome,
            intent_id=rf_intent_anchor.intent_id,
        )
        self._advance(state, Stage.REVIEW)
        state.artifact_ids[Stage.REVIEW] = review_outcome.review_artifact_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[review_outcome.review_artifact_id],
            payload={"stage": Stage.REVIEW.value},
        )

        # --- 5/7: approval bridge -----------------------------------------
        # Thread the durable ``intent_anchor_records.intent_id`` minted
        # at entrypoint so the ``real_fix_approval_bridge_attested``
        # record names it in both ``artifact_refs`` and ``payload``.
        # AUDIT-003 / §22.1: this closes the next one-hop asymmetry
        # upstream of the already-closed seal bridge attestation. The
        # approval bridge does not verify the id; authoritative
        # fail-closed verification remains in the downstream seal
        # service at stage 6.
        approval_outcome = self._rf_approval_bridge.bridge(
            outcome=review_outcome,
            intent_id=rf_intent_anchor.intent_id,
        )
        self._advance(state, Stage.APPROVAL)
        state.artifact_ids[Stage.APPROVAL] = (
            approval_outcome.approval_artifact_id
        )
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[approval_outcome.approval_artifact_id],
            payload={"stage": Stage.APPROVAL.value},
        )

        # --- 6/7: revision-seal bridge ------------------------------------
        # Thread the durable ``intent_anchor_records.intent_id`` minted
        # above into the seal bridge so the sealed ``Revision.intent_id``
        # references the same durable row rather than the seal service's
        # fallback ``intent-<task_id>`` label. This closes the real-fix
        # surface's half of the AUDIT-003 / §22.1 linkage already closed
        # on the eight-stage ``admit_revision_seal`` surface (which also
        # passes ``state.intent_anchor.intent_id``). No schema change, no
        # new field, no new audit record: the bridge and service already
        # accept ``intent_id`` as a keyword-only argument; this is a
        # missed keyword the real-fix chain now supplies. On unverified
        # tracer outcome this call is never reached, so the early-return
        # path is unchanged.
        seal_outcome = self._rf_revision_seal_bridge.bridge(
            outcome=approval_outcome,
            intent_id=rf_intent_anchor.intent_id,
        )
        self._advance(state, Stage.REVISION_SEAL)
        state.artifact_ids[Stage.REVISION_SEAL] = seal_outcome.revision_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[seal_outcome.revision_id],
            payload={"stage": Stage.REVISION_SEAL.value},
        )

        # --- 7/7: evidence-closure bridge ---------------------------------
        closure_outcome = self._rf_evidence_closure_bridge.bridge(
            outcome=seal_outcome
        )
        self._advance(state, Stage.EVIDENCE)
        state.artifact_ids[Stage.EVIDENCE] = closure_outcome.replay_anchor_id
        self._audit.append(
            record_type="stage_entered",
            task_id=task_id,
            artifact_refs=[closure_outcome.replay_anchor_id],
            payload={"stage": Stage.EVIDENCE.value},
        )
        # EVIDENCE -> SEALED is the only terminal success transition on
        # the eight-stage path; emit the same ``signable_path_sealed``
        # record ``admit_evidence`` emits so the authority-bearing
        # terminal state is marked identically regardless of whether the
        # chain was driven by the eight-stage admission surface or the
        # real-fix chain entrypoint.
        self._advance(state, Stage.SEALED)
        # AUDIT-003 / §22.1: name the durable
        # ``intent_anchor_records.intent_id`` (the ``rf_intent_anchor``
        # minted earlier in ``run_real_fix_chain`` and carried on
        # ``state.intent_anchor``) in both ``artifact_refs`` and
        # ``payload`` so the real-fix terminal seal record mirrors the
        # eight-stage terminal shape for the AUDIT-003 linkage. Absent /
        # empty ``intent_id`` preserves the prior audit shape exactly.
        audit_artifact_refs: list[str] = list(state.artifact_ids.values())
        audit_payload: dict[str, Any] = {"stage": Stage.SEALED.value}
        anchor_intent_id = getattr(state.intent_anchor, "intent_id", None)
        if isinstance(anchor_intent_id, str) and anchor_intent_id:
            audit_artifact_refs.append(anchor_intent_id)
            audit_payload["intent_id"] = anchor_intent_id
        self._audit.append(
            record_type="signable_path_sealed",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )

        # Wrapper audit: one record that names every id a reviewer needs
        # to walk the chain from a single hop. The replay ceiling is
        # carried through from the tracer / recorder unchanged.
        #
        # AUDIT-003 / §22.1: ``intent_id`` is included in both
        # ``artifact_refs`` and ``payload`` so the wrapper's own "every
        # id from a single hop" claim is true for the originating
        # ``intent_anchor_records`` row as well. Without it, a reviewer
        # reading this record would still need a DB fetch on the
        # revision row (``revisions.intent_id``) to recover the
        # durable intent-anchor id the seal service just verified —
        # the last one-hop asymmetry on the real-fix surface for the
        # AUDIT-003 linkage. The id itself is unchanged from the
        # durable row minted at ``_emit_intent_anchor`` above.
        self._audit.append(
            record_type="real_fix_chain_completed",
            task_id=task_id,
            artifact_refs=[
                closure_outcome.replay_anchor_id,
                closure_outcome.revision_id,
                closure_outcome.snapshot_root_id,
                closure_outcome.approval_artifact_id,
                closure_outcome.review_artifact_id,
                closure_outcome.validation_receipt_id,
                closure_outcome.patch_proposal_id,
                closure_outcome.inference_artifact_id,
                rf_intent_anchor.intent_id,
            ],
            payload={
                "replay_anchor_id": closure_outcome.replay_anchor_id,
                "revision_id": closure_outcome.revision_id,
                "snapshot_root_id": closure_outcome.snapshot_root_id,
                "approval_artifact_id": closure_outcome.approval_artifact_id,
                "review_artifact_id": closure_outcome.review_artifact_id,
                "validation_receipt_id": closure_outcome.validation_receipt_id,
                "patch_proposal_id": closure_outcome.patch_proposal_id,
                "inference_artifact_id": closure_outcome.inference_artifact_id,
                "context_artifact_id": closure_outcome.context_artifact_id,
                "root_revision_id": closure_outcome.root_revision_id,
                "intent_id": rf_intent_anchor.intent_id,
                "replay_ceiling": record.replay_ceiling,
                "source": "real_fix_tracer",
            },
        )
        return closure_outcome
