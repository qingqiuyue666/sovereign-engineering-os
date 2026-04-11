"""
Replay classification decision engine (P0).

Constitutional anchors:
- v11 §22.5 Replay Fidelity Contract
- v11 §23.12 ReplayAnchor (schema surface)
- v11 §24.1 AT-013 / AT-032
- v11 §24.2 INV-010 (replay claims may not exceed captured evidence)
- v11 §24.2 INV-011 (uncertified equivalence is never exact replay)
- foundation §6 P0 (replay classifier + durable ReplayAnchor output)

Scope lock (phase 1):
- Classify a proposed replay claim against the artifacts observably
  present for a given root revision + task.
- Emit a `ReplayAnchor` record shaped to the frozen schema.
- Honest downgrade semantics only: exact claims that cannot be proven
  are downgraded, never silently accepted.
- No "equivalence proof bundle" acceptance in phase 1 (foundation §6):
  if an exact claim is requested without the full evidence closure and
  without an admitted proof bundle, we downgrade to `degraded` or
  `diagnostic` with an explicit reason.

Inputs the classifier needs per §22.5:
- truth evidence completeness (root_revision present + journal continuity)
- context completeness (ContextArtifact present)
- inference artifact availability (InferenceArtifact present)
- environment capture level (passed in; phase-1 forwards caller-declared)
- nondeterminism tolerance class (ignored in phase 1; reserved)
- divergence reporting path (caller attaches as degradation_reason)

This module does not talk to SQLite directly. It accepts an opaque
`EvidenceView` protocol provided by the evidence/audit layer so that the
classifier is trivially testable and does not entangle with persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class ReplayClass(str, Enum):
    EXACT = "exact"
    DIAGNOSTIC = "diagnostic"
    SEMANTIC = "semantic"
    DEGRADED = "degraded"
    UNREPLAYABLE = "unreplayable"


class EvidenceView(Protocol):
    """Minimal surface the classifier needs from the evidence plane.

    Real implementation is provided in `kernel/evidence/` / `kernel/stores/`.
    """

    def has_sealed_revision(self, root_revision_id: str) -> bool: ...
    def has_context_artifact(self, task_id: str, root_revision_id: str) -> bool: ...
    def has_inference_artifact(
        self, task_id: str, root_revision_id: str
    ) -> bool: ...
    def required_artifact_ids(
        self, task_id: str, root_revision_id: str
    ) -> list[str]: ...


@dataclass(frozen=True)
class ReplayClaimRequest:
    task_id: str
    project_id: str
    root_revision_id: str
    requested_class: ReplayClass
    environment_fingerprint_hash: str
    equivalence_proof_bundle_admitted: bool = False


@dataclass(frozen=True)
class ReplayClassification:
    replay_class: ReplayClass
    degradation_reason: str | None
    unreplayable_reason: str | None
    required_artifact_ids: tuple[str, ...]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReplayClassifier:
    """Classify a replay claim against evidence presence (honest downgrade)."""

    def __init__(self, evidence: EvidenceView) -> None:
        self._evidence = evidence

    def classify(self, request: ReplayClaimRequest) -> ReplayClassification:
        # Step 1: truth evidence presence.
        if not self._evidence.has_sealed_revision(request.root_revision_id):
            return ReplayClassification(
                replay_class=ReplayClass.UNREPLAYABLE,
                degradation_reason=None,
                unreplayable_reason="sealed revision not found",
                required_artifact_ids=(),
            )

        has_ctx = self._evidence.has_context_artifact(
            request.task_id, request.root_revision_id
        )
        has_inf = self._evidence.has_inference_artifact(
            request.task_id, request.root_revision_id
        )
        required = tuple(
            self._evidence.required_artifact_ids(
                request.task_id, request.root_revision_id
            )
        )

        # Step 2: honest exact-replay rule.
        # INV-010: claim may not exceed captured evidence.
        # INV-011: uncertified equivalence is never exact replay.
        if request.requested_class is ReplayClass.EXACT:
            if not has_ctx or not has_inf:
                reason = "missing context or inference artifact; exact replay refused"
                if request.equivalence_proof_bundle_admitted:
                    # Phase-1 rule: we do not admit proof bundles yet.
                    reason = (
                        "equivalence proof bundle not admitted in phase 1; "
                        "downgrade required (INV-011)"
                    )
                return ReplayClassification(
                    replay_class=ReplayClass.DEGRADED,
                    degradation_reason=reason,
                    unreplayable_reason=None,
                    required_artifact_ids=required,
                )
            # Exact replay is admissible only if the evidence closure is
            # complete AND the caller did not rely on equivalence
            # substitution. Phase-1 does not admit equivalence substitution
            # at all; if the caller asserts a proof bundle, we still deny.
            if request.equivalence_proof_bundle_admitted:
                return ReplayClassification(
                    replay_class=ReplayClass.DEGRADED,
                    degradation_reason=(
                        "equivalence proof bundle not admissible in phase 1"
                    ),
                    unreplayable_reason=None,
                    required_artifact_ids=required,
                )
            return ReplayClassification(
                replay_class=ReplayClass.EXACT,
                degradation_reason=None,
                unreplayable_reason=None,
                required_artifact_ids=required,
            )

        # Step 3: semantic / diagnostic / degraded downgrade ordering.
        # The rule is: honor the requested class if the evidence supports
        # it; otherwise deterministically downgrade one step at a time.
        if request.requested_class is ReplayClass.SEMANTIC:
            if has_ctx:
                return ReplayClassification(
                    replay_class=ReplayClass.SEMANTIC,
                    degradation_reason=None,
                    unreplayable_reason=None,
                    required_artifact_ids=required,
                )
            return ReplayClassification(
                replay_class=ReplayClass.DEGRADED,
                degradation_reason="missing context artifact",
                unreplayable_reason=None,
                required_artifact_ids=required,
            )

        if request.requested_class is ReplayClass.DIAGNOSTIC:
            return ReplayClassification(
                replay_class=ReplayClass.DIAGNOSTIC,
                degradation_reason=None,
                unreplayable_reason=None,
                required_artifact_ids=required,
            )

        if request.requested_class is ReplayClass.DEGRADED:
            return ReplayClassification(
                replay_class=ReplayClass.DEGRADED,
                degradation_reason="caller-declared degraded",
                unreplayable_reason=None,
                required_artifact_ids=required,
            )

        # UNREPLAYABLE request is self-honoring.
        return ReplayClassification(
            replay_class=ReplayClass.UNREPLAYABLE,
            degradation_reason=None,
            unreplayable_reason="caller-declared unreplayable",
            required_artifact_ids=required,
        )

    def build_replay_anchor(
        self,
        *,
        request: ReplayClaimRequest,
        classification: ReplayClassification,
        replay_anchor_id: str,
        version_tuple_hash: str,
    ) -> dict:
        """Construct a §23.12-shaped ReplayAnchor dict for persistence.

        The returned mapping is schema-valid against
        `kernel/schemas/replay_anchor.schema.json` and is ready to be
        persisted via `ReplayAnchorRepository.insert`.
        """
        return {
            "replay_anchor_id": replay_anchor_id,
            "root_revision_id": request.root_revision_id,
            "project_id": request.project_id,
            "task_id": request.task_id,
            "replay_class_claim": classification.replay_class.value,
            "required_artifact_ids": list(classification.required_artifact_ids),
            "version_tuple_hash": version_tuple_hash,
            "environment_fingerprint_hash": request.environment_fingerprint_hash,
            "created_at": _now_iso(),
            "degradation_reason": classification.degradation_reason,
            "unreplayable_reason": classification.unreplayable_reason,
        }
