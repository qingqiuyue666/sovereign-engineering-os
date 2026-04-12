"""
Review service: produce §23.10 ReviewArtifact under C22.14 governance.

Constitutional anchors:
- v11 §22.14 Review Surface Governance Contract
- v11 §23.10 ReviewArtifact
- v11 §24.1 AT-022 / AT-023 (self-summary rejection, high-risk secondary review)
- v11 §24.2 INV-019 (review provenance auditable)
- foundation §6 step 7 (P1 review + approval path)

Phase-1 posture:
- Required fields per §22.14 are produced explicitly:
  * diff_hash (derived from PatchProposal + ValidationReceipt provenance)
  * semantic_impact_hash (phase-1: SHA-256 over the patch_group_hash +
    validator_identity; production uses a real semantic impact analysis)
  * risk_rendering_provenance (dict with renderer_id, renderer_version,
    self_summary_flag)
  * reviewer identity / reviewer route (captured as `renderer_id`)
  * disclosure flag for AI-generated summary (`self_summary_flag`)
- Self-summary gate: if the caller declares `self_summary_flag=True` and
  the active policy forbids same-worker self-summary, the service
  rejects fail-closed. Phase-1 policy: self-summary is admissible but
  MUST be flagged; the review_artifact carries the disclosure and the
  approval service pairs it with a secondary-review check when risk is
  high.
- Risk class: phase-1 narrow path (single-file text substitution) is
  classified `low` by default; callers can override.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.stores.sqlite.repositories import (
    PatchProposalRepository,
    ReviewArtifactRepository,
    ValidationReceiptRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash


class ReviewRejected(Exception):
    """Fail-closed rejection of a review artifact under §22.14."""


@dataclass(frozen=True)
class RenderingProvenance:
    renderer_id: str
    renderer_version: str
    self_summary_flag: bool


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ReviewService:
    #: Phase-1 policy: self-summary is admissible but must be flagged.
    #: `forbid_self_summary=True` would reject any self-summary at this gate.
    FORBID_SELF_SUMMARY = False

    def __init__(
        self,
        *,
        repository: ReviewArtifactRepository,
        patch_reader: PatchProposalRepository,
        receipt_reader: ValidationReceiptRepository,
        audit_ledger: Any,
        default_renderer: RenderingProvenance = RenderingProvenance(
            renderer_id="phase1_review_renderer",
            renderer_version="phase1-slice1",
            self_summary_flag=False,
        ),
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._patch_reader = patch_reader
        self._receipt_reader = receipt_reader
        self._audit = audit_ledger
        self._default_renderer = default_renderer
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("review_artifact")

    def render_review(
        self,
        *,
        task_id: str,
        patch_proposal_id: str,
        validation_receipt_id: str,
        risk_class: str = "low",
        rendering_provenance: RenderingProvenance | None = None,
    ) -> str:
        proposal = self._patch_reader.fetch(patch_proposal_id)
        if proposal is None:
            raise ReviewRejected(
                f"patch proposal not found: {patch_proposal_id}"
            )
        receipt = self._receipt_reader.fetch(validation_receipt_id)
        if receipt is None:
            raise ReviewRejected(
                f"validation receipt not found: {validation_receipt_id}"
            )

        provenance = rendering_provenance or self._default_renderer

        if self.FORBID_SELF_SUMMARY and provenance.self_summary_flag:
            self._audit.append(
                record_type="review_self_summary_rejected",
                task_id=task_id,
                artifact_refs=[patch_proposal_id, validation_receipt_id],
                payload={"renderer_id": provenance.renderer_id},
            )
            raise ReviewRejected(
                f"self-summary by {provenance.renderer_id!r} forbidden by policy"
            )

        diff_hash = _canonical_hash(
            {
                "patch_group_hash": proposal["patch_group_hash"],
                "target_file_ids": list(proposal.get("target_file_ids", [])),
                "validation_receipt_id": validation_receipt_id,
            }
        )
        semantic_impact_hash = _canonical_hash(
            {
                "patch_group_hash": proposal["patch_group_hash"],
                "validator_identity": receipt["validator_identity"],
                "result": receipt["result"],
            }
        )

        # §22.11 taint surfacing: material taint from the upstream
        # receipt MUST be reflected on the review artifact so the
        # reviewer cannot silently drop it.
        taint_set = sorted(
            set(proposal.get("taint_set", []))
            | set(receipt.get("taint_set", []))
        )

        artifact = {
            "review_artifact_id": f"rv-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": proposal["root_revision_id"],
            "patch_proposal_id": patch_proposal_id,
            "diff_hash": diff_hash,
            "semantic_impact_hash": semantic_impact_hash,
            "risk_class": risk_class,
            "rendering_provenance": {
                "renderer_id": provenance.renderer_id,
                "renderer_version": provenance.renderer_version,
                "self_summary_flag": provenance.self_summary_flag,
            },
            "taint_set": taint_set,
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
        }

        for field_name in self._schema["required"]:
            if field_name not in artifact:
                raise ReviewRejected(
                    f"review artifact missing required field: {field_name}"
                )

        self._repo.insert(artifact)

        self._audit.append(
            record_type="review_artifact_created",
            task_id=task_id,
            artifact_refs=[
                artifact["review_artifact_id"],
                patch_proposal_id,
                validation_receipt_id,
            ],
            payload={
                "risk_class": risk_class,
                "self_summary_flag": provenance.self_summary_flag,
                "renderer_id": provenance.renderer_id,
                "taint_surfaced": list(taint_set),
            },
        )
        return artifact["review_artifact_id"]
