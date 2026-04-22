"""
Evidence service: close the evidence plane with a §23.12 ReplayAnchor.

Constitutional anchors:
- v11 §22.5 Replay Fidelity Contract
- v11 §23.12 ReplayAnchor
- v11 §24.1 AT-013 / AT-032
- v11 §24.2 INV-010 (claims may not exceed captured evidence)
- v11 §24.2 INV-011 (uncertified equivalence is never exact replay)
- foundation §6 step 10 (P0 replay classifier + durable anchor output)

This service is the terminal stage of the narrow signable path. It
composes:
- `kernel/replay/replay_classifier.ReplayClassifier` for honest
  classification
- `kernel/stores/sqlite/repositories.ReplayAnchorRepository` for
  persistence
- `kernel/stores/sqlite/repositories.RevisionRepository` (read) to
  check sealed-revision presence

The service implements `EvidenceView` (the protocol the classifier
expects) by delegating to the repository layer. This keeps the
classifier decoupled from SQLite while allowing the service to provide
live data.

Phase-1 posture:
- The requested replay class is `DIAGNOSTIC` (not `EXACT`) because
  phase-1 does not capture the full environment fingerprint at
  container-equivalent precision.
- `environment_fingerprint_hash` is a declared placeholder hash over
  the hardware boundary string from `runner_adapter`.
- The service's job is closure, not evaluation. It closes the evidence
  plane and emits a ReplayAnchor that downstream consumers can bind.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from kernel.replay.replay_classifier import (
    ReplayClaimRequest,
    ReplayClass,
    ReplayClassifier,
)
from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
    ReplayAnchorRepository,
    RevisionRepository,
    TaintRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash
from validation.quarantine.runner_adapter import QUARANTINE_HARDWARE_ENVELOPE

_REPLAY_ANCHOR_SCHEMA = load_schema("replay_anchor")


class EvidenceClosureRejected(Exception):
    """Fail-closed rejection when evidence closure cannot proceed."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_fingerprint_hash() -> str:
    """Phase-1 environment fingerprint: hash of the declared hardware boundary."""
    return "sha256:" + hashlib.sha256(
        QUARANTINE_HARDWARE_ENVELOPE.encode("utf-8")
    ).hexdigest()


class _LiveEvidenceView:
    """EvidenceView protocol implementation backed by live repositories."""

    def __init__(
        self,
        *,
        revision_repo: RevisionRepository,
        context_repo: ContextArtifactRepository,
        inference_repo: InferenceArtifactRepository,
        approval_repo: ApprovalArtifactRepository | None = None,
        taint_repo: TaintRepository | None = None,
    ) -> None:
        self._rev = revision_repo
        self._ctx = context_repo
        self._inf = inference_repo
        self._approval = approval_repo
        self._taint = taint_repo

    def has_sealed_revision(self, root_revision_id: str) -> bool:
        return self._rev.has_sealed(root_revision_id)

    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool:
        return self._ctx.exists_for(task_id, root_revision_id)

    def has_inference_artifact(
        self, task_id: str, root_revision_id: str
    ) -> bool:
        return self._inf.exists_for(task_id, root_revision_id)

    def required_artifact_ids(
        self, task_id: str, root_revision_id: str
    ) -> list[str]:
        # In phase-1, required artifacts are the context + inference
        # artifact ids for this task, plus already-durable validation
        # taint records when the evidence composition root wires that
        # read surface. Full artifact closure is a hardening-stage expansion.
        ids: list[str] = []
        ctx_row = self._ctx._conn.execute(
            "SELECT context_artifact_id FROM context_artifacts "
            "WHERE task_id = ? AND root_revision_id = ?;",
            (task_id, root_revision_id),
        ).fetchone()
        if ctx_row:
            ids.append(ctx_row[0])
        inf_row = self._inf._conn.execute(
            "SELECT inference_artifact_id FROM inference_artifacts "
            "WHERE task_id = ? AND root_revision_id = ?;",
            (task_id, root_revision_id),
        ).fetchone()
        if inf_row:
            ids.append(inf_row[0])
        ids.extend(self._validation_taint_record_ids(root_revision_id))
        return ids

    def _validation_taint_record_ids(self, root_revision_id: str) -> list[str]:
        if self._approval is None or self._taint is None:
            return []

        revision = self._rev.fetch(root_revision_id)
        if revision is None:
            return []

        approval_id = revision.get("approval_id")
        if not isinstance(approval_id, str) or not approval_id:
            return []

        approval = self._approval.fetch(approval_id)
        if approval is None:
            raise EvidenceClosureRejected(
                f"approval not found for sealed revision {root_revision_id}: "
                f"{approval_id}"
            )

        taint_record_ids: list[str] = []
        seen: set[str] = set()
        for receipt_id in approval.get("required_receipt_ids", []):
            if not isinstance(receipt_id, str) or not receipt_id:
                continue
            for record in self._taint.list_for_subject(receipt_id):
                taint_record_id = record.get("taint_record_id")
                if not isinstance(taint_record_id, str) or not taint_record_id:
                    continue
                if taint_record_id in seen:
                    continue
                seen.add(taint_record_id)
                taint_record_ids.append(taint_record_id)
        return taint_record_ids


