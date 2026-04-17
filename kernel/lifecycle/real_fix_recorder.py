"""
Real-fix narrow-path recorder: promote a verified real-provider minimal
fix from tracer-local audit into an authority-bearing ``InferenceArtifact``
row on the current-stage signable-path surface.

Constitutional anchors:
- v11 §23.5 InferenceArtifact — the governed narrow-path record for
  model output. This module inserts exactly one such row per verified
  real-fix tracer run.
- v11 §23.14 AuditRecord — the recorder emits one
  ``inference_artifact_created`` audit record that cross-references the
  persisted inference artifact id.
- v11 §22.9 (inter-plane interface discipline) — the recorder does not
  call the adapter; it consumes a ``RealFixResult`` already produced by
  ``kernel.tracers.real_fix_tracer.RealFixTracer`` under the governed
  adapter boundary.
- governance/design/replay_claim_taxonomy/02_claim_class_definitions.md §3
  — real-provider output admits a maximum replay ceiling of ``semantic``.
  Every narrow-path audit record this module emits carries
  ``replay_ceiling == "semantic"`` unless the caller pins a stricter-or-
  equal declared ceiling on the adapter.

Scope lock:
- ONE verified result in, ONE InferenceArtifact row out. Unverified
  results (any non-``real_fix_verified_pass`` outcome) are NOT admitted;
  the caller retains the existing tracer-local audit evidence and no
  narrow-path row is produced. This preserves fail-closed honesty: an
  authority-bearing record is created only when the real provider
  produced a fix that passed every verification case.
- No new artifact type. No new table. No new schema. Reuses the
  existing ``inference_artifacts`` surface and the existing
  ``inference_artifact_created`` audit record type.
- No side effects beyond one ``INSERT`` into ``inference_artifacts`` and
  one ``append`` on the audit ledger. No orchestrator stage advancement,
  no capability token, no budget accounting — those are downstream
  concerns of the governed stage-entry path and are explicitly out of
  scope for this minimum honest integration.
- No multi-file fix execution. No repository mutation. No exact replay
  claim. No silent downgrade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.stores.sqlite.repositories import InferenceArtifactRepository
from kernel.version.version_tuple import compose_version_tuple_hash


class RealFixRecorderRejected(Exception):
    """Raised when a real-fix result is not admissible for narrow-path recording.

    Fail-closed: the caller receives an explicit rejection and no row
    is persisted. The only admission condition in this minimum honest
    integration is ``outcome == "real_fix_verified_pass"``.
    """


@dataclass(frozen=True)
class RealFixNarrowPathRecord:
    """The durable narrow-path record produced by a successful recording.

    This is a thin return value, not a persisted artifact type — the
    persisted artifact IS the ``InferenceArtifact`` row pointed at by
    ``inference_artifact_id``. The dataclass exists so the tracer can
    surface the authority-bearing id back to its caller.
    """

    inference_artifact_id: str
    context_artifact_id: str
    root_revision_id: str
    output_hash: str
    replay_ceiling: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RealFixNarrowPathRecorder:
    """Persist one verified real-fix result as an ``InferenceArtifact`` row.

    The recorder is a single-purpose helper. It does not orchestrate
    stages, does not consume capabilities, and does not touch git. It
    converts a tracer-local verified result into an authority-bearing
    row on the narrow-path surface and emits the matching audit event.

    Callers (today: ``RealFixTracer``) must pass:
    - the ``RealFixTask`` that was run
    - the ``RealFixResult`` returned by the tracer
    - the ``replay_ceiling`` the tracer computed from the adapter
    - the ``worker_profile`` / ``model_route_id`` strings the tracer used

    The recorder synthesizes ``context_artifact_id`` and
    ``root_revision_id`` as ``real-fix::<task_id>`` identifiers when the
    caller supplies no overrides. This is reviewable by inspection: the
    ids are clearly labelled as tracer-scoped and are not claimed to
    point at a full ContextArtifact row.

    Callers that have already minted a real ContextArtifact row for
    this task (today: ``SignablePathOrchestrator.run_real_fix_chain``
    via the already-wired ``ContextService``) may pass
    ``context_artifact_id`` and/or ``root_revision_id`` overrides to
    ``.record(...)``. When supplied, the recorder writes the overrides
    verbatim into the persisted ``InferenceArtifact`` row so every
    downstream bridge (which reads ``context_artifact_id`` off that
    row) propagates the authority-bearing id without any other change.
    Non-empty string values are required when overrides are supplied;
    ``None`` preserves the synthetic-label fallback exactly.
    """

    def __init__(
        self,
        *,
        repository: InferenceArtifactRepository,
        audit_ledger: Any,
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_ledger
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("inference_artifact")

    # ------------------------------------------------------------------

    def record(
        self,
        *,
        task: Any,
        result: Any,
        worker_profile: str,
        model_route_id: str,
        context_artifact_id: str | None = None,
        root_revision_id: str | None = None,
        intent_id: str | None = None,
    ) -> RealFixNarrowPathRecord:
        """Insert one InferenceArtifact row and emit one audit record.

        Raises ``RealFixRecorderRejected`` if the result is not a
        verified pass. In that case no row is persisted and no audit
        event is appended — the tracer's existing failure-class audit
        records remain the sole evidence.

        ``context_artifact_id`` / ``root_revision_id`` overrides bind
        the persisted InferenceArtifact row to an authority-bearing id
        minted upstream (e.g. a real ContextArtifact row produced by
        ``ContextService``). When an override is ``None`` the recorder
        falls back to the tracer-scoped synthetic label. Empty-string
        overrides are rejected fail-closed — supplying an override is a
        positive assertion that an authority-bearing id exists.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint. The recorder only names
        it in the ``inference_artifact_created`` attestation so a
        reviewer reading that single audit hop can recover the
        originating intent-anchor id without a second fetch (via
        ``context_artifact_id -> intent_anchor_records``). The recorder
        performs no independent verification; authoritative fail-closed
        verification of ``intent_id`` against ``intent_anchor_records``
        remains the responsibility of the downstream
        ``RevisionSealService`` at stage 6. When ``None`` the recorder
        preserves the prior audit shape exactly (no ``intent_id`` in
        ``artifact_refs`` or ``payload``) so hand-built tracer-bullet
        tests that do not thread the id continue to pass unchanged.
        """
        outcome = getattr(result, "outcome", None)
        if outcome != "real_fix_verified_pass" or not getattr(result, "verified", False):
            raise RealFixRecorderRejected(
                "real-fix narrow-path recording requires "
                f"outcome=real_fix_verified_pass; got {outcome!r}"
            )

        output_hash = getattr(result, "output_hash", "")
        if not isinstance(output_hash, str) or not output_hash:
            raise RealFixRecorderRejected("verified result missing output_hash")

        task_id = getattr(task, "task_id", "")
        if not isinstance(task_id, str) or not task_id:
            raise RealFixRecorderRejected("task is missing task_id")

        # When the caller supplies an authority-bearing id (e.g. a real
        # ContextArtifact row minted by ``ContextService`` upstream of
        # the tracer dispatch) use it verbatim. Otherwise fall back to
        # the tracer-scoped synthetic label `real-fix::<task_id>`: this
        # label is reviewable by inspection and satisfies the non-empty
        # string schema constraint honestly. Empty-string overrides are
        # rejected fail-closed — an override must be a real id.
        if context_artifact_id is not None:
            if not isinstance(context_artifact_id, str) or not context_artifact_id:
                raise RealFixRecorderRejected(
                    "context_artifact_id override must be a non-empty string"
                )
        else:
            context_artifact_id = f"real-fix::context::{task_id}"
        if root_revision_id is not None:
            if not isinstance(root_revision_id, str) or not root_revision_id:
                raise RealFixRecorderRejected(
                    "root_revision_id override must be a non-empty string"
                )
        else:
            root_revision_id = f"real-fix::root::{task_id}"

        ceiling = getattr(result, "replay_ceiling", "") or "semantic"

        artifact = {
            "inference_artifact_id": f"inf-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": root_revision_id,
            "context_artifact_id": context_artifact_id,
            "worker_run_id": f"wrun-{uuid4().hex}",
            "worker_profile": worker_profile,
            "model_route_id": model_route_id,
            "output_hash": output_hash,
            "provenance_refs": [context_artifact_id, model_route_id],
            "taint_set": [],
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
            "token_usage": {},
            "latency_ms": int(getattr(result, "latency_ms", 0) or 0),
        }

        violations = validate_artifact(artifact, self._schema)
        if violations:
            # Fail-closed: never persist a row that does not satisfy the
            # schema contract. The narrow-path surface is authority-
            # bearing and must not admit a half-valid record.
            raise RealFixRecorderRejected(
                "real-fix inference artifact failed schema validation: "
                f"{'; '.join(violations[:5])}"
            )

        self._repo.insert(artifact)

        # The audit record is the cross-plane evidence hook. It carries
        # the honest replay ceiling and the ids a reviewer needs to go
        # read the persisted row.
        #
        # AUDIT-003 / §22.1: when the caller supplies the durable
        # ``intent_anchor_records.intent_id`` minted at the real-fix
        # chain entrypoint, name it in both ``artifact_refs`` and
        # ``payload``. This mirrors the pattern already applied to
        # ``patch_proposal_created`` (projector),
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
        # (via ``context_artifact_id -> intent_anchor_records``).
        # Authoritative fail-closed verification of ``intent_id``
        # against ``intent_anchor_records`` remains in
        # ``RevisionSealService`` at stage 6; this recorder performs no
        # independent verification. No schema change, no migration, no
        # new artifact family, no new audit record type.
        artifact_refs = [
            artifact["inference_artifact_id"],
            context_artifact_id,
        ]
        if intent_id is not None:
            artifact_refs.append(intent_id)
        audit_payload: dict[str, Any] = {
            "worker_profile": worker_profile,
            "model_route_id": model_route_id,
            "output_hash": output_hash,
            "replay_ceiling": ceiling,
            "source": "real_fix_tracer",
        }
        if intent_id is not None:
            audit_payload["intent_id"] = intent_id
        self._audit.append(
            record_type="inference_artifact_created",
            task_id=task_id,
            artifact_refs=artifact_refs,
            payload=audit_payload,
        )

        return RealFixNarrowPathRecord(
            inference_artifact_id=artifact["inference_artifact_id"],
            context_artifact_id=context_artifact_id,
            root_revision_id=root_revision_id,
            output_hash=output_hash,
            replay_ceiling=ceiling,
        )
