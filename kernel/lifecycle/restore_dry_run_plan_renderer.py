"""Read-only renderer for R2 restore dry-run plans.

This module is a pure, JSON-safe renderer. It accepts an already
rendered R1-CI payload together with an already rendered dry-run
candidate payload, and returns a bounded deterministic dry-run plan.
It never opens external resources, never calls upstream builders,
evaluators, renderers, contract checkers, CI consumers, or aggregators,
and keeps every authorization flag False. The renderer never executes
the plan; it merely projects a declarative plan view.
"""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy
from dataclasses import dataclass


__all__ = [
    "RestoreDryRunPlan",
    "restore_dry_run_plan_renderer_manifest",
    "render_restore_dry_run_plan",
    "render_restore_dry_run_plan_payload",
]


_SURFACE = "restore_dry_run_plan_renderer"
_PLAN_SURFACE = "restore_dry_run_plan"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_restore_dry_run_plan_inputs"

_REASON_INVALID = "invalid_plan_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "plan_ready"

_TOP_LEVEL_KEYS = ("readiness_ci", "dry_run_candidate")

_READINESS_CI_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "contract_ready",
    "contract_reason_code",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "json_safe",
)

_READINESS_CI_AUTH_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_READINESS_CI_OPTIONAL_BOOL_FIELDS = _READINESS_CI_AUTH_FLAGS + ("json_safe",)

_READINESS_CI_EXPECTED_SURFACE = "restore_dry_run_readiness"
_READINESS_CI_EXPECTED_VERSION = 1

_DRY_RUN_KEYS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "replay_status",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
    "human_approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
    "approval_present",
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_safe",
    "mutates_state",
    "creates_files",
    "opens_write_transaction",
    "calls_restore",
)

_DRY_RUN_REQUIRED_STRINGS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
    "human_approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
)

_DRY_RUN_BOOL_FIELDS = (
    "approval_present",
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_safe",
    "mutates_state",
    "creates_files",
    "opens_write_transaction",
    "calls_restore",
)

_DRY_RUN_SIDE_EFFECT_FLAGS = (
    "mutates_state",
    "creates_files",
    "opens_write_transaction",
    "calls_restore",
)

_DRY_RUN_REPLAY_VALUES = ("new", "same_attempt_safe")

_DRY_RUN_PROJECTED_EVIDENCE_FIELDS = (
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "readiness_ci_invalid",
    "readiness_ci_not_ready",
    "readiness_ci_authorization_hazard",
    "dry_run_candidate_invalid",
    "dry_run_candidate_not_ready",
    "dry_run_candidate_target_mismatch",
    "dry_run_candidate_not_deterministic",
    "dry_run_candidate_side_effect_hazard",
    "projected_action_missing",
    "projected_evidence_missing",
    "idempotency_missing",
    "idempotency_replay_risk",
    "human_approval_missing",
    "human_approval_invalid",
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_violation",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "readiness_ci_invalid",
        "dry_run_candidate_invalid",
    }
)

_PLAN_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)

