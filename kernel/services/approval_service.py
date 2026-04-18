"""
Approval service: issue §23.11 ApprovalArtifact and evaluate C22.3 barrier.

Constitutional anchors:
- v11 §22.3 Atomic Approval Barrier Contract
- v11 §23.11 ApprovalArtifact
- v11 §24.1 AT-004 / AT-005 / AT-006
- v11 §24.2 INV-006 / INV-007 (no approval time-travel)
- foundation §6 step 8 (P1 approval barrier evaluation)

This service does two things:
1. Issue an ApprovalArtifact (state='approved') referencing the reviewed
   patch + context + receipts. In phase-1 narrow-path mode, approval
   admission is local-operator and synthetic (the kernel acts as the
   approver); a real operator UI is explicitly out of scope. The
   service records an `approver_identity` drawn from policy.
2. Evaluate the §22.3 barrier rule set (`kernel/contracts/barrier_rules.py`)
   against live truth as observed by the repositories. A failing barrier
   raises `ApprovalBarrierFailed` with the stable reason code and emits
   an audit record; it never returns "passes".

Phase-1 policy:
- `approver_identity = "kernel:phase1"` (kernel auto-approval)
- `approval_scope = "phase1_narrow_path_single_file"`
- `policy_version = "phase1_approval_policy_v1"`
- Approval expires 24h after issuance.

The service owns barrier evaluation at approval *and* at seal time —
the seal-time re-evaluation is invoked by `RevisionSealService` to
enforce INV-006 (no time-travel across drift between approval and
seal).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import uuid4

from kernel.contracts.barrier_rules import (
    BarrierEvaluationError,
    BarrierInputs,
    BarrierVerdict,
    REASON_PASS,
    evaluate_barrier,
)
from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
    ValidationReceiptRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash


class ApprovalBarrierFailed(Exception):
    """Raised when the §22.3 barrier rejects an approval."""

    def __init__(self, verdict: BarrierVerdict) -> None:
        super().__init__(f"{verdict.reason_code}: {verdict.detail}")
        self.verdict = verdict


class ApprovalRejected(Exception):
    """Raised when approval cannot be issued."""


#: Phase-1 policy constants (foundation §6 step 8 minimal surface).
PHASE1_APPROVER_IDENTITY = "kernel:phase1"
PHASE1_APPROVAL_SCOPE = "phase1_narrow_path_single_file"
PHASE1_APPROVAL_POLICY_VERSION = "phase1_approval_policy_v1"
PHASE1_APPROVAL_TTL = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime) -> str:
    return ts.isoformat()


class ApprovalService:
    def __init__(
        self,
        *,
        repository: ApprovalArtifactRepository,
        patch_reader: PatchProposalRepository,
        receipt_reader: ValidationReceiptRepository,
        review_reader: ReviewArtifactRepository,
        audit_ledger: Any,
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._patch_reader = patch_reader
        self._receipt_reader = receipt_reader
        self._review_reader = review_reader
        self._audit = audit_ledger
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("approval_artifact")

    def evaluate_barrier(
        self,
        *,
        task_id: str,
        review_artifact_id: str,
        required_receipt_ids: list[str] | None = None,
        reviewed_context_artifact_id: str | None = None,
        intent_id: str | None = None,
    ) -> str:
        """Issue an ApprovalArtifact gated by the §22.3 barrier.

        The orchestrator passes the `review_artifact_id` that this stage
        is gating. The service reads the live patch / receipt / context
        state, constructs `BarrierInputs`, runs `evaluate_barrier`, and
        only issues the artifact if the verdict is `REASON_PASS`.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint (or the eight-stage
        ``admit_context`` surface) and threaded in by the caller. When
        supplied and non-empty it is named in both ``artifact_refs`` and
        ``payload`` of the ``approval_artifact_issued`` audit record and,
        on barrier failure, in the ``approval_barrier_rejected``
        rejection record as well, so a reviewer reading only either
        record can recover the AUDIT-003 / §22.1 linkage without a
        second fetch. Authoritative fail-closed verification of
        ``intent_id`` against ``intent_anchor_records`` remains the
        responsibility of ``RevisionSealService`` downstream; this
        service performs no independent verification. Absent / empty
        ``intent_id`` preserves the prior audit shape exactly.
        """
        review = self._review_reader.fetch(review_artifact_id)
        if review is None:
            raise ApprovalRejected(
                f"review artifact not found: {review_artifact_id}"
            )

        patch_proposal_id = review["patch_proposal_id"]
        proposal = self._patch_reader.fetch(patch_proposal_id)
        if proposal is None:
            raise ApprovalRejected(
                f"patch proposal not found: {patch_proposal_id}"
            )

        # `required_receipt_ids` is supplied by the caller, or defaults
        # to the single most recent receipt for this task on the
        # phase-1 narrow path. The tracer test passes the explicit
        # receipt id.
        if not required_receipt_ids:
            raise ApprovalRejected(
                "required_receipt_ids must be non-empty at approval time"
            )

        receipts_live: dict[str, Mapping[str, object]] = {}
        for rid in required_receipt_ids:
            r = self._receipt_reader.fetch(rid)
            if r is None:
                raise ApprovalRejected(
                    f"required receipt not found at approval time: {rid}"
                )
            receipts_live[rid] = r

        # Caller-declared reviewed_context_artifact_id is the context
        # this approval is bound to; we default to the patch proposal's
        # root-bound context id that the orchestrator tracks, but the
        # service requires it to be passed for clarity.
        if not reviewed_context_artifact_id:
            raise ApprovalRejected(
                "reviewed_context_artifact_id is required"
            )

        now = _now()
        expires_at = now + PHASE1_APPROVAL_TTL
        approval_id = f"ap-{uuid4().hex}"

        # Build barrier inputs. Phase-1 narrow-path truth:
        # - current_root = proposal.root_revision_id (no drift possible
        #   within the same task lifecycle in phase 1)
        # - current_patch_hash = proposal.patch_group_hash
        # - current_policy_version = PHASE1_APPROVAL_POLICY_VERSION
        # - task_superseded = False (no multi-lane arbitration in phase 1)
        inputs = BarrierInputs(
            approval_id=approval_id,
            approval_state="pending",
            approval_policy_version=PHASE1_APPROVAL_POLICY_VERSION,
            originating_root_revision_id=proposal["root_revision_id"],
            reviewed_patch_hash=proposal["patch_group_hash"],
            reviewed_context_artifact_id=reviewed_context_artifact_id,
            required_receipt_ids=tuple(required_receipt_ids),
            approval_expires_at=_iso(expires_at),
            current_root_revision_id=proposal["root_revision_id"],
            current_context_artifact_id=reviewed_context_artifact_id,
            current_patch_hash=proposal["patch_group_hash"],
            current_policy_version=PHASE1_APPROVAL_POLICY_VERSION,
            receipts_live=receipts_live,
            task_superseded=False,
            now_iso=_iso(now),
        )

        try:
            verdict = evaluate_barrier(inputs)
        except BarrierEvaluationError as exc:
            self._audit.append(
                record_type="approval_barrier_evaluation_error",
                task_id=task_id,
                artifact_refs=[review_artifact_id, patch_proposal_id],
                payload={"detail": str(exc)},
            )
            raise ApprovalRejected(f"barrier evaluation error: {exc}") from exc

        if not verdict.passes:
            audit_artifact_refs = [review_artifact_id, patch_proposal_id]
            audit_payload: dict[str, Any] = {
                "reason_code": verdict.reason_code,
                "detail": verdict.detail,
            }
            if isinstance(intent_id, str) and intent_id:
                audit_artifact_refs.append(intent_id)
                audit_payload["intent_id"] = intent_id
            self._audit.append(
                record_type="approval_barrier_rejected",
                task_id=task_id,
                artifact_refs=audit_artifact_refs,
                payload=audit_payload,
            )
            raise ApprovalBarrierFailed(verdict)

        artifact = {
            "approval_id": approval_id,
            "task_id": task_id,
            "originating_root_revision_id": proposal["root_revision_id"],
            "reviewed_patch_hash": proposal["patch_group_hash"],
            "reviewed_context_artifact_id": reviewed_context_artifact_id,
            "required_receipt_ids": list(required_receipt_ids),
            "approval_scope": PHASE1_APPROVAL_SCOPE,
            "approver_identity": PHASE1_APPROVER_IDENTITY,
            "approval_state": "approved",
            "policy_version": PHASE1_APPROVAL_POLICY_VERSION,
            "created_at": _iso(now),
            "expires_at": _iso(expires_at),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
        }

        violations = validate_artifact(artifact, self._schema)
        if violations:
            raise ApprovalRejected(
                f"approval artifact schema validation failed: "
                f"{'; '.join(violations[:5])}"
            )

        self._repo.insert(artifact)

        audit_artifact_refs = [approval_id, review_artifact_id, patch_proposal_id]
        audit_payload: dict[str, Any] = {
            "barrier_reason": REASON_PASS,
            "approval_scope": PHASE1_APPROVAL_SCOPE,
            "approver_identity": PHASE1_APPROVER_IDENTITY,
            "policy_version": PHASE1_APPROVAL_POLICY_VERSION,
            "expires_at": _iso(expires_at),
        }
        if isinstance(intent_id, str) and intent_id:
            audit_artifact_refs.append(intent_id)
            audit_payload["intent_id"] = intent_id
        self._audit.append(
            record_type="approval_artifact_issued",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )
        return approval_id

    # ------------------------------------------------------------------
    # seal-time re-evaluation (INV-006)
    # ------------------------------------------------------------------

    def reverify_for_seal(
        self,
        *,
        approval_id: str,
        current_root_revision_id: str,
        current_context_artifact_id: str,
        current_patch_hash: str,
        intent_id: str | None = None,
    ) -> BarrierVerdict:
        """Re-run §22.3 at seal time. Raises `ApprovalBarrierFailed` on drift.

        Called by `RevisionSealService` before the nine-step seal
        sequence begins. This is what makes the approval *atomic*
        relative to seal execution.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        the seal service already fail-closed-verified against
        ``intent_anchor_records`` before invoking this method. When
        supplied and non-empty it is named in both ``artifact_refs`` and
        ``payload`` of the ``approval_seal_time_barrier_rejected`` audit
        record so a reviewer reading only that rejection record can
        recover the AUDIT-003 / §22.1 linkage without a second fetch.
        This service performs no independent verification of
        ``intent_id``; authoritative fail-closed verification remains
        the responsibility of ``RevisionSealService`` upstream of this
        call. Absent / empty ``intent_id`` preserves the prior audit
        shape exactly.
        """
        approval = self._repo.fetch(approval_id)
        if approval is None:
            raise ApprovalRejected(
                f"approval not found at seal time: {approval_id}"
            )
        receipts_live: dict[str, Mapping[str, object]] = {}
        for rid in approval["required_receipt_ids"]:
            r = self._receipt_reader.fetch(rid)
            if r is None:
                raise ApprovalRejected(
                    f"required receipt missing at seal time: {rid}"
                )
            receipts_live[rid] = r

        inputs = BarrierInputs(
            approval_id=approval_id,
            approval_state=approval["approval_state"],
            approval_policy_version=approval["policy_version"],
            originating_root_revision_id=approval["originating_root_revision_id"],
            reviewed_patch_hash=approval["reviewed_patch_hash"],
            reviewed_context_artifact_id=approval["reviewed_context_artifact_id"],
            required_receipt_ids=tuple(approval["required_receipt_ids"]),
            approval_expires_at=approval["expires_at"],
            current_root_revision_id=current_root_revision_id,
            current_context_artifact_id=current_context_artifact_id,
            current_patch_hash=current_patch_hash,
            current_policy_version=PHASE1_APPROVAL_POLICY_VERSION,
            receipts_live=receipts_live,
            task_superseded=False,
        )
        verdict = evaluate_barrier(inputs)
        if not verdict.passes:
            audit_artifact_refs = [approval_id]
            audit_payload: dict[str, Any] = {
                "reason_code": verdict.reason_code,
                "detail": verdict.detail,
            }
            if isinstance(intent_id, str) and intent_id:
                audit_artifact_refs.append(intent_id)
                audit_payload["intent_id"] = intent_id
            self._audit.append(
                record_type="approval_seal_time_barrier_rejected",
                task_id=approval["task_id"],
                artifact_refs=audit_artifact_refs,
                payload=audit_payload,
            )
            raise ApprovalBarrierFailed(verdict)
        return verdict
