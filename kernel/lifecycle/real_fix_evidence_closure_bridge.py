"""
Real-fix narrow-path evidence-closure bridge: take exactly one
``RealFixRevisionSealBridgeOutcome`` that came from the verified real-fix
path and produce exactly one schema-valid ``ReplayAnchor`` row via the
existing ``EvidenceService.close_evidence``, with an explicit audit
cross-reference that names the originating ``Revision``, ``SnapshotRoot``,
``ApprovalArtifact``, ``ReviewArtifact``, ``ValidationReceipt``,
``PatchProposal``, AND the upstream ``InferenceArtifact`` (plus the
``context_artifact_id``) so a reviewer can walk the full end-to-end chain
from a single record.

Constitutional anchors:
- v11 §22.5 Replay Fidelity Contract / §23.12 ReplayAnchor — the bridge
  produces exactly one evidence-plane closure by delegating to
  ``EvidenceService.close_evidence`` unchanged. No new schema, no new
  table, no migration, no change to the replay classifier or to the
  version tuple.
- v11 §23.1 Revision / §23.3 SnapshotRoot — the bridge refuses any
  revision row whose ``state != "sealed"``, or whose on-row identities
  disagree with the bridged seal outcome, and refuses any missing
  snapshot-root linkage.
- v11 §23.14 AuditRecord — the bridge emits one
  ``real_fix_evidence_closure_bridge_attested`` record whose
  ``artifact_refs`` carries all eight identities (replay anchor, revision,
  snapshot root, approval, review, receipt, patch, inference) so a
  reviewer can walk ``InferenceArtifact → PatchProposal →
  ValidationReceipt → ReviewArtifact → ApprovalArtifact → Revision +
  SnapshotRoot → ReplayAnchor`` end-to-end from a single record. The
  existing ``evidence_closure`` audit record emitted by
  ``EvidenceService.close_evidence`` is preserved unchanged.
- foundation §1, §D-004, §6 step 10 — phase-1 narrow signable path
  terminates at a durable ReplayAnchor. The bridge refuses any upstream
  row whose on-row ids no longer match the seal-bridge outcome, any
  altered real-fix narrow-path label, or any missing inference linkage.

Scope lock:
- ONE ``RealFixRevisionSealBridgeOutcome`` in, ONE ``ReplayAnchor`` row
  out. Fail-closed on any identity mismatch, missing row, non-sealed
  revision state, missing snapshot root, missing inference linkage,
  altered real-fix narrow-path label, or any evidence-plane refusal from
  the existing ``EvidenceService``; in those cases no close_evidence
  call is dispatched after a detected upstream tamper and no bridge
  attestation is appended. Any ``EvidenceClosureRejected`` raised by the
  service bubbles up unchanged.
- No evidence-plane expansion. No repository mutation beyond what
  ``EvidenceService`` already does. No multi-file fixes. No retries.
  No background loops. No new providers. No phase-2 runtime work. No
  UI. No orchestrator redesign. No change to ``EvidenceService``,
  ``ReplayClassifier``, ``RevisionSealService``, ``ApprovalService``,
  ``ReviewService``, ``ValidationService``, any prior real-fix bridge,
  or ``RealFixPatchProjector``.
- No new artifact type, table, or schema. Reuses
  ``kernel/schemas/replay_anchor.schema.json``, ``EvidenceService``,
  and the eight existing read-only repositories.

The bridge is an adapter over already-verified surfaces. Its only new
contributions are:
  (a) fail-closed admission that the persisted revision row is sealed,
      bound to the outcome's approval / context / snapshot ids, and
      that the upstream approval / review / receipt / patch / inference
      rows still match on-row (same tamper checks the seal bridge
      performed, re-run here so the evidence-plane closure refuses to
      attest over a chain that has been mutated since seal); and
  (b) one audit event that names all eight ids so downstream chain
      walking can reach any upstream artifact from the evidence anchor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.lifecycle.real_fix_revision_seal_bridge import (
    RealFixRevisionSealBridgeOutcome,
)
from kernel.services.evidence_service import (
    EvidenceClosureRejected,
    EvidenceService,
)
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ReplayAnchorRepository,
    ReviewArtifactRepository,
    RevisionRepository,
    SnapshotRootRepository,
    ValidationReceiptRepository,
)


class RealFixEvidenceClosureBridgeRejected(Exception):
    """Raised when a bridged seal outcome is not admissible for closure.

    Fail-closed: no ``EvidenceService.close_evidence`` call is dispatched
    on a detected upstream tamper, no replay anchor is written by this
    bridge, and no bridge attestation is appended. An
    ``EvidenceClosureRejected`` from the service bubbles up unchanged so
    that evidence-plane refusal continues to use its existing surface.

    Admission conditions:

    - The outcome's ``revision_id`` exists, is in state ``"sealed"``,
      and its ``task_id`` / ``approval_id`` / ``originating_context_artifact_id``
      / ``snapshot_root_id`` equal the outcome's values.
    - The outcome's ``snapshot_root_id`` exists and is bound to the
      outcome's ``revision_id``.
    - The outcome's ``approval_artifact_id`` exists, is in ``"approved"``
      state, is not invalidated, its ``required_receipt_ids`` equals
      exactly ``[outcome.validation_receipt_id]``, and its
      ``task_id`` / ``originating_root_revision_id`` /
      ``reviewed_context_artifact_id`` equal the outcome's values.
    - The outcome's ``review_artifact_id`` exists and its ``task_id`` /
      ``root_revision_id`` / ``patch_proposal_id`` equal the outcome's
      values.
    - The outcome's ``validation_receipt_id`` exists, its ``result`` is
      ``"pass"``, it is not invalidated, and its ``task_id`` /
      ``root_revision_id`` equal the outcome's values.
    - The outcome's ``patch_proposal_id`` exists, its
      ``inference_artifact_id`` equals the outcome's value, its
      ``task_id`` / ``root_revision_id`` equal the outcome's values,
      and its single ``target_file_ids`` entry equals the real-fix
      narrow-path synthetic label ``real-fix::file::<task_id>``.
    - The outcome's ``inference_artifact_id`` exists and its
      ``task_id`` / ``root_revision_id`` / ``context_artifact_id``
      equal the outcome's values.
    """


@dataclass(frozen=True)
class RealFixEvidenceClosureBridgeOutcome:
    """Return value of a successful evidence-closure bridge call.

    The persisted ``ReplayAnchor`` row is the authority-bearing terminal
    artifact of the narrow signable path; this dataclass carries the
    ten ids a reviewer needs to walk the end-to-end chain from the
    originating ``InferenceArtifact`` through the projected patch, its
    receipt, the rendered review, the issued approval, the produced
    revision + snapshot root, and the emitted replay anchor.
    """

    replay_anchor_id: str
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


class RealFixEvidenceClosureBridge:
    """Bridge a bridged real-fix sealed ``Revision`` to its ``ReplayAnchor``.

    The bridge holds no state of its own. It composes the existing
    ``EvidenceService`` (which itself owns §22.5 replay classification
    and §23.12 replay-anchor persistence) plus eight read-only
    repositories. The bridge's only mutations are the row written by
    ``EvidenceService`` and one append-only audit record emitted
    directly by this bridge. The service's own ``evidence_closure``
    audit record is preserved unchanged.
    """

    def __init__(
        self,
        *,
        evidence_service: EvidenceService,
        revision_reader: RevisionRepository,
        snapshot_reader: SnapshotRootRepository,
        approval_reader: ApprovalArtifactRepository,
        review_reader: ReviewArtifactRepository,
        receipt_reader: ValidationReceiptRepository,
        patch_reader: PatchProposalRepository,
        inference_reader: InferenceArtifactRepository,
        replay_anchor_reader: ReplayAnchorRepository,
        audit_ledger: Any,
    ) -> None:
        self._service = evidence_service
        self._revision_reader = revision_reader
        self._snapshot_reader = snapshot_reader
        self._approval_reader = approval_reader
        self._review_reader = review_reader
        self._receipt_reader = receipt_reader
        self._patch_reader = patch_reader
        self._inference_reader = inference_reader
        self._replay_anchor_reader = replay_anchor_reader
        self._audit = audit_ledger

    # ------------------------------------------------------------------

    def bridge(
        self,
        *,
        outcome: RealFixRevisionSealBridgeOutcome,
    ) -> RealFixEvidenceClosureBridgeOutcome:
        """Admit the outcome and produce one closed ``ReplayAnchor``."""
        if not isinstance(outcome, RealFixRevisionSealBridgeOutcome):
            raise RealFixEvidenceClosureBridgeRejected(
                "bridge input must be a RealFixRevisionSealBridgeOutcome; "
                f"got {type(outcome).__name__}"
            )

        # --- admit the sealed revision row ---------------------------
        revision = self._revision_reader.fetch(outcome.revision_id)
        if revision is None:
            raise RealFixEvidenceClosureBridgeRejected(
                f"bridged revision not found: {outcome.revision_id}"
            )
        if revision.get("state") != "sealed":
            raise RealFixEvidenceClosureBridgeRejected(
                "bridged revision is not in 'sealed' state; "
                f"got {revision.get('state')!r}"
            )
        if revision.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted revision task_id mismatch"
            )
        if revision.get("approval_id") != outcome.approval_artifact_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted revision approval_id mismatch"
            )
        if (
            revision.get("originating_context_artifact_id")
            != outcome.context_artifact_id
        ):
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted revision originating_context_artifact_id mismatch"
            )
        if revision.get("snapshot_root_id") != outcome.snapshot_root_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted revision snapshot_root_id mismatch"
            )

        # --- admit the snapshot root row -----------------------------
        snapshot = self._snapshot_reader.fetch(outcome.snapshot_root_id)
        if snapshot is None:
            raise RealFixEvidenceClosureBridgeRejected(
                f"bridged snapshot root not found: {outcome.snapshot_root_id}"
            )
        if snapshot.get("revision_id") != outcome.revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted snapshot root revision_id mismatch"
            )

        # --- admit the approval row ----------------------------------
        approval = self._approval_reader.fetch(outcome.approval_artifact_id)
        if approval is None:
            raise RealFixEvidenceClosureBridgeRejected(
                "bridged approval artifact not found: "
                f"{outcome.approval_artifact_id}"
            )
        if approval.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted approval artifact task_id mismatch"
            )
        if approval.get("originating_root_revision_id") != outcome.root_revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted approval artifact originating_root_revision_id mismatch"
            )
        if (
            approval.get("reviewed_context_artifact_id")
            != outcome.context_artifact_id
        ):
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted approval artifact reviewed_context_artifact_id "
                "mismatch"
            )
        if approval.get("approval_state") != "approved":
            raise RealFixEvidenceClosureBridgeRejected(
                "approval is not in 'approved' state; "
                f"got {approval.get('approval_state')!r}"
            )
        if approval.get("invalidated_at") is not None:
            raise RealFixEvidenceClosureBridgeRejected(
                "approval has been invalidated; not admissible for closure"
            )
        required_receipt_ids = list(approval.get("required_receipt_ids") or [])
        if required_receipt_ids != [outcome.validation_receipt_id]:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted approval required_receipt_ids is not the "
                "expected single-receipt narrow-path shape: "
                f"expected [{outcome.validation_receipt_id!r}], "
                f"got {required_receipt_ids!r}"
            )

        # --- admit the review row ------------------------------------
        review = self._review_reader.fetch(outcome.review_artifact_id)
        if review is None:
            raise RealFixEvidenceClosureBridgeRejected(
                "bridged review artifact not found: "
                f"{outcome.review_artifact_id}"
            )
        if review.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted review artifact task_id mismatch"
            )
        if review.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted review artifact root_revision_id mismatch"
            )
        if review.get("patch_proposal_id") != outcome.patch_proposal_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted review artifact patch_proposal_id mismatch"
            )

        # --- admit the receipt (still pass, still live) --------------
        receipt = self._receipt_reader.fetch(outcome.validation_receipt_id)
        if receipt is None:
            raise RealFixEvidenceClosureBridgeRejected(
                "bridged validation receipt not found: "
                f"{outcome.validation_receipt_id}"
            )
        if receipt.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted validation receipt task_id mismatch"
            )
        if receipt.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted validation receipt root_revision_id mismatch"
            )
        if receipt.get("invalidated_at") is not None:
            raise RealFixEvidenceClosureBridgeRejected(
                "validation receipt has been invalidated; "
                "not admissible for closure"
            )
        if receipt.get("result") != "pass":
            raise RealFixEvidenceClosureBridgeRejected(
                "validation receipt result is not 'pass'; "
                f"got {receipt.get('result')!r}"
            )

        # --- admit the patch row (still real-fix narrow-path) --------
        stored = self._patch_reader.fetch(outcome.patch_proposal_id)
        if stored is None:
            raise RealFixEvidenceClosureBridgeRejected(
                "upstream patch proposal not found: "
                f"{outcome.patch_proposal_id}"
            )
        if stored.get("inference_artifact_id") != outcome.inference_artifact_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted patch proposal inference_artifact_id mismatch"
            )
        if stored.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted patch proposal task_id mismatch"
            )
        if stored.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted patch proposal root_revision_id mismatch"
            )
        target_file_ids = list(stored.get("target_file_ids") or [])
        expected_target = f"real-fix::file::{outcome.task_id}"
        if target_file_ids != [expected_target]:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted patch proposal target_file_ids is not the "
                f"real-fix narrow-path label: expected [{expected_target!r}], "
                f"got {target_file_ids!r}"
            )

        # --- admit the inference row ---------------------------------
        inference = self._inference_reader.fetch(outcome.inference_artifact_id)
        if inference is None:
            raise RealFixEvidenceClosureBridgeRejected(
                "upstream inference artifact not found: "
                f"{outcome.inference_artifact_id}"
            )
        if inference.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted inference artifact task_id mismatch"
            )
        if inference.get("root_revision_id") != outcome.root_revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted inference artifact root_revision_id mismatch"
            )
        if inference.get("context_artifact_id") != outcome.context_artifact_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted inference artifact context_artifact_id mismatch"
            )

        # --- delegate to the service ---------------------------------
        # EvidenceClosureRejected bubbles up unchanged; the bridge does
        # not emit an attestation on rejection. The service's own
        # evidence_closure audit record is the evidence the reviewer
        # will see on success.
        try:
            replay_anchor_id = self._service.close_evidence(
                task_id=outcome.task_id,
                revision_id=outcome.revision_id,
            )
        except EvidenceClosureRejected:
            raise

        anchor = self._replay_anchor_reader.fetch(replay_anchor_id)
        if anchor is None:
            # Defense-in-depth: the service just wrote this row; if it
            # is somehow absent, refuse to emit an attestation pointing
            # at a non-existent artifact.
            raise RealFixEvidenceClosureBridgeRejected(
                "evidence service reported id "
                f"{replay_anchor_id!r} but row is not present"
            )
        if anchor.get("task_id") != outcome.task_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted replay anchor task_id mismatch"
            )
        # The existing EvidenceService uses the sealed revision_id as the
        # replay anchor's root_revision_id surface; the originating
        # ``real-fix::root::<task_id>`` identity is preserved on every
        # upstream row and is additionally named on the bridge
        # attestation payload. This dual binding lets a reviewer walk
        # from anchor back through revision and from revision back to
        # the originating root without ambiguity.
        if anchor.get("root_revision_id") != outcome.revision_id:
            raise RealFixEvidenceClosureBridgeRejected(
                "persisted replay anchor root_revision_id does not equal "
                "the sealed revision id"
            )

        # The attestation record is the single audit hop that names all
        # eight identities a reviewer needs to walk the chain. The
        # evidence service has already appended its own
        # ``evidence_closure`` record linking the anchor to the
        # revision; this record adds the upstream approval / review /
        # receipt / patch / inference / snapshot-root bindings that the
        # replay-anchor schema does not carry on-row, and tags the
        # source as real-fix tracer.
        self._audit.append(
            record_type="real_fix_evidence_closure_bridge_attested",
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
            artifact_refs=[
                replay_anchor_id,
                outcome.revision_id,
                outcome.snapshot_root_id,
                outcome.approval_artifact_id,
                outcome.review_artifact_id,
                outcome.validation_receipt_id,
                outcome.patch_proposal_id,
                outcome.inference_artifact_id,
            ],
            payload={
                "replay_anchor_id": replay_anchor_id,
                "revision_id": outcome.revision_id,
                "snapshot_root_id": outcome.snapshot_root_id,
                "approval_artifact_id": outcome.approval_artifact_id,
                "review_artifact_id": outcome.review_artifact_id,
                "validation_receipt_id": outcome.validation_receipt_id,
                "patch_proposal_id": outcome.patch_proposal_id,
                "inference_artifact_id": outcome.inference_artifact_id,
                "context_artifact_id": outcome.context_artifact_id,
                "originating_root_revision_id": outcome.root_revision_id,
                "anchor_root_revision_id": anchor["root_revision_id"],
                "replay_class_claim": anchor["replay_class_claim"],
                "source": "real_fix_tracer",
            },
        )

        return RealFixEvidenceClosureBridgeOutcome(
            replay_anchor_id=replay_anchor_id,
            revision_id=outcome.revision_id,
            snapshot_root_id=outcome.snapshot_root_id,
            approval_artifact_id=outcome.approval_artifact_id,
            review_artifact_id=outcome.review_artifact_id,
            validation_receipt_id=outcome.validation_receipt_id,
            patch_proposal_id=outcome.patch_proposal_id,
            inference_artifact_id=outcome.inference_artifact_id,
            context_artifact_id=outcome.context_artifact_id,
            task_id=outcome.task_id,
            root_revision_id=outcome.root_revision_id,
        )
