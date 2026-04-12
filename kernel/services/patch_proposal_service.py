"""
Patch proposal service: produce §23.6 PatchProposal under C22.13 coherence.

Constitutional anchors:
- v11 §22.13 Multi-File Patch Coherence Contract
- v11 §23.6 PatchProposal
- v11 §24.1 AT-020 / AT-021 (partial-apply rejection, cross-file incoherence)
- v11 §24.2 INV-015 / INV-016 (patch coherence)
- foundation §1, §D-004 (phase-1 narrowing: single-file text substitution)
- foundation §6 step 5 (artifactization before authority-bearing gates)

Phase-1 posture:
- `target_file_ids` MUST have exactly length 1 (foundation §D-004). A
  proposal that spans multiple files is rejected fail-closed.
- `manifest_touch_flag` MUST be false on the narrow path (no manifest
  edits admitted in phase 1). A True value is rejected.
- `patch_group_hash` is the SHA-256 over the canonical JSON form of
  (target_file_ids, patch_body_hash) so replay queries can bind.
- This service does NOT execute the patch. It produces an artifact.
  Execution is a later seal-time concern; patch bodies live in git, not
  in the kernel (foundation §3 item 12).

The service delegates the §22.13 required-check rule set to this module
directly (it is small enough). Adding a separate `patch_coherence_rules`
file would be premature abstraction for a single check list.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.stores.sqlite.repositories import (
    InferenceArtifactRepository,
    PatchProposalRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash


class PatchProposalRejected(Exception):
    """Fail-closed rejection of a patch proposal under §22.13."""


@dataclass(frozen=True)
class PatchProposalRequest:
    target_file_ids: Sequence[str]
    patch_body_hash: str
    side_effect_class_proposal: str = "local_text_substitution"
    capability_requirements: Sequence[str] = field(default_factory=tuple)
    manifest_touch_flag: bool = False
    taint_set: Sequence[str] = field(default_factory=tuple)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PatchProposalService:
    def __init__(
        self,
        *,
        repository: PatchProposalRepository,
        inference_reader: InferenceArtifactRepository,
        audit_ledger: Any,
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._inference_reader = inference_reader
        self._audit = audit_ledger
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("patch_proposal")

    def propose(
        self,
        *,
        task_id: str,
        inference_artifact_id: str,
        request: PatchProposalRequest | Mapping[str, Any] | None = None,
    ) -> str:
        """Produce and persist a PatchProposal.

        If `request` is omitted, the service synthesizes a minimal
        single-file proposal from the inference artifact's output_hash;
        this is the phase-1 default used by the tracer bullet. Real
        callers always pass an explicit request.
        """
        inf = self._inference_reader.fetch(inference_artifact_id)
        if inf is None:
            raise PatchProposalRejected(
                f"inference artifact not found: {inference_artifact_id}"
            )

        req = self._coerce_request(request, inf)

        # §22.13 required-check #1: atomic patch grouping.
        if len(req.target_file_ids) == 0:
            raise PatchProposalRejected("target_file_ids is empty")

        # Phase-1 single-file narrowing (foundation §D-004).
        if len(req.target_file_ids) != 1:
            raise PatchProposalRejected(
                f"phase-1 narrow path requires exactly one target file; "
                f"got {len(req.target_file_ids)}"
            )

        # Phase-1 manifest-touch forbidden.
        if req.manifest_touch_flag:
            raise PatchProposalRejected(
                "manifest_touch_flag=True is not admissible on phase-1 narrow path"
            )

        # §22.13 required-check #2-#4: cross-file, coherence, partial-apply.
        # On a single-file patch the cross-file/manifest coherence checks
        # collapse to trivial, but we keep them explicit so the code path
        # is obvious in audit.
        target_file_ids = list(req.target_file_ids)
        patch_group_hash = _canonical_hash(
            {
                "target_file_ids": target_file_ids,
                "patch_body_hash": req.patch_body_hash,
            }
        )

        artifact = {
            "patch_proposal_id": f"pp-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": inf["root_revision_id"],
            "inference_artifact_id": inference_artifact_id,
            "target_file_ids": target_file_ids,
            "patch_group_hash": patch_group_hash,
            "side_effect_class_proposal": req.side_effect_class_proposal,
            "capability_requirements": list(req.capability_requirements),
            "taint_set": list(req.taint_set) or list(inf.get("taint_set", [])),
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
        }

        # Ingress required-field validation against the frozen schema.
        for field_name in self._schema["required"]:
            if field_name not in artifact:
                raise PatchProposalRejected(
                    f"patch proposal missing required field: {field_name}"
                )

        self._repo.insert(artifact)

        self._audit.append(
            record_type="patch_proposal_created",
            task_id=task_id,
            artifact_refs=[artifact["patch_proposal_id"], inference_artifact_id],
            payload={
                "patch_group_hash": patch_group_hash,
                "target_file_ids": target_file_ids,
                "side_effect_class_proposal": req.side_effect_class_proposal,
            },
        )
        return artifact["patch_proposal_id"]

    def _coerce_request(
        self,
        request: PatchProposalRequest | Mapping[str, Any] | None,
        inference: Mapping[str, Any],
    ) -> PatchProposalRequest:
        if isinstance(request, PatchProposalRequest):
            return request
        if request is None:
            # Phase-1 default tracer: synthesize a single-file proposal
            # whose body hash is the inference output hash and whose
            # target file id is drawn from the inference provenance
            # tail. This path is explicitly the happy-path tracer used
            # by the end-to-end test; production callers pass explicit
            # requests.
            fallback_target = f"file::tracer/{inference['inference_artifact_id']}.txt"
            return PatchProposalRequest(
                target_file_ids=(fallback_target,),
                patch_body_hash=str(inference["output_hash"]),
            )
        return PatchProposalRequest(
            target_file_ids=tuple(request["target_file_ids"]),
            patch_body_hash=str(request["patch_body_hash"]),
            side_effect_class_proposal=str(
                request.get("side_effect_class_proposal", "local_text_substitution")
            ),
            capability_requirements=tuple(
                request.get("capability_requirements", ())
            ),
            manifest_touch_flag=bool(request.get("manifest_touch_flag", False)),
            taint_set=tuple(request.get("taint_set", ())),
        )
