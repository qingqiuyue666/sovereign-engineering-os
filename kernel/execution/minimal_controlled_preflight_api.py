"""Human-invoked Minimal Controlled Execution preflight API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from kernel.execution.minimal_controlled_execution_contract import (
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
)
from kernel.execution.minimal_controlled_preflight_sequence import (
    MinimalControlledPreflightResult,
    PREFLIGHT_ORDER,
    run_minimal_controlled_preflight_sequence,
)
from kernel.execution.minimal_controlled_runner_shared import canonical_json, sha256_text

__all__ = [
    "HUMAN_PREFLIGHT_ALLOWED_FIELDS",
    "HUMAN_PREFLIGHT_FORBIDDEN_FIELDS",
    "MinimalControlledPreflightApiResponse",
    "MinimalControlledPreflightEvidenceManifest",
    "human_preflight_manifest_hash",
    "run_human_invoked_minimal_controlled_preflight",
]

HUMAN_PREFLIGHT_ALLOWED_FIELDS = frozenset(
    {
        "approval_token_id",
        "caller_intent",
        "preflight_id",
        "requested_at",
        "requester",
        "run_id",
        "snapshot_ref",
        "task_id",
        "use_case_ids",
    }
)
HUMAN_PREFLIGHT_FORBIDDEN_FIELDS = frozenset(
    {
        "auto_reexecution",
        "background",
        "command_id",
        "command_ids",
        "commands",
        "graph",
        "parallel",
        "retry",
        "steps",
        "tasks",
    }
) | EXECUTION_REQUEST_FORBIDDEN_FIELDS


@dataclass(frozen=True)
class MinimalControlledPreflightEvidenceManifest:
    manifest_id: str
    preflight_id: str
    task_id: str
    run_id: str
    ordered_command_ids: tuple[str, ...]
    child_request_hashes: tuple[str, ...]
    child_decision_hashes: tuple[str, ...]
    child_admission_hashes: tuple[str, ...]
    child_receipt_hashes: tuple[str, ...]
    child_failure_bundle_hashes: tuple[str, ...]
    child_verifier_input_hashes: tuple[str, ...]
    child_verifier_binding_hashes: tuple[str, ...]
    pre_snapshot_hashes: tuple[str, ...]
    post_snapshot_hashes: tuple[str, ...]
    preflight_result_hash: str
    overall_status: str
    execution_performed: bool
    manifest_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "ordered_command_ids",
            "child_request_hashes",
            "child_decision_hashes",
            "child_admission_hashes",
            "child_receipt_hashes",
            "child_failure_bundle_hashes",
            "child_verifier_input_hashes",
            "child_verifier_binding_hashes",
            "pre_snapshot_hashes",
            "post_snapshot_hashes",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if self.ordered_command_ids != PREFLIGHT_ORDER:
            raise ValueError("manifest_preflight_order_mismatch")
        expected = human_preflight_manifest_hash(self)
        if self.manifest_hash and self.manifest_hash != expected:
            raise ValueError("manifest_hash_mismatch")
        object.__setattr__(self, "manifest_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MinimalControlledPreflightApiResponse:
    api_invocation_id: str
    preflight_result: MinimalControlledPreflightResult
    evidence_manifest: MinimalControlledPreflightEvidenceManifest
    execution_performed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_human_invoked_minimal_controlled_preflight(
    payload: Mapping[str, object],
) -> MinimalControlledPreflightApiResponse:
    data = _validated_api_payload(payload)
    result = run_minimal_controlled_preflight_sequence(data)
    manifest = _manifest_from_result(result)
    return MinimalControlledPreflightApiResponse(
        api_invocation_id="human-preflight-api-" + str(data["preflight_id"]),
        preflight_result=result,
        evidence_manifest=manifest,
        execution_performed=result.execution_performed,
    )


def human_preflight_manifest_hash(
    manifest: MinimalControlledPreflightEvidenceManifest | Mapping[str, object],
) -> str:
    data = manifest.as_dict() if isinstance(manifest, MinimalControlledPreflightEvidenceManifest) else dict(manifest)
    data.pop("manifest_hash", None)
    return "sha256:" + sha256_text(canonical_json(_json_ready(data)))


def _validated_api_payload(payload: Mapping[str, object]) -> dict[str, object]:
    data = dict(payload)
    forbidden = sorted(HUMAN_PREFLIGHT_FORBIDDEN_FIELDS.intersection(data))
    if forbidden:
        raise ValueError("human_preflight_field_forbidden:" + ",".join(forbidden))
    extra = sorted(set(data) - HUMAN_PREFLIGHT_ALLOWED_FIELDS)
    if extra:
        raise ValueError("human_preflight_field_not_allowed:" + ",".join(extra))
    for field_name in ("preflight_id", "task_id", "run_id", "requested_at", "requester"):
        if not isinstance(data.get(field_name), str) or not data[field_name]:
            raise ValueError(field_name + "_required")
    if "approval_token_id" in data and not isinstance(data["approval_token_id"], str):
        raise ValueError("approval_token_id_must_be_string")
    for field_name in ("caller_intent", "snapshot_ref"):
        if field_name in data and (
            not isinstance(data[field_name], str) or not data[field_name]
        ):
            raise ValueError(field_name + "_must_be_non_empty_string")
    if "use_case_ids" in data:
        values = data["use_case_ids"]
        if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
            raise ValueError("use_case_ids_must_be_sequence")
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("use_case_ids_must_be_non_empty_strings")
    return data


def _manifest_from_result(
    result: MinimalControlledPreflightResult,
) -> MinimalControlledPreflightEvidenceManifest:
    return MinimalControlledPreflightEvidenceManifest(
        manifest_id="human-preflight-manifest-" + result.preflight_id,
        preflight_id=result.preflight_id,
        task_id=result.task_id,
        run_id=result.run_id,
        ordered_command_ids=result.ordered_command_ids,
        child_request_hashes=result.child_request_hashes,
        child_decision_hashes=result.child_decision_hashes,
        child_admission_hashes=result.child_admission_hashes,
        child_receipt_hashes=result.child_receipt_hashes,
        child_failure_bundle_hashes=result.child_failure_bundle_hashes,
        child_verifier_input_hashes=result.child_verifier_input_hashes,
        child_verifier_binding_hashes=result.child_verifier_binding_hashes,
        pre_snapshot_hashes=result.pre_snapshot_hashes,
        post_snapshot_hashes=result.post_snapshot_hashes,
        preflight_result_hash=result.preflight_result_hash,
        overall_status=result.overall_status,
        execution_performed=result.execution_performed,
    )


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value