_PLAN_KEYS = (
    "surface",
    "version",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
    "human_approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
    "transaction_required",
    "rollback_required",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
        "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": "write-side-precondition-checker-v1",
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "durable_writes": False,
    "executes_plan": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


@dataclass(frozen=True)
class RestoreDryRunPlan:
    plan_ok: bool
    reason_code: str
    failures: tuple[str, ...]
    plan: dict[str, object]


def restore_dry_run_plan_renderer_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def render_restore_dry_run_plan(payload: object) -> RestoreDryRunPlan:
    if not isinstance(payload, _Mapping):
        return _build_plan(
            failures=["payload_not_mapping"],
            projected={},
        )

    if set(payload.keys()) != set(_TOP_LEVEL_KEYS):
        return _build_plan(
            failures=["payload_shape_mismatch"],
            projected={},
        )

    failures: list[str] = []

    readiness_ci = payload.get("readiness_ci")
    dry_run_candidate = payload.get("dry_run_candidate")

    readiness_ci_invalid = _validate_readiness_ci(readiness_ci, failures)
    dry_run_invalid = _validate_dry_run_candidate(
        dry_run_candidate, failures
    )

    if not readiness_ci_invalid:
        _check_readiness_ci_readiness(readiness_ci, failures)

    if not dry_run_invalid:
        _check_dry_run_candidate(dry_run_candidate, failures)

    projected = _project_dry_run_candidate(dry_run_candidate)

    ordered = _ordered_failures(failures)
    return _build_plan(failures=ordered, projected=projected)


def render_restore_dry_run_plan_payload(
    plan: RestoreDryRunPlan,
) -> dict[str, object]:
    return {
        "plan_ok": plan.plan_ok,
        "reason_code": plan.reason_code,
        "failures": list(plan.failures),
        "plan": _deepcopy(plan.plan),
    }


def _build_plan(
    *,
    failures: list[str],
    projected: dict[str, object | None],
) -> RestoreDryRunPlan:
    structural = any(item in _STRUCTURAL_FAILURES for item in failures)
    plan_ok = failures == []
    if plan_ok:
        reason_code = _REASON_READY
    elif structural:
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    plan: dict[str, object] = {
        "surface": _PLAN_SURFACE,
        "version": _VERSION,
        "target_task_id": projected.get("target_task_id"),
        "operation_kind": projected.get("operation_kind"),
        "idempotency_key": projected.get("idempotency_key"),
        "projected_action": projected.get("projected_action"),
        "projected_evidence_ref": projected.get("projected_evidence_ref"),
        "projected_before_snapshot_ref": projected.get(
            "projected_before_snapshot_ref"
        ),
        "projected_after_snapshot_ref": projected.get(
            "projected_after_snapshot_ref"
        ),
        "determinism_hash": projected.get("determinism_hash"),
        "human_approval_ref": projected.get("human_approval_ref"),
        "actor_identity": projected.get("actor_identity"),
        "approval_scope": projected.get("approval_scope"),
        "approval_reason": projected.get("approval_reason"),
        "transaction_required": True,
        "rollback_required": True,
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "durable_writes": False,
        "executes_plan": False,
        "json_safe": True,
    }

    return RestoreDryRunPlan(
        plan_ok=plan_ok,
        reason_code=reason_code,
        failures=tuple(failures),
        plan=plan,
    )


def _validate_readiness_ci(
    readiness_ci: object, failures: list[str]
) -> bool:
    if not isinstance(readiness_ci, _Mapping):
        _append(failures, "readiness_ci_invalid")
        return True

    invalid = False
    if set(readiness_ci.keys()) != set(_READINESS_CI_KEYS):
        _append(failures, "readiness_ci_invalid")
        invalid = True

    ci_ok_value = readiness_ci.get("ci_ok")
    if type(ci_ok_value) is not bool:
        _append(failures, "readiness_ci_invalid")
        invalid = True

    reason_code_value = readiness_ci.get("reason_code")
    if not isinstance(reason_code_value, str):
        _append(failures, "readiness_ci_invalid")
        invalid = True

    failures_value = readiness_ci.get("failures")
    if not _is_string_list(failures_value):
        _append(failures, "readiness_ci_invalid")
        invalid = True

    contract_ready_value = readiness_ci.get("contract_ready")
    if type(contract_ready_value) is not bool:
        _append(failures, "readiness_ci_invalid")
        invalid = True

    contract_reason_value = readiness_ci.get("contract_reason_code")
    if not isinstance(contract_reason_value, str):
        _append(failures, "readiness_ci_invalid")
        invalid = True

    surface_value = readiness_ci.get("surface")
    if surface_value is not None and not isinstance(surface_value, str):
        _append(failures, "readiness_ci_invalid")
        invalid = True

    version_value = readiness_ci.get("version")
    if version_value is not None and type(version_value) is not int:
        _append(failures, "readiness_ci_invalid")
        invalid = True

    for flag in _READINESS_CI_OPTIONAL_BOOL_FIELDS:
        value = readiness_ci.get(flag)
        if value is not None and type(value) is not bool:
            _append(failures, "readiness_ci_invalid")
            invalid = True

    return invalid


def _check_readiness_ci_readiness(
    readiness_ci: object, failures: list[str]
) -> None:
    assert isinstance(readiness_ci, _Mapping)

    if (
        readiness_ci.get("ci_ok") is not True
        or readiness_ci.get("reason_code") != "ready"
        or readiness_ci.get("failures") != []
        or readiness_ci.get("surface") != _READINESS_CI_EXPECTED_SURFACE
        or readiness_ci.get("version") != _READINESS_CI_EXPECTED_VERSION
        or readiness_ci.get("contract_ready") is not True
        or readiness_ci.get("contract_reason_code") != "ready"
        or readiness_ci.get("json_safe") is not True
    ):
        _append(failures, "readiness_ci_not_ready")

    for flag in _READINESS_CI_AUTH_FLAGS:
        value = readiness_ci.get(flag)
        if value is not False:
            _append(failures, "readiness_ci_authorization_hazard")
            break


def _validate_dry_run_candidate(
    candidate: object, failures: list[str]
) -> bool:
    if not isinstance(candidate, _Mapping):
        _append(failures, "dry_run_candidate_invalid")
        return True

    invalid = False
    if set(candidate.keys()) != set(_DRY_RUN_KEYS):
        _append(failures, "dry_run_candidate_invalid")
        invalid = True

    for field in _DRY_RUN_REQUIRED_STRINGS:
        if field not in candidate:
            continue
        value = candidate.get(field)
        if not isinstance(value, str):
            _append(failures, "dry_run_candidate_invalid")
            invalid = True

    replay_value = candidate.get("replay_status")
    if "replay_status" in candidate and not isinstance(replay_value, str):
        _append(failures, "dry_run_candidate_invalid")
        invalid = True

    for field in _DRY_RUN_BOOL_FIELDS:
        if field not in candidate:
            continue
        value = candidate.get(field)
        if type(value) is not bool:
            _append(failures, "dry_run_candidate_invalid")
            invalid = True

    return invalid


def _check_dry_run_candidate(
    candidate: object, failures: list[str]
) -> None:
    assert isinstance(candidate, _Mapping)

    empty_strings: set[str] = set()
    for field in _DRY_RUN_REQUIRED_STRINGS:
        value = candidate.get(field)
        if isinstance(value, str) and value == "":
            empty_strings.add(field)

    if empty_strings:
        _append(failures, "dry_run_candidate_not_ready")

    if "determinism_hash" in empty_strings:
        _append(failures, "dry_run_candidate_not_deterministic")

    side_effect_hazard = False
    for flag in _DRY_RUN_SIDE_EFFECT_FLAGS:
        if candidate.get(flag) is True:
            side_effect_hazard = True
            break
    if side_effect_hazard:
        _append(failures, "dry_run_candidate_side_effect_hazard")

    if "projected_action" in empty_strings:
        _append(failures, "projected_action_missing")

    if any(
        field in empty_strings
        for field in _DRY_RUN_PROJECTED_EVIDENCE_FIELDS
    ):
        _append(failures, "projected_evidence_missing")

    if "idempotency_key" in empty_strings:
        _append(failures, "idempotency_missing")

    replay_value = candidate.get("replay_status")
    if (
        not isinstance(replay_value, str)
        or replay_value not in _DRY_RUN_REPLAY_VALUES
    ):
        _append(failures, "idempotency_replay_risk")

    approval_present = candidate.get("approval_present")
    human_approval_ref = candidate.get("human_approval_ref")
    if (
        approval_present is not True
        or not isinstance(human_approval_ref, str)
        or human_approval_ref == ""
    ):
        _append(failures, "human_approval_missing")

    approval_invalid = False
    for field in (
        "human_approval_ref",
        "actor_identity",
        "approval_scope",
        "approval_reason",
    ):
        if field in empty_strings:
            approval_invalid = True
            break
    if approval_invalid:
        _append(failures, "human_approval_invalid")

    if candidate.get("schema_migration_required") is True:
        _append(failures, "schema_migration_required")

    if candidate.get("db_repair_required") is True:
        _append(failures, "db_repair_required")

    if candidate.get("runtime_boundary_safe") is False:
        _append(failures, "runtime_boundary_violation")


def _project_dry_run_candidate(
    candidate: object,
) -> dict[str, object | None]:
    projected: dict[str, object | None] = {
        field: None
        for field in _DRY_RUN_REQUIRED_STRINGS
    }
    if not isinstance(candidate, _Mapping):
        return projected
    for field in _DRY_RUN_REQUIRED_STRINGS:
        value = candidate.get(field)
        if isinstance(value, str) and value != "":
            projected[field] = value
    return projected


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
