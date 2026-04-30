"""Read-only CI projection for rendered R2 restore dry-run plans.

This module is a pure, JSON-safe consumer. It accepts an already
rendered restore dry-run plan payload and returns a bounded CI verdict.
It never opens external resources, never calls upstream builders,
evaluators, renderers, contract checkers, CI consumers, or aggregators,
and keeps every authorization flag False. ci_ok=True does not authorize
restore or write-side execution; the plan is never executed here.
"""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "restore_dry_run_plan_ci_manifest",
    "consume_restore_dry_run_plan_ci",
]


_SURFACE = "restore_dry_run_plan_ci"
_VERSION = 1
_INPUT_SHAPE = "rendered_restore_dry_run_plan"
_PLAN_SURFACE = "restore_dry_run_plan"
_PLAN_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_PLAN_REASON_READY = "plan_ready"

_PAYLOAD_KEYS = ("plan_ok", "reason_code", "failures", "plan")

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

_PLAN_REQUIRED_STRINGS = (
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

_PLAN_READINESS_BOOL_FIELDS = (
    "transaction_required",
    "rollback_required",
)

_PLAN_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_OUTPUT_STRING_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
)

_OUTPUT_BOOL_FIELDS = (
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

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "payload_failures_invalid",
    "plan_invalid",
    "plan_shape_mismatch",
    "plan_surface_invalid",
    "plan_version_invalid",
    "plan_field_invalid",
    "plan_field_missing",
    "plan_not_ready",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "execution_flag_invalid",
    "execution_flag_true",
    "json_safe_invalid",
    "source_plan_not_ready",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "plan_invalid",
        "plan_shape_mismatch",
        "plan_surface_invalid",
        "plan_version_invalid",
        "plan_field_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
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
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _PLAN_REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


def restore_dry_run_plan_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_restore_dry_run_plan_ci(payload: object) -> dict[str, object]:
    if not isinstance(payload, _Mapping):
        return _empty_result(
            failures=["payload_not_mapping"],
            reason_code=_REASON_INVALID,
        )

    failures: list[str] = []
    structurally_invalid = False

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True

    plan_ok_value = payload.get("plan_ok")
    plan_reason_value = payload.get("reason_code")
    payload_failures = payload.get("failures")
    plan = payload.get("plan")

    plan_ok_is_valid = "plan_ok" in payload and type(plan_ok_value) is bool
    plan_reason_is_valid = (
        "reason_code" in payload and isinstance(plan_reason_value, str)
    )
    failures_are_valid = (
        "failures" in payload and _is_string_list(payload_failures)
    )
    plan_is_mapping = (
        "plan" in payload and isinstance(plan, _Mapping)
    )

    if "plan_ok" in payload and not plan_ok_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "reason_code" in payload and not plan_reason_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_failures_invalid")
        structurally_invalid = True
    if "plan" in payload and not plan_is_mapping:
        _append(failures, "plan_invalid")
        structurally_invalid = True

    surface: str | None = None
    version: int | None = None
    string_projections: dict[str, str | None] = {
        field: None for field in _OUTPUT_STRING_FIELDS
    }
    bool_projections: dict[str, bool | None] = {
        field: None for field in _OUTPUT_BOOL_FIELDS
    }

    if plan_is_mapping:
        assert isinstance(plan, _Mapping)
        surface, version = _project_plan_identity(plan)
        for field in _OUTPUT_STRING_FIELDS:
            value = plan.get(field)
            if isinstance(value, str) and value != "":
                string_projections[field] = value
        for field in _OUTPUT_BOOL_FIELDS:
            value = plan.get(field)
            if type(value) is bool:
                bool_projections[field] = value

        plan_structural = _validate_plan(plan, failures)
        if plan_structural:
            structurally_invalid = True
        _check_plan_readiness(plan, failures)

    if (
        plan_ok_is_valid
        and plan_reason_is_valid
        and failures_are_valid
        and (
            plan_ok_value is not True
            or plan_reason_value != _PLAN_REASON_READY
            or payload_failures != []
        )
    ):
        _append(failures, "source_plan_not_ready")

    ordered_failures = _ordered_failures(failures)
    has_structural = structurally_invalid or any(
        failure in _STRUCTURAL_FAILURES for failure in ordered_failures
    )
    ci_ok = not has_structural and ordered_failures == []
    if ci_ok:
        reason_code = _REASON_READY
    elif has_structural:
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ci_ok=ci_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        surface=surface,
        version=version,
        plan_ready=plan_ok_value if plan_ok_is_valid else False,
        plan_reason_code=(
            plan_reason_value if plan_reason_is_valid else _REASON_INVALID
        ),
        string_projections=string_projections,
        bool_projections=bool_projections,
    )


