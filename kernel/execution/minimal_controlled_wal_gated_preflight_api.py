"""Human-invoked WAL-gated preflight API for Minimal Controlled Execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Callable, Mapping

from kernel.execution.minimal_controlled_wal_adapter_contract import (
    WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES,
    WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES,
    MinimalControlledWalAdapterRecord,
)
from kernel.execution.minimal_controlled_wal_gated_preflight_wrapper import (
    MinimalControlledWalGatedPreflightInput,
    MinimalControlledWalGatedPreflightResult,
    WAL_GATED_PREFLIGHT_WRAPPER_VERSION,
    run_minimal_controlled_wal_gated_preflight_wrapper,
)

__all__ = [
    "WAL_GATED_PREFLIGHT_API_VERSION",
    "WAL_GATED_PREFLIGHT_API_ALLOWED_FIELDS",
    "WAL_GATED_PREFLIGHT_API_FORBIDDEN_FIELDS",
    "MinimalControlledWalGatedPreflightApiResponse",
    "minimal_controlled_wal_gated_preflight_api_response_hash",
    "run_human_invoked_minimal_controlled_wal_gated_preflight",
]

WAL_GATED_PREFLIGHT_API_VERSION = "minimal_controlled_wal_gated_preflight_api_v1"

WAL_GATED_PREFLIGHT_API_ALLOWED_FIELDS = frozenset(
    {
        "admission_evidence",
        "api_invocation_id",
        "approval_token_id",
        "approved_for_wal_gated_preflight",
        "caller_intent",
        "human_invoked",
        "outcome_evidence",
        "preflight_id",
        "preflight_result_evidence",
        "requested_at",
        "requester",
        "run_id",
        "single_run_scope",
        "task_id",
        "verifier_binding_evidence",
        "wrapper_input_id",
    }
)

WAL_GATED_PREFLIGHT_API_FORBIDDEN_FIELDS = frozenset(
    {
        "append_callable",
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
) | WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES | WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES

_EVIDENCE_FORBIDDEN_FIELDS = (
    WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES | WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES
)

_REQUIRED_TRUE_FLAGS = (
    "human_invoked",
    "single_run_scope",
    "approved_for_wal_gated_preflight",
)
_REQUIRED_STRING_FIELDS = (
    "wrapper_input_id",
    "task_id",
    "run_id",
    "preflight_id",
    "requested_at",
    "requester",
)
_EVIDENCE_FIELDS = (
    "admission_evidence",
    "outcome_evidence",
    "verifier_binding_evidence",
    "preflight_result_evidence",
)


@dataclass(frozen=True)
class MinimalControlledWalGatedPreflightApiResponse:
    api_invocation_id: str
    wal_gated_preflight_api_version: str
    task_id: str
    run_id: str
    preflight_id: str
    wrapper_result: MinimalControlledWalGatedPreflightResult
    execution_may_proceed: bool
    accepted: bool
    rejection_reasons: tuple[str, ...]
    api_response_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in ("api_invocation_id", "task_id", "run_id", "preflight_id"):
            _require_string(getattr(self, field_name), field_name)
        if self.wal_gated_preflight_api_version != WAL_GATED_PREFLIGHT_API_VERSION:
            raise ValueError("wal_gated_preflight_api_version_mismatch")
        if not isinstance(self.wrapper_result, MinimalControlledWalGatedPreflightResult):
            raise ValueError("wrapper_result_required")
        _require_bool(self.execution_may_proceed, "execution_may_proceed")
        _require_bool(self.accepted, "accepted")
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(self.rejection_reasons, "rejection_reasons"),
        )
        if self.execution_may_proceed != self.wrapper_result.execution_may_proceed:
            raise ValueError("execution_may_proceed_mismatch")
        if self.accepted != self.wrapper_result.accepted:
            raise ValueError("accepted_mismatch")
        if self.rejection_reasons != self.wrapper_result.rejection_reasons:
            raise ValueError("rejection_reasons_mismatch")
        expected = minimal_controlled_wal_gated_preflight_api_response_hash(self)
        if self.api_response_hash and self.api_response_hash != expected:
            raise ValueError("api_response_hash_mismatch")
        object.__setattr__(self, "api_response_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_human_invoked_minimal_controlled_wal_gated_preflight(
    payload: Mapping[str, object],
    append_callable: Callable[[MinimalControlledWalAdapterRecord], object],
) -> MinimalControlledWalGatedPreflightApiResponse:
    if not callable(append_callable):
        raise ValueError("append_callable_required")

    data = _validated_api_payload(payload)
    wrapper_input = MinimalControlledWalGatedPreflightInput(
        wrapper_input_id=str(data["wrapper_input_id"]),
        wal_gated_preflight_wrapper_version=WAL_GATED_PREFLIGHT_WRAPPER_VERSION,
        task_id=str(data["task_id"]),
        run_id=str(data["run_id"]),
        preflight_id=str(data["preflight_id"]),
        admission_evidence=data["admission_evidence"],
        outcome_evidence=data["outcome_evidence"],
        verifier_binding_evidence=data["verifier_binding_evidence"],
        preflight_result_evidence=data["preflight_result_evidence"],
    )
    wrapper_result = run_minimal_controlled_wal_gated_preflight_wrapper(
        wrapper_input,
        append_callable,
    )

    return MinimalControlledWalGatedPreflightApiResponse(
        api_invocation_id=str(
            data.get(
                "api_invocation_id",
                "wal-gated-preflight-api-" + str(data["preflight_id"]),
            )
        ),
        wal_gated_preflight_api_version=WAL_GATED_PREFLIGHT_API_VERSION,
        task_id=str(data["task_id"]),
        run_id=str(data["run_id"]),
        preflight_id=str(data["preflight_id"]),
        wrapper_result=wrapper_result,
        execution_may_proceed=wrapper_result.execution_may_proceed,
        accepted=wrapper_result.accepted,
        rejection_reasons=wrapper_result.rejection_reasons,
    )


def minimal_controlled_wal_gated_preflight_api_response_hash(
    response: MinimalControlledWalGatedPreflightApiResponse | Mapping[str, object],
) -> str:
    data = response.as_dict() if isinstance(response, MinimalControlledWalGatedPreflightApiResponse) else dict(response)
    data.pop("api_response_hash", None)
    return "sha256:" + _sha256_hex(_canonical_json(_json_ready(data)))


def _validated_api_payload(payload: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise ValueError("wal_gated_preflight_api_payload_must_be_mapping")
    data = dict(payload)
    forbidden = sorted(WAL_GATED_PREFLIGHT_API_FORBIDDEN_FIELDS.intersection(data))
    if forbidden:
        raise ValueError("wal_gated_preflight_api_field_forbidden:" + ",".join(forbidden))
    extra = sorted(set(data) - WAL_GATED_PREFLIGHT_API_ALLOWED_FIELDS)
    if extra:
        raise ValueError("wal_gated_preflight_api_field_not_allowed:" + ",".join(extra))

    for field_name in _REQUIRED_TRUE_FLAGS:
        if data.get(field_name) is not True:
            raise ValueError(field_name + "_required_true")
    for field_name in _REQUIRED_STRING_FIELDS:
        _require_string(data.get(field_name), field_name)
    for optional_string in ("api_invocation_id", "approval_token_id", "caller_intent"):
        if optional_string in data:
            _require_string(data.get(optional_string), optional_string)
    for field_name in _EVIDENCE_FIELDS:
        data[field_name] = _validated_evidence_mapping(data.get(field_name), field_name, data)
    return data


def _validated_evidence_mapping(
    value: object,
    field_name: str,
    data: Mapping[str, object],
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(field_name + "_must_be_mapping")
    evidence = dict(value)
    forbidden = sorted(_EVIDENCE_FORBIDDEN_FIELDS.intersection(evidence))
    if forbidden:
        raise ValueError(field_name + "_field_forbidden:" + ",".join(forbidden))
    for identity_field in ("task_id", "run_id", "preflight_id"):
        if identity_field in evidence and evidence[identity_field] != data[identity_field]:
            raise ValueError(field_name + "_" + identity_field + "_mismatch")
    return evidence


def _require_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(field_name + "_required")


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(field_name + "_must_be_bool")


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_string_sequence")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(field_name + "_cannot_contain_empty_string")
        normalized.append(value)
    return tuple(normalized)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
