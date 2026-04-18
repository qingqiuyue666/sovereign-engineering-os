"""
Real-fix narrow-path review bridge: take exactly one bridged
``ValidationReceipt`` that came from the verified real-fix path and
produce exactly one schema-valid ``ReviewArtifact`` via the existing
``ReviewService``, with an explicit audit cross-reference back to the
originating ``PatchProposal`` AND the upstream ``InferenceArtifact``.

Constitutional anchors:
- v11 §23.7 ValidationReceipt — the bridge reads (does not mutate) the
  persisted receipt row and refuses any result that is not ``pass`` or
  any receipt that has been invalidated.
- v11 §23.10 ReviewArtifact — the bridge produces exactly one such row
  by delegating to ``ReviewService.render_review`` unchanged. No new
  schema.
- v11 §22.14 Review Surface Governance Contract — the bridge does not
  bypass the existing review governance; it simply reuses it. Any
  ``ReviewRejected`` from the service bubbles up untouched.
- v11 §22.11 Taint Visibility — the service already merges the
  upstream receipt's taint_set into the review artifact; the bridge
  relies on that behavior and does not mask it.
- v11 §23.14 AuditRecord — the bridge emits one
  ``real_fix_review_bridge_attested`` record whose ``artifact_refs``
  carries all four identities so a reviewer can walk
  ``InferenceArtifact → PatchProposal → ValidationReceipt →
  ReviewArtifact`` end-to-end.
- foundation §1, §D-004 — phase-1 narrow path: single-file text
  substitution with no manifest touch. The bridge refuses any patch row
  whose target id is not the real-fix narrow-path synthetic id, and any
  receipt whose on-row ids do not match the validation-bridge outcome.

Scope lock:
- ONE ``RealFixValidationBridgeOutcome`` in, ONE ``ReviewArtifact`` row
  out. Fail-closed on any identity mismatch or non-admissible receipt
  state (result != "pass", or invalidated); in those cases no review is
  rendered and no bridge audit event is appended.
- No approval. No revision sealing. No evidence-plane expansion. No
  repository mutation. No multi-file fixes. No retries. No background
  loops. No new providers. No phase-2 runtime work. No UI. No
  orchestrator redesign. No change to ``ReviewService``,
  ``RealFixValidationBridge``, or ``RealFixPatchProjector``.
- No new artifact type, table, or schema. Reuses
  ``kernel/schemas/review_artifact.schema.json``, ``ReviewService``,
  ``PatchProposalRepository``, ``ValidationReceiptRepository``, and the
  existing append-only audit ledger.

The bridge is an adapter over two already-verified surfaces. Its only
new contribution is:
  (a) fail-closed admission that the persisted ``ValidationReceipt`` is
      the one produced by ``RealFixValidationBridge`` for this outcome
      (task/root match, not invalidated, and result == "pass"), and
      that the associated ``PatchProposal`` is still the real-fix
      narrow-path row (target id and inference linkage preserved); and
  (b) one audit event that names all four ids so downstream review can
      walk the full chain from a single record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridgeOutcome,
)
from kernel.services.review_service import (
    RenderingProvenance,
    ReviewRejected,
    ReviewService,
)
from kernel.stores.sqlite.repositories import (
    PatchProposalRepository,
    ReviewArtifactRepository,
    ValidationReceiptRepository,
)


class RealFixReviewBridgeRejected(Exception):
    """Raised when a bridged receipt is not admissible for review.

    Fail-closed: no ``ReviewService.render_review`` call is dispatched,
    no review row is written, and no bridge audit event is appended.
    Any downstream ``ReviewRejected`` from the service is re-raised
    unchanged so that review-governance rejection continues to use its
    existing surface.

    Admission conditions:

    - The outcome's ``validation_receipt_id`` exists in the repository.
    - The persisted receipt's ``task_id`` and ``root_revision_id`` equal
      the outcome's values.
    - The persisted receipt's ``result`` is ``"pass"``. ``fail`` and
      ``quarantined`` receipts are explicitly non-admissible for the
      minimum honest bridge.
    - The persisted receipt's ``invalidated_at`` is ``None``. An
      already-invalidated receipt cannot be promoted to review.
    - The outcome's ``patch_proposal_id`` exists in the repository, its
      ``inference_artifact_id`` equals the outcome's value, and its
      ``task_id`` / ``root_revision_id`` equal the outcome's values.
    - The persisted patch row's single ``target_file_ids`` entry equals
      the real-fix narrow-path synthetic label. This is the
      audit-visible tag that distinguishes rows produced by the real-fix
      projector from any other origin.
    """


@dataclass(frozen=True)
class RealFixReviewBridgeOutcome:
    """Return value of a successful review bridge call.

    The ``ReviewArtifact`` row is the authority-bearing artifact; this
    dataclass carries the four ids that a reviewer needs to walk the
    end-to-end chain from a verified real-fix inference through the
    projected patch proposal and its receipt to the produced review.
    """

    review_artifact_id: str
    validation_receipt_id: str
    patch_proposal_id: str
    inference_artifact_id: str
    task_id: str
    root_revision_id: str


class RealFixReviewBridge:
    """Bridge a bridged real-fix ``ValidationReceipt`` to its ``ReviewArtifact``.

    The bridge holds no state of its own. It composes the existing
    ``ReviewService`` (which itself owns §22.14 review governance and
    §23.10 review production) and the existing
    ``ValidationReceiptRepository`` + ``PatchProposalRepository`` (both
    read-only here). The bridge's only mutations are:

    - the one ``ReviewArtifact`` row written by the service, and
    - one append-only audit record emitted directly by this bridge.
    """

    def __init__(
        self,
        *,
        review_service: ReviewService,
        receipt_reader: ValidationReceiptRepository,
        patch_reader: PatchProposalRepository,
        review_reader: ReviewArtifactRepository,
        audit_ledger: Any,
    ) -> None:
        self._service = review_service
        self._receipt_reader = receipt_reader
        self._patch_reader = patch_reader
        self._review_reader = review_reader
        self._audit = audit_ledger

    # ------------------------------------------------------------------

    def bridge(
        self,
        *,
        outcome: RealFixValidationBridgeOutcome,
        risk_class: str = "low",
        rendering_provenance: RenderingProvenance | None = None,
        intent_id: str | None = None,
    ) -> RealFixReviewBridgeOutcome:
        """Admit the outcome and produce one ``ReviewArtifact``.

        ``risk_class`` and ``rendering_provenance`` are passed through
        to ``ReviewService.render_review`` unchanged; defaults match the
        phase-1 narrow path (``risk_class="low"`` and the service's
        default renderer). Callers that need explicit overrides use the
        same surface they already use with ``ReviewService`` directly.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint. The bridge only names
        it in the attestation record so a reviewer reading that single
        audit hop can recover the originating intent-anchor id without
        a second fetch. Authoritative fail-closed verification of
        ``intent_id`` against ``intent_anchor_records`` remains the
        responsibility of the downstream ``RevisionSealService`` at
        stage 6; this bridge performs no independent verification.
        """
        if not isinstance(outcome, RealFixValidationBridgeOutcome):
            raise RealFixReviewBridgeRejected(
                "bridge input must be a RealFixValidationBridgeOutcome; "
                f"got {type(outcome).__name__}"
            )

        # --- admit the receipt ----------------------------------------
        receipt = self._receipt_reader.fetch(outcome.validation_receipt_id)
        if receipt is None:
            raise RealFixReviewBridgeRejected(
                "bridged validation receipt not found: "
                f"{outcome.validation_receipt_id}"
            )
        if receipt.get("task_id") != outcome.task_id:
            raise RealFixReviewBridgeRejected(
                "persisted validation receipt task_id mismatch"
            )
        if receipt.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixReviewBridgeRejected(
                "persisted validation receipt root_revision_id mismatch"
            )
        if receipt.get("invalidated_at") is not None:
            raise RealFixReviewBridgeRejected(
                "validation receipt has been invalidated; "
                "not admissible for review"
            )
        if receipt.get("result") != "pass":
            # Only a pass receipt is admissible for the minimum honest
            # review bridge. fail/quarantined receipts are their own
            # evidence and do not cross the review threshold here.
            raise RealFixReviewBridgeRejected(
                "validation receipt result is not 'pass'; "
                f"got {receipt.get('result')!r}"
            )

        # --- admit the upstream patch row -----------------------------
        stored = self._patch_reader.fetch(outcome.patch_proposal_id)
        if stored is None:
            raise RealFixReviewBridgeRejected(
                "upstream patch proposal not found: "
                f"{outcome.patch_proposal_id}"
            )
        if stored.get("inference_artifact_id") != outcome.inference_artifact_id:
            raise RealFixReviewBridgeRejected(
                "persisted patch proposal inference_artifact_id mismatch"
            )
        if stored.get("task_id") != outcome.task_id:
            raise RealFixReviewBridgeRejected(
                "persisted patch proposal task_id mismatch"
            )
        if stored.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixReviewBridgeRejected(
                "persisted patch proposal root_revision_id mismatch"
            )

        target_file_ids = list(stored.get("target_file_ids") or [])
        expected_target = f"real-fix::file::{outcome.task_id}"
        if target_file_ids != [expected_target]:
            raise RealFixReviewBridgeRejected(
                "persisted patch proposal target_file_ids is not the "
                f"real-fix narrow-path label: expected [{expected_target!r}], "
                f"got {target_file_ids!r}"
            )

        # --- delegate to the service ----------------------------------
        try:
            review_artifact_id = self._service.render_review(
                task_id=outcome.task_id,
                patch_proposal_id=outcome.patch_proposal_id,
                validation_receipt_id=outcome.validation_receipt_id,
                risk_class=risk_class,
                rendering_provenance=rendering_provenance,
                intent_id=intent_id,
            )
        except ReviewRejected:
            # Fail-closed: no bridge attestation on rejection. The
            # service's own rejection audit (if any) is the evidence
            # the reviewer will see.
            raise

        review = self._review_reader.fetch(review_artifact_id)
        if review is None:
            # Defense-in-depth: the service just wrote this row; if it
            # is somehow absent, refuse to emit an attestation pointing
            # at a non-existent artifact.
            raise RealFixReviewBridgeRejected(
                "review service reported id "
                f"{review_artifact_id!r} but row is not present"
            )

        # The attestation record is the single audit hop that names all
        # four identities a reviewer needs to walk the chain. The
        # service has already appended its own
        # ``review_artifact_created`` record linking the review to the
        # patch proposal and the receipt; this record adds the upstream
        # ``InferenceArtifact`` binding that the review schema does not
        # carry on-row, and tags the source as real-fix tracer.
        #
        # AUDIT-003 / §22.1: name ``intent_id`` in both ``artifact_refs``
        # and ``payload``. The id is the durable
        # ``intent_anchor_records.intent_id`` minted at the real-fix
        # chain entrypoint and threaded in by the orchestrator. Naming
        # it here mirrors the pattern already applied to
        # ``real_fix_approval_bridge_attested`` (stage 5),
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
        self._audit.append(
            record_type="real_fix_review_bridge_attested",
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
            artifact_refs=[
                review_artifact_id,
                outcome.validation_receipt_id,
                outcome.patch_proposal_id,
                outcome.inference_artifact_id,
                intent_id,
            ],
            payload={
                "review_artifact_id": review_artifact_id,
                "validation_receipt_id": outcome.validation_receipt_id,
                "patch_proposal_id": outcome.patch_proposal_id,
                "inference_artifact_id": outcome.inference_artifact_id,
                "intent_id": intent_id,
                "risk_class": review["risk_class"],
                "self_summary_flag": bool(
                    review.get("rendering_provenance", {}).get(
                        "self_summary_flag", False
                    )
                ),
                "source": "real_fix_tracer",
            },
        )

        return RealFixReviewBridgeOutcome(
            review_artifact_id=review_artifact_id,
            validation_receipt_id=outcome.validation_receipt_id,
            patch_proposal_id=outcome.patch_proposal_id,
            inference_artifact_id=outcome.inference_artifact_id,
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
        )
