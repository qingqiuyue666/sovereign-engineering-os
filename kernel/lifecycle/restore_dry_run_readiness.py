"""Read-only restore dry-run readiness surface.

This module is a pure evaluator. It consumes already-rendered restore
dry-run readiness payloads (mappings of dictionaries) and returns a
bounded, JSON-safe readiness verdict. It never opens external
resources, never mutates state, never calls upstream renderers, and
keeps every authorization flag False.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "restore_dry_run_readiness"
_VERSION = 1
_INPUT_SHAPE = "mapping_of_already_rendered_restore_dry_run_readiness_payloads"

_REASON_INVALID = "invalid_readiness_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_TAG_GOVERNANCE = "read-only-governance-layer-v1"
_TAG_PRECONDITION_CHECKER = "write-side-precondition-checker-v1"
_TAG_PRECONDITION_CI = "write-side-precondition-ci-v1"
_TAG_RECOVERY_SPEC_ONLY = "write-side-recovery-spec-only-v1"

_EXPECTED_TAGS: dict[str, str] = {
    _TAG_GOVERNANCE: "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
    _TAG_PRECONDITION_CHECKER: "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6",
    _TAG_PRECONDITION_CI: "05c81541ad3d7deee20023843142f702937f6c3f",
    _TAG_RECOVERY_SPEC_ONLY: "ad560cc2dab135f2c1d56d948410ae47586d118e",
}

_TOP_LEVEL_KEYS = (
    "source_truth",
    "governance_ci",
    "precondition_ci",
    "target_task",
    "dry_run",
    "idempotency",
    "evidence_snapshot",
    "human_approval",
    "schema_runtime",
)

_SOURCE_TRUTH_KEYS = ("current_head", "working_tree_clean", "tags")

_TARGET_TASK_KEYS = (
    "target_task_id",
    "task_ready",
    "snapshot_ready",
    "lifecycle_ready",
)

_DRY_RUN_KEYS = (
    "dry_run_present",
    "dry_run_ok",
    "target_task_id",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
    "mutates_state",
    "creates_files",
    "opens_write_transaction",
    "calls_restore",
)

_IDEMPOTENCY_KEYS = (
    "idempotency_key",
    "target_task_id",
    "operation_kind",
    "replay_status",
)

_EVIDENCE_SNAPSHOT_KEYS = (
    "before_snapshot_ref",
    "projected_after_snapshot_ref",
    "projected_evidence_ref",
    "immutable",
    "target_task_id",
)

_HUMAN_APPROVAL_KEYS = (
    "approval_present",
    "actor_identity",
    "scope",
    "reason",
    "created_at",
    "target_task_id",
    "bound_idempotency_key",
)

_SCHEMA_RUNTIME_KEYS = (
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_safe",
)

_REPLAY_STATUS_OK = ("new", "same_attempt_safe")

_GOVERNANCE_HAZARD_FALSE_FIELDS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "durable_writes",
)
_GOVERNANCE_HAZARD_TRUE_FIELDS = ("json_safe",)

_FAILURE_ORDER: tuple[str, ...] = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "source_truth_invalid",
    "baseline_tag_unresolved",
    "baseline_commit_mismatch",
    "working_tree_dirty",
    "governance_ci_invalid",
    "governance_ci_not_ready",
    "precondition_ci_invalid",
    "precondition_ci_not_ready",
    "target_task_invalid",
    "target_task_not_ready",
    "dry_run_invalid",
    "dry_run_missing",
    "dry_run_failed",
    "dry_run_target_mismatch",
    "dry_run_not_deterministic",
    "projected_action_missing",
    "projected_evidence_missing",
    "idempotency_invalid",
    "idempotency_missing",
    "idempotency_replay_risk",
    "evidence_snapshot_invalid",
    "evidence_snapshot_missing",
    "human_approval_invalid",
    "human_approval_missing",
    "schema_runtime_invalid",
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_violation",
)

_INVALID_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "source_truth_invalid",
        "governance_ci_invalid",
        "precondition_ci_invalid",
        "target_task_invalid",
        "dry_run_invalid",
        "idempotency_invalid",
        "evidence_snapshot_invalid",
        "human_approval_invalid",
        "schema_runtime_invalid",
    }
)

_SECTION_FLAGS: tuple[str, ...] = (
    "source_truth_ready",
    "governance_ci_ready",
    "precondition_ci_ready",
    "target_task_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "human_approval_ready",
    "schema_migration_safe",
    "db_repair_safe",
    "runtime_boundary_safe",
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "baseline_tags": {
        "read_only_governance_layer": _TAG_GOVERNANCE,
        "write_side_precondition_checker": _TAG_PRECONDITION_CHECKER,
        "write_side_precondition_ci": _TAG_PRECONDITION_CI,
        "write_side_recovery_spec_only": _TAG_RECOVERY_SPEC_ONLY,
    },
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "durable_writes": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


@dataclass(frozen=True)
class RestoreDryRunReadiness:
    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    readiness: dict[str, object]


def restore_dry_run_readiness_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def evaluate_restore_dry_run_readiness(
    payload: object,
) -> RestoreDryRunReadiness:
    section_ready: dict[str, bool] = {flag: False for flag in _SECTION_FLAGS}
    failures: list[str] = []

    if not isinstance(payload, Mapping):
        failures.append("payload_not_mapping")
        return _finalize(failures, section_ready)

    if set(payload.keys()) != set(_TOP_LEVEL_KEYS):
        failures.append("payload_shape_mismatch")
        return _finalize(failures, section_ready)

    section_ready["source_truth_ready"] = _check_source_truth(
        payload["source_truth"], failures
    )
    section_ready["governance_ci_ready"] = _check_ci_like(
        payload["governance_ci"],
        failures,
        invalid_failure="governance_ci_invalid",
        not_ready_failure="governance_ci_not_ready",
    )
    section_ready["precondition_ci_ready"] = _check_ci_like(
        payload["precondition_ci"],
        failures,
        invalid_failure="precondition_ci_invalid",
        not_ready_failure="precondition_ci_not_ready",
    )

    target_task_id, target_task_ready = _check_target_task(
        payload["target_task"], failures
    )
    section_ready["target_task_ready"] = target_task_ready

    dry_run_state, dry_run_ready = _check_dry_run(
        payload["dry_run"], failures, target_task_id
    )
    section_ready["dry_run_ready"] = dry_run_ready

    idempotency_key, idempotency_ready = _check_idempotency(
        payload["idempotency"], failures, target_task_id
    )
    section_ready["idempotency_ready"] = idempotency_ready

    section_ready["evidence_snapshot_ready"] = _check_evidence_snapshot(
        payload["evidence_snapshot"],
        failures,
        target_task_id=target_task_id,
        dry_run_state=dry_run_state,
    )

    section_ready["human_approval_ready"] = _check_human_approval(
        payload["human_approval"],
        failures,
        target_task_id=target_task_id,
        idempotency_key=idempotency_key,
    )

    schema_state = _check_schema_runtime(payload["schema_runtime"], failures)
    section_ready["schema_migration_safe"] = schema_state[
        "schema_migration_safe"
    ]
    section_ready["db_repair_safe"] = schema_state["db_repair_safe"]
    section_ready["runtime_boundary_safe"] = schema_state[
        "runtime_boundary_safe"
    ]

    return _finalize(failures, section_ready)


def render_restore_dry_run_readiness(
    result: RestoreDryRunReadiness,
) -> dict[str, object]:
    return {
        "ready": result.ready,
        "reason_code": result.reason_code,
        "failures": list(result.failures),
        "readiness": deepcopy(result.readiness),
    }


def _finalize(
    failures: list[str], section_ready: dict[str, bool]
) -> RestoreDryRunReadiness:
    ordered = _ordered_failures(failures)
    ready = (
        not ordered
        and all(section_ready[flag] for flag in _SECTION_FLAGS)
    )
    if ready:
        reason_code = _REASON_READY
    elif any(failure in _INVALID_FAILURES for failure in ordered):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    readiness: dict[str, object] = {
        "surface": _SURFACE,
        "version": _VERSION,
        "source_truth_ready": section_ready["source_truth_ready"],
        "governance_ci_ready": section_ready["governance_ci_ready"],
        "precondition_ci_ready": section_ready["precondition_ci_ready"],
        "target_task_ready": section_ready["target_task_ready"],
        "dry_run_ready": section_ready["dry_run_ready"],
        "idempotency_ready": section_ready["idempotency_ready"],
        "evidence_snapshot_ready": section_ready["evidence_snapshot_ready"],
        "human_approval_ready": section_ready["human_approval_ready"],
        "schema_migration_safe": section_ready["schema_migration_safe"],
        "db_repair_safe": section_ready["db_repair_safe"],
        "runtime_boundary_safe": section_ready["runtime_boundary_safe"],
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "durable_writes": False,
        "json_safe": True,
    }

    return RestoreDryRunReadiness(
        ready=ready,
        reason_code=reason_code,
        failures=ordered,
        readiness=readiness,
    )


def _ordered_failures(failures: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for failure in _FAILURE_ORDER:
        if failure in failures and failure not in seen:
            ordered.append(failure)
            seen.add(failure)
    return tuple(ordered)


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _is_bool(value: object) -> bool:
    return type(value) is bool


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and len(value) > 0


def _check_source_truth(section: object, failures: list[str]) -> bool:
    if not isinstance(section, Mapping):
        _append(failures, "source_truth_invalid")
        return False
    if set(section.keys()) != set(_SOURCE_TRUTH_KEYS):
        _append(failures, "source_truth_invalid")
        return False

    current_head = section["current_head"]
    working_tree_clean = section["working_tree_clean"]
    tags = section["tags"]

    if not _is_non_empty_str(current_head):
        _append(failures, "source_truth_invalid")
        return False
    if not _is_bool(working_tree_clean):
        _append(failures, "source_truth_invalid")
        return False
    if not isinstance(tags, Mapping):
        _append(failures, "source_truth_invalid")
        return False

    section_valid = True
    tag_unresolved = False
    commit_mismatch = False

    for expected_tag, expected_commit in _EXPECTED_TAGS.items():
        if expected_tag not in tags:
            tag_unresolved = True
            continue
        actual = tags[expected_tag]
        if not isinstance(actual, str):
            _append(failures, "source_truth_invalid")
            section_valid = False
            continue
        if actual != expected_commit:
            commit_mismatch = True

    if tag_unresolved:
        _append(failures, "baseline_tag_unresolved")
        section_valid = False
    if commit_mismatch:
        _append(failures, "baseline_commit_mismatch")
        section_valid = False
    if working_tree_clean is False:
        _append(failures, "working_tree_dirty")
        section_valid = False

    return section_valid


def _check_ci_like(
    section: object,
    failures: list[str],
    *,
    invalid_failure: str,
    not_ready_failure: str,
) -> bool:
    if not isinstance(section, Mapping):
        _append(failures, invalid_failure)
        return False

    ci_ok = section.get("ci_ok")
    ready_flag = section.get("ready")
    reason_code = section.get("reason_code")
    section_failures = section.get("failures")

    has_ci_ok_true = "ci_ok" in section and ci_ok is True
    has_ready_true = "ready" in section and ready_flag is True

    section_ready = True
    if not (has_ci_ok_true or has_ready_true):
        section_ready = False
    if reason_code != _REASON_READY:
        section_ready = False
    if section_failures != []:
        section_ready = False

    for field in _GOVERNANCE_HAZARD_FALSE_FIELDS:
        if field in section:
            value = section[field]
            if not (value is False or value is None):
                section_ready = False
    for field in _GOVERNANCE_HAZARD_TRUE_FIELDS:
        if field in section:
            value = section[field]
            if not (value is True or value is None):
                section_ready = False

    if not section_ready:
        _append(failures, not_ready_failure)
    return section_ready


def _check_target_task(
    section: object, failures: list[str]
) -> tuple[str | None, bool]:
    if not isinstance(section, Mapping):
        _append(failures, "target_task_invalid")
        return None, False
    if set(section.keys()) != set(_TARGET_TASK_KEYS):
        _append(failures, "target_task_invalid")
        return None, False

    target_task_id = section["target_task_id"]
    task_ready = section["task_ready"]
    snapshot_ready = section["snapshot_ready"]
    lifecycle_ready = section["lifecycle_ready"]

    if not isinstance(target_task_id, str):
        _append(failures, "target_task_invalid")
        return None, False
    if not (
        _is_bool(task_ready)
        and _is_bool(snapshot_ready)
        and _is_bool(lifecycle_ready)
    ):
        _append(failures, "target_task_invalid")
        return None, False

    resolved_id = target_task_id if len(target_task_id) > 0 else None

    if (
        len(target_task_id) == 0
        or not task_ready
        or not snapshot_ready
        or not lifecycle_ready
    ):
        _append(failures, "target_task_not_ready")
        return resolved_id, False

    return resolved_id, True


def _check_dry_run(
    section: object,
    failures: list[str],
    target_task_id: str | None,
) -> tuple[dict[str, object], bool]:
    state: dict[str, object] = {
        "projected_evidence_ref": None,
        "projected_after_snapshot_ref": None,
    }

    if not isinstance(section, Mapping):
        _append(failures, "dry_run_invalid")
        return state, False
    if set(section.keys()) != set(_DRY_RUN_KEYS):
        _append(failures, "dry_run_invalid")
        return state, False

    bool_fields = (
        "dry_run_present",
        "dry_run_ok",
        "mutates_state",
        "creates_files",
        "opens_write_transaction",
        "calls_restore",
    )
    str_fields = (
        "target_task_id",
        "projected_action",
        "projected_evidence_ref",
        "projected_before_snapshot_ref",
        "projected_after_snapshot_ref",
        "determinism_hash",
    )
    for field in bool_fields:
        if not _is_bool(section[field]):
            _append(failures, "dry_run_invalid")
            return state, False
    for field in str_fields:
        if not isinstance(section[field], str):
            _append(failures, "dry_run_invalid")
            return state, False

    state["projected_evidence_ref"] = section["projected_evidence_ref"]
    state["projected_after_snapshot_ref"] = section[
        "projected_after_snapshot_ref"
    ]

    section_ready = True

    if (
        section["mutates_state"] is True
        or section["creates_files"] is True
        or section["opens_write_transaction"] is True
        or section["calls_restore"] is True
    ):
        _append(failures, "dry_run_invalid")
        section_ready = False

    if section["dry_run_present"] is False:
        _append(failures, "dry_run_missing")
        section_ready = False
    if section["dry_run_ok"] is False:
        _append(failures, "dry_run_failed")
        section_ready = False

    if (
        target_task_id is None
        or section["target_task_id"] != target_task_id
        or len(section["target_task_id"]) == 0
    ):
        _append(failures, "dry_run_target_mismatch")
        section_ready = False

    if len(section["determinism_hash"]) == 0:
        _append(failures, "dry_run_not_deterministic")
        section_ready = False

    if len(section["projected_action"]) == 0:
        _append(failures, "projected_action_missing")
        section_ready = False

    if (
        len(section["projected_evidence_ref"]) == 0
        or len(section["projected_before_snapshot_ref"]) == 0
        or len(section["projected_after_snapshot_ref"]) == 0
    ):
        _append(failures, "projected_evidence_missing")
        section_ready = False

    return state, section_ready


def _check_idempotency(
    section: object,
    failures: list[str],
    target_task_id: str | None,
) -> tuple[str | None, bool]:
    if not isinstance(section, Mapping):
        _append(failures, "idempotency_invalid")
        return None, False
    if set(section.keys()) != set(_IDEMPOTENCY_KEYS):
        _append(failures, "idempotency_invalid")
        return None, False

    for field in _IDEMPOTENCY_KEYS:
        if not isinstance(section[field], str):
            _append(failures, "idempotency_invalid")
            return None, False

    idempotency_key = section["idempotency_key"]
    operation_kind = section["operation_kind"]
    section_target_id = section["target_task_id"]
    replay_status = section["replay_status"]

    section_ready = True

    if len(idempotency_key) == 0:
        _append(failures, "idempotency_missing")
        section_ready = False

    if (
        target_task_id is None
        or section_target_id != target_task_id
        or len(section_target_id) == 0
        or len(operation_kind) == 0
        or replay_status not in _REPLAY_STATUS_OK
    ):
        _append(failures, "idempotency_replay_risk")
        section_ready = False

    resolved = idempotency_key if len(idempotency_key) > 0 else None
    return resolved, section_ready


def _check_evidence_snapshot(
    section: object,
    failures: list[str],
    *,
    target_task_id: str | None,
    dry_run_state: dict[str, object],
) -> bool:
    if not isinstance(section, Mapping):
        _append(failures, "evidence_snapshot_invalid")
        return False
    if set(section.keys()) != set(_EVIDENCE_SNAPSHOT_KEYS):
        _append(failures, "evidence_snapshot_invalid")
        return False

    before_ref = section["before_snapshot_ref"]
    after_ref = section["projected_after_snapshot_ref"]
    evidence_ref = section["projected_evidence_ref"]
    immutable = section["immutable"]
    section_target_id = section["target_task_id"]

    if not (
        isinstance(before_ref, str)
        and isinstance(after_ref, str)
        and isinstance(evidence_ref, str)
        and isinstance(section_target_id, str)
        and _is_bool(immutable)
    ):
        _append(failures, "evidence_snapshot_invalid")
        return False

    section_ready = True

    if (
        len(before_ref) == 0
        or len(after_ref) == 0
        or len(evidence_ref) == 0
        or len(section_target_id) == 0
        or immutable is False
    ):
        _append(failures, "evidence_snapshot_missing")
        section_ready = False

    if target_task_id is None or section_target_id != target_task_id:
        _append(failures, "evidence_snapshot_missing")
        section_ready = False

    expected_after = dry_run_state.get("projected_after_snapshot_ref")
    expected_evidence = dry_run_state.get("projected_evidence_ref")
    if (
        expected_after is None
        or expected_evidence is None
        or after_ref != expected_after
        or evidence_ref != expected_evidence
    ):
        _append(failures, "evidence_snapshot_missing")
        section_ready = False

    return section_ready


def _check_human_approval(
    section: object,
    failures: list[str],
    *,
    target_task_id: str | None,
    idempotency_key: str | None,
) -> bool:
    if not isinstance(section, Mapping):
        _append(failures, "human_approval_invalid")
        return False
    if set(section.keys()) != set(_HUMAN_APPROVAL_KEYS):
        _append(failures, "human_approval_invalid")
        return False

    approval_present = section["approval_present"]
    if not _is_bool(approval_present):
        _append(failures, "human_approval_invalid")
        return False

    string_fields = (
        "actor_identity",
        "scope",
        "reason",
        "created_at",
        "target_task_id",
        "bound_idempotency_key",
    )
    for field in string_fields:
        if not isinstance(section[field], str):
            _append(failures, "human_approval_invalid")
            return False

    section_ready = True

    if approval_present is False:
        _append(failures, "human_approval_missing")
        section_ready = False

    if any(len(section[field]) == 0 for field in string_fields):
        _append(failures, "human_approval_invalid")
        section_ready = False

    if target_task_id is None or section["target_task_id"] != target_task_id:
        _append(failures, "human_approval_invalid")
        section_ready = False

    if (
        idempotency_key is None
        or section["bound_idempotency_key"] != idempotency_key
    ):
        _append(failures, "human_approval_invalid")
        section_ready = False

    return section_ready


def _check_schema_runtime(
    section: object, failures: list[str]
) -> dict[str, bool]:
    state = {
        "schema_migration_safe": False,
        "db_repair_safe": False,
        "runtime_boundary_safe": False,
    }

    if not isinstance(section, Mapping):
        _append(failures, "schema_runtime_invalid")
        return state
    if set(section.keys()) != set(_SCHEMA_RUNTIME_KEYS):
        _append(failures, "schema_runtime_invalid")
        return state

    schema_required = section["schema_migration_required"]
    db_repair_required = section["db_repair_required"]
    runtime_boundary_safe = section["runtime_boundary_safe"]

    if not (
        _is_bool(schema_required)
        and _is_bool(db_repair_required)
        and _is_bool(runtime_boundary_safe)
    ):
        _append(failures, "schema_runtime_invalid")
        return state

    if schema_required is True:
        _append(failures, "schema_migration_required")
    else:
        state["schema_migration_safe"] = True

    if db_repair_required is True:
        _append(failures, "db_repair_required")
    else:
        state["db_repair_safe"] = True

    if runtime_boundary_safe is False:
        _append(failures, "runtime_boundary_violation")
    else:
        state["runtime_boundary_safe"] = True

    return state


__all__ = [
    "RestoreDryRunReadiness",
    "restore_dry_run_readiness_manifest",
    "evaluate_restore_dry_run_readiness",
    "render_restore_dry_run_readiness",
]
