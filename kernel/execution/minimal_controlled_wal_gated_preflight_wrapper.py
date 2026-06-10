"""Callable-only WAL-gated preflight wrapper for Minimal Controlled Execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Callable, Mapping, Sequence

from kernel.execution.minimal_controlled_wal_adapter_contract import (
    WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES,
    WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES,
    MinimalControlledWalAdapterRecord,
)
from kernel.execution.minimal_controlled_wal_adapter_integration import (
    WAL_ADAPTER_INTEGRATION_VERSION,
    append_minimal_controlled_wal_adapter_records,
    map_admission_to_wal_adapter_record,
    map_failure_to_wal_adapter_record,
    map_preflight_result_to_wal_adapter_record,
    map_receipt_to_wal_adapter_record,
    map_verifier_binding_to_wal_adapter_record,
    prepare_append_before_execution_plan,
    replay_minimal_controlled_wal_adapter_records,
)

__all__ = [
    "WAL_GATED_PREFLIGHT_WRAPPER_VERSION",
    "MinimalControlledWalGatedPreflightInput",
    "MinimalControlledWalGatedPreflightResult",
    "build_minimal_controlled_wal_gated_preflight_records",
    "run_minimal_controlled_wal_gated_preflight_wrapper",
]

WAL_GATED_PREFLIGHT_WRAPPER_VERSION = "minimal_controlled_wal_gated_preflight_wrapper_v1"

_FORBIDDEN_EVIDENCE_FIELDS = (
    WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES | WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES
)
_OUTCOME_RECEIPT = "EXECUTION_RECEIPT"
_OUTCOME_FAILURE = "EXECUTION_FAILURE"


class _WrapperDictMixin:
    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MinimalControlledWalGatedPreflightInput(_WrapperDictMixin):
    wrapper_input_id: str
    wal_gated_preflight_wrapper_version: str
    task_id: str
    run_id: str
    preflight_id: str
    admission_evidence: Mapping[str, object]
    outcome_evidence: Mapping[str, object]
    verifier_binding_evidence: Mapping[str, object]
    preflight_result_evidence: Mapping[str, object]
    wrapper_input_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in ("wrapper_input_id", "task_id", "run_id", "preflight_id"):
            _require_string(getattr(self, field_name), field_name)
        _require_wrapper_version(self.wal_gated_preflight_wrapper_version)
        for field_name in (
            "admission_evidence",
            "outcome_evidence",
            "verifier_binding_evidence",
            "preflight_result_evidence",
        ):
            evidence = _validated_evidence_mapping(getattr(self, field_name), field_name)
            _require_matching_identity(evidence, self, field_name)
            object.__setattr__(self, field_name, evidence)
        _validate_hash_value(self.wrapper_input_hash, "wrapper_input_hash", allow_empty=True)
        _install_or_verify_hash(
            self,
            "wrapper_input_hash",
            minimal_controlled_wal_gated_preflight_input_hash,
        )


@dataclass(frozen=True)
class MinimalControlledWalGatedPreflightResult(_WrapperDictMixin):
    wrapper_result_id: str
    wal_gated_preflight_wrapper_version: str
    task_id: str
    run_id: str
    preflight_id: str
    ordered_record_hashes: tuple[str, ...]
    append_result_hashes: tuple[str, ...]
    append_plan_hash: str
    batch_hash: str
    replay_result_hash: str
    integration_result_hash: str
    execution_may_proceed: bool
    accepted: bool
    rejection_reasons: tuple[str, ...]
    wrapper_result_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in ("wrapper_result_id", "task_id", "run_id", "preflight_id"):
            _require_string(getattr(self, field_name), field_name)
        _require_wrapper_version(self.wal_gated_preflight_wrapper_version)
        object.__setattr__(
            self,
            "ordered_record_hashes",
            _hash_tuple(self.ordered_record_hashes, "ordered_record_hashes"),
        )
        object.__setattr__(
            self,
            "append_result_hashes",
            _hash_tuple(self.append_result_hashes, "append_result_hashes"),
        )
        for field_name in (
            "append_plan_hash",
            "batch_hash",
            "replay_result_hash",
            "integration_result_hash",
            "wrapper_result_hash",
        ):
            _validate_hash_value(
                getattr(self, field_name),
                field_name,
                allow_empty=field_name == "wrapper_result_hash",
            )
        _require_bool(self.execution_may_proceed, "execution_may_proceed")
        _require_bool(self.accepted, "accepted")
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(self.rejection_reasons, "rejection_reasons", allow_empty=True),
        )
        expected_accepted = self.execution_may_proceed and not self.rejection_reasons
        if self.accepted != expected_accepted:
            raise ValueError("accepted_must_match_execution_and_rejections")
        _install_or_verify_hash(
            self,
            "wrapper_result_hash",
            minimal_controlled_wal_gated_preflight_result_hash,
        )


def build_minimal_controlled_wal_gated_preflight_records(
    wrapper_input: MinimalControlledWalGatedPreflightInput,
) -> tuple[MinimalControlledWalAdapterRecord, ...]:
    _require_wrapper_input(wrapper_input)
    outcome_evidence = dict(wrapper_input.outcome_evidence)
    outcome_type = _outcome_type(outcome_evidence)
    clean_outcome_evidence = dict(outcome_evidence)
    clean_outcome_evidence.pop("outcome_type", None)
    clean_outcome_evidence.pop("record_type", None)

    if outcome_type == _OUTCOME_RECEIPT:
        outcome_record = map_receipt_to_wal_adapter_record(clean_outcome_evidence, 2)
    elif outcome_type == _OUTCOME_FAILURE:
        outcome_record = map_failure_to_wal_adapter_record(clean_outcome_evidence, 2)
    else:
        raise ValueError("outcome_type_invalid")

    return (
        map_admission_to_wal_adapter_record(wrapper_input.admission_evidence, 1),
        outcome_record,
        map_verifier_binding_to_wal_adapter_record(
            wrapper_input.verifier_binding_evidence,
            3,
        ),
        map_preflight_result_to_wal_adapter_record(
            wrapper_input.preflight_result_evidence,
            4,
        ),
    )


def run_minimal_controlled_wal_gated_preflight_wrapper(
    wrapper_input: MinimalControlledWalGatedPreflightInput,
    append_callable: Callable[[MinimalControlledWalAdapterRecord], object],
) -> MinimalControlledWalGatedPreflightResult:
    _require_wrapper_input(wrapper_input)
    if not callable(append_callable):
        raise ValueError("append_callable_required")

    records = build_minimal_controlled_wal_gated_preflight_records(wrapper_input)
    append_results = append_minimal_controlled_wal_adapter_records(records, append_callable)
    append_plan = prepare_append_before_execution_plan(records, append_results)
    integration_result = replay_minimal_controlled_wal_adapter_records(records)

    append_rejection_reasons = tuple(
        reason
        for result in append_results
        if not result.accepted
        for reason in result.rejection_reasons
    )
    rejection_reasons = _dedupe_strings(
        append_rejection_reasons
        + tuple(append_plan.rejection_reasons)
        + (() if integration_result.accepted else tuple(integration_result.rejection_reasons))
    )
    execution_may_proceed = (
        append_plan.execution_may_proceed
        and not append_rejection_reasons
        and integration_result.accepted
        and not rejection_reasons
    )
    accepted = execution_may_proceed and not rejection_reasons

    return MinimalControlledWalGatedPreflightResult(
        wrapper_result_id=_stable_id(
            "wal-gated-preflight-wrapper-result",
            {
                "wrapper_input_hash": wrapper_input.wrapper_input_hash,
                "append_plan_hash": append_plan.append_plan_hash,
                "integration_result_hash": integration_result.integration_result_hash,
                "accepted": accepted,
                "rejection_reasons": rejection_reasons,
            },
        ),
        wal_gated_preflight_wrapper_version=WAL_GATED_PREFLIGHT_WRAPPER_VERSION,
        task_id=wrapper_input.task_id,
        run_id=wrapper_input.run_id,
        preflight_id=wrapper_input.preflight_id,
        ordered_record_hashes=tuple(record.record_hash for record in records),
        append_result_hashes=tuple(result.append_result_hash for result in append_results),
        append_plan_hash=append_plan.append_plan_hash,
        batch_hash=integration_result.batch_hash,
        replay_result_hash=integration_result.replay_result_hash,
        integration_result_hash=integration_result.integration_result_hash,
        execution_may_proceed=execution_may_proceed,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
    )


def minimal_controlled_wal_gated_preflight_input_hash(
    wrapper_input: MinimalControlledWalGatedPreflightInput | Mapping[str, object],
) -> str:
    return _hash_wrapper(wrapper_input, "wrapper_input_hash")


def minimal_controlled_wal_gated_preflight_result_hash(
    result: MinimalControlledWalGatedPreflightResult | Mapping[str, object],
) -> str:
    return _hash_wrapper(result, "wrapper_result_hash")


def _validated_evidence_mapping(
    value: object,
    field_name: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(field_name + "_must_be_mapping")
    evidence = dict(value)
    forbidden = sorted(_FORBIDDEN_EVIDENCE_FIELDS.intersection(evidence))
    if forbidden:
        raise ValueError("wal_gated_preflight_evidence_field_forbidden:" + ",".join(forbidden))
    return evidence


def _require_matching_identity(
    evidence: Mapping[str, object],
    wrapper_input: MinimalControlledWalGatedPreflightInput,
    field_name: str,
) -> None:
    for identity_field in ("task_id", "run_id", "preflight_id"):
        if identity_field in evidence and evidence[identity_field] != getattr(wrapper_input, identity_field):
            raise ValueError(field_name + "_" + identity_field + "_mismatch")


def _outcome_type(evidence: Mapping[str, object]) -> str:
    outcome_values = tuple(
        value
        for value in (evidence.get("outcome_type"), evidence.get("record_type"))
        if value is not None
    )
    if not outcome_values:
        raise ValueError("outcome_type_required")
    for value in outcome_values:
        if value not in {_OUTCOME_RECEIPT, _OUTCOME_FAILURE}:
            raise ValueError("outcome_type_invalid")
    if len(set(outcome_values)) != 1:
        raise ValueError("outcome_type_mismatch")
    return str(outcome_values[0])


def _hash_wrapper(value: object, hash_field: str) -> str:
    data = _wrapper_dict(value)
    data.pop(hash_field, None)
    return "sha256:" + _sha256_hex(_canonical_json(data))


def _wrapper_dict(value: object) -> dict[str, object]:
    if hasattr(value, "__dataclass_fields__"):
        data = asdict(value)
    elif isinstance(value, Mapping):
        data = dict(value)
    else:
        raise TypeError("wrapper value must be a dataclass or mapping")
    return _json_ready(data)


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    return prefix + ":" + _sha256_hex(_canonical_json(_json_ready(payload)))[:24]


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if not current:
        object.__setattr__(target, field_name, expected)
        return
    if current != expected:
        raise ValueError(field_name + "_mismatch")


def _require_wrapper_input(value: object) -> None:
    if not isinstance(value, MinimalControlledWalGatedPreflightInput):
        raise ValueError("wal_gated_preflight_input_required")


def _require_wrapper_version(value: object) -> None:
    _require_string(value, "wal_gated_preflight_wrapper_version")
    if value != WAL_GATED_PREFLIGHT_WRAPPER_VERSION:
        raise ValueError("wal_gated_preflight_wrapper_version_mismatch")


def _require_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(field_name + "_required")


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(field_name + "_must_be_bool")


def _string_tuple(
    values: Sequence[str],
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_string_sequence")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(field_name + "_cannot_contain_empty_string")
        normalized.append(value)
    if not normalized and allow_empty:
        return ()
    return tuple(normalized)


def _hash_tuple(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_hash_sequence")
    if not values:
        raise ValueError(field_name + "_required")
    normalized: list[str] = []
    for value in values:
        _validate_hash_value(value, field_name, allow_empty=False)
        normalized.append(value)
    return tuple(normalized)


def _validate_hash_value(value: object, field_name: str, *, allow_empty: bool) -> None:
    if not isinstance(value, str):
        raise ValueError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return
        raise ValueError(field_name + "_required")
    prefix = "sha256:"
    digest = value[len(prefix) :]
    if not value.startswith(prefix) or len(digest) != 64 or not _is_lower_hex(digest):
        raise ValueError(field_name + "_must_be_sha256")


def _is_lower_hex(value: str) -> bool:
    return all(character in "0123456789abcdef" for character in value)


def _dedupe_strings(values: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return tuple(ordered)
