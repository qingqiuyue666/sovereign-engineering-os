"""
Real-fix narrow-path validation bridge: take exactly one projected
``PatchProposal`` that came from the verified real-fix path and produce
exactly one schema-valid ``ValidationReceipt`` via the existing
``ValidationService``, with an explicit audit cross-reference back to
the originating ``InferenceArtifact``.

Constitutional anchors:
- v11 §23.6 PatchProposal — the bridge reads (does not mutate) the
  projected patch row.
- v11 §23.7 ValidationReceipt — the bridge produces exactly one such
  row by delegating to ``ValidationService`` unchanged. No new schema.
- v11 §22.4 Validation Quarantine Enforcement Contract — the bridge
  does not bypass the existing quarantine admission; it simply reuses
  it. Any ``ValidationRejected`` from the service bubbles up untouched.
- v11 §23.14 AuditRecord — the bridge emits one
  ``real_fix_validation_bridge_attested`` record whose
  ``artifact_refs`` carries all three identities so a reviewer can walk
  ``InferenceArtifact → PatchProposal → ValidationReceipt`` end-to-end.
- foundation §1, §D-004 — phase-1 narrow path: single-file text
  substitution with no manifest touch. The bridge refuses any patch row
  whose target id is not the real-fix narrow-path synthetic id.

Scope lock:
- ONE projected ``PatchProposal`` row in, ONE ``ValidationReceipt`` row
  out. Fail-closed on any admission mismatch; no receipt issued and no
  bridge audit event appended.
- No review. No approval. No revision sealing. No evidence plane
  expansion. No repository mutation. No multi-file fixes. No retries.
  No background loops. No new providers. No phase-2 runtime work. No
  UI. No orchestrator redesign. No change to ``ValidationService`` or
  ``RealFixPatchProjector``.
- No new artifact type, table, or schema. Reuses
  ``kernel/schemas/validation_receipt.schema.json``,
  ``ValidationService``, ``PatchProposalRepository``, and the existing
  append-only audit ledger.

The bridge is an adapter over two already-verified surfaces. Its only
new contribution is:
  (a) fail-closed admission that the inbound ``PatchProposal`` row is
      the one that was written by ``RealFixPatchProjector`` (projection
      identities must match the persisted row, target id must be the
      real-fix synthetic label); and
  (b) one audit event that names all three ids so downstream review
      can walk the full chain from a single record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.lifecycle.real_fix_patch_projector import RealFixPatchProjection
from kernel.services.validation_service import (
    StaticCheckResult,
    ValidationRejected,
    ValidationService,
)
from kernel.stores.sqlite.repositories import (
    PatchProposalRepository,
    ValidationReceiptRepository,
)
from validation.quarantine.runner_adapter import QuarantineRun


class RealFixValidationBridgeRejected(Exception):
    """Raised when a projected patch row is not admissible for bridging.

    Fail-closed: no ``ValidationService.validate`` call is dispatched,
    no receipt row is written, and no bridge audit event is appended.
    Any downstream ``ValidationRejected`` from the service is re-raised
    unchanged so that quarantine admissibility failures continue to use
    their existing rejection surface.

    Admission conditions:

    - The projection's ``patch_proposal_id`` exists in the repository.
    - The persisted row's ``inference_artifact_id`` equals the
      projection's ``inference_artifact_id``.
    - The persisted row's ``task_id`` and ``root_revision_id`` equal the
      projection's values.
    - The persisted row's single ``target_file_ids`` entry equals the
      projection's real-fix narrow-path synthetic label. This is the
      audit-visible tag that distinguishes rows produced by the
      real-fix projector from any other origin.
    """


@dataclass(frozen=True)
class RealFixValidationBridgeOutcome:
    """Return value of a successful bridge call.

    The ``ValidationReceipt`` row is the authority-bearing artifact;
    this dataclass carries the three ids that a reviewer needs to walk
    the end-to-end chain from a verified real-fix inference through the
    projected patch proposal to its receipt.
    """

    validation_receipt_id: str
    patch_proposal_id: str
    inference_artifact_id: str
    task_id: str
    root_revision_id: str


class RealFixValidationBridge:
    """Bridge a projected real-fix ``PatchProposal`` to its ``ValidationReceipt``.

    The bridge holds no state of its own. It composes the existing
    ``ValidationService`` (which itself owns §22.4 quarantine
    enforcement and §23.7 receipt issuance) and the existing
    ``PatchProposalRepository`` (read-only here). The bridge's only
    mutations are:

    - the one ``ValidationReceipt`` row written by the service, and
    - one append-only audit record emitted directly by this bridge.
    """

    def __init__(
        self,
        *,
        validation_service: ValidationService,
        patch_reader: PatchProposalRepository,
        receipt_reader: ValidationReceiptRepository,
        audit_ledger: Any,
    ) -> None:
        self._service = validation_service
        self._patch_reader = patch_reader
        self._receipt_reader = receipt_reader
        self._audit = audit_ledger

    # ------------------------------------------------------------------

    def bridge(
        self,
        *,
        projection: RealFixPatchProjection,
        run: QuarantineRun | None = None,
        static_result: StaticCheckResult | None = None,
        intent_id: str | None = None,
    ) -> RealFixValidationBridgeOutcome:
        """Admit the projection and produce one ``ValidationReceipt``.

        ``run`` and ``static_result`` are passed through to
        ``ValidationService.validate`` unchanged. Both default to
        ``None`` so the bridge stays thin: callers that need to inject a
        specific quarantine envelope or static outcome use the same
        surface they already use with ``ValidationService`` directly.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint. The bridge only names
        it in the attestation record so a reviewer reading that single
        audit hop can recover the originating intent-anchor id without
        a second fetch. Authoritative fail-closed verification of
        ``intent_id`` against ``intent_anchor_records`` remains the
        responsibility of the downstream ``RevisionSealService`` at
        stage 6; this bridge performs no independent verification.
        """
        if not isinstance(projection, RealFixPatchProjection):
            raise RealFixValidationBridgeRejected(
                "bridge input must be a RealFixPatchProjection; "
                f"got {type(projection).__name__}"
            )

        stored = self._patch_reader.fetch(projection.patch_proposal_id)
        if stored is None:
            raise RealFixValidationBridgeRejected(
                "projected patch proposal not found: "
                f"{projection.patch_proposal_id}"
            )

        # Identity binding: the persisted row must be the one that was
        # written by the real-fix projector for this projection. Any
        # mismatch means the caller is trying to validate a row this
        # bridge did not admit, and must be refused fail-closed.
        if stored.get("inference_artifact_id") != projection.inference_artifact_id:
            raise RealFixValidationBridgeRejected(
                "persisted patch proposal inference_artifact_id mismatch"
            )
        if stored.get("task_id") != projection.task_id:
            raise RealFixValidationBridgeRejected(
                "persisted patch proposal task_id mismatch"
            )
        if stored.get("root_revision_id") != projection.root_revision_id:
            raise RealFixValidationBridgeRejected(
                "persisted patch proposal root_revision_id mismatch"
            )

        # Phase-1 narrow path: exactly one target file, and it must be
        # the real-fix synthetic label the projector produced. This is
        # the audit-visible tag that distinguishes a real-fix-projected
        # row from any other origin; without it we cannot claim this
        # receipt is bound to the verified real-fix path.
        target_file_ids = list(stored.get("target_file_ids") or [])
        expected_target = f"real-fix::file::{projection.task_id}"
        if target_file_ids != [expected_target]:
            raise RealFixValidationBridgeRejected(
                "persisted patch proposal target_file_ids is not the "
                f"real-fix narrow-path label: expected [{expected_target!r}], "
                f"got {target_file_ids!r}"
            )

        # Delegate to the existing service. Any ValidationRejected
        # (quarantine admissibility, schema violation, missing row)
        # bubbles up unchanged: the bridge does not issue an attestation
        # audit event in that case.
        try:
            validation_receipt_id = self._service.validate(
                task_id=projection.task_id,
                patch_proposal_id=projection.patch_proposal_id,
                run=run,
                static_result=static_result,
                intent_id=intent_id,
            )
        except ValidationRejected:
            # Fail-closed: no bridge attestation on rejection. The
            # service's own rejection audit (if any) is the evidence
            # the reviewer will see.
            raise

        receipt = self._receipt_reader.fetch(validation_receipt_id)
        if receipt is None:
            # Defense-in-depth: the service just wrote this row; if it
            # is somehow absent, refuse to emit an attestation pointing
            # at a non-existent artifact.
            raise RealFixValidationBridgeRejected(
                "validation service reported id "
                f"{validation_receipt_id!r} but row is not present"
            )

        # The attestation record is the single audit hop that names all
        # three identities a reviewer needs to walk the chain. The
        # service has already appended its own
        # ``validation_receipt_created`` record linking the receipt to
        # the patch proposal; this record adds the upstream
        # ``InferenceArtifact`` binding that the receipt schema does
        # not carry on-row.
        #
        # AUDIT-003 / §22.1: name ``intent_id`` in both ``artifact_refs``
        # and ``payload``. The id is the durable
        # ``intent_anchor_records.intent_id`` minted at the real-fix
        # chain entrypoint and threaded in by the orchestrator. Naming
        # it here mirrors the pattern already applied to
        # ``real_fix_review_bridge_attested`` (stage 4),
        # ``real_fix_approval_bridge_attested`` (stage 5),
        # ``real_fix_revision_seal_bridge_attested`` (stage 6),
        # ``real_fix_evidence_closure_bridge_attested`` (stage 7),
        # ``revision_sealed`` (seal service), and
        # ``real_fix_chain_completed`` (orchestrator wrapper), closing
        # the last one-hop asymmetry on the real-fix bridge surface so a
        # reviewer reading only this record can recover the originating
        # durable intent-anchor id without a second fetch. Authoritative
        # fail-closed verification of ``intent_id`` against
        # ``intent_anchor_records`` remains in ``RevisionSealService``
        # at stage 6; this bridge performs no independent verification.
        # No schema change, no migration, no new artifact family, no
        # new audit record type.
        self._audit.append(
            record_type="real_fix_validation_bridge_attested",
            task_id=projection.task_id,
            root_revision_id=projection.root_revision_id,
            artifact_refs=[
                validation_receipt_id,
                projection.patch_proposal_id,
                projection.inference_artifact_id,
                intent_id,
            ],
            payload={
                "validation_receipt_id": validation_receipt_id,
                "patch_proposal_id": projection.patch_proposal_id,
                "inference_artifact_id": projection.inference_artifact_id,
                "intent_id": intent_id,
                "receipt_result": receipt["result"],
                "source": "real_fix_tracer",
            },
        )

        return RealFixValidationBridgeOutcome(
            validation_receipt_id=validation_receipt_id,
            patch_proposal_id=projection.patch_proposal_id,
            inference_artifact_id=projection.inference_artifact_id,
            task_id=projection.task_id,
            root_revision_id=projection.root_revision_id,
        )
