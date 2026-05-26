"""Pure WAL adapter evidence integration for Minimal Controlled Execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
from typing import Callable, Mapping, Sequence

from kernel.execution.minimal_controlled_wal_adapter_contract import (
    WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES,
    WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES,
    WAL_ADAPTER_VERSION,
    MinimalControlledWalAdapterBatch,
    MinimalControlledWalAdapterRecord,
    minimal_controlled_wal_adapter_batch_hash,
    replay_wal_adapter_batch,
    validate_wal_adapter_batch,
)

__all__ = [
    "WAL_ADAPTER_INTEGRATION_VERSION",
    "MinimalControlledWalAdapterAppendResult",
    "MinimalControlledWalAdapterAppendPlan",
    "MinimalControlledWalAdapterIntegrationResult",
    "map_admission_to_wal_adapter_record",
    "map_receipt_to_wal_adapter_record",
    "map_failure_to_wal_adapter_record",
    "map_verifier_binding_to_wal_adapter_record",
    "map_preflight_result_to_wal_adapter_record",
    "build_minimal_controlled_wal_adapter_batch",
    "replay_minimal_controlled_wal_adapter_records",
    "append_minimal_controlled_wal_adapter_record",
    "append_minimal_controlled_wal_adapter_records",
    "prepare_append_before_execution_plan",
]

WAL_ADAPTER_INTEGRATION_VERSION = "minimal_controlled_wal_adapter_integration_v1"

_OPTIONAL_PREFLIGHT_CHILD_HASH_FIELDS = frozenset({"child_receipt_hashes", "child_failure_bundle_hashes"})

_DEFAULT_CREATED_AT = "1970-01-01T00:00:00Z"
_PREFLIGHT_COMMAND_ID = "minimal_controlled_preflight"
_FORBIDDEN_EVIDENCE_FIELDS = (
    WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES | WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES
)
_OPTIONAL_HASH_FIELDS = (
    "request_hash",
    "decision_hash",
    "admission_record_hash",
    "receipt_hash",
    "failure_bundle_hash",
    "verifier_input_hash",
    "verifier_binding_hash",
    "preflight_result_hash",
    "record_hash",
)
_PREFLIGHT_SEQUENCE_FIELDS = (
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
)
_PREFLIGHT_HASH_SEQUENCE_FIELDS = tuple(
    field_name
    for field_name in _PREFLIGHT_SEQUENCE_FIELDS
    if field_name != "ordered_command_ids"
)
_EXPECTED_INTEGRATION_ORDER = (
    "EXECUTION_ADMISSION",
    ("EXECUTION_RECEIPT", "EXECUTION_FAILURE"),
    "EXECUTION_VERIFIER_BINDING",
    "PREFLIGHT_RESULT",
)


class _IntegrationDictMixin:
    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MinimalControlledWalAdapterAppendResult(_IntegrationDictMixin):
    append_result_id: str
    wal_adapter_integration_version: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    attempted_record_hash: str
    append_result_hash: str = ""

    def __post_init__(self) -> None:
        _require_string(self.append_result_id, "append_result_id")
        _require_integration_version(self.wal_adapter_integration_version)
        _require_bool(self.accepted, "accepted")
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(
                self.rejection_reasons,
                "rejection_reasons",
                allow_empty=True,
            ),
        )
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted_append_result_cannot_have_rejection_reasons")
        if not self.accepted and not self.rejection_reasons:
            raise ValueError("rejected_append_result_requires_rejection_reasons")
        _validate_hash_value(
            self.attempted_record_hash,
            "attempted_record_hash",
            allow_empty=False,
        )
        _validate_hash_value(
            self.append_result_hash,
            "append_result_hash",
            allow_empty=True,
        )
        _install_or_verify_hash(
            self,
            "append_result_hash",
            minimal_controlled_wal_adapter_append_result_hash,
        )


@dataclass(frozen=True)
class MinimalControlledWalAdapterAppendPlan(_IntegrationDictMixin):
    append_plan_id: str
    wal_adapter_integration_version: str
    task_id: str
    run_id: str
    preflight_id: str
    ordered_record_hashes: tuple[str, ...]
    append_before_execution: bool
    execution_may_proceed: bool
    rejection_reasons: tuple[str, ...]
    append_plan_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "append_plan_id",
            "task_id",
            "run_id",
            "preflight_id",
        ):
            _require_string(getattr(self, field_name), field_name)
        _require_integration_version(self.wal_adapter_integration_version)
        object.__setattr__(
            self,
            "ordered_record_hashes",
            _hash_tuple(
                self.ordered_record_hashes,
                "ordered_record_hashes",
                allow_empty_sequence=True,
            ),
        )
        _require_bool(self.append_before_execution, "append_before_execution")
        _require_bool(self.execution_may_proceed, "execution_may_proceed")
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(
                self.rejection_reasons,
                "rejection_reasons",
                allow_empty=True,
            ),
        )
        if self.execution_may_proceed and self.rejection_reasons:
            raise ValueError("execution_may_proceed_cannot_have_rejection_reasons")
        if not self.execution_may_proceed and not self.rejection_reasons:
            raise ValueError("blocked_append_plan_requires_rejection_reasons")
        _validate_hash_value(
            self.append_plan_hash,
            "append_plan_hash",
            allow_empty=True,
        )
        _install_or_verify_hash(
            self,
            "append_plan_hash",
            minimal_controlled_wal_adapter_append_plan_hash,
        )


@dataclass(frozen=True)
class MinimalControlledWalAdapterIntegrationResult(_IntegrationDictMixin):
    integration_result_id: str
    wal_adapter_integration_version: str
    task_id: str
    run_id: str
    preflight_id: str
    ordered_record_hashes: tuple[str, ...]
    batch_hash: str
    replay_result_hash: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    integration_result_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "integration_result_id",
            "task_id",
            "run_id",
            "preflight_id",
        ):
            _require_string(getattr(self, field_name), field_name)
        _require_integration_version(self.wal_adapter_integration_version)
        object.__setattr__(
            self,
            "ordered_record_hashes",
            _hash_tuple(self.ordered_record_hashes, "ordered_record_hashes"),
        )
        for field_name in (
            "batch_hash",
            "replay_result_hash",
            "integration_result_hash",
        ):
            _validate_hash_value(
                getattr(self, field_name),
                field_name,
                allow_empty=field_name == "integration_result_hash",
            )
        _require_bool(self.accepted, "accepted")
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(
                self.rejection_reasons,
                "rejection_reasons",
                allow_empty=True,
            ),
        )
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted_integration_result_cannot_have_rejection_reasons")
        if not self.accepted and not self.rejection_reasons:
            raise ValueError("rejected_integration_result_requires_rejection_reasons")
        _install_or_verify_hash(
            self,
            "integration_result_hash",
            minimal_controlled_wal_adapter_integration_result_hash,
        )


def minimal_controlled_wal_adapter_append_result_hash(
    result: MinimalControlledWalAdapterAppendResult | Mapping[str, object],
) -> str:
    return _hash_integration(result, "append_result_hash")


def minimal_controlled_wal_adapter_append_plan_hash(
    plan: MinimalControlledWalAdapterAppendPlan | Mapping[str, object],
) -> str:
    return _hash_integration(plan, "append_plan_hash")


def minimal_controlled_wal_adapter_integration_result_hash(
    result: MinimalControlledWalAdapterIntegrationResult | Mapping[str, object],
) -> str:
    return _hash_integration(result, "integration_result_hash")


def map_admission_to_wal_adapter_record(
    evidence: Mapping[str, object] | object,
    sequence: int,
) -> MinimalControlledWalAdapterRecord:
    data = _validated_evidence(
        evidence,
        sequence,
        required_strings=("task_id", "run_id", "command_id"),
        required_hashes=("request_hash", "decision_hash", "admission_record_hash"),
    )
    return _wal_adapter_record(
        data,
        record_type="EXECUTION_ADMISSION",
        sequence=sequence,
        execution_performed=False,
        hash_fields={
            "request_hash": str(data["request_hash"]),
            "decision_hash": str(data["decision_hash"]),
            "admission_record_hash": str(data["admission_record_hash"]),
        },
    )


def map_receipt_to_wal_adapter_record(
    evidence: Mapping[str, object] | object,
    sequence: int,
) -> MinimalControlledWalAdapterRecord:
    data = _validated_evidence(
        evidence,
        sequence,
        required_strings=("task_id", "run_id", "command_id"),
        required_hashes=(
            "request_hash",
            "decision_hash",
            "admission_record_hash",
            "receipt_hash",
        ),
    )
    hash_fields = {
        "request_hash": str(data["request_hash"]),
        "decision_hash": str(data["decision_hash"]),
        "admission_record_hash": str(data["admission_record_hash"]),
        "receipt_hash": str(data["receipt_hash"]),
    }
    for field_name in ("verifier_input_hash", "verifier_binding_hash"):
        if data.get(field_name):
            hash_fields[field_name] = str(data[field_name])
    return _wal_adapter_record(
        data,
        record_type="EXECUTION_RECEIPT",
        sequence=sequence,
        execution_performed=True,
        hash_fields=hash_fields,
    )


def map_failure_to_wal_adapter_record(
    evidence: Mapping[str, object] | object,
    sequence: int,
) -> MinimalControlledWalAdapterRecord:
    data = _validated_evidence(
        evidence,
        sequence,
        required_strings=("task_id", "run_id", "command_id"),
        required_hashes=("request_hash", "decision_hash", "failure_bundle_hash"),
    )
    return _wal_adapter_record(
        data,
        record_type="EXECUTION_FAILURE",
        sequence=sequence,
        execution_performed=_optional_bool(data, "execution_performed", default=False),
        hash_fields={
            "request_hash": str(data["request_hash"]),
            "decision_hash": str(data["decision_hash"]),
            "failure_bundle_hash": str(data["failure_bundle_hash"]),
        },
    )


def map_verifier_binding_to_wal_adapter_record(
    evidence: Mapping[str, object] | object,
    sequence: int,
) -> MinimalControlledWalAdapterRecord:
    data = _validated_evidence(
        evidence,
        sequence,
        required_strings=("task_id", "run_id", "command_id"),
        required_hashes=("verifier_binding_hash",),
    )
    hash_fields = {"verifier_binding_hash": str(data["verifier_binding_hash"])}
    for field_name in (
        "request_hash",
        "decision_hash",
        "admission_record_hash",
        "receipt_hash",
        "failure_bundle_hash",
        "verifier_input_hash",
    ):
        if data.get(field_name):
            hash_fields[field_name] = str(data[field_name])
    return _wal_adapter_record(
        data,
        record_type="EXECUTION_VERIFIER_BINDING",
        sequence=sequence,
        execution_performed=_optional_bool(data, "execution_performed", default=False),
        hash_fields=hash_fields,
    )


def map_preflight_result_to_wal_adapter_record(
    evidence: Mapping[str, object] | object,
    sequence: int,
) -> MinimalControlledWalAdapterRecord:
    data = _validated_evidence(
        evidence,
        sequence,
        required_strings=("task_id", "run_id", "preflight_id"),
        required_hashes=("preflight_result_hash",),
        required_sequences=_PREFLIGHT_SEQUENCE_FIELDS,
        required_bools=("execution_performed",),
    )
    sequence_fields = {
        field_name: _string_sequence(data, field_name, allow_empty_item=field_name in _OPTIONAL_PREFLIGHT_CHILD_HASH_FIELDS)
        for field_name in _PREFLIGHT_SEQUENCE_FIELDS
    }
    return _wal_adapter_record(
        data,
        record_type="PREFLIGHT_RESULT",
        sequence=sequence,
        command_id=_PREFLIGHT_COMMAND_ID,
        preflight_id=str(data["preflight_id"]),
        execution_performed=_optional_bool(data, "execution_performed", default=False),
        hash_fields={"preflight_result_hash": str(data["preflight_result_hash"])},
        sequence_fields=sequence_fields,
    )


def build_minimal_controlled_wal_adapter_batch(
    records: Sequence[MinimalControlledWalAdapterRecord],
) -> MinimalControlledWalAdapterBatch:
    ordered_records = _ordered_records(records)
    _validate_integration_record_order(ordered_records)
    first = ordered_records[0]
    batch = MinimalControlledWalAdapterBatch(
        wal_adapter_batch_id=_stable_id(
            "wal-adapter-batch",
            {
                "ordered_record_hashes": tuple(
                    record.record_hash for record in ordered_records
                ),
                "task_id": first.task_id,
                "run_id": first.run_id,
                "preflight_id": first.preflight_id,
            },
        ),
        wal_adapter_version=WAL_ADAPTER_VERSION,
        task_id=first.task_id,
        run_id=first.run_id,
        preflight_id=first.preflight_id,
        ordered_record_hashes=tuple(record.record_hash for record in ordered_records),
        record_count=len(ordered_records),
        first_sequence=ordered_records[0].sequence,
        last_sequence=ordered_records[-1].sequence,
    )
    validate_wal_adapter_batch(batch, ordered_records)
    return batch


def replay_minimal_controlled_wal_adapter_records(
    records: Sequence[MinimalControlledWalAdapterRecord],
) -> MinimalControlledWalAdapterIntegrationResult:
    try:
        ordered_records = _ordered_records(records)
        first = ordered_records[0]
        ordered_record_hashes = tuple(record.record_hash for record in ordered_records)
        batch = build_minimal_controlled_wal_adapter_batch(ordered_records)
        replay_result = replay_wal_adapter_batch(batch, ordered_records)
        return _integration_result(
            task_id=first.task_id,
            run_id=first.run_id,
            preflight_id=first.preflight_id,
            ordered_record_hashes=ordered_record_hashes,
            batch_hash=batch.batch_hash,
            replay_result_hash=replay_result.replay_result_hash,
            accepted=replay_result.accepted,
            rejection_reasons=replay_result.rejection_reasons,
        )
    except ValueError as exc:
        ordered_records = _best_effort_ordered_records(records)
        ordered_record_hashes = tuple(record.record_hash for record in ordered_records)
        first = ordered_records[0] if ordered_records else None
        rejection_reasons = (str(exc),)
        return _integration_result(
            task_id=first.task_id if first else "unknown-task",
            run_id=first.run_id if first else "unknown-run",
            preflight_id=first.preflight_id if first else "unknown-preflight",
            ordered_record_hashes=ordered_record_hashes or (_placeholder_hash("no-records"),),
            batch_hash=_placeholder_hash("batch-unavailable", rejection_reasons),
            replay_result_hash=_placeholder_hash("replay-unavailable", rejection_reasons),
            accepted=False,
            rejection_reasons=rejection_reasons,
        )


def append_minimal_controlled_wal_adapter_record(
    record: MinimalControlledWalAdapterRecord,
    append_callable: Callable[[MinimalControlledWalAdapterRecord], object],
) -> MinimalControlledWalAdapterAppendResult:
    _require_record(record)
    try:
        append_callable(record)
    except Exception as exc:  # noqa: BLE001 - fail closed for any append failure.
        return _append_result(
            record.record_hash,
            accepted=False,
            rejection_reasons=(
                "WAL_ADAPTER_APPEND_FAILED",
                "EXECUTION_NOT_ATTEMPTED",
                type(exc).__name__,
            ),
        )
    return _append_result(record.record_hash, accepted=True, rejection_reasons=())


def append_minimal_controlled_wal_adapter_records(
    records: Sequence[MinimalControlledWalAdapterRecord],
    append_callable: Callable[[MinimalControlledWalAdapterRecord], object],
) -> tuple[MinimalControlledWalAdapterAppendResult, ...]:
    results: list[MinimalControlledWalAdapterAppendResult] = []
    for record in _ordered_records(records):
        result = append_minimal_controlled_wal_adapter_record(record, append_callable)
        results.append(result)
        if not result.accepted:
            break
    return tuple(results)


def prepare_append_before_execution_plan(
    records: Sequence[MinimalControlledWalAdapterRecord],
    append_results: Sequence[MinimalControlledWalAdapterAppendResult],
) -> MinimalControlledWalAdapterAppendPlan:
    ordered_records = _best_effort_ordered_records(records)
    ordered_record_hashes = tuple(record.record_hash for record in ordered_records)
    first = ordered_records[0] if ordered_records else None
    rejection_reasons: list[str] = []
    try:
        checked_records = _ordered_records(records)
        _validate_integration_record_order(checked_records)
    except ValueError as exc:
        rejection_reasons.append(str(exc))

    normalized_results = tuple(append_results)
    for result in normalized_results:
        if not isinstance(result, MinimalControlledWalAdapterAppendResult):
            rejection_reasons.append("append_result_type_invalid")

    admission_result = normalized_results[0] if normalized_results else None
    append_before_execution = False
    admission_append_succeeded = False
    if first is None:
        rejection_reasons.append("admission_record_required")
    elif admission_result is None:
        rejection_reasons.append("admission_append_result_required")
    elif isinstance(admission_result, MinimalControlledWalAdapterAppendResult):
        append_before_execution = admission_result.attempted_record_hash == first.record_hash
        if not append_before_execution:
            rejection_reasons.append("admission_append_result_mismatch")
        admission_append_succeeded = append_before_execution and admission_result.accepted
        if not admission_result.accepted:
            rejection_reasons.extend(admission_result.rejection_reasons)

    if not admission_append_succeeded and any(
        record.record_type == "EXECUTION_RECEIPT" and record.execution_performed
        for record in ordered_records
    ):
        rejection_reasons.append("EXECUTION_PERFORMED_CLAIM_BLOCKED")

    rejection_reasons = list(dict.fromkeys(rejection_reasons))
    execution_may_proceed = admission_append_succeeded and not rejection_reasons
    if not rejection_reasons and not execution_may_proceed:
        rejection_reasons.append("EXECUTION_NOT_ATTEMPTED")

    return MinimalControlledWalAdapterAppendPlan(
        append_plan_id=_stable_id(
            "wal-adapter-append-plan",
            {
                "ordered_record_hashes": ordered_record_hashes,
                "append_result_hashes": tuple(
                    result.append_result_hash
                    for result in normalized_results
                    if isinstance(result, MinimalControlledWalAdapterAppendResult)
                ),
            },
        ),
        wal_adapter_integration_version=WAL_ADAPTER_INTEGRATION_VERSION,
        task_id=first.task_id if first else "unknown-task",
        run_id=first.run_id if first else "unknown-run",
        preflight_id=first.preflight_id if first else "unknown-preflight",
        ordered_record_hashes=ordered_record_hashes or (_placeholder_hash("no-records"),),
        append_before_execution=append_before_execution,
        execution_may_proceed=execution_may_proceed,
        rejection_reasons=tuple(rejection_reasons),
    )


def _wal_adapter_record(
    data: Mapping[str, object],
    *,
    record_type: str,
    sequence: int,
    execution_performed: bool,
    hash_fields: Mapping[str, str],
    command_id: str | None = None,
    preflight_id: str | None = None,
    sequence_fields: Mapping[str, tuple[str, ...]] | None = None,
) -> MinimalControlledWalAdapterRecord:
    payload: dict[str, object] = {
        "wal_adapter_record_id": _stable_id(
            "wal-adapter-record",
            {
                "record_type": record_type,
                "task_id": str(data["task_id"]),
                "run_id": str(data["run_id"]),
                "command_id": command_id or str(data["command_id"]),
                "sequence": sequence,
            },
        ),
        "wal_adapter_version": WAL_ADAPTER_VERSION,
        "record_type": record_type,
        "task_id": str(data["task_id"]),
        "run_id": str(data["run_id"]),
        "command_id": command_id or str(data["command_id"]),
        "preflight_id": preflight_id or _evidence_preflight_id(data),
        "sequence": sequence,
        "created_at": _optional_string(data, "created_at", default=_DEFAULT_CREATED_AT),
        "request_hash": "",
        "decision_hash": "",
        "admission_record_hash": "",
        "receipt_hash": "",
        "failure_bundle_hash": "",
        "verifier_input_hash": "",
        "verifier_binding_hash": "",
        "preflight_result_hash": "",
        "ordered_command_ids": (),
        "child_request_hashes": (),
        "child_decision_hashes": (),
        "child_admission_hashes": (),
        "child_receipt_hashes": (),
        "child_failure_bundle_hashes": (),
        "child_verifier_input_hashes": (),
        "child_verifier_binding_hashes": (),
        "pre_snapshot_hashes": (),
        "post_snapshot_hashes": (),
        "execution_performed": execution_performed,
    }
    payload.update(hash_fields)
    if sequence_fields:
        payload.update(sequence_fields)
    if data.get("record_hash"):
        payload["record_hash"] = str(data["record_hash"])
    return MinimalControlledWalAdapterRecord(**payload)


def _validated_evidence(
    evidence: Mapping[str, object] | object,
    sequence: int,
    *,
    required_strings: Sequence[str],
    required_hashes: Sequence[str],
    required_sequences: Sequence[str] = (),
    required_bools: Sequence[str] = (),
) -> dict[str, object]:
    _require_positive_int(sequence, "sequence")
    data = _evidence_dict(evidence)
    # _required_hash_missing_guard_v1
    for field_name in required_hashes:
        value = data.get(field_name)
        if not isinstance(value, str) or not value:
            raise ValueError(field_name + "_required")

    forbidden = sorted(_FORBIDDEN_EVIDENCE_FIELDS.intersection(data))
    if forbidden:
        raise ValueError("wal_adapter_evidence_field_forbidden:" + ",".join(forbidden))
    if "record_type" in data:
        raise ValueError("record_type_override_not_allowed")
    for field_name in required_strings:
        _require_string(data.get(field_name), field_name)
    for field_name in required_hashes:
        _validate_hash_value(data.get(field_name), field_name, allow_empty=False)
    for field_name in _OPTIONAL_HASH_FIELDS:
        if field_name in data and data[field_name]:
            _validate_hash_value(data[field_name], field_name, allow_empty=False)
    for field_name in required_sequences:
        _string_sequence(data, field_name, allow_empty_item=field_name in _OPTIONAL_PREFLIGHT_CHILD_HASH_FIELDS)
    for field_name in required_bools:
        _require_bool(data.get(field_name), field_name)
    return data


def _evidence_dict(evidence: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(evidence, Mapping):
        return dict(evidence)
    if hasattr(evidence, "as_dict"):
        result = evidence.as_dict()  # type: ignore[attr-defined]
        if not isinstance(result, Mapping):
            raise ValueError("evidence_as_dict_must_return_mapping")
        return dict(result)
    if is_dataclass(evidence):
        return asdict(evidence)
    raise TypeError("evidence_must_be_mapping_or_as_dict")


def _integration_result(
    *,
    task_id: str,
    run_id: str,
    preflight_id: str,
    ordered_record_hashes: tuple[str, ...],
    batch_hash: str,
    replay_result_hash: str,
    accepted: bool,
    rejection_reasons: tuple[str, ...],
) -> MinimalControlledWalAdapterIntegrationResult:
    return MinimalControlledWalAdapterIntegrationResult(
        integration_result_id=_stable_id(
            "wal-adapter-integration-result",
            {
                "batch_hash": batch_hash,
                "replay_result_hash": replay_result_hash,
                "accepted": accepted,
                "rejection_reasons": rejection_reasons,
            },
        ),
        wal_adapter_integration_version=WAL_ADAPTER_INTEGRATION_VERSION,
        task_id=task_id,
        run_id=run_id,
        preflight_id=preflight_id,
        ordered_record_hashes=ordered_record_hashes,
        batch_hash=batch_hash,
        replay_result_hash=replay_result_hash,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
    )


def _append_result(
    attempted_record_hash: str,
    *,
    accepted: bool,
    rejection_reasons: tuple[str, ...],
) -> MinimalControlledWalAdapterAppendResult:
    return MinimalControlledWalAdapterAppendResult(
        append_result_id=_stable_id(
            "wal-adapter-append-result",
            {
                "attempted_record_hash": attempted_record_hash,
                "accepted": accepted,
                "rejection_reasons": rejection_reasons,
            },
        ),
        wal_adapter_integration_version=WAL_ADAPTER_INTEGRATION_VERSION,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
        attempted_record_hash=attempted_record_hash,
    )


def _validate_integration_record_order(
    records: tuple[MinimalControlledWalAdapterRecord, ...],
) -> None:
    if len(records) != 4:
        raise ValueError("wal_adapter_integration_record_count_mismatch")
    record_types = tuple(record.record_type for record in records)
    if record_types[0] != _EXPECTED_INTEGRATION_ORDER[0]:
        raise ValueError("admission_must_be_first")
    if record_types[3] != _EXPECTED_INTEGRATION_ORDER[3]:
        raise ValueError("preflight_result_must_be_last")
    if record_types[1] not in _EXPECTED_INTEGRATION_ORDER[1]:
        raise ValueError("receipt_or_failure_must_follow_admission")
    if record_types[2] != _EXPECTED_INTEGRATION_ORDER[2]:
        raise ValueError("verifier_binding_must_follow_outcome")


def _ordered_records(
    records: Sequence[MinimalControlledWalAdapterRecord],
) -> tuple[MinimalControlledWalAdapterRecord, ...]:
    ordered_records = _best_effort_ordered_records(records)
    if not ordered_records:
        raise ValueError("records_required")
    for record in ordered_records:
        _require_record(record)
    sequences = tuple(record.sequence for record in ordered_records)
    if len(set(sequences)) != len(sequences):
        raise ValueError("duplicate_sequence")
    return ordered_records


def _best_effort_ordered_records(
    records: Sequence[MinimalControlledWalAdapterRecord],
) -> tuple[MinimalControlledWalAdapterRecord, ...]:
    return tuple(
        sorted(
            (record for record in tuple(records) if isinstance(record, MinimalControlledWalAdapterRecord)),
            key=lambda record: record.sequence,
        )
    )


def _require_record(record: object) -> None:
    if not isinstance(record, MinimalControlledWalAdapterRecord):
        raise ValueError("wal_adapter_record_required")


def _evidence_preflight_id(data: Mapping[str, object]) -> str:
    if data.get("preflight_id"):
        return _optional_string(data, "preflight_id", default="")
    return "preflight-" + str(data["run_id"])


def _optional_string(
    data: Mapping[str, object],
    field_name: str,
    *,
    default: str,
) -> str:
    if field_name not in data:
        return default
    value = data[field_name]
    _require_string(value, field_name)
    return str(value)


def _optional_bool(
    data: Mapping[str, object],
    field_name: str,
    *,
    default: bool,
) -> bool:
    if field_name not in data:
        return default
    _require_bool(data[field_name], field_name)
    return bool(data[field_name])


def _string_sequence(
    data: Mapping[str, object],
    field_name: str,
    *,
    allow_empty_item: bool = False,
) -> tuple[str, ...]:
    raw = data.get(field_name)
    if not isinstance(raw, (list, tuple)) or isinstance(raw, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_string_sequence")

    values: list[str] = []
    for value in raw:
        if not isinstance(value, str):
            raise ValueError(field_name + "_must_be_ordered_string_sequence")
        if not value and not allow_empty_item:
            raise ValueError(field_name + "_must_be_ordered_string_sequence")
        values.append(value)

    return tuple(values)


def _hash_integration(value: object, hash_field: str) -> str:
    data = _integration_dict(value)
    data.pop(hash_field, None)
    return "sha256:" + _sha256_hex(_canonical_json(data))


def _integration_dict(value: object) -> dict[str, object]:
    if hasattr(value, "__dataclass_fields__"):
        data = asdict(value)
    elif isinstance(value, Mapping):
        data = dict(value)
    else:
        raise TypeError("integration value must be a dataclass or mapping")
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


def _placeholder_hash(label: str, extra: object = "") -> str:
    return "sha256:" + _sha256_hex(
        _canonical_json({"label": label, "extra": _json_ready(extra)})
    )


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


def _require_integration_version(value: object) -> None:
    _require_string(value, "wal_adapter_integration_version")
    if value != WAL_ADAPTER_INTEGRATION_VERSION:
        raise ValueError("wal_adapter_integration_version_mismatch")


def _require_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(field_name + "_required")


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(field_name + "_must_be_bool")


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(field_name + "_must_be_int")
    if value <= 0:
        raise ValueError(field_name + "_must_be_positive")


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


def _hash_tuple(
    values: Sequence[str],
    field_name: str,
    *,
    allow_empty_sequence: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_hash_sequence")
    if not values and not allow_empty_sequence:
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