class EvidenceService:
    def __init__(
        self,
        *,
        replay_anchor_repo: ReplayAnchorRepository,
        revision_repo: RevisionRepository,
        context_repo: ContextArtifactRepository,
        inference_repo: InferenceArtifactRepository,
        audit_ledger: Any,
        approval_repo: ApprovalArtifactRepository | None = None,
        taint_repo: TaintRepository | None = None,
        project_id: str = "phase1_default",
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._anchor_repo = replay_anchor_repo
        self._revision_repo = revision_repo
        self._context_repo = context_repo
        self._inference_repo = inference_repo
        self._approval_repo = approval_repo
        self._taint_repo = taint_repo
        self._audit = audit_ledger
        self._project_id = project_id
        self._vt_overrides = dict(version_tuple_overrides or {})

    def close_evidence(
        self,
        *,
        task_id: str,
        revision_id: str,
        requested_class: ReplayClass = ReplayClass.DIAGNOSTIC,
    ) -> str:
        """Close the evidence plane for a sealed revision.

        Returns the `replay_anchor_id` persisted. The anchor is the
        terminal artifact of the narrow signable path.
        """
        revision = self._revision_repo.fetch(revision_id)
        if revision is None:
            raise EvidenceClosureRejected(
                f"revision not found: {revision_id}"
            )
        if revision["state"] != "sealed":
            raise EvidenceClosureRejected(
                f"revision {revision_id} is not sealed (state={revision['state']!r})"
            )

        root_revision_id = revision["revision_id"]
        evidence_view = _LiveEvidenceView(
            revision_repo=self._revision_repo,
            context_repo=self._context_repo,
            inference_repo=self._inference_repo,
            approval_repo=self._approval_repo,
            taint_repo=self._taint_repo,
        )
        classifier = ReplayClassifier(evidence_view)

        claim_request = ReplayClaimRequest(
            task_id=task_id,
            project_id=self._project_id,
            root_revision_id=root_revision_id,
            requested_class=requested_class,
            environment_fingerprint_hash=_env_fingerprint_hash(),
        )
        classification = classifier.classify(claim_request)

        vt_hash = compose_version_tuple_hash(self._vt_overrides)
        replay_anchor_id = f"ra-{uuid4().hex}"
        anchor = classifier.build_replay_anchor(
            request=claim_request,
            classification=classification,
            replay_anchor_id=replay_anchor_id,
            version_tuple_hash=vt_hash,
        )

        # Ingress validation (foundation §3.4): validate before persist.
        violations = validate_artifact(anchor, _REPLAY_ANCHOR_SCHEMA)
        if violations:
            raise EvidenceClosureRejected(
                f"replay anchor schema validation failed: "
                f"{'; '.join(violations[:5])}"
            )

        self._anchor_repo.insert(anchor)

        # AUDIT-003 / §22.1: name the originating durable
        # ``intent_anchor_records.intent_id`` in both ``artifact_refs``
        # and ``payload``. The id is already in local scope on the
        # sealed ``revision`` row fetched above; by the time this
        # service runs, ``RevisionSealService.seal_revision`` has
        # already fail-closed on missing / empty / unknown id and, when
        # the intent-anchor reader is wired, on any id whose durable
        # row's ``task_id`` does not match the seal's. Naming it here
        # closes the evidence-stage service-record one-hop asymmetry
        # that the already-closed
        # ``real_fix_evidence_closure_bridge_attested`` covers at the
        # bridge layer, matching the precedent set by
        # ``revision_sealed`` (seal service, PR #33). This service
        # performs no independent verification. No schema change, no
        # migration, no new artifact family, no new audit record type.
        # Absent / empty ``intent_id`` preserves the prior audit shape
        # exactly.
        revision_intent_id = revision.get("intent_id")
        audit_artifact_refs = [replay_anchor_id, revision_id]
        audit_payload: dict[str, Any] = {
            "replay_class_claim": classification.replay_class.value,
            "degradation_reason": classification.degradation_reason,
            "unreplayable_reason": classification.unreplayable_reason,
            "required_artifact_ids": list(classification.required_artifact_ids),
        }
        if isinstance(revision_intent_id, str) and revision_intent_id:
            audit_artifact_refs.append(revision_intent_id)
            audit_payload["intent_id"] = revision_intent_id
        self._audit.append(
            record_type="evidence_closure",
            task_id=task_id,
            root_revision_id=root_revision_id,
            replay_anchor_id=replay_anchor_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )
        return replay_anchor_id
