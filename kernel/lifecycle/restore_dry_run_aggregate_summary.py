"""Pure aggregate summary for rendered restore dry-run CI verdicts."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "restore_dry_run_aggregate_summary_manifest",
    "summarize_restore_dry_run_readiness",
]


_SURFACE = "restore_dry_run_aggregate_summary"
_VERSION = 1

_REASON_READY = "ready"
_REASON_INVALID = "invalid_summary_payload"
_REASON_NOT_READY = "not_ready"

_INPUT_KEYS = ("readiness_ci", "plan_ci")

_AUTHORIZATION_FIELDS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_READINESS_REQUIRED_KEYS = (
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

_PLAN_REQUIRED_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "plan_ready",
    "plan_reason_code",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "determinism_hash",
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

_PLAN_OPTIONAL_KEYS = (
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
)

_STRING_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "determinism_hash",
)

_CROSS_CHECK_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
)

_MISMATCH_FAILURES = {
    "target_task_id": "target_mismatch",
    "operation_kind": "operation_mismatch",
    "idempotency_key": "idempotency_mismatch",
    "projected_action": "projected_action_mismatch",
    "projected_evidence_ref": "projected_evidence_mismatch",
}

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "readiness_ci_invalid",
    "readiness_ci_not_ready",
    "readiness_ci_authorization_hazard",
    "plan_ci_invalid",
    "plan_ci_not_ready",
    "plan_ci_authorization_hazard",
    "plan_ci_execution_hazard",
    "target_mismatch",
    "operation_mismatch",
    "idempotency_mismatch",
    "projected_action_mismatch",
    "projected_evidence_mismatch",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "readiness_ci_invalid",
        "plan_ci_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": "already_rendered_restore_dry_run_ci_pair",
    "depends_on": {
        "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
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
}


def restore_dry_run_aggregate_summary_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def summarize_restore_dry_run_readiness(payload: object) -> dict[str, object]:
    failures: list[str] = []
    readiness_ok = False
    plan_ok = False
    readiness_values = {field: None for field in _CROSS_CHECK_FIELDS}
    plan_values = {field: None for field in _STRING_FIELDS}
    plan_bools: dict[str, bool | None] = {
        "transaction_required": None,
        "rollback_required": None,
    }

    if not isinstance(payload, _Mapping):
        return _result(
            aggregate_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            readiness_ok=False,
            plan_ok=False,
            plan_values=plan_values,
            plan_bools=plan_bools,
        )

    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    if "readiness_ci" in payload:
        readiness_result = _validate_readiness_ci(payload.get("readiness_ci"))
        readiness_ok = readiness_result["ok"] is True
        _extend(failures, readiness_result["failures"])
        readiness_values = readiness_result["values"]  # type: ignore[assignment]

    if "plan_ci" in payload:
        plan_result = _validate_plan_ci(payload.get("plan_ci"))
        plan_ok = plan_result["ok"] is True
        _extend(failures, plan_result["failures"])
        plan_values = plan_result["values"]  # type: ignore[assignment]
        plan_bools = plan_result["bools"]  # type: ignore[assignment]

    _check_cross_fields(
        readiness_values=readiness_values,
        plan_values=plan_values,
        failures=failures,
    )

    ordered_failures = _ordered_failures(failures)
    aggregate_ok = readiness_ok and plan_ok and ordered_failures == []
    if aggregate_ok:
        reason_code = _REASON_READY
    elif any(failure in _STRUCTURAL_FAILURES for failure in ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        aggregate_ok=aggregate_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        readiness_ok=readiness_ok,
        plan_ok=plan_ok,
        plan_values=plan_values,
        plan_bools=plan_bools,
    )


def _validate_readiness_ci(payload: object) -> dict[str, object]:
    failures: list[str] = []
    values = {field: None for field in _CROSS_CHECK_FIELDS}

    if not isinstance(payload, _Mapping):
        return {"ok": False, "failures": ["readiness_ci_invalid"], "values": values}

    allowed_keys = set(_READINESS_REQUIRED_KEYS) | set(_CROSS_CHECK_FIELDS)
    if (
        not set(_READINESS_REQUIRED_KEYS).issubset(payload.keys())
        or not set(payload.keys()).issubset(allowed_keys)
    ):
        _append(failures, "readiness_ci_invalid")

    for field in _CROSS_CHECK_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value != "":
            values[field] = value

    _validate_common_ci_identity(
        payload=payload,
        surface="restore_dry_run_readiness",
        ready_reason=_REASON_READY,
        ready_field="contract_ready",
        ready_reason_field="contract_reason_code",
        invalid_failure="readiness_ci_invalid",
        not_ready_failure="readiness_ci_not_ready",
        hazard_failure="readiness_ci_authorization_hazard",
        failures=failures,
    )

    return {
        "ok": failures == [],
        "failures": _ordered_failures(failures),
        "values": values,
    }


def _validate_plan_ci(payload: object) -> dict[str, object]:
    failures: list[str] = []
    values = {field: None for field in _STRING_FIELDS}
    bools: dict[str, bool | None] = {
        "transaction_required": None,
        "rollback_required": None,
    }

    if not isinstance(payload, _Mapping):
        return {
            "ok": False,
            "failures": ["plan_ci_invalid"],
            "values": values,
            "bools": bools,
        }

    allowed_keys = set(_PLAN_REQUIRED_KEYS) | set(_PLAN_OPTIONAL_KEYS)
    if (
        not set(_PLAN_REQUIRED_KEYS).issubset(payload.keys())
        or not set(payload.keys()).issubset(allowed_keys)
    ):
        _append(failures, "plan_ci_invalid")

    for field in _STRING_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value != "":
            values[field] = value

    for field in ("transaction_required", "rollback_required"):
        value = payload.get(field)
        if type(value) is bool:
            bools[field] = value

    _validate_common_ci_identity(
        payload=payload,
        surface="restore_dry_run_plan",
        ready_reason=_REASON_READY,
        ready_field="plan_ready",
        ready_reason_field="plan_reason_code",
        invalid_failure="plan_ci_invalid",
        not_ready_failure="plan_ci_not_ready",
        hazard_failure="plan_ci_authorization_hazard",
        failures=failures,
    )

    if _has_invalid_required_strings(payload, _STRING_FIELDS):
        _append(failures, "plan_ci_invalid")
    elif _has_empty_required_strings(payload, _STRING_FIELDS):
        _append(failures, "plan_ci_not_ready")

    for field in ("transaction_required", "rollback_required"):
        value = payload.get(field)
        if field in payload and type(value) is not bool:
            _append(failures, "plan_ci_invalid")
        elif value is False:
            _append(failures, "plan_ci_not_ready")

    executes_value = payload.get("executes_plan")
    if "executes_plan" in payload and type(executes_value) is not bool:
        _append(failures, "plan_ci_invalid")
    elif executes_value is True:
        _append(failures, "plan_ci_execution_hazard")

    return {
        "ok": failures == [],
        "failures": _ordered_failures(failures),
        "values": values,
        "bools": bools,
    }


def _validate_common_ci_identity(
    *,
    payload: _Mapping[str, object],
    surface: str,
    ready_reason: str,
    ready_field: str,
    ready_reason_field: str,
    invalid_failure: str,
    not_ready_failure: str,
    hazard_failure: str,
    failures: list[str],
) -> None:
    ci_ok_value = payload.get("ci_ok")
    reason_value = payload.get("reason_code")
    failures_value = payload.get("failures")
    surface_value = payload.get("surface")
    version_value = payload.get("version")
    ready_value = payload.get(ready_field)
    ready_reason_value = payload.get(ready_reason_field)
    json_safe_value = payload.get("json_safe")

    if "ci_ok" in payload and type(ci_ok_value) is not bool:
        _append(failures, invalid_failure)
    elif ci_ok_value is False:
        _append(failures, not_ready_failure)

    if "reason_code" in payload:
        if not isinstance(reason_value, str):
            _append(failures, invalid_failure)
        elif reason_value != ready_reason:
            _append(failures, not_ready_failure)

    if "failures" in payload:
        if not _is_string_list(failures_value):
            _append(failures, invalid_failure)
        elif failures_value != []:
            _append(failures, not_ready_failure)

    if "surface" in payload and surface_value != surface:
        _append(failures, invalid_failure)

    if "version" in payload:
        if type(version_value) is not int or version_value != _VERSION:
            _append(failures, invalid_failure)

    if ready_field in payload and type(ready_value) is not bool:
        _append(failures, invalid_failure)
    elif ready_value is False:
        _append(failures, not_ready_failure)

    if ready_reason_field in payload:
        expected_ready_reason = (
            "plan_ready"
            if ready_reason_field == "plan_reason_code"
            else ready_reason
        )
        if not isinstance(ready_reason_value, str):
            _append(failures, invalid_failure)
        elif ready_reason_value != expected_ready_reason:
            _append(failures, not_ready_failure)

    for field in _AUTHORIZATION_FIELDS:
        value = payload.get(field)
        if field in payload and type(value) is not bool:
            _append(failures, invalid_failure)
        elif value is True:
            _append(failures, hazard_failure)

    if "json_safe" in payload:
        if type(json_safe_value) is not bool:
            _append(failures, invalid_failure)
        elif json_safe_value is not True:
            _append(failures, invalid_failure)


def _has_invalid_required_strings(
    payload: _Mapping[str, object],
    fields: tuple[str, ...],
) -> bool:
    return any(
        field in payload and not isinstance(payload.get(field), str)
        for field in fields
    )


def _has_empty_required_strings(
    payload: _Mapping[str, object],
    fields: tuple[str, ...],
) -> bool:
    return any(payload.get(field) == "" for field in fields)


def _check_cross_fields(
    *,
    readiness_values: dict[str, str | None],
    plan_values: dict[str, str | None],
    failures: list[str],
) -> None:
    for field in _CROSS_CHECK_FIELDS:
        readiness_value = readiness_values.get(field)
        plan_value = plan_values.get(field)
        if (
            isinstance(readiness_value, str)
            and readiness_value != ""
            and isinstance(plan_value, str)
            and plan_value != ""
            and readiness_value != plan_value
        ):
            _append(failures, _MISMATCH_FAILURES[field])


def _result(
    *,
    aggregate_ok: bool,
    reason_code: str,
    failures: list[str],
    readiness_ok: bool,
    plan_ok: bool,
    plan_values: dict[str, str | None],
    plan_bools: dict[str, bool | None],
) -> dict[str, object]:
    return {
        "aggregate_ok": aggregate_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "summary": {
            "surface": _SURFACE,
            "version": _VERSION,
            "readiness_ci_ok": readiness_ok,
            "plan_ci_ok": plan_ok,
            "target_task_id": plan_values["target_task_id"],
            "operation_kind": plan_values["operation_kind"],
            "idempotency_key": plan_values["idempotency_key"],
            "projected_action": plan_values["projected_action"],
            "projected_evidence_ref": plan_values["projected_evidence_ref"],
            "determinism_hash": plan_values["determinism_hash"],
            "transaction_required": plan_bools["transaction_required"],
            "rollback_required": plan_bools["rollback_required"],
            "restore_authorized": False,
            "write_side_recovery_authorized": False,
            "cli_execution_authorized": False,
            "schema_migration_authorized": False,
            "daemon_server_queue_authorized": False,
            "db_repair_authorized": False,
            "durable_writes": False,
            "executes_plan": False,
            "json_safe": True,
        },
    }


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _extend(failures: list[str], new_failures: object) -> None:
    if isinstance(new_failures, list):
        for failure in new_failures:
            if isinstance(failure, str):
                _append(failures, failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
