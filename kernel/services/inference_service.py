"""
Inference service: governed model-integration boundary.

Constitutional anchors:
- v11 §22.9 (inter-plane interface discipline)
- v11 §23.5 InferenceArtifact
- v11 §23.15 FailureBundle linkage on API failure
- foundation §4.2 ModelIntegrationContract (reinforcement-only)
- foundation §8 module mapping: `kernel/services/inference_service.py`

ModelIntegrationContract (exact phase-1 enforcement):
- prompt construction is governed from `ContextArtifact`; no ungoverned
  prompt surface may be accepted. A caller that tries to hand us a raw
  prompt string is rejected fail-closed.
- model responses are parsed through typed response handling BEFORE
  `InferenceArtifact` creation. The parse layer is explicit: raw bytes
  never touch the artifact writer.
- timeout/retry/token-budget controls are policy-governed and auditable:
  phase-1 enforces a static policy surface (`InferencePolicy`), and
  every invocation records its policy class in the AuditRecord payload.
- model API failure paths emit `FailureBundle` (via `_emit_failure_bundle`)
  with causality refs back to the ContextArtifact.
- model output is NEVER authority. This module produces exactly one
  output shape (an `InferenceArtifact` row); it cannot drive the state
  machine, and it does not mutate any ledger other than the inference
  artifact table + audit/failure ledgers.

Phase-1 posture:
- No real model adapter is wired in; this is the kernel boundary. A
  `ModelAdapter` protocol is declared here, and a single concrete
  adapter (stub) is accepted at construction time. Real adapters live
  outside this module (they are workers, not authority) and must
  conform to this protocol.
- If no adapter is injected the service uses `_NullAdapter`, which
  deterministically refuses to produce output and emits a FailureBundle
  referencing `model_adapter_not_configured`. This is the honest
  phase-1 default.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.services.budget_governor import BudgetExhausted, BudgetGovernor
from kernel.stores.sqlite.repositories import (
    FailureBundleRepository,
    InferenceArtifactRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash


class ModelIntegrationViolation(Exception):
    """Raised when a caller breaches the governed model-integration boundary."""


class InferenceFailure(Exception):
    """Raised when model invocation fails under governed conditions."""


class InferenceBudgetExhausted(InferenceFailure):
    """Raised when the BudgetGovernor refuses an inference (AT-027 / INV-021).

    Carries the governance reason string so callers / tests can assert
    which AT-027 case fired (`budget_would_be_exceeded`,
    `budget_already_suspended`, `budget_already_exceeded`,
    `budget_exceeded_during_inference`).
    """

    def __init__(self, *, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class InferencePolicy:
    """Phase-1 static policy surface for model invocation.

    These are POLICY KNOBS, not capabilities. They enter the audit
    payload on every invocation so replay can reconstruct the policy
    class under which any given InferenceArtifact was produced.
    """

    max_output_tokens: int = 4096
    timeout_seconds: float = 120.0
    max_retries: int = 0  # phase 1: no retry; failure is explicit


class ModelAdapter(Protocol):
    """The only admissible model entry point.

    Adapters must be pure functions over a structured prompt envelope
    built by this service. They must never mutate ledger state.
    """

    def invoke(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> Mapping[str, Any]:
        """Return a typed model response.

        Required keys in the response:
        - `output_text` (str)
        - `token_usage` (dict)
        - `latency_ms` (int)
        - `model_route_id` (str)

        Any other shape MUST raise or return a deterministic error dict.
        """
        ...


class _NullAdapter:
    """Phase-1 honest default: refuses to produce output."""

    def invoke(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> Mapping[str, Any]:
        raise InferenceFailure("model_adapter_not_configured")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_hash(output_text: str) -> str:
    return "sha256:" + hashlib.sha256(output_text.encode("utf-8")).hexdigest()


def _failure_cause_hash(
    *,
    failure_class: str,
    detail: str,
    evidence_refs: Sequence[str],
) -> str:
    payload = {
        "failure_class": failure_class,
        "detail": detail,
        "evidence_refs": list(evidence_refs),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _actual_total_tokens(token_usage: Mapping[str, Any]) -> int:
    """Derive a conservative total-token count from a parsed token_usage.

    Phase-1 adapters report `{"input": int, "output": int}` shapes.
    Unknown shapes fall back to 0 rather than silently under-count; the
    governor is still responsible for admissibility. This helper is
    intentionally narrow and only used for budget accounting.
    """
    total = 0
    for value in token_usage.values():
        if isinstance(value, int):
            total += max(0, value)
    return total


class InferenceService:
    def __init__(
        self,
        *,
        repository: InferenceArtifactRepository,
        audit_ledger: Any,
        context_reader: Any,
        adapter: ModelAdapter | None = None,
        policy: InferencePolicy | None = None,
        version_tuple_overrides: Mapping[str, Any] | None = None,
        budget_governor: BudgetGovernor | None = None,
        failure_bundle_repository: FailureBundleRepository | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_ledger
        self._context_reader = context_reader
        self._adapter: ModelAdapter = adapter or _NullAdapter()
        self._policy = policy or InferencePolicy()
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("inference_artifact")
        # Optional budget governor (AT-027 / INV-021). When wired, the
        # service refuses adapter invocation on budget exhaustion and
        # refuses to persist inference artifacts whose actual token
        # usage pushes past the task's hard budget.
        self._budget: BudgetGovernor | None = budget_governor
        self._failure_bundles = failure_bundle_repository

    # ------------------------------------------------------------------
    # governed prompt construction
    # ------------------------------------------------------------------

    def _build_prompt_envelope(
        self, *, context_artifact: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Construct the typed prompt envelope from ContextArtifact.

        This is the ONLY admissible prompt construction path. It is
        intentionally a small, explicit shape so the authority surface
        is obvious in audit.
        """
        return {
            "context_artifact_id": context_artifact["context_artifact_id"],
            "root_revision_id": context_artifact["root_revision_id"],
            "candidate_file_ids": list(context_artifact.get("candidate_file_ids", [])),
            "symbol_frontier_ids": list(
                context_artifact.get("symbol_frontier_ids", [])
            ),
            "content_hash": context_artifact["content_hash"],
            "packing_policy_version": context_artifact["packing_policy_version"],
            "taint_set": list(context_artifact.get("taint_set", [])),
            "phase": "phase1",
        }

    # ------------------------------------------------------------------
    # governed response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response: Mapping[str, Any]) -> Mapping[str, Any]:
        """Typed parse of the adapter response.

        Rejects any response that is not a mapping with the required
        keys. This is where raw model output stops being raw bytes and
        becomes a governed object.
        """
        if not isinstance(response, Mapping):
            raise ModelIntegrationViolation(
                f"model response must be a mapping, got {type(response).__name__}"
            )
        required = ("output_text", "token_usage", "latency_ms", "model_route_id")
        missing = [k for k in required if k not in response]
        if missing:
            raise ModelIntegrationViolation(
                f"model response missing required keys: {missing}"
            )
        if not isinstance(response["output_text"], str):
            raise ModelIntegrationViolation(
                "model response `output_text` must be a str"
            )
        return {
            "output_text": response["output_text"],
            "token_usage": dict(response["token_usage"]),
            "latency_ms": int(response["latency_ms"]),
            "model_route_id": str(response["model_route_id"]),
        }

    # ------------------------------------------------------------------
    # failure-bundle emission
    # ------------------------------------------------------------------

    def _emit_failure_bundle(
        self,
        *,
        task_id: str,
        root_revision_id: str,
        context_artifact_id: str,
        failure_class: str,
        detail: str,
        taint_set: Sequence[str] | None = None,
        intent_id: str | None = None,
    ) -> None:
        # When a FailureBundleRepository is wired, persist the durable
        # failure row before appending the audit record that names it.
        # Unwired direct-service tests retain the pre-existing audit-only
        # failure behavior.
        #
        # ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        # threaded in by ``run_inference``. When supplied and non-empty
        # it is named in both ``artifact_refs`` and ``payload`` of the
        # ``inference_failure`` audit record so a reviewer reading only
        # that rejection record can recover the AUDIT-003 / §22.1
        # linkage without a second fetch. Authoritative fail-closed
        # verification of ``intent_id`` against ``intent_anchor_records``
        # remains the responsibility of ``RevisionSealService``
        # downstream; this service performs no independent verification.
        # Absent / empty ``intent_id`` preserves the prior audit shape
        # exactly.
        failure_bundle_id: str | None = None
        evidence_refs = [context_artifact_id]
        taints = list(taint_set or [])
        if self._failure_bundles is not None:
            failure_bundle_id = f"fb-{uuid4().hex}"
            self._failure_bundles.append(
                artifact={
                    "failure_bundle_id": failure_bundle_id,
                    "task_id": task_id,
                    "root_revision_id": root_revision_id,
                    "failure_class": failure_class,
                    "cause_hash": _failure_cause_hash(
                        failure_class=failure_class,
                        detail=detail,
                        evidence_refs=evidence_refs,
                    ),
                    "evidence_refs": evidence_refs,
                    "taint_set": taints,
                    "created_at": _now_iso(),
                }
            )

        audit_artifact_refs: list[str] = [context_artifact_id]
        audit_payload: dict[str, Any] = {
            "failure_class": failure_class,
            "detail": detail,
            "root_revision_id": root_revision_id,
        }
        if isinstance(intent_id, str) and intent_id:
            audit_artifact_refs.append(intent_id)
            audit_payload["intent_id"] = intent_id
        self._audit.append(
            record_type="inference_failure",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
            failure_bundle_id=failure_bundle_id,
        )

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------

    def run_inference(
        self,
        *,
        task_id: str,
        context_artifact_id: str,
        worker_profile: str,
        model_route_id: str,
        intent_id: str | None = None,
    ) -> str:
        """Run a governed inference for `task_id`.

        The caller (orchestrator) has already:
        - verified a capability token for `invoke_inference`
        - advanced the task to the INFERENCE stage

        Responsibilities here:
        - fetch ContextArtifact (governed source of prompt state)
        - build prompt envelope (typed)
        - invoke adapter under static policy
        - parse response (typed)
        - persist InferenceArtifact row
        - emit AuditRecord
        - on failure emit FailureBundle-equivalent audit note and raise

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        minted at the real-fix chain entrypoint (or the eight-stage
        ``admit_context`` surface) and threaded in by the caller. When
        supplied and non-empty it is named in both ``artifact_refs`` and
        ``payload`` of the ``inference_artifact_created`` happy-path
        audit record and of every ``inference_failure`` rejection-path
        audit record emitted via ``_emit_failure_bundle`` so a reviewer
        reading only that record can recover the AUDIT-003 / §22.1
        linkage without a second fetch. Authoritative fail-closed
        verification of ``intent_id`` against ``intent_anchor_records``
        remains the responsibility of ``RevisionSealService`` downstream;
        this service performs no independent verification. Absent /
        empty ``intent_id`` preserves the prior audit shape exactly.
        """
        context_artifact = self._context_reader.fetch(context_artifact_id)
        if context_artifact is None:
            raise ModelIntegrationViolation(
                f"context artifact not found: {context_artifact_id}"
            )

        envelope = self._build_prompt_envelope(context_artifact=context_artifact)

        # AT-027 pre-flight: budget admissibility check. If the governor
        # refuses, we emit a FailureBundle-equivalent audit record and
        # raise InferenceBudgetExhausted BEFORE the adapter is invoked
        # and BEFORE any InferenceArtifact is persisted. This is the
        # fail-closed "no unsafe shortcut" surface.
        if self._budget is not None:
            try:
                self._budget.assert_admissible(
                    task_id=task_id,
                    projected_tokens=self._policy.max_output_tokens,
                )
            except BudgetExhausted as be:
                self._emit_failure_bundle(
                    task_id=task_id,
                    root_revision_id=context_artifact["root_revision_id"],
                    context_artifact_id=context_artifact_id,
                    failure_class=be.reason,
                    detail=be.detail,
                    taint_set=context_artifact.get("taint_set", []),
                    intent_id=intent_id,
                )
                raise InferenceBudgetExhausted(
                    reason=be.reason, detail=be.detail
                ) from be

        try:
            raw = self._adapter.invoke(
                prompt_envelope=envelope, policy=self._policy
            )
        except InferenceFailure as exc:
            self._emit_failure_bundle(
                task_id=task_id,
                root_revision_id=context_artifact["root_revision_id"],
                context_artifact_id=context_artifact_id,
                failure_class="model_api_failure",
                detail=str(exc),
                taint_set=context_artifact.get("taint_set", []),
                intent_id=intent_id,
            )
            raise
        except Exception as exc:  # noqa: BLE001 — fail closed on any error
            self._emit_failure_bundle(
                task_id=task_id,
                root_revision_id=context_artifact["root_revision_id"],
                context_artifact_id=context_artifact_id,
                failure_class="model_adapter_exception",
                detail=f"{type(exc).__name__}: {exc}",
                taint_set=context_artifact.get("taint_set", []),
                intent_id=intent_id,
            )
            raise InferenceFailure(str(exc)) from exc

        parsed = self._parse_response(raw)

        # AT-027 post-flight: record actual consumption against the
        # task's budget. If the governor detects that the reported
        # actual tokens push total consumption past the hard budget,
        # it transitions the budget to exceeded -> suspended, emits
        # audit evidence, and raises. We refuse to persist the
        # InferenceArtifact in that case (no unsafe shortcut).
        if self._budget is not None:
            actual = _actual_total_tokens(parsed["token_usage"])
            try:
                self._budget.record_consumption(
                    task_id=task_id,
                    actual_tokens=actual,
                )
            except BudgetExhausted as be:
                self._emit_failure_bundle(
                    task_id=task_id,
                    root_revision_id=context_artifact["root_revision_id"],
                    context_artifact_id=context_artifact_id,
                    failure_class=be.reason,
                    detail=be.detail,
                    taint_set=context_artifact.get("taint_set", []),
                    intent_id=intent_id,
                )
                raise InferenceBudgetExhausted(
                    reason=be.reason, detail=be.detail
                ) from be

        worker_run_id = f"wrun-{uuid4().hex}"
        artifact = {
            "inference_artifact_id": f"inf-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": context_artifact["root_revision_id"],
            "context_artifact_id": context_artifact_id,
            "worker_run_id": worker_run_id,
            "worker_profile": worker_profile,
            "model_route_id": parsed["model_route_id"] or model_route_id,
            "output_hash": _output_hash(parsed["output_text"]),
            "provenance_refs": [context_artifact_id, model_route_id],
            "taint_set": list(context_artifact.get("taint_set", [])),
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
            "token_usage": parsed["token_usage"],
            "latency_ms": parsed["latency_ms"],
        }

        violations = validate_artifact(artifact, self._schema)
        if violations:
            raise ModelIntegrationViolation(
                f"inference artifact schema validation failed: "
                f"{'; '.join(violations[:5])}"
            )

        self._repo.insert(artifact)

        # Honest replay-claim posture recording.
        #
        # If the adapter declares a `replay_ceiling` attribute (for
        # example, real-provider adapters that cannot host-deterministically
        # reproduce output declare `replay_ceiling = "semantic"`), record
        # it on the audit payload. Absence of the attribute is equivalent
        # to the phase-1 default (caller/evidence-driven classification).
        # This is intentionally additive and does not change the replay
        # classifier's admission logic; it surfaces the honest upper bound
        # to downstream evidence consumers.
        adapter_ceiling = getattr(self._adapter, "replay_ceiling", None)

        audit_payload: dict[str, Any] = {
            "worker_profile": worker_profile,
            "model_route_id": artifact["model_route_id"],
            "policy": {
                "max_output_tokens": self._policy.max_output_tokens,
                "timeout_seconds": self._policy.timeout_seconds,
                "max_retries": self._policy.max_retries,
            },
        }
        if isinstance(adapter_ceiling, str) and adapter_ceiling:
            audit_payload["replay_ceiling"] = adapter_ceiling

        audit_artifact_refs: list[str] = [
            artifact["inference_artifact_id"],
            context_artifact_id,
        ]
        if isinstance(intent_id, str) and intent_id:
            audit_artifact_refs.append(intent_id)
            audit_payload["intent_id"] = intent_id
        self._audit.append(
            record_type="inference_artifact_created",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )
        return artifact["inference_artifact_id"]
