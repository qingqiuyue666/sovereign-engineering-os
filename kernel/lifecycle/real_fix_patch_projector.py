"""
Real-fix narrow-path patch projector: project one verified real-fix
result + its persisted ``InferenceArtifact`` row into exactly one
schema-valid ``PatchProposal`` row on the authority-bearing signable-path
surface.

Constitutional anchors:
- v11 §23.6 PatchProposal — the governed narrow-path record for a
  proposed fix. This module inserts exactly one such row per verified
  real-fix tracer run.
- v11 §22.13 Multi-File Patch Coherence Contract — phase-1 narrowing
  collapses the required-check surface to a single file with no manifest
  touch. Both invariants are enforced here, fail-closed.
- v11 §23.14 AuditRecord — the projector emits one
  ``patch_proposal_created`` audit record that cross-references the
  originating ``InferenceArtifact`` id and the produced
  ``PatchProposal`` id.
- foundation §1, §D-004 — phase-1 narrow path: exactly one target file,
  no manifest edits, ``local_text_substitution`` side-effect class.

Scope lock:
- ONE verified + recorded real-fix result in, ONE PatchProposal row out.
  The projector refuses any input whose outcome is not
  ``real_fix_verified_pass`` or whose ``RealFixNarrowPathRecord`` is
  missing an ``inference_artifact_id``. Fail-closed by outcome class.
- No validation. No review. No approval. No sealing. No evidence. No
  repository mutation. No multi-file fixes. No retries. No background
  loops. No new providers. Those are explicitly out of scope for this
  minimum honest bridge.
- No new artifact type, table, or schema. Reuses
  ``kernel/schemas/patch_proposal.schema.json`` and
  ``PatchProposalRepository``. No orchestrator hook.
- Tracer-scoped synthetic target file id ``real-fix::file::<task_id>``
  is clearly labelled so a reviewer can see at a glance that this is
  not claimed to be a real repository file. Upgrading to a real file id
  drawn from a ContextArtifact is a later increment once the full
  upstream signable-path frame is wired.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.stores.sqlite.repositories import PatchProposalRepository
from kernel.version.version_tuple import compose_version_tuple_hash


class RealFixProjectorRejected(Exception):
    """Raised when a real-fix input is not admissible for projection.

    Fail-closed: the caller receives an explicit rejection and no
    ``PatchProposal`` row is persisted and no audit event is appended.
    The admission conditions in this minimum honest bridge are:

    - ``result.outcome == "real_fix_verified_pass"``
    - ``result.verified is True``
    - ``record.inference_artifact_id`` is a non-empty string (this is
      only populated when the tracer's narrow-path recorder produced an
      authority-bearing ``InferenceArtifact`` row)
    - ``record.root_revision_id`` and ``record.output_hash`` are
      non-empty strings
    """


@dataclass(frozen=True)
class RealFixPatchProjection:
    """The thin return value of a successful projection.

    The persisted artifact IS the ``PatchProposal`` row pointed at by
    ``patch_proposal_id``. This dataclass exists so callers can surface
    the authority-bearing id and the cross-reference to the originating
    inference artifact.
    """

    patch_proposal_id: str
    inference_artifact_id: str
    task_id: str
    root_revision_id: str
    target_file_id: str
    patch_group_hash: str
    patch_body_hash: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RealFixPatchProjector:
    """Project one verified real-fix result into one ``PatchProposal`` row.

    The projector is a single-purpose bridge. It does not orchestrate
    stages, does not consume capabilities, does not validate, does not
    review, does not approve, and does not mutate any repository. It
    converts (a) a tracer-local verified result and (b) the already-
    persisted ``RealFixNarrowPathRecord`` from
    ``RealFixNarrowPathRecorder`` into an authority-bearing row on the
    ``patch_proposals`` surface, and emits the matching audit event.

    Typical call shape::

        record = recorder.record(task=task, result=result, ...)
        projection = projector.project(task=task, result=result, record=record)
        # `projection.patch_proposal_id` is the persisted row id.
    """

    def __init__(
        self,
        *,
        repository: PatchProposalRepository,
        audit_ledger: Any,
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_ledger
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("patch_proposal")

    # ------------------------------------------------------------------

    def project(
        self,
        *,
        task: Any,
        result: Any,
        record: Any,
        intent_id: str | None = None,
    ) -> RealFixPatchProjection:
        """Insert one PatchProposal row and emit one audit record.

        Raises ``RealFixProjectorRejected`` if the inputs are not
        admissible. In that case no row is persisted and no audit event
        is appended — the tracer's existing evidence remains intact.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint. The projector only
        names it in the ``patch_proposal_created`` attestation so a
        reviewer reading that single audit hop can recover the
        originating intent-anchor id without a second fetch. The
        projector performs no independent verification; authoritative
        fail-closed verification of ``intent_id`` against
        ``intent_anchor_records`` remains the responsibility of the
        downstream ``RevisionSealService`` at stage 6.
        """
        outcome = getattr(result, "outcome", None)
        if outcome != "real_fix_verified_pass" or not getattr(result, "verified", False):
            raise RealFixProjectorRejected(
                "real-fix patch projection requires "
                f"outcome=real_fix_verified_pass; got {outcome!r}"
            )

        inference_artifact_id = getattr(record, "inference_artifact_id", "")
        if not isinstance(inference_artifact_id, str) or not inference_artifact_id:
            raise RealFixProjectorRejected(
                "record is missing inference_artifact_id; "
                "no authority-bearing upstream row to link"
            )

        root_revision_id = getattr(record, "root_revision_id", "")
        if not isinstance(root_revision_id, str) or not root_revision_id:
            raise RealFixProjectorRejected(
                "record is missing root_revision_id"
            )

        output_hash = getattr(record, "output_hash", "") or getattr(result, "output_hash", "")
        if not isinstance(output_hash, str) or not output_hash:
            raise RealFixProjectorRejected(
                "verified result missing output_hash"
            )

        task_id = getattr(task, "task_id", "")
        if not isinstance(task_id, str) or not task_id:
            raise RealFixProjectorRejected("task is missing task_id")

        # Phase-1 narrow path: exactly one target file. The id is
        # labelled `real-fix::file::<task_id>` so a reviewer can see at
        # a glance that this is a tracer-scoped synthetic id, not a
        # claim about a repository path. The patch body hash is the
        # verified fixed-source hash already recorded on the inference
        # row — the `PatchProposal.patch_group_hash` is derived from
        # both, giving replay queries an honest bind point.
        target_file_id = f"real-fix::file::{task_id}"
        patch_body_hash = output_hash
        patch_group_hash = _canonical_hash(
            {
                "target_file_ids": [target_file_id],
                "patch_body_hash": patch_body_hash,
            }
        )

        artifact = {
            "patch_proposal_id": f"pp-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": root_revision_id,
            "inference_artifact_id": inference_artifact_id,
            "target_file_ids": [target_file_id],
            "patch_group_hash": patch_group_hash,
            # Phase-1 narrow class: a single-file local text
            # substitution. The projector does NOT execute it; no
            # repository mutation is in scope.
            "side_effect_class_proposal": "local_text_substitution",
            "capability_requirements": [],
            "taint_set": [],
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
            # Explicit false: no manifest edits admitted on the narrow
            # path. This matches foundation §D-004.
            "manifest_touch_flag": False,
        }

        violations = validate_artifact(artifact, self._schema)
        if violations:
            # Fail-closed: never persist a row that does not satisfy
            # the schema contract. The narrow-path surface is
            # authority-bearing and must not admit a half-valid record.
            raise RealFixProjectorRejected(
                "real-fix patch proposal failed schema validation: "
                f"{'; '.join(violations[:5])}"
            )

        self._repo.insert(artifact)

        # The audit record is the cross-plane evidence hook. It carries
        # the originating inference artifact id and the produced patch
        # proposal id so a reviewer can walk from either direction. The
        # ``source`` tag lets the reviewer see that the row was
        # projected from a real-fix tracer result, not produced by the
        # full signable-path orchestrator.
        #
        # AUDIT-003 / §22.1: when the caller supplies the durable
        # ``intent_anchor_records.intent_id`` minted at the real-fix
        # chain entrypoint, name it in both ``artifact_refs`` and
        # ``payload``. This mirrors the pattern already applied to
        # ``real_fix_validation_bridge_attested`` (stage 3),
        # ``real_fix_review_bridge_attested`` (stage 4),
        # ``real_fix_approval_bridge_attested`` (stage 5),
        # ``real_fix_revision_seal_bridge_attested`` (stage 6),
        # ``real_fix_evidence_closure_bridge_attested`` (stage 7),
        # ``revision_sealed`` (seal service), and
        # ``real_fix_chain_completed`` (orchestrator wrapper), closing
        # the next upstream one-hop asymmetry on the real-fix narrow-
        # path so a reviewer reading only this record can recover the
        # originating durable intent-anchor id without a second fetch
        # (via ``inference_artifact_id -> context_artifact_id ->
        # intent_anchor_records``). Authoritative fail-closed
        # verification of ``intent_id`` against ``intent_anchor_records``
        # remains in ``RevisionSealService`` at stage 6; this projector
        # performs no independent verification. No schema change, no
        # migration, no new artifact family, no new audit record type.
        artifact_refs = [
            artifact["patch_proposal_id"],
            inference_artifact_id,
        ]
        if intent_id is not None:
            artifact_refs.append(intent_id)
        self._audit.append(
            record_type="patch_proposal_created",
            task_id=task_id,
            artifact_refs=artifact_refs,
            payload={
                "patch_group_hash": patch_group_hash,
                "target_file_ids": [target_file_id],
                "side_effect_class_proposal": "local_text_substitution",
                "inference_artifact_id": inference_artifact_id,
                "intent_id": intent_id,
                "source": "real_fix_tracer",
                # Real-provider output admits at most a semantic replay
                # ceiling. Preserving the ceiling tag on this downstream
                # audit record keeps the evidence chain honest end-to-
                # end (governance/design/replay_claim_taxonomy §3).
                "replay_ceiling": getattr(
                    record, "replay_ceiling", "semantic"
                ) or "semantic",
            },
        )

        return RealFixPatchProjection(
            patch_proposal_id=artifact["patch_proposal_id"],
            inference_artifact_id=inference_artifact_id,
            task_id=task_id,
            root_revision_id=root_revision_id,
            target_file_id=target_file_id,
            patch_group_hash=patch_group_hash,
            patch_body_hash=patch_body_hash,
        )
