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
    ``root_revision_id`` as ``real-fix::<task_id>`` identifiers. This is
    reviewable by inspection: the ids are clearly labelled as tracer-
    scoped and are not claimed to point at a full ContextArtifact row.
    Upgrading the recorder to consume a real ContextArtifact is a later
    increment once the full upstream signable-path frame is wired.
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
    ) -> RealFixNarrowPathRecord:
        """Insert one InferenceArtifact row and emit one audit record.

        Raises ``RealFixRecorderRejected`` if the result is not a
        verified pass. In that case no row is persisted and no audit
        event is appended — the tracer's existing failure-class audit
        records remain the sole evidence.
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

        # Synthetic ids are labelled `real-fix::<task_id>` so a reviewer
        # can see at a glance that these are tracer-scoped, not drawn
        # from a full signable-path frame. They satisfy the non-empty
        # string schema constraint honestly.
        context_artifact_id = f"real-fix::context::{task_id}"
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
        self._audit.append(
            record_type="inference_artifact_created",
            task_id=task_id,
            artifact_refs=[
                artifact["inference_artifact_id"],
                context_artifact_id,
            ],
            payload={
                "worker_profile": worker_profile,
                "model_route_id": model_route_id,
                "output_hash": output_hash,
                "replay_ceiling": ceiling,
                "source": "real_fix_tracer",
            },
        )

        return RealFixNarrowPathRecord(
            inference_artifact_id=artifact["inference_artifact_id"],
            context_artifact_id=context_artifact_id,
            root_revision_id=root_revision_id,
            output_hash=output_hash,
            replay_ceiling=ceiling,
        )
