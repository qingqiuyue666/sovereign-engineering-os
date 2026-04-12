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
from kernel.stores.sqlite.repositories import (
    ContextArtifactRepository,
    InferenceArtifactRepository,
    ReplayAnchorRepository,
    RevisionRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash
from validation.quarantine.runner_adapter import QUARANTINE_HARDWARE_ENVELOPE


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
    ) -> None:
        self._rev = revision_repo
        self._ctx = context_repo
        self._inf = inference_repo

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
        # artifact ids for this task. Full artifact closure is a
        # hardening-stage expansion.
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
        return ids


class EvidenceService:
    def __init__(
        self,
        *,
        replay_anchor_repo: ReplayAnchorRepository,
        revision_repo: RevisionRepository,
        context_repo: ContextArtifactRepository,
        inference_repo: InferenceArtifactRepository,
        audit_ledger: Any,
        project_id: str = "phase1_default",
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._anchor_repo = replay_anchor_repo
        self._revision_repo = revision_repo
        self._context_repo = context_repo
        self._inference_repo = inference_repo
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

        self._anchor_repo.insert(anchor)

        self._audit.append(
            record_type="evidence_closure",
            task_id=task_id,
            root_revision_id=root_revision_id,
            replay_anchor_id=replay_anchor_id,
            artifact_refs=[replay_anchor_id, revision_id],
            payload={
                "replay_class_claim": classification.replay_class.value,
                "degradation_reason": classification.degradation_reason,
                "unreplayable_reason": classification.unreplayable_reason,
                "required_artifact_ids": list(classification.required_artifact_ids),
            },
        )
        return replay_anchor_id
