"""Read-only batch digest for task lifecycle journal snapshots.

This module accepts already materialized
`TaskLifecycleSnapshot` objects or rendered P1-01 snapshot contract
checks. It aggregates readiness into a bounded JSON-safe digest for
downstream operator and CI consumers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass

from kernel.lifecycle.task_lifecycle_journal_snapshot_contract import (
    check_task_lifecycle_journal_snapshot_contract,
    render_task_lifecycle_journal_snapshot_contract_check,
)
from kernel.lifecycle.task_recovery import TaskLifecycleSnapshot


_SURFACE = "task_lifecycle_journal_snapshot_batch"
_VERSION = 1
_INPUT_SHAPE = (
    "sequence_of_TaskLifecycleSnapshot_or_rendered_snapshot_contract_check"
)
_SNAPSHOT_SURFACE = "task_lifecycle_journal_snapshot"

_REASON_CODE_INVALID_BATCH = "invalid_batch"
_REASON_CODE_NOT_READY = "not_ready"
_REASON_CODE_READY = "ready"
_REASON_CODES: tuple[str, ...] = (
    _REASON_CODE_INVALID_BATCH,
    _REASON_CODE_NOT_READY,
    _REASON_CODE_READY,
)

_FAILURE_BATCH_NOT_SEQUENCE = "batch_not_sequence"
_FAILURE_BATCH_EMPTY = "batch_empty"
_FAILURE_ITEM_INVALID_TYPE = "item_invalid_type"
_FAILURE_ITEM_CONTRACT_NOT_READY = "item_contract_not_ready"
_FAILURE_ITEM_CONTRACT_INVALID = "item_contract_invalid"
_FAILURE_DUPLICATE_TASK_ID = "duplicate_task_id"
_FAILURE_MIXED_READY_STATE = "mixed_ready_state"
_FAILURE_VALUES: tuple[str, ...] = (
    _FAILURE_BATCH_NOT_SEQUENCE,
    _FAILURE_BATCH_EMPTY,
    _FAILURE_ITEM_INVALID_TYPE,
    _FAILURE_ITEM_CONTRACT_NOT_READY,
    _FAILURE_ITEM_CONTRACT_INVALID,
    _FAILURE_DUPLICATE_TASK_ID,
    _FAILURE_MIXED_READY_STATE,
)


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


_MANIFEST: dict[str, object] = _build_manifest()


@dataclass(frozen=True)
class TaskLifecycleJournalSnapshotBatchDigest:
    """Frozen batch verdict over snapshot contract checks."""

    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    digest: dict[str, object]


def task_lifecycle_journal_snapshot_batch_manifest() -> dict[str, object]:
    """Return a deep-copied JSON-safe manifest for this batch surface."""

    return deepcopy(_MANIFEST)


def build_task_lifecycle_journal_snapshot_batch_digest(
    items: object,
) -> TaskLifecycleJournalSnapshotBatchDigest:
    """Build a bounded read-only digest from snapshot contract inputs."""

    if not _is_supported_sequence(items):
        return _build_batch_digest(
            ready=False,
            reason_code=_REASON_CODE_INVALID_BATCH,
            failures=[_FAILURE_BATCH_NOT_SEQUENCE],
            item_count=0,
            ready_count=0,
            not_ready_count=0,
            invalid_count=0,
            task_ids=[],
            duplicate_task_ids=[],
            reason_counts={},
            failure_counts={_FAILURE_BATCH_NOT_SEQUENCE: 1},
        )

    sequence = tuple(items)
    if not sequence:
        return _build_batch_digest(
            ready=False,
            reason_code=_REASON_CODE_INVALID_BATCH,
            failures=[_FAILURE_BATCH_EMPTY],
            item_count=0,
            ready_count=0,
            not_ready_count=0,
            invalid_count=0,
            task_ids=[],
            duplicate_task_ids=[],
            reason_counts={},
            failure_counts={_FAILURE_BATCH_EMPTY: 1},
        )

    ready_count = 0
    not_ready_count = 0
    invalid_count = 0
    task_ids: list[str] = []
    ready_task_ids: list[str] = []
    not_ready_task_ids: list[str] = []
    real_task_id_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    batch_failure_flags: set[str] = set()

    for index, item in enumerate(sequence):
        rendered: dict[str, object] | None
        task_id: str | None
        is_real_snapshot = isinstance(item, TaskLifecycleSnapshot)

        if is_real_snapshot:
            rendered = _render_snapshot_contract_check(item)
            task_id = _snapshot_item_id(item, index)
            if isinstance(item.task_id, str):
                real_task_id_counts[item.task_id] = (
                    real_task_id_counts.get(item.task_id, 0) + 1
                )
        elif isinstance(item, Mapping):
            task_id = f"rendered::{index}"
            rendered = dict(item)
            if not _is_valid_rendered_snapshot_contract_check(rendered):
                invalid_count += 1
                task_ids.append(task_id)
                batch_failure_flags.add(_FAILURE_ITEM_CONTRACT_INVALID)
                _increment(failure_counts, _FAILURE_ITEM_CONTRACT_INVALID)
                continue
        else:
            invalid_count += 1
            batch_failure_flags.add(_FAILURE_ITEM_INVALID_TYPE)
            _increment(failure_counts, _FAILURE_ITEM_INVALID_TYPE)
            continue

        task_ids.append(task_id)
        ready = rendered["ready"]
        reason_code = rendered["reason_code"]
        failures = rendered["failures"]

        _increment(reason_counts, reason_code)
        for failure in failures:
            _increment(failure_counts, failure)

        if ready:
            ready_count += 1
            ready_task_ids.append(task_id)
        else:
            not_ready_count += 1
            not_ready_task_ids.append(task_id)
            batch_failure_flags.add(_FAILURE_ITEM_CONTRACT_NOT_READY)
            _increment(failure_counts, _FAILURE_ITEM_CONTRACT_NOT_READY)

    duplicate_task_ids = sorted(
        task_id
        for task_id, count in real_task_id_counts.items()
        if count > 1
    )
    if duplicate_task_ids:
        batch_failure_flags.add(_FAILURE_DUPLICATE_TASK_ID)
        failure_counts[_FAILURE_DUPLICATE_TASK_ID] = len(duplicate_task_ids)

    if ready_count > 0 and not_ready_count > 0:
        batch_failure_flags.add(_FAILURE_MIXED_READY_STATE)
        failure_counts[_FAILURE_MIXED_READY_STATE] = 1

    failures = [
        failure for failure in _FAILURE_VALUES if failure in batch_failure_flags
    ]
    ready = (
        invalid_count == 0
        and not_ready_count == 0
        and ready_count == len(sequence)
        and not duplicate_task_ids
        and _FAILURE_MIXED_READY_STATE not in batch_failure_flags
    )

    if ready:
        reason_code = _REASON_CODE_READY
    elif invalid_count > 0:
        reason_code = _REASON_CODE_INVALID_BATCH
    else:
        reason_code = _REASON_CODE_NOT_READY

    return _build_batch_digest(
        ready=ready,
        reason_code=reason_code,
        failures=failures,
        item_count=len(sequence),
        ready_count=ready_count,
        not_ready_count=not_ready_count,
        invalid_count=invalid_count,
        task_ids=task_ids,
        duplicate_task_ids=duplicate_task_ids,
        reason_counts=reason_counts,
        failure_counts=failure_counts,
        ready_task_ids=ready_task_ids,
        not_ready_task_ids=not_ready_task_ids,
    )


def render_task_lifecycle_journal_snapshot_batch_digest(
    digest: TaskLifecycleJournalSnapshotBatchDigest,
) -> dict[str, object]:
    """Render a batch digest to a deep-copied JSON-safe dictionary."""

    return {
        "ready": bool(digest.ready),
        "reason_code": str(digest.reason_code),
        "failures": list(digest.failures),
        "digest": deepcopy(digest.digest),
    }


def _is_supported_sequence(items: object) -> bool:
    return isinstance(items, Sequence) and not isinstance(
        items, (str, bytes, bytearray)
    )


def _render_snapshot_contract_check(
    snapshot: TaskLifecycleSnapshot,
) -> dict[str, object]:
    check = check_task_lifecycle_journal_snapshot_contract(snapshot)
    return render_task_lifecycle_journal_snapshot_contract_check(check)


def _snapshot_item_id(
    snapshot: TaskLifecycleSnapshot,
    index: int,
) -> str:
    if isinstance(snapshot.task_id, str):
        return snapshot.task_id
    return f"snapshot::{index}"


def _is_valid_rendered_snapshot_contract_check(
    payload: Mapping[str, object],
) -> bool:
    if set(payload.keys()) != {"ready", "reason_code", "failures", "contract"}:
        return False
    if type(payload.get("ready")) is not bool:
        return False
    if not isinstance(payload.get("reason_code"), str):
        return False
    failures = payload.get("failures")
    if type(failures) is not list or not all(
        isinstance(failure, str) for failure in failures
    ):
        return False
    contract = payload.get("contract")
    if type(contract) is not dict:
        return False
    return _is_valid_snapshot_contract(contract)


def _is_valid_snapshot_contract(contract: Mapping[str, object]) -> bool:
    if contract.get("surface") != _SNAPSHOT_SURFACE:
        return False
    if type(contract.get("version")) is not int:
        return False
    if contract.get("restore_supported") is not False:
        return False
    if contract.get("durable_writes") is not False:
        return False
    cli_commands = contract.get("cli_commands")
    if type(cli_commands) is not list or cli_commands != []:
        return False
    runtime_dependencies = contract.get("runtime_dependencies")
    if type(runtime_dependencies) is not list or runtime_dependencies != []:
        return False
    if contract.get("json_safe") is not True:
        return False
    return True


def _build_batch_digest(
    *,
    ready: bool,
    reason_code: str,
    failures: list[str],
    item_count: int,
    ready_count: int,
    not_ready_count: int,
    invalid_count: int,
    task_ids: list[str],
    duplicate_task_ids: list[str],
    reason_counts: dict[str, int],
    failure_counts: dict[str, int],
    ready_task_ids: list[str] | None = None,
    not_ready_task_ids: list[str] | None = None,
) -> TaskLifecycleJournalSnapshotBatchDigest:
    ready_task_ids = list(ready_task_ids or [])
    not_ready_task_ids = list(not_ready_task_ids or [])
    digest = {
        "surface": _SURFACE,
        "version": _VERSION,
        "item_count": int(item_count),
        "ready_count": int(ready_count),
        "not_ready_count": int(not_ready_count),
        "invalid_count": int(invalid_count),
        "unique_task_count": len(set(task_ids)),
        "duplicate_task_ids": list(duplicate_task_ids),
        "reason_counts": _ordered_counts(reason_counts, _REASON_CODES),
        "failure_counts": _ordered_counts(failure_counts, _FAILURE_VALUES),
        "ready_task_ids": ready_task_ids,
        "not_ready_task_ids": not_ready_task_ids,
        "operator_safe": bool(ready),
        "restore_supported": False,
        "durable_writes": False,
        "cli_command_count": 0,
        "runtime_dependency_count": 0,
        "json_safe": True,
    }
    return TaskLifecycleJournalSnapshotBatchDigest(
        ready=bool(ready),
        reason_code=str(reason_code),
        failures=tuple(failures),
        digest=digest,
    )


def _increment(counts: dict[str, int], key: object) -> None:
    if not isinstance(key, str):
        return
    counts[key] = counts.get(key, 0) + 1


def _ordered_counts(
    counts: Mapping[str, int],
    preferred_order: tuple[str, ...],
) -> dict[str, int]:
    ordered: dict[str, int] = {}
    for key in preferred_order:
        value = counts.get(key)
        if value:
            ordered[key] = int(value)
    for key in sorted(key for key in counts if key not in ordered):
        value = counts[key]
        if value:
            ordered[key] = int(value)
    return ordered


__all__ = [
    "TaskLifecycleJournalSnapshotBatchDigest",
    "build_task_lifecycle_journal_snapshot_batch_digest",
    "render_task_lifecycle_journal_snapshot_batch_digest",
    "task_lifecycle_journal_snapshot_batch_manifest",
]
