"""Read-only contract over the task lifecycle journal snapshot boundary.

Boundary:

`kernel.lifecycle.task_recovery.TaskLifecycleSnapshot` is the existing
read-only shape produced by the task lifecycle journal layer
(`intent_anchor_records` + `audit_records`) and consumed by the
read-only chain (classifier, recovery gate, recovery session host).

This module is a structural contract over that boundary. It validates
that a snapshot instance is shape-safe for downstream read-only
consumers and emits a JSON-safe contract manifest. It does not write
rows, mutate the snapshot, instantiate runtime services, call restore,
or load CLI surfaces. It depends only on stdlib + the existing
snapshot dataclass + the existing `Stage` enum.

Output shape:

    {
        "ready": bool,
        "reason_code": str,
        "failures": list[str],
        "contract": dict[str, object],
    }

`ready` is True iff the snapshot is structurally valid for downstream
read-only consumers. Otherwise `failures` lists deterministic stable
failure codes in field-declaration order, and `reason_code` is the
single fixed `not_ready` code.

The renderer deep-copies `contract` before returning so caller
mutations do not propagate.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Optional

from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import TaskLifecycleSnapshot


_SURFACE = "task_lifecycle_journal_snapshot"
_VERSION = 1
_INPUT_SHAPE = "TaskLifecycleSnapshot"

_REQUIRED_FIELDS: tuple[str, ...] = (
    "task_id",
    "intent_id",
    "current_stage",
    "artifact_ids",
    "terminal_state",
    "last_event_sequence",
    "lifecycle_record_count",
    "malformed_event_count",
    "intent_anchor_count",
    "intent_created_at",
)

_ARTIFACT_BEARING_STAGE_VALUES: tuple[str, ...] = (
    Stage.CONTEXT.value,
    Stage.INFERENCE.value,
    Stage.PATCH_PROPOSAL.value,
    Stage.VALIDATION.value,
    Stage.REVIEW.value,
    Stage.APPROVAL.value,
    Stage.REVISION_SEAL.value,
    Stage.EVIDENCE.value,
)

_LEGAL_STAGE_VALUES: tuple[str, ...] = tuple(sorted(s.value for s in Stage))
_LEGAL_TERMINAL_VALUES: tuple[str, ...] = (
    Stage.ABANDONED.value,
    Stage.SEALED.value,
)
_REASON_CODE_READY = "ready"
_REASON_CODE_NOT_READY = "not_ready"

_FAILURE_VALUES: tuple[str, ...] = (
    "input_not_snapshot",
    "task_id_invalid",
    "intent_id_invalid",
    "current_stage_invalid",
    "artifact_ids_not_mapping",
    "artifact_ids_key_invalid",
    "artifact_ids_value_invalid",
    "artifact_ids_stage_not_artifact_bearing",
    "terminal_state_invalid",
    "last_event_sequence_invalid",
    "lifecycle_record_count_invalid",
    "malformed_event_count_invalid",
    "intent_anchor_count_invalid",
    "intent_created_at_invalid",
    "terminal_state_inconsistent",
)


def _build_contract() -> dict[str, object]:
    return {
        "surface": _SURFACE,
        "version": _VERSION,
        "input_shape": _INPUT_SHAPE,
        "required_fields": list(_REQUIRED_FIELDS),
        "legal_stage_values": list(_LEGAL_STAGE_VALUES),
        "legal_terminal_values": list(_LEGAL_TERMINAL_VALUES),
        "artifact_bearing_stage_values": list(_ARTIFACT_BEARING_STAGE_VALUES),
        "failure_values": list(_FAILURE_VALUES),
        "reason_codes": [_REASON_CODE_NOT_READY, _REASON_CODE_READY],
        "restore_supported": False,
        "durable_writes": False,
        "cli_commands": [],
        "runtime_dependencies": [],
        "json_safe": True,
    }


_CONTRACT: dict[str, object] = _build_contract()


@dataclass(frozen=True)
class TaskLifecycleJournalSnapshotContractCheck:
    """Frozen verdict from the snapshot read-only contract."""

    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    contract: dict[str, object]


def task_lifecycle_journal_snapshot_contract_manifest() -> dict[str, object]:
    """Return a deep-copied JSON-safe contract manifest."""

    return deepcopy(_CONTRACT)


def check_task_lifecycle_journal_snapshot_contract(
    snapshot: object,
) -> TaskLifecycleJournalSnapshotContractCheck:
    """Validate `snapshot` and return a frozen contract check.

    Read-only: never mutates the snapshot, never writes rows, never
    instantiates downstream services.
    """

    contract = task_lifecycle_journal_snapshot_contract_manifest()
    failures: list[str] = []

    if not isinstance(snapshot, TaskLifecycleSnapshot):
        failures.append("input_not_snapshot")
        return _build_check(failures, contract)

    if not _is_non_empty_str(snapshot.task_id):
        failures.append("task_id_invalid")

    if not _is_non_empty_str(snapshot.intent_id):
        failures.append("intent_id_invalid")

    current_stage_valid = snapshot.current_stage is None or isinstance(
        snapshot.current_stage, Stage
    )
    if not current_stage_valid:
        failures.append("current_stage_invalid")

    artifact_ids = snapshot.artifact_ids
    artifact_ids_is_dict = isinstance(artifact_ids, dict)
    if not artifact_ids_is_dict:
        failures.append("artifact_ids_not_mapping")
    else:
        if not all(isinstance(key, Stage) for key in artifact_ids):
            failures.append("artifact_ids_key_invalid")
        if not all(_is_non_empty_str(value) for value in artifact_ids.values()):
            failures.append("artifact_ids_value_invalid")
        if any(
            isinstance(key, Stage)
            and key.value not in _ARTIFACT_BEARING_STAGE_VALUES
            for key in artifact_ids
        ):
            failures.append("artifact_ids_stage_not_artifact_bearing")

    terminal_state = snapshot.terminal_state
    terminal_state_valid = terminal_state is None or (
        isinstance(terminal_state, Stage)
        and terminal_state.value in _LEGAL_TERMINAL_VALUES
    )
    if not terminal_state_valid:
        failures.append("terminal_state_invalid")

    if not _is_optional_non_negative_int(snapshot.last_event_sequence):
        failures.append("last_event_sequence_invalid")

    if not _is_non_negative_int(snapshot.lifecycle_record_count):
        failures.append("lifecycle_record_count_invalid")

    if not _is_non_negative_int(snapshot.malformed_event_count):
        failures.append("malformed_event_count_invalid")

    if not _is_non_negative_int(snapshot.intent_anchor_count):
        failures.append("intent_anchor_count_invalid")

    intent_created_at = snapshot.intent_created_at
    intent_created_at_valid = intent_created_at is None or isinstance(
        intent_created_at, str
    )
    if not intent_created_at_valid:
        failures.append("intent_created_at_invalid")

    if (
        terminal_state_valid
        and current_stage_valid
        and terminal_state is not None
        and snapshot.current_stage is not terminal_state
    ):
        failures.append("terminal_state_inconsistent")

    return _build_check(failures, contract)


def render_task_lifecycle_journal_snapshot_contract_check(
    check: TaskLifecycleJournalSnapshotContractCheck,
) -> dict[str, object]:
    """Render a contract check to a JSON-safe deep-copied dict.

    Never returns a reference to the check's internal `contract` mapping.
    """

    return {
        "ready": bool(check.ready),
        "reason_code": str(check.reason_code),
        "failures": list(check.failures),
        "contract": deepcopy(check.contract),
    }


def _build_check(
    failures: list[str],
    contract: dict[str, object],
) -> TaskLifecycleJournalSnapshotContractCheck:
    if failures:
        return TaskLifecycleJournalSnapshotContractCheck(
            ready=False,
            reason_code=_REASON_CODE_NOT_READY,
            failures=tuple(failures),
            contract=contract,
        )
    return TaskLifecycleJournalSnapshotContractCheck(
        ready=True,
        reason_code=_REASON_CODE_READY,
        failures=(),
        contract=contract,
    )


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _is_non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_optional_non_negative_int(value: object) -> bool:
    if value is None:
        return True
    return _is_non_negative_int(value)


__all__ = [
    "TaskLifecycleJournalSnapshotContractCheck",
    "check_task_lifecycle_journal_snapshot_contract",
    "render_task_lifecycle_journal_snapshot_contract_check",
    "task_lifecycle_journal_snapshot_contract_manifest",
]
