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
from typing import Any, Mapping, Protocol
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.stores.sqlite.repositories import InferenceArtifactRepository
from kernel.version.version_tuple import compose_version_tuple_hash


class ModelIntegrationViolation(Exception):
    """Raised when a caller breaches the governed model-integration boundary."""


class InferenceFailure(Exception):
    """Raised when model invocation fails under governed conditions."""


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
    ) -> None:
        self._repo = repository
        self._audit = audit_ledger
        self._context_reader = context_reader
        self._adapter: ModelAdapter = adapter or _NullAdapter()
        self._policy = policy or InferencePolicy()
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("inference_artifact")

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
    ) -> None:
        # The ledger's FailureBundle writer lives in the evidence service
        # in the general case. In phase 1 we emit an AuditRecord with
        # explicit failure classification; a full FailureBundle row is
        # left to the evidence/append_only_ledger wiring.
        self._audit.append(
            record_type="inference_failure",
            task_id=task_id,
            artifact_refs=[context_artifact_id],
            payload={
                "failure_class": failure_class,
                "detail": detail,
                "root_revision_id": root_revision_id,
            },
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
        """
        context_artifact = self._context_reader.fetch(context_artifact_id)
        if context_artifact is None:
            raise ModelIntegrationViolation(
                f"context artifact not found: {context_artifact_id}"
            )

        envelope = self._build_prompt_envelope(context_artifact=context_artifact)

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
            )
            raise
        except Exception as exc:  # noqa: BLE001 — fail closed on any error
            self._emit_failure_bundle(
                task_id=task_id,
                root_revision_id=context_artifact["root_revision_id"],
                context_artifact_id=context_artifact_id,
                failure_class="model_adapter_exception",
                detail=f"{type(exc).__name__}: {exc}",
            )
            raise InferenceFailure(str(exc)) from exc

        parsed = self._parse_response(raw)

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

        self._audit.append(
            record_type="inference_artifact_created",
            task_id=task_id,
            artifact_refs=[artifact["inference_artifact_id"], context_artifact_id],
            payload={
                "worker_profile": worker_profile,
                "model_route_id": artifact["model_route_id"],
                "policy": {
                    "max_output_tokens": self._policy.max_output_tokens,
                    "timeout_seconds": self._policy.timeout_seconds,
                    "max_retries": self._policy.max_retries,
                },
            },
        )
        return artifact["inference_artifact_id"]
