"""
Real-fix narrow-path approval bridge: take exactly one bridged
``ReviewArtifact`` that came from the verified real-fix path and produce
exactly one schema-valid ``ApprovalArtifact`` via the existing
``ApprovalService.evaluate_barrier``, with an explicit audit
cross-reference that names the originating ``ReviewArtifact``,
``ValidationReceipt``, ``PatchProposal``, AND the upstream
``InferenceArtifact`` so a reviewer can walk the full chain from one
record.

Constitutional anchors:
- v11 §23.10 ReviewArtifact — the bridge reads (does not mutate) the
  persisted review row and refuses any row whose on-row identities
  disagree with the bridged outcome.
- v11 §23.11 ApprovalArtifact — the bridge produces exactly one such
  row by delegating to ``ApprovalService.evaluate_barrier`` unchanged.
  No new schema.
- v11 §22.3 Atomic Approval Barrier Contract — the bridge does not
  bypass the barrier. ``ApprovalBarrierFailed`` and ``ApprovalRejected``
  from the service bubble up untouched; the bridge does not emit its
  own attestation in that case.
- v11 §23.7 ValidationReceipt — the bridge re-checks that the receipt
  bound by the upstream review bridge is still admissible at approval
  time (``result == "pass"`` and not invalidated). An invalidated or
  non-pass receipt is non-admissible regardless of review state.
- v11 §23.14 AuditRecord — the bridge emits one
  ``real_fix_approval_bridge_attested`` record whose ``artifact_refs``
  carries all five identities so a reviewer can walk
  ``InferenceArtifact → PatchProposal → ValidationReceipt →
  ReviewArtifact → ApprovalArtifact`` end-to-end.
- foundation §1, §D-004 — phase-1 narrow path: single-file text
  substitution with no manifest touch. The bridge refuses any patch row
  whose target id is not the real-fix narrow-path synthetic id, and any
  review whose on-row ids do not match the review-bridge outcome.

Scope lock:
- ONE ``RealFixReviewBridgeOutcome`` in, ONE ``ApprovalArtifact`` row
  out. Fail-closed on any identity mismatch or non-admissible receipt
  state (result != "pass", or invalidated); in those cases no approval
  is issued and no bridge attestation is appended.
- No revision sealing. No evidence-plane expansion. No repository
  mutation. No multi-file fixes. No retries. No background loops. No
  new providers. No phase-2 runtime work. No UI. No orchestrator
  redesign. No change to ``ApprovalService``, ``ReviewService``,
  ``RealFixReviewBridge``, ``RealFixValidationBridge``, or
  ``RealFixPatchProjector``.
- No new artifact type, table, or schema. Reuses
  ``kernel/schemas/approval_artifact.schema.json``, ``ApprovalService``,
  ``ReviewArtifactRepository``, ``PatchProposalRepository``,
  ``ValidationReceiptRepository``, ``InferenceArtifactRepository``, and
  the existing append-only audit ledger.

The bridge is an adapter over already-verified surfaces. Its only new
contribution is:
  (a) fail-closed admission that the persisted ``ReviewArtifact`` is
      the one produced by ``RealFixReviewBridge`` for this outcome
      (task / root / patch_proposal_id match), that the bound receipt
      is still pass and not invalidated, that the associated
      ``PatchProposal`` is still the real-fix narrow-path row, and that
      the ``InferenceArtifact`` named by that patch row still exists
      and still matches the outcome; and
  (b) one audit event that names all five ids so downstream sealing can
      walk the full chain from a single record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.lifecycle.real_fix_review_bridge import (
    RealFixReviewBridgeOutcome,
)
from kernel.services.approval_service import (
    ApprovalBarrierFailed,
    ApprovalRejected,
    ApprovalService,
)
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
    ValidationReceiptRepository,
)


class RealFixApprovalBridgeRejected(Exception):
    """Raised when a bridged review is not admissible for approval.

    Fail-closed: no ``ApprovalService.evaluate_barrier`` call is
    dispatched, no approval row is written, and no bridge attestation
    is appended. Any downstream ``ApprovalBarrierFailed`` or
    ``ApprovalRejected`` from the service is re-raised unchanged so
    that barrier-governance rejection continues to use its existing
    surface.

    Admission conditions:

    - The outcome's ``review_artifact_id`` exists in the repository.
    - The persisted review's ``task_id`` / ``root_revision_id`` /
      ``patch_proposal_id`` equal the outcome's values.
    - The outcome's ``validation_receipt_id`` exists in the repository,
      its ``task_id`` / ``root_revision_id`` equal the outcome's
      values, its ``result`` is ``"pass"``, and its ``invalidated_at``
      is ``None``. ``fail`` / ``quarantined`` / invalidated receipts
      are explicitly non-admissible for the minimum honest bridge.
    - The outcome's ``patch_proposal_id`` exists in the repository, its
      ``inference_artifact_id`` equals the outcome's value, and its
      ``task_id`` / ``root_revision_id`` equal the outcome's values.
    - The persisted patch row's single ``target_file_ids`` entry equals
      the real-fix narrow-path synthetic label. This is the
      audit-visible tag that distinguishes rows produced by the
      real-fix projector from any other origin.
    - The outcome's ``inference_artifact_id`` exists in the repository
      and its ``task_id`` / ``root_revision_id`` equal the outcome's
      values. The approval needs this row to resolve the
      ``reviewed_context_artifact_id`` the barrier contract requires.
    """


@dataclass(frozen=True)
class RealFixApprovalBridgeOutcome:
    """Return value of a successful approval bridge call.

    The ``ApprovalArtifact`` row is the authority-bearing artifact;
    this dataclass carries the five ids that a reviewer needs to walk
    the end-to-end chain from the originating ``InferenceArtifact``
    through the projected patch, its receipt, the rendered review, and
    the issued approval.
    """

    approval_artifact_id: str
    review_artifact_id: str
    validation_receipt_id: str
    patch_proposal_id: str
    inference_artifact_id: str
    context_artifact_id: str
    task_id: str
    root_revision_id: str


class RealFixApprovalBridge:
    """Bridge a bridged real-fix ``ReviewArtifact`` to its ``ApprovalArtifact``.

    The bridge holds no state of its own. It composes the existing
    ``ApprovalService`` (which itself owns §22.3 barrier evaluation and
    §23.11 approval issuance) plus four read-only repositories. The
    bridge's only mutations are:

    - the one ``ApprovalArtifact`` row written by the service, and
    - one append-only audit record emitted directly by this bridge.
    """

    def __init__(
        self,
        *,
        approval_service: ApprovalService,
        review_reader: ReviewArtifactRepository,
        receipt_reader: ValidationReceiptRepository,
        patch_reader: PatchProposalRepository,
        inference_reader: InferenceArtifactRepository,
        approval_reader: ApprovalArtifactRepository,
        audit_ledger: Any,
    ) -> None:
        self._service = approval_service
        self._review_reader = review_reader
        self._receipt_reader = receipt_reader
        self._patch_reader = patch_reader
        self._inference_reader = inference_reader
        self._approval_reader = approval_reader
        self._audit = audit_ledger

    # ------------------------------------------------------------------

    def bridge(
        self,
        *,
        outcome: RealFixReviewBridgeOutcome,
        intent_id: str | None = None,
    ) -> RealFixApprovalBridgeOutcome:
        """Admit the outcome and produce one ``ApprovalArtifact``.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint. The bridge only names
        it in the attestation record so a reviewer reading that single
        audit hop can recover the originating intent-anchor id without
        a second fetch. Authoritative fail-closed verification of
        ``intent_id`` against ``intent_anchor_records`` remains the
        responsibility of the downstream ``RevisionSealService`` at
        stage 6; this bridge performs no independent verification.
        """
        if not isinstance(outcome, RealFixReviewBridgeOutcome):
            raise RealFixApprovalBridgeRejected(
                "bridge input must be a RealFixReviewBridgeOutcome; "
                f"got {type(outcome).__name__}"
            )

        # --- admit the review row -------------------------------------
        review = self._review_reader.fetch(outcome.review_artifact_id)
        if review is None:
            raise RealFixApprovalBridgeRejected(
                "bridged review artifact not found: "
                f"{outcome.review_artifact_id}"
            )
        if review.get("task_id") != outcome.task_id:
            raise RealFixApprovalBridgeRejected(
                "persisted review artifact task_id mismatch"
            )
        if review.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixApprovalBridgeRejected(
                "persisted review artifact root_revision_id mismatch"
            )
        if review.get("patch_proposal_id") != outcome.patch_proposal_id:
            raise RealFixApprovalBridgeRejected(
                "persisted review artifact patch_proposal_id mismatch"
            )

        # --- admit the receipt (still pass, still live) ---------------
        receipt = self._receipt_reader.fetch(outcome.validation_receipt_id)
        if receipt is None:
            raise RealFixApprovalBridgeRejected(
                "bridged validation receipt not found: "
                f"{outcome.validation_receipt_id}"
            )
        if receipt.get("task_id") != outcome.task_id:
            raise RealFixApprovalBridgeRejected(
                "persisted validation receipt task_id mismatch"
            )
        if receipt.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixApprovalBridgeRejected(
                "persisted validation receipt root_revision_id mismatch"
            )
        if receipt.get("invalidated_at") is not None:
            raise RealFixApprovalBridgeRejected(
                "validation receipt has been invalidated; "
                "not admissible for approval"
            )
        if receipt.get("result") != "pass":
            raise RealFixApprovalBridgeRejected(
                "validation receipt result is not 'pass'; "
                f"got {receipt.get('result')!r}"
            )

        # --- admit the patch row (still real-fix narrow-path) ---------
        stored = self._patch_reader.fetch(outcome.patch_proposal_id)
        if stored is None:
            raise RealFixApprovalBridgeRejected(
                "upstream patch proposal not found: "
                f"{outcome.patch_proposal_id}"
            )
        if stored.get("inference_artifact_id") != outcome.inference_artifact_id:
            raise RealFixApprovalBridgeRejected(
                "persisted patch proposal inference_artifact_id mismatch"
            )
        if stored.get("task_id") != outcome.task_id:
            raise RealFixApprovalBridgeRejected(
                "persisted patch proposal task_id mismatch"
            )
        if stored.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixApprovalBridgeRejected(
                "persisted patch proposal root_revision_id mismatch"
            )

        target_file_ids = list(stored.get("target_file_ids") or [])
        expected_target = f"real-fix::file::{outcome.task_id}"
        if target_file_ids != [expected_target]:
            raise RealFixApprovalBridgeRejected(
                "persisted patch proposal target_file_ids is not the "
                f"real-fix narrow-path label: expected [{expected_target!r}], "
                f"got {target_file_ids!r}"
            )

        # --- admit the inference row (needed for context binding) -----
        inference = self._inference_reader.fetch(outcome.inference_artifact_id)
        if inference is None:
            raise RealFixApprovalBridgeRejected(
                "upstream inference artifact not found: "
                f"{outcome.inference_artifact_id}"
            )
        if inference.get("task_id") != outcome.task_id:
            raise RealFixApprovalBridgeRejected(
                "persisted inference artifact task_id mismatch"
            )
        if inference.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixApprovalBridgeRejected(
                "persisted inference artifact root_revision_id mismatch"
            )
        context_artifact_id = inference.get("context_artifact_id")
        if not context_artifact_id:
            raise RealFixApprovalBridgeRejected(
                "persisted inference artifact has no context_artifact_id"
            )

        # --- delegate to the service ----------------------------------
        # Any ApprovalBarrierFailed / ApprovalRejected bubbles up
        # unchanged; the bridge does not emit an attestation on
        # rejection. The service's own barrier-rejection audit (if any)
        # is the evidence the reviewer will see.
        try:
            approval_id = self._service.evaluate_barrier(
                task_id=outcome.task_id,
                review_artifact_id=outcome.review_artifact_id,
                required_receipt_ids=[outcome.validation_receipt_id],
                reviewed_context_artifact_id=context_artifact_id,
                intent_id=intent_id,
            )
        except (ApprovalBarrierFailed, ApprovalRejected):
            raise

        approval = self._approval_reader.fetch(approval_id)
        if approval is None:
            # Defense-in-depth: the service just wrote this row; if it
            # is somehow absent, refuse to emit an attestation pointing
            # at a non-existent artifact.
            raise RealFixApprovalBridgeRejected(
                "approval service reported id "
                f"{approval_id!r} but row is not present"
            )

        # The attestation record is the single audit hop that names all
        # five identities a reviewer needs to walk the chain. The
        # service has already appended its own
        # ``approval_artifact_issued`` record linking the approval to
        # the review and patch proposal; this record adds the upstream
        # ``ValidationReceipt`` and ``InferenceArtifact`` bindings and
        # tags the source as real-fix tracer.
        #
        # AUDIT-003 / §22.1: name ``intent_id`` in both ``artifact_refs``
        # and ``payload``. The id is the durable
        # ``intent_anchor_records.intent_id`` minted at the real-fix
        # chain entrypoint and threaded in by the orchestrator.
        # Naming it here mirrors the pattern already applied to
        # ``real_fix_revision_seal_bridge_attested`` (stage 6),
        # ``real_fix_evidence_closure_bridge_attested`` (stage 7),
        # ``revision_sealed`` (seal service), and
        # ``real_fix_chain_completed`` (orchestrator wrapper), closing
        # the next one-hop asymmetry going upstream so a reviewer
        # reading only this record can recover the originating durable
        # intent-anchor id without a second fetch. Authoritative fail-
        # closed verification of ``intent_id`` against
        # ``intent_anchor_records`` remains in ``RevisionSealService``
        # at stage 6; this bridge performs no independent verification.
        # No schema change, no migration, no new artifact family, no
        # new audit record type.
        audit_artifact_refs: list[str] = [
            approval_id,
            outcome.review_artifact_id,
            outcome.validation_receipt_id,
            outcome.patch_proposal_id,
            outcome.inference_artifact_id,
        ]
        if intent_id is not None:
            audit_artifact_refs.append(intent_id)
        self._audit.append(
            record_type="real_fix_approval_bridge_attested",
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
            artifact_refs=audit_artifact_refs,
            payload={
                "approval_artifact_id": approval_id,
                "review_artifact_id": outcome.review_artifact_id,
                "validation_receipt_id": outcome.validation_receipt_id,
                "patch_proposal_id": outcome.patch_proposal_id,
                "inference_artifact_id": outcome.inference_artifact_id,
                "reviewed_context_artifact_id": context_artifact_id,
                "intent_id": intent_id,
                "approval_state": approval["approval_state"],
                "approval_scope": approval["approval_scope"],
                "policy_version": approval["policy_version"],
                "source": "real_fix_tracer",
            },
        )

        return RealFixApprovalBridgeOutcome(
            approval_artifact_id=approval_id,
            review_artifact_id=outcome.review_artifact_id,
            validation_receipt_id=outcome.validation_receipt_id,
            patch_proposal_id=outcome.patch_proposal_id,
            inference_artifact_id=outcome.inference_artifact_id,
            context_artifact_id=context_artifact_id,
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
        )