def _project_plan_identity(
    plan: _Mapping[str, object],
) -> tuple[str | None, int | None]:
    surface_value = plan.get("surface")
    surface = surface_value if isinstance(surface_value, str) else None
    version_value = plan.get("version")
    version = version_value if type(version_value) is int else None
    return surface, version


def _validate_plan(plan: _Mapping[str, object], failures: list[str]) -> bool:
    structural = False

    if set(plan.keys()) != set(_PLAN_KEYS):
        _append(failures, "plan_shape_mismatch")
        structural = True

    if "surface" in plan and plan.get("surface") != _PLAN_SURFACE:
        _append(failures, "plan_surface_invalid")
        structural = True

    if "version" in plan:
        version_value = plan.get("version")
        if (
            type(version_value) is not int
            or version_value != _PLAN_VERSION
        ):
            _append(failures, "plan_version_invalid")
            structural = True

    for field in _PLAN_REQUIRED_STRINGS:
        if field not in plan:
            continue
        value = plan.get(field)
        if not isinstance(value, str):
            _append(failures, "plan_field_invalid")
            structural = True

    for field in _PLAN_READINESS_BOOL_FIELDS:
        if field not in plan:
            continue
        value = plan.get(field)
        if type(value) is not bool:
            _append(failures, "plan_field_invalid")
            structural = True

    for field in _PLAN_AUTHORIZATION_FLAGS:
        if field not in plan:
            continue
        value = plan.get(field)
        if type(value) is not bool:
            _append(failures, "authorization_flag_invalid")
            structural = True

    if "executes_plan" in plan:
        value = plan.get("executes_plan")
        if type(value) is not bool:
            _append(failures, "execution_flag_invalid")
            structural = True

    if "json_safe" in plan:
        value = plan.get("json_safe")
        if type(value) is not bool:
            _append(failures, "json_safe_invalid")
            structural = True

    return structural


def _check_plan_readiness(
    plan: _Mapping[str, object], failures: list[str]
) -> None:
    for field in _PLAN_REQUIRED_STRINGS:
        value = plan.get(field)
        if isinstance(value, str) and value == "":
            _append(failures, "plan_field_missing")
            break

    for field in _PLAN_READINESS_BOOL_FIELDS:
        value = plan.get(field)
        if type(value) is bool and value is False:
            _append(failures, "plan_not_ready")
            break

    for field in _PLAN_AUTHORIZATION_FLAGS:
        value = plan.get(field)
        if type(value) is bool and value is True:
            _append(failures, "authorization_flag_true")
            break

    executes_value = plan.get("executes_plan")
    if type(executes_value) is bool and executes_value is True:
        _append(failures, "execution_flag_true")

    json_safe_value = plan.get("json_safe")
    if type(json_safe_value) is bool and json_safe_value is False:
        _append(failures, "json_safe_invalid")


def _empty_result(
    *,
    failures: list[str],
    reason_code: str,
) -> dict[str, object]:
    return _result(
        ci_ok=False,
        reason_code=reason_code,
        failures=failures,
        surface=None,
        version=None,
        plan_ready=False,
        plan_reason_code=_REASON_INVALID,
        string_projections={field: None for field in _OUTPUT_STRING_FIELDS},
        bool_projections={field: None for field in _OUTPUT_BOOL_FIELDS},
    )


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    surface: str | None,
    version: int | None,
    plan_ready: bool,
    plan_reason_code: str,
    string_projections: dict[str, str | None],
    bool_projections: dict[str, bool | None],
) -> dict[str, object]:
    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "surface": surface,
        "version": version,
        "plan_ready": plan_ready,
        "plan_reason_code": plan_reason_code,
        "target_task_id": string_projections["target_task_id"],
        "operation_kind": string_projections["operation_kind"],
        "idempotency_key": string_projections["idempotency_key"],
        "projected_action": string_projections["projected_action"],
        "projected_evidence_ref": string_projections["projected_evidence_ref"],
        "projected_before_snapshot_ref": string_projections[
            "projected_before_snapshot_ref"
        ],
        "projected_after_snapshot_ref": string_projections[
            "projected_after_snapshot_ref"
        ],
        "determinism_hash": string_projections["determinism_hash"],
        "transaction_required": bool_projections["transaction_required"],
        "rollback_required": bool_projections["rollback_required"],
        "restore_authorized": bool_projections["restore_authorized"],
        "write_side_recovery_authorized": bool_projections[
            "write_side_recovery_authorized"
        ],
        "cli_execution_authorized": bool_projections[
            "cli_execution_authorized"
        ],
        "schema_migration_authorized": bool_projections[
            "schema_migration_authorized"
        ],
        "daemon_server_queue_authorized": bool_projections[
            "daemon_server_queue_authorized"
        ],
        "db_repair_authorized": bool_projections["db_repair_authorized"],
        "durable_writes": bool_projections["durable_writes"],
        "executes_plan": bool_projections["executes_plan"],
        "json_safe": bool_projections["json_safe"],
    }


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
