"""Read-only readiness check over rendered task lifecycle batch digests.

This module consumes only the already-rendered P1-02 batch digest payload.
It performs bounded structural and consistency checks for downstream
operator/CI surfaces without opening databases, invoking repositories,
calling CLI code, or executing recovery behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "task_lifecycle_journal_snapshot_batch_readiness"
_VERSION = 1
_INPUT_SHAPE = "rendered_task_lifecycle_journal_snapshot_batch_digest"
_BATCH_SURFACE = "task_lifecycle_journal_snapshot_batch"

_REASON_CODE_INVALID_BATCH_DIGEST = "invalid_batch_digest"
_REASON_CODE_NOT_READY = "not_ready"
_REASON_CODE_READY = "ready"
_REASON_CODES: tuple[str, ...] = (
    _REASON_CODE_INVALID_BATCH_DIGEST,
    _REASON_CODE_NOT_READY,
    _REASON_CODE_READY,
)

_P1_02_REASON_CODE_INVALID_BATCH = "invalid_batch"
_P1_02_INVALID_BATCH_FAILURES = {
    "batch_not_sequence",
    "batch_empty",
    "item_invalid_type",
    "item_contract_invalid",
}

_FAILURE_PAYLOAD_NOT_MAPPING = "payload_not_mapping"
_FAILURE_PAYLOAD_SHAPE_MISMATCH = "payload_shape_mismatch"
_FAILURE_PAYLOAD_FAILURES_INVALID = "payload_failures_invalid"
_FAILURE_DIGEST_INVALID = "digest_invalid"
_FAILURE_DIGEST_SHAPE_MISMATCH = "digest_shape_mismatch"
_FAILURE_DIGEST_COUNTER_INVALID = "digest_counter_invalid"
_FAILURE_DIGEST_BOOL_INVALID = "digest_bool_invalid"
_FAILURE_DIGEST_LIST_INVALID = "digest_list_invalid"
_FAILURE_DIGEST_MAPPING_INVALID = "digest_mapping_invalid"
_FAILURE_STATUS_INCONSISTENT = "status_inconsistent"
_FAILURE_SAFETY_INCONSISTENT = "safety_inconsistent"
_FAILURE_OPERATOR_NOT_SAFE = "operator_not_safe"
_FAILURE_VALUES: tuple[str, ...] = (
    _FAILURE_PAYLOAD_NOT_MAPPING,
    _FAILURE_PAYLOAD_SHAPE_MISMATCH,
    _FAILURE_PAYLOAD_FAILURES_INVALID,
    _FAILURE_DIGEST_INVALID,
    _FAILURE_DIGEST_SHAPE_MISMATCH,
    _FAILURE_DIGEST_COUNTER_INVALID,
    _FAILURE_DIGEST_BOOL_INVALID,
    _FAILURE_DIGEST_LIST_INVALID,
    _FAILURE_DIGEST_MAPPING_INVALID,
    _FAILURE_STATUS_INCONSISTENT,
    _FAILURE_SAFETY_INCONSISTENT,
    _FAILURE_OPERATOR_NOT_SAFE,
)

_TOP_LEVEL_KEYS = {"ready", "reason_code", "failures", "digest"}
_REQUIRED_DIGEST_KEYS = {
    "surface",
    "version",
    "item_count",
    "ready_count",
    "not_ready_count",
    "invalid_count",
    "unique_task_count",
    "duplicate_task_ids",
    "reason_counts",
    "failure_counts",
    "ready_task_ids",
    "not_ready_task_ids",
    "operator_safe",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
}
_COUNTER_FIELDS = (
    "version",
    "item_count",
    "ready_count",
    "not_ready_count",
    "invalid_count",
    "unique_task_count",
    "cli_command_count",
    "runtime_dependency_count",
)
_LIST_FIELDS = (
    "duplicate_task_ids",
    "ready_task_ids",
    "not_ready_task_ids",
)
_MAPPING_FIELDS = ("reason_counts", "failure_counts")


@dataclass(frozen=True)
class TaskLifecycleJournalSnapshotBatchReadinessCheck:
    """Frozen readiness verdict over a rendered P1-02 batch digest."""

    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    contract: dict[str, object]


def _build_manifest() -> dict[str, object]:
    return {
        "surface": _SURFACE,
        "version": _VERSION,
        "input_shape": _INPUT_SHAPE,
        "restore_supported": False,
        "durable_writes": False,
        "cli_commands": [],
        "runtime_dependencies": [],
        "json_safe": True,
        "reason_codes": list(_REASON_CODES),
        "failure_values": list(_FAILURE_VALUES),
    }


_MANIFEST = _build_manifest()


def task_lifecycle_journal_snapshot_batch_readiness_manifest() -> (
    dict[str, object]
):
    """Return a defensive JSON-safe manifest for the readiness surface."""

    return deepcopy(_MANIFEST)


def check_task_lifecycle_journal_snapshot_batch_readiness(
    rendered_batch: object,
) -> TaskLifecycleJournalSnapshotBatchReadinessCheck:
    """Validate a rendered P1-02 batch digest without upstream calls."""

    contract = task_lifecycle_journal_snapshot_batch_readiness_manifest()
    failures = _validate_rendered_batch(rendered_batch)
    structural_failures = [
        failure
        for failure in failures
        if failure != _FAILURE_OPERATOR_NOT_SAFE
    ]

    if structural_failures:
        return TaskLifecycleJournalSnapshotBatchReadinessCheck(
            ready=False,
            reason_code=_REASON_CODE_INVALID_BATCH_DIGEST,
            failures=tuple(structural_failures),
            contract=contract,
        )

    if _batch_operator_safe(rendered_batch):
        return TaskLifecycleJournalSnapshotBatchReadinessCheck(
            ready=True,
            reason_code=_REASON_CODE_READY,
            failures=(),
            contract=contract,
        )

    return TaskLifecycleJournalSnapshotBatchReadinessCheck(
        ready=False,
        reason_code=_REASON_CODE_NOT_READY,
        failures=(_FAILURE_OPERATOR_NOT_SAFE,),
        contract=contract,
    )


def render_task_lifecycle_journal_snapshot_batch_readiness_check(
    check: TaskLifecycleJournalSnapshotBatchReadinessCheck,
) -> dict[str, object]:
    """Render a readiness check to a defensive JSON-safe payload."""

    return {
        "ready": bool(check.ready),
        "reason_code": str(check.reason_code),
        "failures": list(check.failures),
        "contract": deepcopy(check.contract),
    }


def _validate_rendered_batch(rendered_batch: object) -> list[str]:
    failure_set: set[str] = set()

    if not isinstance(rendered_batch, Mapping):
        return [_FAILURE_PAYLOAD_NOT_MAPPING]

    top_level_shape_valid = set(rendered_batch.keys()) == _TOP_LEVEL_KEYS
    ready = rendered_batch.get("ready")
    reason_code = rendered_batch.get("reason_code")
    payload_failures = rendered_batch.get("failures")
    digest = rendered_batch.get("digest")

    ready_valid = type(ready) is bool
    reason_code_valid = isinstance(reason_code, str)
    if not top_level_shape_valid or not ready_valid or not reason_code_valid:
        failure_set.add(_FAILURE_PAYLOAD_SHAPE_MISMATCH)

    payload_failures_valid = _is_string_list(payload_failures)
    if not payload_failures_valid:
        failure_set.add(_FAILURE_PAYLOAD_FAILURES_INVALID)

    if type(digest) is not dict:
        failure_set.add(_FAILURE_DIGEST_INVALID)
        return _ordered_failures(failure_set)

    digest_shape_valid = _REQUIRED_DIGEST_KEYS.issubset(set(digest.keys()))
    if not digest_shape_valid:
        failure_set.add(_FAILURE_DIGEST_SHAPE_MISMATCH)
        return _ordered_failures(failure_set)

    counter_valid = _has_valid_counter_fields(digest)
    bool_valid = _has_valid_bool_fields(digest)
    list_valid = _has_valid_list_fields(digest)
    mapping_valid = _has_valid_mapping_fields(digest)

    if not counter_valid:
        failure_set.add(_FAILURE_DIGEST_COUNTER_INVALID)
    if not bool_valid:
        failure_set.add(_FAILURE_DIGEST_BOOL_INVALID)
    if not list_valid:
        failure_set.add(_FAILURE_DIGEST_LIST_INVALID)
    if not mapping_valid:
        failure_set.add(_FAILURE_DIGEST_MAPPING_INVALID)

    if (
        counter_valid
        and bool_valid
        and list_valid
        and mapping_valid
        and not _has_valid_digest_constants(digest)
    ):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        ready_valid
        and reason_code_valid
        and payload_failures_valid
        and counter_valid
        and bool_valid
        and list_valid
        and mapping_valid
        and not _status_is_consistent(
            ready=ready,
            reason_code=reason_code,
            payload_failures=payload_failures,
            digest=digest,
        )
    ):
        failure_set.add(_FAILURE_STATUS_INCONSISTENT)

    if (
        counter_valid
        and bool_valid
        and not _operator_safe_is_consistent(digest)
    ):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        counter_valid
        and bool_valid
        and list_valid
        and not digest["operator_safe"]
    ):
        failure_set.add(_FAILURE_OPERATOR_NOT_SAFE)

    return _ordered_failures(failure_set)


def _has_valid_digest_constants(digest: Mapping[str, object]) -> bool:
    return (
        digest.get("surface") == _BATCH_SURFACE
        and type(digest.get("version")) is int
        and digest.get("restore_supported") is False
        and digest.get("durable_writes") is False
        and digest.get("cli_command_count") == 0
        and digest.get("runtime_dependency_count") == 0
        and digest.get("json_safe") is True
    )


def _has_valid_counter_fields(digest: Mapping[str, object]) -> bool:
    return all(_is_non_negative_int(digest.get(field)) for field in _COUNTER_FIELDS)


def _has_valid_bool_fields(digest: Mapping[str, object]) -> bool:
    return all(
        type(digest.get(field)) is bool
        for field in (
            "operator_safe",
            "restore_supported",
            "durable_writes",
            "json_safe",
        )
    )


def _has_valid_list_fields(digest: Mapping[str, object]) -> bool:
    return all(_is_string_list(digest.get(field)) for field in _LIST_FIELDS)


def _has_valid_mapping_fields(digest: Mapping[str, object]) -> bool:
    return all(_is_string_int_mapping(digest.get(field)) for field in _MAPPING_FIELDS)


def _status_is_consistent(
    *,
    ready: object,
    reason_code: object,
    payload_failures: object,
    digest: Mapping[str, object],
) -> bool:
    item_count = digest["item_count"]
    ready_count = digest["ready_count"]
    not_ready_count = digest["not_ready_count"]
    invalid_count = digest["invalid_count"]
    unique_task_count = digest["unique_task_count"]
    duplicate_task_ids = digest["duplicate_task_ids"]
    operator_safe = digest["operator_safe"]

    if ready_count + not_ready_count + invalid_count != item_count:
        return False
    if unique_task_count > item_count:
        return False

    if ready is True:
        return (
            reason_code == _REASON_CODE_READY
            and payload_failures == []
            and operator_safe is True
            and invalid_count == 0
            and not_ready_count == 0
            and duplicate_task_ids == []
        )

    if reason_code == _P1_02_REASON_CODE_INVALID_BATCH:
        return invalid_count > 0 or any(
            failure in _P1_02_INVALID_BATCH_FAILURES
            for failure in payload_failures
        )

    if reason_code == _REASON_CODE_NOT_READY:
        return (
            operator_safe is False
            and (
                not_ready_count > 0
                or duplicate_task_ids != []
                or payload_failures != []
            )
        )

    return False


def _operator_safe_is_consistent(digest: Mapping[str, object]) -> bool:
    operator_safe = digest["operator_safe"]
    ready_count = digest["ready_count"]
    not_ready_count = digest["not_ready_count"]
    invalid_count = digest["invalid_count"]
    item_count = digest["item_count"]
    duplicate_task_ids = digest.get("duplicate_task_ids")

    expected_safe = (
        item_count > 0
        and ready_count == item_count
        and not_ready_count == 0
        and invalid_count == 0
        and duplicate_task_ids == []
    )
    return operator_safe is expected_safe


def _batch_operator_safe(rendered_batch: object) -> bool:
    if not isinstance(rendered_batch, Mapping):
        return False
    digest = rendered_batch.get("digest")
    if type(digest) is not dict:
        return False
    return digest.get("operator_safe") is True


def _is_non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_string_list(value: object) -> bool:
    return type(value) is list and all(isinstance(item, str) for item in value)


def _is_string_int_mapping(value: object) -> bool:
    return type(value) is dict and all(
        isinstance(key, str) and _is_non_negative_int(count)
        for key, count in value.items()
    )


def _ordered_failures(failures: set[str]) -> list[str]:
    return [failure for failure in _FAILURE_VALUES if failure in failures]


__all__ = [
    "TaskLifecycleJournalSnapshotBatchReadinessCheck",
    "check_task_lifecycle_journal_snapshot_batch_readiness",
    "render_task_lifecycle_journal_snapshot_batch_readiness_check",
    "task_lifecycle_journal_snapshot_batch_readiness_manifest",
]
