"""AI router runtime boundary V1.

This module constrains the AI router to proposal generation. It can bind a
digest-only model route plan to WAL, artifact, and review queue evidence, but it
cannot call providers, execute tools, apply patches, merge, push, or mutate the
runtime outside the explicit review/approval queue path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence

from kernel.runtime.ai_worker_router import (
    AIWorkerRoutePlan,
    DEFAULT_AI_WORKER_DECLARATIONS,
    route_ai_worker_task,
)
from kernel.runtime.durable_job_queue import (
    DurableJobQueue,
    DurableJobQueueError,
)
from kernel.stores.artifact_store_persistence import (
    ArtifactStorePersistenceError,
    FileBackedArtifactStore,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)

__all__ = [
    "AI_ROUTER_RUNTIME_BOUNDARY_VERSION",
    "ZERO_HASH",
    "AIRouterRuntimeBoundaryError",
    "AIRouterRuntimeBoundaryReceipt",
    "FileBackedAIRouterRuntimeBoundary",
    "ModelRoutingReceipt",
    "compute_ai_router_runtime_boundary_receipt_hash",
    "compute_model_routing_receipt_hash",
]

AI_ROUTER_RUNTIME_BOUNDARY_VERSION = "ai_router_runtime_boundary_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_RUNTIME_ROOT_RELPATH = "ai-router-runtime"
_RUNTIME_WAL_RELPATH = _RUNTIME_ROOT_RELPATH + "/ai-router.real-wal.jsonl"
_ARTIFACT_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/artifacts"
_ARTIFACT_STORE_ID = "ai-router-runtime-artifacts-v1"
_RECEIPT_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/receipts"

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)

_ALLOWED_ACTIONS = frozenset(
    {
        "emit_patch_candidate",
        "emit_plan",
        "emit_proposal",
        "emit_review_packet",
    }
)
_ACTION_EFFECTS = {
    "emit_patch_candidate": "patch_candidate_emitted",
    "emit_plan": "plan_emitted",
    "emit_proposal": "proposal_emitted",
    "emit_review_packet": "review_packet_emitted",
}
_ACTION_OUTPUT_KINDS = {
    "emit_patch_candidate": "patch_candidate",
    "emit_plan": "plan",
    "emit_proposal": "proposal",
    "emit_review_packet": "review_packet",
}
_ALLOWED_OUTPUT_KINDS = frozenset(
    {
        "patch_candidate",
        "plan",
        "proposal",
        "review_packet",
    }
)
_ALLOWED_PAYLOAD_FIELDS = frozenset(
    {
        "blocked_worker_ids",
        "declared_effects",
        "human_invoked",
        "idempotency_key",
        "input_artifact_hash",
        "output_candidate_hash",
        "output_kind",
        "prompt_artifact_hash",
        "proposal_body_hash",
        "requested_action",
        "requested_by",
        "requested_worker_id",
        "required_capabilities",
        "review_packet_hash",
        "risk_level",
        "route_id",
        "run_id",
        "task_class",
        "task_id",
    }
)
_FORBIDDEN_FIELD_MARKERS = (
    "api_key",
    "apply",
    "authorization",
    "browser",
    "command",
    "credential",
    "env",
    "execute",
    "main",
    "merge",
    "network",
    "password",
    "private_key",
    "provider_response",
    "push",
    "raw",
    "secret",
    "subprocess",
    "tool",
    "token",
)
_FORBIDDEN_VALUE_MARKERS = (
    "api_key=",
    "apply_patch",
    "authorization:",
    "bearer ",
    "checkout main",
    "credential",
    "execute ",
    "merge ",
    "os." + "environ",
    "password=",
    "private_key",
    "push ",
    "secret=",
    "subprocess",
    "tool_request",
    "token=",
)


class AIRouterRuntimeBoundaryError(ValueError):
    """Raised when the AI router runtime boundary fails closed."""


@dataclass(frozen=True)
class ModelRoutingReceipt:
    """Deterministic receipt for a model route plan."""

    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    route_id: str
    task_id: str
    run_id: str
    task_class: str
    risk_level: str
    selected_worker_id: str
    provider_family: str
    candidate_worker_ids: tuple[str, ...]
    route_plan_hash: str
    prompt_artifact_hash: str
    input_artifact_hash: str
    output_candidate_hash: str
    provider_execution_permitted: bool
    provider_execution_performed: bool
    tool_execution_performed: bool
    credential_accessed: bool
    network_accessed: bool
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != AI_ROUTER_RUNTIME_BOUNDARY_VERSION:
            raise AIRouterRuntimeBoundaryError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise AIRouterRuntimeBoundaryError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise AIRouterRuntimeBoundaryError("accepted_routing_receipt_has_failures")
        if not self.accepted and not self.failures:
            raise AIRouterRuntimeBoundaryError("rejected_routing_receipt_requires_failures")
        for field_name in (
            "route_id",
            "task_id",
            "run_id",
            "task_class",
            "risk_level",
            "selected_worker_id",
            "provider_family",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "route_plan_hash",
            "prompt_artifact_hash",
            "input_artifact_hash",
            "output_candidate_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        object.__setattr__(
            self,
            "candidate_worker_ids",
            _normalize_string_sequence(self.candidate_worker_ids, "candidate_worker_ids"),
        )
        for flag_name in (
            "provider_execution_permitted",
            "provider_execution_performed",
            "tool_execution_performed",
            "credential_accessed",
            "network_accessed",
        ):
            if getattr(self, flag_name) is not False:
                raise AIRouterRuntimeBoundaryError(flag_name + "_must_be_false")
        _install_or_verify_hash(self, "receipt_hash", compute_model_routing_receipt_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class AIRouterRuntimeBoundaryReceipt:
    """Receipt for a safe AI proposal routing attempt."""

    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    route_id: str
    task_id: str
    run_id: str
    requested_action: str
    output_kind: str
    selected_worker_id: str
    provider_family: str
    route_plan_hash: str
    model_routing_receipt_hash: str
    prompt_artifact_hash: str
    input_artifact_hash: str
    output_candidate_hash: str
    proposal_body_hash: str
    review_packet_hash: str
    artifact_record_hash: str
    artifact_manifest_hash: str
    review_queue_job_id: str
    queue_record_hash: str
    ai_router_wal_record_hash: str
    review_required: bool
    approval_required: bool
    provider_execution_performed: bool
    tool_execution_performed: bool
    runtime_state_mutated: bool
    automatic_merge_performed: bool
    automatic_push_performed: bool
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != AI_ROUTER_RUNTIME_BOUNDARY_VERSION:
            raise AIRouterRuntimeBoundaryError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise AIRouterRuntimeBoundaryError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise AIRouterRuntimeBoundaryError("accepted_receipt_has_failures")
        if not self.accepted and not self.failures:
            raise AIRouterRuntimeBoundaryError("rejected_receipt_requires_failures")
        for field_name in (
            "route_id",
            "task_id",
            "run_id",
            "requested_action",
            "output_kind",
            "selected_worker_id",
            "provider_family",
            "review_queue_job_id",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "route_plan_hash",
            "model_routing_receipt_hash",
            "prompt_artifact_hash",
            "input_artifact_hash",
            "output_candidate_hash",
            "proposal_body_hash",
            "review_packet_hash",
            "artifact_record_hash",
            "artifact_manifest_hash",
            "queue_record_hash",
            "ai_router_wal_record_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        if self.accepted:
            for field_name in (
                "route_plan_hash",
                "model_routing_receipt_hash",
                "artifact_record_hash",
                "artifact_manifest_hash",
                "queue_record_hash",
                "ai_router_wal_record_hash",
            ):
                if getattr(self, field_name) == ZERO_HASH:
                    raise AIRouterRuntimeBoundaryError(field_name + "_required_when_accepted")
        for flag_name in (
            "review_required",
            "approval_required",
        ):
            if getattr(self, flag_name) is not True:
                raise AIRouterRuntimeBoundaryError(flag_name + "_must_be_true")
        for flag_name in (
            "provider_execution_performed",
            "tool_execution_performed",
            "runtime_state_mutated",
            "automatic_merge_performed",
            "automatic_push_performed",
        ):
            if getattr(self, flag_name) is not False:
                raise AIRouterRuntimeBoundaryError(flag_name + "_must_be_false")
        _install_or_verify_hash(self, "receipt_hash", compute_ai_router_runtime_boundary_receipt_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


class FileBackedAIRouterRuntimeBoundary:
    """File-backed proposal-only AI router runtime boundary."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        runtime_wal_relpath: str = _RUNTIME_WAL_RELPATH,
        artifact_store_relpath: str = _ARTIFACT_STORE_RELPATH,
        artifact_store_id: str = _ARTIFACT_STORE_ID,
        receipt_store_relpath: str = _RECEIPT_STORE_RELPATH,
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.runtime_wal_relpath = _validate_relpath_text(
            runtime_wal_relpath,
            "runtime_wal_relpath",
            allow_empty=False,
        )
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
            allow_empty=False,
        )
        self.artifact_store_id = _validated_identifier(
            artifact_store_id,
            "artifact_store_id",
        )
        self.receipt_store_relpath = _validate_relpath_text(
            receipt_store_relpath,
            "receipt_store_relpath",
            allow_empty=False,
        )

    def route_proposal(
        self,
        payload: Mapping[str, object],
        review_queue: DurableJobQueue,
        *,
        observed_at: str | None = None,
    ) -> AIRouterRuntimeBoundaryReceipt:
        observed = _timestamp(observed_at)
        data, failures = _admit_payload(payload)
        if not isinstance(review_queue, DurableJobQueue):
            failures = (*failures, "review_queue_required")
        if failures:
            return _rejected_receipt(data, failures)

        try:
            route_plan = route_ai_worker_task(_route_material(data))
            if route_plan.route_status != "ready_for_handoff":
                return _rejected_receipt(data, ("no_model_route_candidate",))
            declaration = _declaration_for_worker(route_plan.selected_worker_id)
            routing_receipt = _model_routing_receipt(
                data=data,
                route_plan=route_plan,
                provider_family=declaration.provider_family,
            )
            router_wal_hash = self._append_ai_router_wal(
                data=data,
                route_plan=route_plan,
                routing_receipt=routing_receipt,
                observed_at=observed,
            )
            artifact = self._write_router_artifact(
                data=data,
                route_plan=route_plan,
                routing_receipt=routing_receipt,
                router_wal_hash=router_wal_hash,
                observed_at=observed,
            )
            queue_state = self._queue_for_review(
                data=data,
                review_queue=review_queue,
                route_plan=route_plan,
                routing_receipt=routing_receipt,
                artifact_record_hash=artifact.record_hash,
                artifact_manifest_hash=artifact.manifest.manifest_hash,
                observed_at=observed,
            )
        except (
            AIRouterRuntimeBoundaryError,
            ArtifactStorePersistenceError,
            DurableJobQueueError,
            RealWalStorageError,
            ValueError,
        ) as exc:
            return _rejected_receipt(
                data,
                ("ai_router_boundary_failed:" + exc.__class__.__name__, str(exc)),
            )

        receipt = AIRouterRuntimeBoundaryReceipt(
            integration_version=AI_ROUTER_RUNTIME_BOUNDARY_VERSION,
            accepted=True,
            failures=(),
            route_id=str(data["route_id"]),
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            requested_action=str(data["requested_action"]),
            output_kind=str(data["output_kind"]),
            selected_worker_id=route_plan.selected_worker_id,
            provider_family=declaration.provider_family,
            route_plan_hash=route_plan.content_hash,
            model_routing_receipt_hash=routing_receipt.receipt_hash,
            prompt_artifact_hash=str(data["prompt_artifact_hash"]),
            input_artifact_hash=str(data["input_artifact_hash"]),
            output_candidate_hash=str(data["output_candidate_hash"]),
            proposal_body_hash=str(data["proposal_body_hash"]),
            review_packet_hash=str(data["review_packet_hash"]),
            artifact_record_hash=artifact.record_hash,
            artifact_manifest_hash=artifact.manifest.manifest_hash,
            review_queue_job_id=_review_job_id(data),
            queue_record_hash=queue_state.last_event_hash,
            ai_router_wal_record_hash=router_wal_hash,
            review_required=True,
            approval_required=True,
            provider_execution_performed=False,
            tool_execution_performed=False,
            runtime_state_mutated=False,
            automatic_merge_performed=False,
            automatic_push_performed=False,
        )
        self._persist_receipt(receipt)
        return receipt

    def _append_ai_router_wal(
        self,
        *,
        data: Mapping[str, object],
        route_plan: AIWorkerRoutePlan,
        routing_receipt: ModelRoutingReceipt,
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        material = {
            "input_artifact_hash": data["input_artifact_hash"],
            "model_routing_receipt_hash": routing_receipt.receipt_hash,
            "output_candidate_hash": data["output_candidate_hash"],
            "prompt_artifact_hash": data["prompt_artifact_hash"],
            "requested_action_hash": _sha256_text(str(data["requested_action"])),
            "route_plan_hash": route_plan.content_hash,
        }
        receipt = FileBackedRealWalStorage(wal_path).append(
            record_type="AI_ROUTER_EVENT",
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            payload_hash=_sha256_json(material),
            digest_bindings={
                "input_artifact_hash": str(data["input_artifact_hash"]),
                "model_routing_hash": routing_receipt.receipt_hash,
                "output_candidate_hash": str(data["output_candidate_hash"]),
                "prompt_artifact_hash": str(data["prompt_artifact_hash"]),
                "route_plan_hash": route_plan.content_hash,
            },
            created_at=observed_at,
        )
        return receipt.record_hash

    def _write_router_artifact(
        self,
        *,
        data: Mapping[str, object],
        route_plan: AIWorkerRoutePlan,
        routing_receipt: ModelRoutingReceipt,
        router_wal_hash: str,
        observed_at: str,
    ):
        material = {
            "approval_required": True,
            "declared_effects_hash": _sha256_json(tuple(data["declared_effects"])),
            "input_artifact_hash": data["input_artifact_hash"],
            "model_routing_receipt_hash": routing_receipt.receipt_hash,
            "output_candidate_hash": data["output_candidate_hash"],
            "output_kind_hash": _sha256_text(str(data["output_kind"])),
            "proposal_body_hash": data["proposal_body_hash"],
            "prompt_artifact_hash": data["prompt_artifact_hash"],
            "requested_action_hash": _sha256_text(str(data["requested_action"])),
            "review_packet_hash": data["review_packet_hash"],
            "review_required": True,
            "route_plan_hash": route_plan.content_hash,
            "router_wal_hash": router_wal_hash,
            "selected_worker_id_hash": _sha256_text(route_plan.selected_worker_id),
        }
        root = self._resolve_relpath(self.artifact_store_relpath, "artifact_store_relpath")
        return FileBackedArtifactStore(
            root,
            store_id=self.artifact_store_id,
        ).write_json_artifact(
            artifact_type="audit_json",
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            payload=material,
            provenance_hash=_sha256_json(material),
            metadata={
                "output_kind": str(data["output_kind"]),
                "route_plan_hash": route_plan.content_hash,
                "runtime_version": AI_ROUTER_RUNTIME_BOUNDARY_VERSION,
                "selected_worker_id": route_plan.selected_worker_id,
            },
            created_at=observed_at,
        )

    def _queue_for_review(
        self,
        *,
        data: Mapping[str, object],
        review_queue: DurableJobQueue,
        route_plan: AIWorkerRoutePlan,
        routing_receipt: ModelRoutingReceipt,
        artifact_record_hash: str,
        artifact_manifest_hash: str,
        observed_at: str,
    ):
        job_id = _review_job_id(data)
        review_queue.submit_job(
            job_id=job_id,
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            payload={
                "ai_router_runtime_hash": _sha256_text(AI_ROUTER_RUNTIME_BOUNDARY_VERSION),
                "approval_required": True,
                "artifact_manifest_hash": artifact_manifest_hash,
                "artifact_record_hash": artifact_record_hash,
                "model_routing_receipt_hash": routing_receipt.receipt_hash,
                "output_candidate_hash": str(data["output_candidate_hash"]),
                "review_required": True,
                "route_plan_hash": route_plan.content_hash,
            },
            idempotency_key=str(data["idempotency_key"]),
            max_attempts=1,
            priority=40,
            submitted_at=observed_at,
        )
        return review_queue.queue_job(job_id, queued_at=observed_at)

    def _persist_receipt(self, receipt: AIRouterRuntimeBoundaryReceipt) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(_receipt_relpath(self.receipt_store_relpath, receipt.receipt_hash), "receipt_relpath"),
            receipt.as_dict(),
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        clean = _validate_relpath_text(relpath, field_name, allow_empty=False)
        candidate = self.runtime_root / clean
        current = self.runtime_root
        for part in PurePosixPath(clean).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise AIRouterRuntimeBoundaryError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise AIRouterRuntimeBoundaryError(field_name + "_escapes_runtime_root")
        return resolved


def compute_model_routing_receipt_hash(
    receipt: ModelRoutingReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if isinstance(receipt, ModelRoutingReceipt) else dict(receipt)
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def compute_ai_router_runtime_boundary_receipt_hash(
    receipt: AIRouterRuntimeBoundaryReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if isinstance(receipt, AIRouterRuntimeBoundaryReceipt) else dict(receipt)
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def _admit_payload(payload: Mapping[str, object]) -> tuple[dict[str, object], tuple[str, ...]]:
    if not isinstance(payload, Mapping):
        return _fallback_data(), ("payload_must_be_mapping",)
    data = {**_fallback_data(), **dict(payload)}
    failures: list[str] = []
    extra = sorted(set(data) - set(_fallback_data()) - _ALLOWED_PAYLOAD_FIELDS)
    if extra:
        failures.append("payload_field_not_allowed:" + ",".join(extra))
    try:
        _scan_json_safety(data)
    except AIRouterRuntimeBoundaryError as exc:
        failures.append(str(exc))
    for field_name in (
        "input_artifact_hash",
        "output_candidate_hash",
        "prompt_artifact_hash",
        "proposal_body_hash",
        "review_packet_hash",
    ):
        if not _is_sha256(data.get(field_name)):
            failures.append(field_name + "_must_be_sha256")
    for field_name in (
        "idempotency_key",
        "output_kind",
        "requested_action",
        "requested_by",
        "risk_level",
        "route_id",
        "run_id",
        "task_class",
        "task_id",
    ):
        if not _nonempty_string(data.get(field_name)):
            failures.append(field_name + "_required")
    if data.get("human_invoked") is not True:
        failures.append("human_invoked_required_true")
    action = str(data.get("requested_action", ""))
    if action and action not in _ALLOWED_ACTIONS:
        if any(marker in action for marker in ("execute", "tool")):
            failures.append("unsafe_tool_request")
        elif any(marker in action for marker in ("merge", "push", "main", "apply")):
            failures.append("runtime_mutation_action_forbidden")
        else:
            failures.append("unsupported_action")
    output_kind = str(data.get("output_kind", ""))
    if output_kind and output_kind not in _ALLOWED_OUTPUT_KINDS:
        failures.append("unsupported_output_kind")
    expected_output = _ACTION_OUTPUT_KINDS.get(action)
    if expected_output is not None and output_kind != expected_output:
        failures.append("action_output_kind_mismatch")
    for field_name in ("required_capabilities", "blocked_worker_ids"):
        value = data.get(field_name)
        if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
            failures.append(field_name + "_must_be_sequence")
        elif not all(_nonempty_string(item) for item in value):
            failures.append(field_name + "_must_contain_nonempty_strings")
        else:
            data[field_name] = tuple(str(item) for item in value)
    requested_worker_id = data.get("requested_worker_id")
    if requested_worker_id is not None and not _nonempty_string(requested_worker_id):
        failures.append("requested_worker_id_must_be_nonempty_when_present")
    declared_effects = data.get("declared_effects")
    if not isinstance(declared_effects, (list, tuple)) or isinstance(declared_effects, (str, bytes)):
        failures.append("declared_effects_must_be_sequence")
    else:
        normalized_effects = tuple(str(item) for item in declared_effects)
        if not normalized_effects or not all(_nonempty_string(item) for item in normalized_effects):
            failures.append("declared_effects_must_be_nonempty_strings")
        else:
            expected_effect = _ACTION_EFFECTS.get(action)
            unexpected = sorted(set(normalized_effects) - ({expected_effect} if expected_effect else set()))
            if unexpected:
                failures.append("hallucinated_action_forbidden:" + ",".join(unexpected))
            data["declared_effects"] = normalized_effects
    return data, tuple(_dedupe(failures))


def _route_material(data: Mapping[str, object]) -> dict[str, object]:
    material: dict[str, object] = {
        "route_id": data["route_id"],
        "task_id": data["task_id"],
        "task_class": data["task_class"],
        "risk_level": data["risk_level"],
        "required_capabilities": data["required_capabilities"],
        "blocked_worker_ids": data["blocked_worker_ids"],
    }
    if data.get("requested_worker_id") is not None:
        material["requested_worker_id"] = data["requested_worker_id"]
    return material


def _model_routing_receipt(
    *,
    data: Mapping[str, object],
    route_plan: AIWorkerRoutePlan,
    provider_family: str,
) -> ModelRoutingReceipt:
    return ModelRoutingReceipt(
        integration_version=AI_ROUTER_RUNTIME_BOUNDARY_VERSION,
        accepted=True,
        failures=(),
        route_id=route_plan.route_id,
        task_id=route_plan.task_id,
        run_id=str(data["run_id"]),
        task_class=route_plan.task_class,
        risk_level=route_plan.risk_level,
        selected_worker_id=route_plan.selected_worker_id,
        provider_family=provider_family,
        candidate_worker_ids=route_plan.candidate_worker_ids,
        route_plan_hash=route_plan.content_hash,
        prompt_artifact_hash=str(data["prompt_artifact_hash"]),
        input_artifact_hash=str(data["input_artifact_hash"]),
        output_candidate_hash=str(data["output_candidate_hash"]),
        provider_execution_permitted=False,
        provider_execution_performed=False,
        tool_execution_performed=False,
        credential_accessed=False,
        network_accessed=False,
    )


def _declaration_for_worker(worker_id: str):
    for declaration in DEFAULT_AI_WORKER_DECLARATIONS:
        if declaration.worker_id == worker_id:
            return declaration
    raise AIRouterRuntimeBoundaryError("selected_worker_declaration_missing")


def _rejected_receipt(
    data: Mapping[str, object],
    failures: Sequence[str],
) -> AIRouterRuntimeBoundaryReceipt:
    return AIRouterRuntimeBoundaryReceipt(
        integration_version=AI_ROUTER_RUNTIME_BOUNDARY_VERSION,
        accepted=False,
        failures=tuple(_normalize_failure_texts(failures)),
        route_id=_safe_identity(data, "route_id", "unknown-route"),
        task_id=_safe_identity(data, "task_id", "unknown-task"),
        run_id=_safe_identity(data, "run_id", "unknown-run"),
        requested_action=_safe_identity(data, "requested_action", "rejected-action"),
        output_kind=_safe_identity(data, "output_kind", "rejected-output"),
        selected_worker_id="none",
        provider_family="none",
        route_plan_hash=ZERO_HASH,
        model_routing_receipt_hash=ZERO_HASH,
        prompt_artifact_hash=_safe_digest(data, "prompt_artifact_hash"),
        input_artifact_hash=_safe_digest(data, "input_artifact_hash"),
        output_candidate_hash=_safe_digest(data, "output_candidate_hash"),
        proposal_body_hash=_safe_digest(data, "proposal_body_hash"),
        review_packet_hash=_safe_digest(data, "review_packet_hash"),
        artifact_record_hash=ZERO_HASH,
        artifact_manifest_hash=ZERO_HASH,
        review_queue_job_id="not-queued",
        queue_record_hash=ZERO_HASH,
        ai_router_wal_record_hash=ZERO_HASH,
        review_required=True,
        approval_required=True,
        provider_execution_performed=False,
        tool_execution_performed=False,
        runtime_state_mutated=False,
        automatic_merge_performed=False,
        automatic_push_performed=False,
    )


def _review_job_id(data: Mapping[str, object]) -> str:
    return "ai-review-" + _sha256_text(str(data["route_id"])).removeprefix("sha256:")[:24]


def _receipt_relpath(receipt_store_relpath: str, receipt_hash: str) -> str:
    return (
        receipt_store_relpath
        + "/"
        + receipt_hash.removeprefix("sha256:")
        + ".json"
    )


def _fallback_data() -> dict[str, object]:
    return {
        "blocked_worker_ids": (),
        "declared_effects": (),
        "human_invoked": False,
        "idempotency_key": "unknown-idempotency",
        "input_artifact_hash": ZERO_HASH,
        "output_candidate_hash": ZERO_HASH,
        "output_kind": "rejected-output",
        "prompt_artifact_hash": ZERO_HASH,
        "proposal_body_hash": ZERO_HASH,
        "requested_action": "rejected-action",
        "requested_by": "unknown-requester",
        "requested_worker_id": None,
        "required_capabilities": (),
        "review_packet_hash": ZERO_HASH,
        "risk_level": "medium",
        "route_id": "unknown-route",
        "run_id": "unknown-run",
        "task_class": "unknown-task-class",
        "task_id": "unknown-task",
    }


def _safe_identity(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name)
    if (
        isinstance(value, str)
        and value
        and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", value)
        and not _SECRET_KEY_PATTERN.search(value)
    ):
        return value
    return default


def _safe_digest(data: Mapping[str, object], field_name: str) -> str:
    value = data.get(field_name)
    return value if _is_sha256(value) else ZERO_HASH


def _scan_json_safety(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise AIRouterRuntimeBoundaryError(
                    "unsafe_ai_router_field:" + ".".join(path + (key_text,))
                )
            _scan_json_safety(item, path=path + (key_text,))
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_json_safety(item, path=path + (str(index),))
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        lowered = value.lower()
        if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
            raise AIRouterRuntimeBoundaryError(
                "unsafe_ai_router_value_sensitive:" + ".".join(path)
            )
        for marker in _FORBIDDEN_VALUE_MARKERS:
            if marker in lowered:
                raise AIRouterRuntimeBoundaryError(
                    "unsafe_ai_router_value:" + ".".join(path)
                )
        return
    raise AIRouterRuntimeBoundaryError("unsafe_ai_router_value_type:" + ".".join(path))


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise AIRouterRuntimeBoundaryError("failures_must_be_sequence")
    failures = tuple(_normalize_failure_texts(value))
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _normalize_failure_texts(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        return (str(value),)
    return tuple(str(item) for item in value if str(item))


def _normalize_string_sequence(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise AIRouterRuntimeBoundaryError(field_name + "_must_be_sequence")
    normalized = tuple(str(item) for item in value)
    if not normalized or not all(_nonempty_string(item) for item in normalized):
        raise AIRouterRuntimeBoundaryError(field_name + "_must_be_nonempty_strings")
    return normalized


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current:
        _require_sha256(current, field_name)
        if current != expected:
            raise AIRouterRuntimeBoundaryError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise AIRouterRuntimeBoundaryError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise AIRouterRuntimeBoundaryError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise AIRouterRuntimeBoundaryError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise AIRouterRuntimeBoundaryError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return ""
        raise AIRouterRuntimeBoundaryError(field_name + "_required")
    if "\\" in value:
        raise AIRouterRuntimeBoundaryError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise AIRouterRuntimeBoundaryError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _validated_identifier(value: object, field_name: str) -> str:
    _require_nonempty_string(value, field_name)
    text = str(value)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,95}", text):
        raise AIRouterRuntimeBoundaryError(field_name + "_invalid")
    return text


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise AIRouterRuntimeBoundaryError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise AIRouterRuntimeBoundaryError(field_name + "_secret_like")


def _write_json_no_overwrite(path: Path, payload: Mapping[str, object]) -> None:
    data = (_canonical_json(payload) + "\n").encode("utf-8")
    if path.exists():
        if path.is_symlink():
            raise AIRouterRuntimeBoundaryError("receipt_target_is_symlink")
        if not path.is_file():
            raise AIRouterRuntimeBoundaryError("receipt_target_not_file")
        if path.read_bytes() == data:
            return
        raise AIRouterRuntimeBoundaryError("receipt_target_mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise AIRouterRuntimeBoundaryError("receipt_parent_is_symlink")
    temp_path = path.with_name(
        "." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16]
    )
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise AIRouterRuntimeBoundaryError("receipt_write_failed")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        if path.exists():
            raise AIRouterRuntimeBoundaryError("receipt_target_exists")
        temp_path.rename(path)
        _fsync_parent(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not _nonempty_string(value):
        raise AIRouterRuntimeBoundaryError(field_name + "_required")


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _require_sha256(value: object, field_name: str) -> None:
    if not _is_sha256(value):
        raise AIRouterRuntimeBoundaryError(field_name + "_must_be_sha256")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AIRouterRuntimeBoundaryError("timestamp_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _canonical_json(payload: object) -> str:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _json_ready(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
