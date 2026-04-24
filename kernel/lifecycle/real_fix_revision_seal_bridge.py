"""
Real-fix narrow-path revision-seal bridge: take exactly one
``RealFixApprovalBridgeOutcome`` that came from the verified real-fix
path and produce exactly one schema-valid ``Revision`` row (a sealed
``RevisionSeal``) via the existing ``RevisionSealService.seal_revision``,
with an explicit audit cross-reference that names the originating
``ApprovalArtifact``, ``ReviewArtifact``, ``ValidationReceipt``,
``PatchProposal``, AND the upstream ``InferenceArtifact`` so a reviewer
can walk the full chain from one record.

Constitutional anchors:
- v11 §23.1 Revision / §22.2 Seal Transaction Ordering Contract — the
  bridge produces exactly one sealed revision by delegating to
  ``RevisionSealService.seal_revision`` unchanged. No new schema, no
  new table, no migration.
- v11 §22.3 Atomic Approval Barrier Contract — the bridge does not
  bypass the seal-time barrier. ``ApprovalBarrierFailed``,
  ``ApprovalRejected``, and ``SealRejected`` bubble up untouched; the
  bridge does not emit its own attestation in that case.
- v11 §23.11 ApprovalArtifact — the bridge reads (does not mutate) the
  persisted approval row and refuses any row whose on-row identities
  disagree with the bridged outcome or whose ``approval_state`` is not
  ``"approved"`` (phase-1 narrow-path live authority state).
- v11 §23.7 ValidationReceipt — the bridge re-checks at seal-bridge
  time that the receipt bound by the upstream approval bridge is still
  admissible (``result == "pass"`` and not invalidated).
- v11 §23.14 AuditRecord — the bridge emits one
  ``real_fix_revision_seal_bridge_attested`` record whose
  ``artifact_refs`` carries all seven identities so a reviewer can walk
  ``InferenceArtifact → PatchProposal → ValidationReceipt →
  ReviewArtifact → ApprovalArtifact → Revision`` end-to-end (plus the
  ``SnapshotRoot`` written by the seal service for the same revision).
- foundation §1, §D-004, §6 step 9 — phase-1 narrow path: single-file
  text substitution with no manifest touch. The bridge refuses any
  patch row whose target id is not the real-fix narrow-path synthetic
  id, and any upstream row whose on-row ids do not match the
  approval-bridge outcome.

Scope lock:
- ONE ``RealFixApprovalBridgeOutcome`` in, ONE ``Revision`` row out.
  Fail-closed on any identity mismatch, missing row, non-admissible
  approval state, invalidated approval, non-pass / invalidated receipt,
  missing inference link, or altered real-fix narrow-path label; in
  those cases no seal is executed and no bridge attestation is
  appended.
- No evidence-plane expansion. No repository mutation beyond what
  ``RevisionSealService`` already does. No multi-file fixes. No
  retries. No background loops. No new providers. No phase-2 runtime
  work. No UI. No orchestrator redesign. No change to
  ``RevisionSealService``, ``ApprovalService``, ``ReviewService``,
  ``ValidationService``, ``RealFixApprovalBridge``,
  ``RealFixReviewBridge``, ``RealFixValidationBridge``, or
  ``RealFixPatchProjector``.
- No new artifact type, table, or schema. Reuses
  ``kernel/schemas/revision.schema.json``, ``RevisionSealService``,
  ``ApprovalArtifactRepository``, ``ReviewArtifactRepository``,
  ``ValidationReceiptRepository``, ``PatchProposalRepository``,
  ``InferenceArtifactRepository``, ``RevisionRepository``, and the
  existing append-only audit ledger.

The bridge is an adapter over already-verified surfaces. Its only new
contributions are:
  (a) fail-closed admission that the persisted ``ApprovalArtifact`` is
      the one produced by ``RealFixApprovalBridge`` for this outcome
      (task / root / reviewed_context / required_receipt_ids match and
      ``approval_state == "approved"``), that the upstream review,
      receipt, patch, and inference rows still match on-row, and that
      the receipt is still admissible (``result == "pass"`` and not
      invalidated); and
  (b) one audit event that names all seven ids so downstream evidence
      closure can walk the full chain from a single record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.lifecycle.real_fix_approval_bridge import (
    RealFixApprovalBridgeOutcome,
)
from kernel.services.approval_service import (
    ApprovalBarrierFailed,
    ApprovalRejected,
)
from kernel.services.revision_seal_service import (
    RevisionSealService,
    SealRejected,
)
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
    RevisionRepository,
    ValidationReceiptRepository,
)


class RealFixRevisionSealBridgeRejected(Exception):
    """Raised when a bridged approval is not admissible for sealing.

    Fail-closed: no ``RevisionSealService.seal_revision`` call is
    dispatched, no revision is written, and no bridge attestation is
    appended. Any downstream ``ApprovalBarrierFailed``,
    ``ApprovalRejected``, or ``SealRejected`` from the service bubbles
    up unchanged so that barrier- and seal-time governance rejection
    continues to use its existing surface.

    Admission conditions:

    - The outcome's ``approval_artifact_id`` exists in the repository.
    - The persisted approval's ``task_id``,
      ``originating_root_revision_id``, and
      ``reviewed_context_artifact_id`` equal the outcome's values.
    - The persisted approval's ``approval_state`` is ``"approved"``.
      ``pending`` / ``rejected`` / ``expired`` / ``invalidated`` states
      are explicitly non-admissible for the minimum honest bridge.
    - The persisted approval's ``required_receipt_ids`` equals exactly
      ``[outcome.validation_receipt_id]`` — the narrow-path invariant
      the approval bridge establishes.
    - The outcome's ``review_artifact_id`` exists and its ``task_id`` /
      ``root_revision_id`` / ``patch_proposal_id`` equal the outcome's
      values.
    - The outcome's ``validation_receipt_id`` exists, its ``task_id`` /
      ``root_revision_id`` equal the outcome's values, its ``result``
      is ``"pass"``, and its ``invalidated_at`` is ``None``.
    - The outcome's ``patch_proposal_id`` exists, its
      ``inference_artifact_id`` equals the outcome's value, its
      ``task_id`` / ``root_revision_id`` equal the outcome's values,
      and its single ``target_file_ids`` entry equals the real-fix
      narrow-path synthetic label.
    - The outcome's ``inference_artifact_id`` exists and its
      ``task_id`` / ``root_revision_id`` / ``context_artifact_id``
      equal the outcome's values.
    """


@dataclass(frozen=True)
class RealFixRevisionSealBridgeOutcome:
    """Return value of a successful revision-seal bridge call.

    The sealed ``Revision`` row is the authority-bearing artifact; this
    dataclass carries the seven ids a reviewer needs to walk the
    end-to-end chain from the originating ``InferenceArtifact`` through
    the projected patch, its receipt, the rendered review, the issued
    approval, and the produced revision + its snapshot root.
    """

    revision_id: str
    snapshot_root_id: str
    approval_artifact_id: str
    review_artifact_id: str
    validation_receipt_id: str
    patch_proposal_id: str
    inference_artifact_id: str
    context_artifact_id: str
    task_id: str
    root_revision_id: str


class RealFixRevisionSealBridge:
    """Bridge a bridged real-fix ``ApprovalArtifact`` to its ``Revision`` seal.

    The bridge holds no state of its own. It composes the existing
    ``RevisionSealService`` (which itself owns §22.2 seal ordering and
    §23.1 revision production, and invokes §22.3 seal-time barrier
    re-evaluation via ``ApprovalService.reverify_for_seal``) plus six
    read-only repositories. The bridge's only mutations are the rows
    written by the seal service and one append-only audit record
    emitted directly by this bridge.
    """

    def __init__(
        self,
        *,
        seal_service: RevisionSealService,
        approval_reader: ApprovalArtifactRepository,
        review_reader: ReviewArtifactRepository,
        receipt_reader: ValidationReceiptRepository,
        patch_reader: PatchProposalRepository,
        inference_reader: InferenceArtifactRepository,
        revision_reader: RevisionRepository,
        audit_ledger: Any,
    ) -> None:
        self._service = seal_service
        self._approval_reader = approval_reader
        self._review_reader = review_reader
        self._receipt_reader = receipt_reader
        self._patch_reader = patch_reader
        self._inference_reader = inference_reader
        self._revision_reader = revision_reader
        self._audit = audit_ledger

    # ------------------------------------------------------------------

    def bridge(
        self,
        *,
        outcome: RealFixApprovalBridgeOutcome,
        parent_revision_id: str | None = None,
        intent_id: str | None = None,
    ) -> RealFixRevisionSealBridgeOutcome:
        """Admit the outcome and produce one sealed ``Revision``."""
        if not isinstance(outcome, RealFixApprovalBridgeOutcome):
            raise RealFixRevisionSealBridgeRejected(
                "bridge input must be a RealFixApprovalBridgeOutcome; "
                f"got {type(outcome).__name__}"
            )

        # --- admit the approval row ----------------------------------
        approval = self._approval_reader.fetch(outcome.approval_artifact_id)
        if approval is None:
            raise RealFixRevisionSealBridgeRejected(
                "bridged approval artifact not found: "
                f"{outcome.approval_artifact_id}"
            )
        if approval.get("task_id") != outcome.task_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted approval artifact task_id mismatch"
            )
        if approval.get("originating_root_revision_id") != outcome.root_revision_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted approval artifact originating_root_revision_id mismatch"
            )
        if (
            approval.get("reviewed_context_artifact_id")
            != outcome.context_artifact_id
        ):
            raise RealFixRevisionSealBridgeRejected(
                "persisted approval artifact reviewed_context_artifact_id "
                "mismatch"
            )
        if approval.get("approval_state") != "approved":
            raise RealFixRevisionSealBridgeRejected(
                "approval is not in 'approved' state; "
                f"got {approval.get('approval_state')!r}"
            )
        if approval.get("invalidated_at") is not None:
            raise RealFixRevisionSealBridgeRejected(
                "approval has been invalidated; not admissible for seal"
            )
        required_receipt_ids = list(approval.get("required_receipt_ids") or [])
        if required_receipt_ids != [outcome.validation_receipt_id]:
            raise RealFixRevisionSealBridgeRejected(
                "persisted approval required_receipt_ids is not the "
                "expected single-receipt narrow-path shape: "
                f"expected [{outcome.validation_receipt_id!r}], "
                f"got {required_receipt_ids!r}"
            )

        # --- admit the review row ------------------------------------
        review = self._review_reader.fetch(outcome.review_artifact_id)
        if review is None:
            raise RealFixRevisionSealBridgeRejected(
                "bridged review artifact not found: "
                f"{outcome.review_artifact_id}"
            )
        if review.get("task_id") != outcome.task_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted review artifact task_id mismatch"
            )
        if review.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted review artifact root_revision_id mismatch"
            )
        if review.get("patch_proposal_id") != outcome.patch_proposal_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted review artifact patch_proposal_id mismatch"
            )

        # --- admit the receipt (still pass, still live) --------------
        receipt = self._receipt_reader.fetch(outcome.validation_receipt_id)
        if receipt is None:
            raise RealFixRevisionSealBridgeRejected(
                "bridged validation receipt not found: "
                f"{outcome.validation_receipt_id}"
            )
        if receipt.get("task_id") != outcome.task_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted validation receipt task_id mismatch"
            )
        if receipt.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted validation receipt root_revision_id mismatch"
            )
        if receipt.get("invalidated_at") is not None:
            raise RealFixRevisionSealBridgeRejected(
                "validation receipt has been invalidated; "
                "not admissible for seal"
            )
        if receipt.get("result") != "pass":
            raise RealFixRevisionSealBridgeRejected(
                "validation receipt result is not 'pass'; "
                f"got {receipt.get('result')!r}"
            )

        # --- admit the patch row (still real-fix narrow-path) --------
        stored = self._patch_reader.fetch(outcome.patch_proposal_id)
        if stored is None:
            raise RealFixRevisionSealBridgeRejected(
                "upstream patch proposal not found: "
                f"{outcome.patch_proposal_id}"
            )
        if stored.get("inference_artifact_id") != outcome.inference_artifact_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted patch proposal inference_artifact_id mismatch"
            )
        if stored.get("task_id") != outcome.task_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted patch proposal task_id mismatch"
            )
        if stored.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted patch proposal root_revision_id mismatch"
            )

        target_file_ids = list(stored.get("target_file_ids") or [])
        expected_target = f"real-fix::file::{outcome.task_id}"
        if target_file_ids != [expected_target]:
            raise RealFixRevisionSealBridgeRejected(
                "persisted patch proposal target_file_ids is not the "
                f"real-fix narrow-path label: expected [{expected_target!r}], "
                f"got {target_file_ids!r}"
            )

        # --- admit the inference row ---------------------------------
        inference = self._inference_reader.fetch(outcome.inference_artifact_id)
        if inference is None:
            raise RealFixRevisionSealBridgeRejected(
                "upstream inference artifact not found: "
                f"{outcome.inference_artifact_id}"
            )
        if inference.get("task_id") != outcome.task_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted inference artifact task_id mismatch"
            )
        if inference.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted inference artifact root_revision_id mismatch"
            )
        if inference.get("context_artifact_id") != outcome.context_artifact_id:
            raise RealFixRevisionSealBridgeRejected(
                "persisted inference artifact context_artifact_id mismatch"
            )

        # --- delegate to the service ---------------------------------
        # ApprovalBarrierFailed / ApprovalRejected / SealRejected bubble
        # up unchanged; the bridge does not emit an attestation on
        # rejection. The service's own ``approval_seal_time_barrier_rejected``
        # or seal-step audit (if any) is the evidence the reviewer will
        # see.
        try:
            revision_id = self._service.seal_revision(
                task_id=outcome.task_id,
                approval_id=outcome.approval_artifact_id,
                context_artifact_id=outcome.context_artifact_id,
                intent_id=intent_id,
                parent_revision_id=parent_revision_id,
            )
        except (ApprovalBarrierFailed, ApprovalRejected, SealRejected):
            raise

        revision = self._revision_reader.fetch(revision_id)
        if revision is None:
            # Defense-in-depth: the service just wrote this row; if it
            # is somehow absent, refuse to emit an attestation pointing
            # at a non-existent artifact.
            raise RealFixRevisionSealBridgeRejected(
                "seal service reported id "
                f"{revision_id!r} but row is not present"
            )
        if revision.get("state") != "sealed":
            raise RealFixRevisionSealBridgeRejected(
                "sealed revision row is not in 'sealed' state; "
                f"got {revision.get('state')!r}"
            )
        if revision.get("task_id") != outcome.task_id:
            raise RealFixRevisionSealBridgeRejected(
                "sealed revision row task_id mismatch"
            )
        if revision.get("approval_id") != outcome.approval_artifact_id:
            raise RealFixRevisionSealBridgeRejected(
                "sealed revision row approval_id mismatch"
            )
        if (
            revision.get("originating_context_artifact_id")
            != outcome.context_artifact_id
        ):
            raise RealFixRevisionSealBridgeRejected(
                "sealed revision row originating_context_artifact_id mismatch"
            )
        snapshot_root_id = revision.get("snapshot_root_id")
        if not snapshot_root_id:
            raise RealFixRevisionSealBridgeRejected(
                "sealed revision row has no snapshot_root_id"
            )

        # The attestation record is the single audit hop that names all
        # seven identities a reviewer needs to walk the chain. The seal
        # service has already appended its own ``revision_sealed``
        # record linking the revision to the snapshot root and approval;
        # this record adds the upstream review / receipt / patch /
        # inference bindings that the revision schema does not carry
        # on-row, and tags the source as real-fix tracer.
        #
        # AUDIT-003 / §22.1: name ``intent_id`` in both ``artifact_refs``
        # and ``payload``. ``RevisionSealService.seal_revision`` above
        # fail-closes on a missing / empty / unknown ``intent_id`` before
        # returning, so at this point the supplied id has been verified
        # (when the intent-anchor reader is wired) to name a durable
        # ``intent_anchor_records`` row whose ``task_id`` matches the
        # seal's, and has been written onto ``Revision.intent_id``.
        # Naming it here mirrors the pattern already applied to the
        # seal service's own ``revision_sealed`` audit and to the
        # orchestrator's ``real_fix_chain_completed`` wrapper, closing
        # the last bridge-layer one-hop asymmetry so a reviewer reading
        # only this record can recover the originating durable intent-
        # anchor id without a second fetch on ``revisions.intent_id``.
        # No schema change, no migration, no new artifact family, no
        # new audit record type.
        audit_artifact_refs: list[str] = [
            revision_id,
            snapshot_root_id,
            outcome.approval_artifact_id,
            outcome.review_artifact_id,
            outcome.validation_receipt_id,
            outcome.patch_proposal_id,
            outcome.inference_artifact_id,
        ]
        if intent_id is not None:
            audit_artifact_refs.append(intent_id)
        self._audit.append(
            record_type="real_fix_revision_seal_bridge_attested",
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
            artifact_refs=audit_artifact_refs,
            payload={
                "revision_id": revision_id,
                "snapshot_root_id": snapshot_root_id,
                "approval_artifact_id": outcome.approval_artifact_id,
                "review_artifact_id": outcome.review_artifact_id,
                "validation_receipt_id": outcome.validation_receipt_id,
                "patch_proposal_id": outcome.patch_proposal_id,
                "inference_artifact_id": outcome.inference_artifact_id,
                "context_artifact_id": outcome.context_artifact_id,
                "intent_id": intent_id,
                "revision_state": revision["state"],
                "sealed_at": revision["sealed_at"],
                "source": "real_fix_tracer",
            },
        )

        return RealFixRevisionSealBridgeOutcome(
            revision_id=revision_id,
            snapshot_root_id=snapshot_root_id,
            approval_artifact_id=outcome.approval_artifact_id,
            review_artifact_id=outcome.review_artifact_id,
            validation_receipt_id=outcome.validation_receipt_id,
            patch_proposal_id=outcome.patch_proposal_id,
            inference_artifact_id=outcome.inference_artifact_id,
            context_artifact_id=outcome.context_artifact_id,
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
        )
