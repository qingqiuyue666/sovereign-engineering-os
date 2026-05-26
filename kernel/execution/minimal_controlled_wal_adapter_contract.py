"""Digest-only WAL adapter contracts for Minimal Controlled Execution evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence

__all__ = [
    "WAL_ADAPTER_VERSION",
    "WAL_ADAPTER_REPLAY_POLICY_VERSION",
    "WAL_ADAPTER_RECORD_TYPES",
    "WAL_ADAPTER_RECORD_FIELDS",
    "WAL_ADAPTER_BATCH_FIELDS",
    "WAL_ADAPTER_REPLAY_INPUT_FIELDS",
    "WAL_ADAPTER_REPLAY_RESULT_FIELDS",
    "WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES",
    "WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES",
    "MinimalControlledWalAdapterRecord",
    "MinimalControlledWalAdapterBatch",
    "MinimalControlledWalAdapterReplayInput",
    "MinimalControlledWalAdapterReplayResult",
    "minimal_controlled_wal_adapter_record_hash",
    "minimal_controlled_wal_adapter_batch_hash",
    "minimal_controlled_wal_adapter_replay_input_hash",
    "minimal_controlled_wal_adapter_replay_result_hash",
    "validate_wal_adapter_record",
    "validate_wal_adapter_batch",
    "replay_wal_adapter_batch",
]

WAL_ADAPTER_VERSION = "minimal_controlled_wal_adapter_contract_v1"
WAL_ADAPTER_REPLAY_POLICY_VERSION = "minimal_controlled_wal_adapter_replay_policy_v1"

WAL_ADAPTER_RECORD_TYPES = frozenset(
    {
        "EXECUTION_ADMISSION",
        "EXECUTION_RECEIPT",
        "EXECUTION_FAILURE",
        "EXECUTION_VERIFIER_BINDING",
        "PREFLIGHT_RESULT",
    }
)

WAL_ADAPTER_RECORD_FIELDS = (
    "wal_adapter_record_id",
    "wal_adapter_version",
    "record_type",
    "task_id",
    "run_id",
    "command_id",
    "preflight_id",
    "sequence",
    "created_at",
    "request_hash",
    "decision_hash",
    "admission_record_hash",
    "receipt_hash",
    "failure_bundle_hash",
    "verifier_input_hash",
    "verifier_binding_hash",
    "preflight_result_hash",
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
    "execution_performed",
    "record_hash",
)

WAL_ADAPTER_BATCH_FIELDS = (
    "wal_adapter_batch_id",
    "wal_adapter_version",
    "task_id",
    "run_id",
    "preflight_id",
    "ordered_record_hashes",
    "record_count",
    "first_sequence",
    "last_sequence",
    "batch_hash",
)

WAL_ADAPTER_REPLAY_INPUT_FIELDS = (
    "replay_input_id",
    "wal_adapter_version",
    "batch_hash",
    "ordered_record_hashes",
    "expected_record_count",
    "replay_policy_version",
    "replay_input_hash",
)

WAL_ADAPTER_REPLAY_RESULT_FIELDS = (
    "replay_result_id",
    "wal_adapter_version",
    "accepted",
    "rejection_reasons",
    "batch_hash",
    "replay_input_hash",
    "replay_result_hash",
)

WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES = frozenset(
    {
        "stdout",
        "stderr",
        "raw_stdout",
        "raw_stderr",
        "stdout_text",
        "stderr_text",
        "command_line",
    }
)

WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES = frozenset(
    {
        "argv",
        "cwd",
        "env",
        "path",
        "executable",
        "timeout",
        "shell",
    }
)

_RECORD_EVIDENCE_HASH_FIELDS = (
    "request_hash",
    "decision_hash",
    "admission_record_hash",
    "receipt_hash",
    "failure_bundle_hash",
    "verifier_input_hash",
    "verifier_binding_hash",
    "preflight_result_hash",
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

_PREFLIGHT_OPTIONAL_CHILD_HASH_SEQUENCE_FIELDS = frozenset(
    {
        "child_receipt_hashes",
        "child_failure_bundle_hashes",
    }
)


class _ContractDictMixin:
    def as_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class MinimalControlledWalAdapterRecord(_ContractDictMixin):
    wal_adapter_record_id: str
    wal_adapter_version: str
    record_type: str
    task_id: str
    run_id: str
    command_id: str
    preflight_id: str
    sequence: int
    created_at: str
    request_hash: str
    decision_hash: str
    admission_record_hash: str
    receipt_hash: str
    failure_bundle_hash: str
    verifier_input_hash: str
    verifier_binding_hash: str
    preflight_result_hash: str
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
    execution_performed: bool
    record_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ordered_command_ids",
            _string_tuple(self.ordered_command_ids, "ordered_command_ids"),
        )
        for field_name in _PREFLIGHT_HASH_SEQUENCE_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _hash_tuple(
                    getattr(self, field_name),
                    field_name,
                    allow_empty_item=field_name
                    in _PREFLIGHT_OPTIONAL_CHILD_HASH_SEQUENCE_FIELDS,
                ),
            )
        _validate_record_shape_and_bindings(self)
        _install_or_verify_hash(
            self,
            "record_hash",
            minimal_controlled_wal_adapter_record_hash,
        )


@dataclass(frozen=True)
class MinimalControlledWalAdapterBatch(_ContractDictMixin):
    wal_adapter_batch_id: str
    wal_adapter_version: str
    task_id: str
    run_id: str
    preflight_id: str
    ordered_record_hashes: tuple[str, ...]
    record_count: int
    first_sequence: int
    last_sequence: int
    batch_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ordered_record_hashes",
            _hash_tuple(self.ordered_record_hashes, "ordered_record_hashes"),
        )
        _validate_batch_shape(self)
        _install_or_verify_hash(
            self,
            "batch_hash",
            minimal_controlled_wal_adapter_batch_hash,
        )


@dataclass(frozen=True)
class MinimalControlledWalAdapterReplayInput(_ContractDictMixin):
    replay_input_id: str
    wal_adapter_version: str
    batch_hash: str
    ordered_record_hashes: tuple[str, ...]
    expected_record_count: int
    replay_policy_version: str
    replay_input_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ordered_record_hashes",
            _hash_tuple(self.ordered_record_hashes, "ordered_record_hashes"),
        )
        _validate_replay_input_shape(self)
        _install_or_verify_hash(
            self,
            "replay_input_hash",
            minimal_controlled_wal_adapter_replay_input_hash,
        )


@dataclass(frozen=True)
class MinimalControlledWalAdapterReplayResult(_ContractDictMixin):
    replay_result_id: str
    wal_adapter_version: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    batch_hash: str
    replay_input_hash: str
    replay_result_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(
                self.rejection_reasons,
                "rejection_reasons",
                allow_empty=True,
            ),
        )
        _validate_replay_result_shape(self)
        _install_or_verify_hash(
            self,
            "replay_result_hash",
            minimal_controlled_wal_adapter_replay_result_hash,
        )


def minimal_controlled_wal_adapter_record_hash(
    record: MinimalControlledWalAdapterRecord | Mapping[str, object],
) -> str:
    return _hash_contract(record, "record_hash")


def minimal_controlled_wal_adapter_batch_hash(
    batch: MinimalControlledWalAdapterBatch | Mapping[str, object],
) -> str:
    return _hash_contract(batch, "batch_hash")


def minimal_controlled_wal_adapter_replay_input_hash(
    replay_input: MinimalControlledWalAdapterReplayInput | Mapping[str, object],
) -> str:
    return _hash_contract(replay_input, "replay_input_hash")


def minimal_controlled_wal_adapter_replay_result_hash(
    replay_result: MinimalControlledWalAdapterReplayResult | Mapping[str, object],
) -> str:
    return _hash_contract(replay_result, "replay_result_hash")


def validate_wal_adapter_record(record: MinimalControlledWalAdapterRecord) -> None:
    _validate_record_shape_and_bindings(record)
    expected = minimal_controlled_wal_adapter_record_hash(record)
    if record.record_hash != expected:
        raise ValueError("record_hash_mismatch")


def validate_wal_adapter_batch(
    batch: MinimalControlledWalAdapterBatch,
    records: Sequence[MinimalControlledWalAdapterRecord],
) -> None:
    _validate_batch_shape(batch)
    if batch.batch_hash != minimal_controlled_wal_adapter_batch_hash(batch):
        raise ValueError("batch_hash_mismatch")

    ordered_records = tuple(sorted(records, key=lambda record: record.sequence))
    if len(ordered_records) != batch.record_count:
        raise ValueError("record_count_mismatch")
    if not ordered_records:
        raise ValueError("records_required")

    for record in ordered_records:
        validate_wal_adapter_record(record)
        if record.wal_adapter_version != batch.wal_adapter_version:
            raise ValueError("record_wal_adapter_version_mismatch")
        if record.task_id != batch.task_id:
            raise ValueError("record_task_id_mismatch")
        if record.run_id != batch.run_id:
            raise ValueError("record_run_id_mismatch")
        if record.preflight_id != batch.preflight_id:
            raise ValueError("record_preflight_id_mismatch")

    sequences = tuple(record.sequence for record in ordered_records)
    if len(set(sequences)) != len(sequences):
        raise ValueError("duplicate_sequence")
    if sequences[0] != batch.first_sequence:
        raise ValueError("first_sequence_mismatch")
    if sequences[-1] != batch.last_sequence:
        raise ValueError("last_sequence_mismatch")
    if batch.last_sequence - batch.first_sequence + 1 != batch.record_count:
        raise ValueError("sequence_range_not_contiguous")

    ordered_record_hashes = tuple(record.record_hash for record in ordered_records)
    if batch.ordered_record_hashes != ordered_record_hashes:
        raise ValueError("ordered_record_hashes_mismatch")


def replay_wal_adapter_batch(
    batch: MinimalControlledWalAdapterBatch,
    records: Sequence[MinimalControlledWalAdapterRecord],
) -> MinimalControlledWalAdapterReplayResult:
    replay_input = MinimalControlledWalAdapterReplayInput(
        replay_input_id=_stable_contract_id(
            "wal-adapter-replay-input",
            {
                "batch_hash": batch.batch_hash,
                "ordered_record_hashes": batch.ordered_record_hashes,
                "expected_record_count": batch.record_count,
            },
        ),
        wal_adapter_version=WAL_ADAPTER_VERSION,
        batch_hash=batch.batch_hash,
        ordered_record_hashes=batch.ordered_record_hashes,
        expected_record_count=batch.record_count,
        replay_policy_version=WAL_ADAPTER_REPLAY_POLICY_VERSION,
    )

    rejection_reasons: tuple[str, ...] = ()
    try:
        validate_wal_adapter_batch(batch, records)
    except ValueError as exc:
        rejection_reasons = (str(exc),)

    accepted = not rejection_reasons
    return MinimalControlledWalAdapterReplayResult(
        replay_result_id=_stable_contract_id(
            "wal-adapter-replay-result",
            {
                "accepted": accepted,
                "rejection_reasons": rejection_reasons,
                "replay_input_hash": replay_input.replay_input_hash,
            },
        ),
        wal_adapter_version=WAL_ADAPTER_VERSION,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
        batch_hash=batch.batch_hash,
        replay_input_hash=replay_input.replay_input_hash,
    )


def _validate_record_shape_and_bindings(record: MinimalControlledWalAdapterRecord) -> None:
    _require_dataclass_fields(record, WAL_ADAPTER_RECORD_FIELDS, "wal_adapter_record")
    _require_strings(
        record.as_dict(),
        (
            "wal_adapter_record_id",
            "wal_adapter_version",
            "record_type",
            "task_id",
            "run_id",
            "command_id",
            "preflight_id",
            "created_at",
        ),
    )
    if record.wal_adapter_version != WAL_ADAPTER_VERSION:
        raise ValueError("wal_adapter_version_mismatch")
    if record.record_type not in WAL_ADAPTER_RECORD_TYPES:
        raise ValueError("record_type_invalid")
    _require_positive_int(record.sequence, "sequence")
    _require_bool(record.execution_performed, "execution_performed")

    for field_name in _RECORD_EVIDENCE_HASH_FIELDS:
        _validate_hash_value(getattr(record, field_name), field_name, allow_empty=True)
    _validate_hash_value(record.record_hash, "record_hash", allow_empty=True)

    _validate_record_type_bindings(record)


def _validate_record_type_bindings(record: MinimalControlledWalAdapterRecord) -> None:
    if record.record_type == "EXECUTION_ADMISSION":
        _require_hash_fields(record, ("request_hash", "decision_hash", "admission_record_hash"))
        _require_empty_hash_fields(
            record,
            (
                "receipt_hash",
                "failure_bundle_hash",
                "verifier_input_hash",
                "verifier_binding_hash",
            ),
        )
        _require_no_preflight_bindings(record)
        return

    if record.record_type == "EXECUTION_RECEIPT":
        _require_hash_fields(
            record,
            (
                "request_hash",
                "decision_hash",
                "admission_record_hash",
                "receipt_hash",
            ),
        )
        _require_empty_hash_fields(record, ("failure_bundle_hash",))
        _require_no_preflight_bindings(record)
        return

    if record.record_type == "EXECUTION_FAILURE":
        _require_hash_fields(record, ("request_hash", "decision_hash", "failure_bundle_hash"))
        _require_empty_hash_fields(
            record,
            ("receipt_hash", "verifier_input_hash", "verifier_binding_hash"),
        )
        _require_no_preflight_bindings(record)
        return

    if record.record_type == "EXECUTION_VERIFIER_BINDING":
        _require_hash_fields(record, ("verifier_binding_hash",))
        _require_no_preflight_bindings(record)
        return

    if record.record_type == "PREFLIGHT_RESULT":
        _require_hash_fields(record, ("preflight_result_hash",))
        _require_empty_hash_fields(
            record,
            (
                "request_hash",
                "decision_hash",
                "admission_record_hash",
                "receipt_hash",
                "failure_bundle_hash",
                "verifier_input_hash",
                "verifier_binding_hash",
            ),
        )
        _require_preflight_child_bindings(record)
        return

    raise ValueError("record_type_invalid")


def _require_no_preflight_bindings(record: MinimalControlledWalAdapterRecord) -> None:
    if record.preflight_result_hash:
        raise ValueError("preflight_result_hash_not_allowed_for_record_type")
    for field_name in _PREFLIGHT_SEQUENCE_FIELDS:
        if getattr(record, field_name):
            raise ValueError(field_name + "_not_allowed_for_record_type")


def _require_preflight_child_bindings(record: MinimalControlledWalAdapterRecord) -> None:
    if not record.ordered_command_ids:
        raise ValueError("ordered_command_ids_required")

    expected_count = len(record.ordered_command_ids)
    for field_name in _PREFLIGHT_HASH_SEQUENCE_FIELDS:
        values = getattr(record, field_name)
        if len(values) != expected_count:
            raise ValueError(field_name + "_count_mismatch")
        if field_name not in _PREFLIGHT_OPTIONAL_CHILD_HASH_SEQUENCE_FIELDS:
            for value in values:
                _validate_hash_value(value, field_name, allow_empty=False)

    for index, receipt_hash in enumerate(record.child_receipt_hashes):
        failure_hash = record.child_failure_bundle_hashes[index]
        if not receipt_hash and not failure_hash:
            raise ValueError("child_receipt_or_failure_bundle_hash_required")


def _validate_batch_shape(batch: MinimalControlledWalAdapterBatch) -> None:
    _require_dataclass_fields(batch, WAL_ADAPTER_BATCH_FIELDS, "wal_adapter_batch")
    _require_strings(
        batch.as_dict(),
        (
            "wal_adapter_batch_id",
            "wal_adapter_version",
            "task_id",
            "run_id",
            "preflight_id",
        ),
    )
    if batch.wal_adapter_version != WAL_ADAPTER_VERSION:
        raise ValueError("wal_adapter_version_mismatch")
    if not batch.ordered_record_hashes:
        raise ValueError("ordered_record_hashes_required")
    _require_positive_int(batch.record_count, "record_count")
    _require_positive_int(batch.first_sequence, "first_sequence")
    _require_positive_int(batch.last_sequence, "last_sequence")
    if batch.first_sequence > batch.last_sequence:
        raise ValueError("sequence_range_invalid")
    if len(batch.ordered_record_hashes) != batch.record_count:
        raise ValueError("ordered_record_hashes_count_mismatch")
    _validate_hash_value(batch.batch_hash, "batch_hash", allow_empty=True)


def _validate_replay_input_shape(
    replay_input: MinimalControlledWalAdapterReplayInput,
) -> None:
    _require_dataclass_fields(
        replay_input,
        WAL_ADAPTER_REPLAY_INPUT_FIELDS,
        "wal_adapter_replay_input",
    )
    _require_strings(
        replay_input.as_dict(),
        (
            "replay_input_id",
            "wal_adapter_version",
            "batch_hash",
            "replay_policy_version",
        ),
    )
    if replay_input.wal_adapter_version != WAL_ADAPTER_VERSION:
        raise ValueError("wal_adapter_version_mismatch")
    if replay_input.replay_policy_version != WAL_ADAPTER_REPLAY_POLICY_VERSION:
        raise ValueError("replay_policy_version_mismatch")
    if not replay_input.ordered_record_hashes:
        raise ValueError("ordered_record_hashes_required")
    _require_positive_int(replay_input.expected_record_count, "expected_record_count")
    if len(replay_input.ordered_record_hashes) != replay_input.expected_record_count:
        raise ValueError("expected_record_count_mismatch")
    _validate_hash_value(replay_input.batch_hash, "batch_hash", allow_empty=False)
    _validate_hash_value(replay_input.replay_input_hash, "replay_input_hash", allow_empty=True)


def _validate_replay_result_shape(
    replay_result: MinimalControlledWalAdapterReplayResult,
) -> None:
    _require_dataclass_fields(
        replay_result,
        WAL_ADAPTER_REPLAY_RESULT_FIELDS,
        "wal_adapter_replay_result",
    )
    _require_strings(
        replay_result.as_dict(),
        (
            "replay_result_id",
            "wal_adapter_version",
            "batch_hash",
            "replay_input_hash",
        ),
    )
    if replay_result.wal_adapter_version != WAL_ADAPTER_VERSION:
        raise ValueError("wal_adapter_version_mismatch")
    _require_bool(replay_result.accepted, "accepted")
    if replay_result.accepted and replay_result.rejection_reasons:
        raise ValueError("accepted_replay_result_cannot_have_rejection_reasons")
    if not replay_result.accepted and not replay_result.rejection_reasons:
        raise ValueError("rejected_replay_result_requires_rejection_reasons")
    _validate_hash_value(replay_result.batch_hash, "batch_hash", allow_empty=False)
    _validate_hash_value(
        replay_result.replay_input_hash,
        "replay_input_hash",
        allow_empty=False,
    )
    _validate_hash_value(
        replay_result.replay_result_hash,
        "replay_result_hash",
        allow_empty=True,
    )


def _require_dataclass_fields(value: object, expected_fields: Sequence[str], name: str) -> None:
    actual_fields = tuple(value.__dataclass_fields__)  # type: ignore[attr-defined]
    if actual_fields != tuple(expected_fields):
        raise ValueError(name + "_fields_mismatch")
    forbidden = set(actual_fields).intersection(
        WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES | WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES
    )
    if forbidden:
        raise ValueError(name + "_forbidden_field:" + ",".join(sorted(forbidden)))


def _require_hash_fields(
    record: MinimalControlledWalAdapterRecord,
    field_names: Sequence[str],
) -> None:
    for field_name in field_names:
        _validate_hash_value(getattr(record, field_name), field_name, allow_empty=False)


def _require_empty_hash_fields(
    record: MinimalControlledWalAdapterRecord,
    field_names: Sequence[str],
) -> None:
    for field_name in field_names:
        if getattr(record, field_name):
            raise ValueError(field_name + "_not_allowed_for_record_type")


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if not current:
        object.__setattr__(target, field_name, expected)
        return
    if current != expected:
        raise ValueError(field_name + "_mismatch")


def _hash_contract(value: object, hash_field: str) -> str:
    data = _contract_dict(value)
    data.pop(hash_field, None)
    return "sha256:" + _sha256_hex(_canonical_json(data))


def _contract_dict(value: object) -> dict[str, object]:
    if hasattr(value, "__dataclass_fields__"):
        data = asdict(value)
    elif isinstance(value, Mapping):
        data = dict(value)
    else:
        raise TypeError("contract value must be a dataclass or mapping")
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


def _stable_contract_id(prefix: str, payload: Mapping[str, object]) -> str:
    return prefix + ":" + _sha256_hex(_canonical_json(_json_ready(payload)))[:24]


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_strings(payload: Mapping[str, object], field_names: Sequence[str]) -> None:
    for field_name in field_names:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value:
            raise ValueError(field_name + "_required")


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(field_name + "_must_be_bool")


def _require_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(field_name + "_must_be_int")


def _require_positive_int(value: object, field_name: str) -> None:
    _require_int(value, field_name)
    if value <= 0:
        raise ValueError(field_name + "_must_be_positive")


def _string_tuple(
    values: Sequence[str],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_string_sequence")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError(field_name + "_must_be_ordered_string_sequence")
        if not value:
            raise ValueError(field_name + "_cannot_contain_empty_string")
        normalized.append(value)
    if not normalized and not allow_empty:
        return ()
    return tuple(normalized)


def _hash_tuple(
    values: Sequence[str],
    field_name: str,
    *,
    allow_empty_item: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_hash_sequence")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError(field_name + "_must_be_ordered_hash_sequence")
        _validate_hash_value(value, field_name, allow_empty=allow_empty_item)
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
