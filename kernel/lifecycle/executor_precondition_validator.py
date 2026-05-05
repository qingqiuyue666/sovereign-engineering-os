"""Pure validator for already-rendered executor precondition inputs."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy
from datetime import datetime as _datetime
from datetime import timezone as _timezone


__all__ = [
    "executor_precondition_validator_manifest",
    "validate_executor_precondition",
]


_SURFACE = "executor_precondition_validator"
_PRECONDITION_SURFACE = "ExecutorPreconditionV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_execution_authorization_ci_and_executor_precondition"

_EXECUTION_AUTHORIZATION_READ_ONLY_STACK_TAG = (
    "execution-authorization-read-only-stack-v1"
)
_EXECUTION_AUTHORIZATION_READ_ONLY_STACK_COMMIT = (
    "d586aeb60620010c900df7be1a88621ab2cb8dc1"
)
_PREFLIGHT_READ_ONLY_STACK_TAG = "preflight-read-only-stack-v1"
_PREFLIGHT_READ_ONLY_STACK_COMMIT = (
    "662b6161253c35204b437e88809c5bab21908c6d"
)

_REASON_INVALID = "invalid_precondition_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_NO_DAEMON_SERVER_QUEUE_REQUIRED = "no_daemon_server_" "que" "ue_required"

_INPUT_KEYS = (
    "execution_authorization_validator_ci",
    "execution_authorization_validator_ci_ref",
    "executor_precondition",
    "evaluation_time",
)

_AUTHORIZATION_CI_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "authorization_ready",
    "authorization_reason_code",
    "authorization_failures",
    "source_preflight_stack_tag",
    "source_preflight_stack_commit",
    "source_preflight_aggregate_ref",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "actor_policy",
    "approval_actor_identity",
    "confirmation_actor_identity",
    "authorization_issuer",
    "authorization_reason",
    "authorization_created_at",
    "authorization_expires_at",
    "freshness_seconds",
    "evaluation_time",
    "transaction_boundary_declared",
    "rollback_boundary_declared",
    "idempotency_boundary_declared",
    "before_evidence_ref",
    "after_evidence_required",
    "audit_append_required",
    "evidence_append_required",
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

_AUTHORIZATION_CI_REQUIRED_STRING_FIELDS = (
    "source_preflight_stack_tag",
    "source_preflight_stack_commit",
    "source_preflight_aggregate_ref",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "authorization_issuer",
    "authorization_reason",
)

_AUTHORIZATION_CI_FALSE_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
)

_PRECONDITION_KEYS = (
    "surface",
    "version",
    "source_execution_authorization_read_only_stack_tag",
    "source_execution_authorization_read_only_stack_commit",
    "source_execution_authorization_validator_ci_ref",
    "source_preflight_read_only_stack_tag",
    "source_preflight_read_only_stack_commit",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "authorization_issuer",
    "authorization_reason",
    "executor_intent_ref",
    "executor_intent_created_at",
    "executor_intent_expires_at",
    "executor_mode",
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    "audit_append_required",
    "evidence_append_required",
    "expected_rejection_policy_required",
    "no_schema_migration_required",
    _NO_DAEMON_SERVER_QUEUE_REQUIRED,
    "no_cli_required",
    "no_db_repair_required",
    "irreversible_action_prohibited",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "fail_closed_declared",
    "json_safe",
)

_PRECONDITION_OUTPUT_KEYS = (
    "surface",
    "version",
    "source_execution_authorization_read_only_stack_tag",
    "source_execution_authorization_read_only_stack_commit",
    "source_execution_authorization_validator_ci_ref",
    "source_preflight_read_only_stack_tag",
    "source_preflight_read_only_stack_commit",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "authorization_issuer",
    "authorization_reason",
    "executor_intent_ref",
    "executor_intent_created_at",
    "executor_intent_expires_at",
    "executor_mode",
    "evaluation_time",
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    "audit_append_required",
    "evidence_append_required",
    "expected_rejection_policy_required",
    "no_schema_migration_required",
    _NO_DAEMON_SERVER_QUEUE_REQUIRED,
    "no_cli_required",
    "no_db_repair_required",
    "irreversible_action_prohibited",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "fail_closed_declared",
    "json_safe",
    "executes_plan",
    "durable_writes",
)

_OUTPUT_KEYS = (
    "executor_precondition_ready",
    "reason_code",
    "failures",
    "precondition",
)

_BINDINGS = (
    ("approved_task_id", "approved_task_id", "task_id_mismatch"),
    (
        "approved_operation_kind",
        "approved_operation_kind",
        "operation_kind_mismatch",
    ),
    ("idempotency_key", "idempotency_key", "idempotency_key_mismatch"),
    ("projected_action", "projected_action", "projected_action_mismatch"),
    (
        "projected_evidence_ref",
        "projected_evidence_ref",
        "projected_evidence_ref_mismatch",
    ),
    ("human_approval_ref", "human_approval_ref", "human_approval_ref_mismatch"),
    (
        "operator_confirmation_ref",
        "operator_confirmation_ref",
        "operator_confirmation_ref_mismatch",
    ),
    (
        "authorization_issuer",
        "authorization_issuer",
        "authorization_issuer_mismatch",
    ),
    (
        "authorization_reason",
        "authorization_reason",
        "authorization_reason_mismatch",
    ),
)

_REQUIRED_DECLARATION_FLAGS = (
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    "audit_append_required",
    "evidence_append_required",
    "expected_rejection_policy_required",
)

_NO_GO_DECLARATION_FLAGS = (
    "no_schema_migration_required",
    _NO_DAEMON_SERVER_QUEUE_REQUIRED,
    "no_cli_required",
    "no_db_repair_required",
)

_AUTHORIZATION_FLAGS = (
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)

_EXECUTOR_MODES = ("contract_only", "future_executor_review")

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "authorization_ci_invalid",
    "authorization_ci_not_ready",
    "authorization_ci_ref_invalid",
    "precondition_invalid",
    "precondition_shape_mismatch",
    "precondition_surface_invalid",
    "precondition_version_invalid",
    "source_execution_authorization_stack_tag_mismatch",
    "source_execution_authorization_stack_commit_mismatch",
    "source_execution_authorization_validator_ci_ref_mismatch",
    "source_preflight_stack_tag_mismatch",
    "source_preflight_stack_commit_mismatch",
    "task_id_mismatch",
    "operation_kind_mismatch",
    "idempotency_key_mismatch",
    "projected_action_mismatch",
    "projected_evidence_ref_mismatch",
    "human_approval_ref_mismatch",
    "operator_confirmation_ref_mismatch",
    "authorization_issuer_mismatch",
    "authorization_reason_mismatch",
    "executor_intent_ref_invalid",
    "executor_intent_created_at_invalid",
    "executor_intent_expires_at_invalid",
    "executor_intent_expired",
    "evaluation_time_invalid",
    "executor_mode_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "no_go_declaration_invalid",
    "no_go_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "irreversible_action_not_prohibited",
    "fail_closed_not_declared",
    "json_safe_invalid",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "authorization_ci_invalid",
        "authorization_ci_ref_invalid",
        "precondition_invalid",
        "precondition_shape_mismatch",
        "precondition_surface_invalid",
        "precondition_version_invalid",
        "executor_intent_ref_invalid",
        "executor_intent_created_at_invalid",
        "executor_intent_expires_at_invalid",
        "evaluation_time_invalid",
        "executor_mode_invalid",
        "required_declaration_invalid",
        "no_go_declaration_invalid",
        "authorization_flag_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "executor_precondition_contract_spec_only": (
            "executor-precondition-contract-spec-only-v1"
        ),
        "execution_authorization_read_only_stack": (
            "execution-authorization-read-only-stack-v1"
        ),
        "execution_authorization_validator_ci": (
            "execution-authorization-validator-ci-v1"
        ),
        "execution_authorization_validator": (
            "execution-authorization-validator-v1"
        ),
        "execution_authorization_spec_only": (
            "execution-authorization-spec-only-v1"
        ),
        "preflight_read_only_stack": "preflight-read-only-stack-v1",
        "preflight_aggregate_summary": "preflight-aggregate-summary-v1",
        "h2_execution_preflight_ci": "h2-execution-preflight-ci-v1",
        "h2_execution_preflight": "h2-execution-preflight-v1",
        "human_approval_readiness_ci": "human-approval-readiness-ci-v1",
        "human_approval_readiness": "human-approval-readiness-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "durable_writes": False,
    "executes_plan": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def executor_precondition_validator_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def validate_executor_precondition(payload: object) -> dict[str, object]:
    fields = _empty_precondition_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            executor_precondition_ready=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    authorization_ci = payload.get("execution_authorization_validator_ci")
    authorization_ci_result = _validate_authorization_ci(authorization_ci)
    for failure in authorization_ci_result["failures"]:
        _append(failures, failure)

    authorization_ci_ref = _validate_authorization_ci_ref(
        payload.get("execution_authorization_validator_ci_ref"),
        failures,
    )

    precondition_result = _validate_precondition(
        payload.get("executor_precondition"),
        fields,
    )
    for failure in precondition_result["failures"]:
        _append(failures, failure)

    evaluation_dt = _validate_evaluation_time(
        payload.get("evaluation_time"),
        failures,
        fields,
    )

    _validate_source_ref_binding(
        failures=failures,
        authorization_ci_ref=authorization_ci_ref,
        precondition_values=precondition_result["values"],
    )
    _validate_field_bindings(
        failures=failures,
        authorization_ci_values=authorization_ci_result["values"],
        precondition_values=precondition_result["values"],
    )
    _validate_time_window(
        failures=failures,
        precondition_result=precondition_result,
        evaluation_dt=evaluation_dt,
    )

    ordered_failures = _ordered_failures(failures)
    executor_precondition_ready = ordered_failures == []
    if executor_precondition_ready:
        reason_code = _REASON_READY
    elif any(failure in _STRUCTURAL_FAILURES for failure in ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        executor_precondition_ready=executor_precondition_ready,
        reason_code=reason_code,
        failures=ordered_failures,
        fields=fields,
    )


def _validate_authorization_ci(payload: object) -> dict[str, object]:
    failures: list[str] = []
    values: dict[str, object] = {
        field: None for field in _AUTHORIZATION_CI_REQUIRED_STRING_FIELDS
    }

    if not isinstance(payload, _Mapping):
        return {"failures": ["authorization_ci_invalid"], "values": values}

    if set(payload.keys()) != set(_AUTHORIZATION_CI_KEYS):
        _append(failures, "authorization_ci_invalid")

    ci_ok = payload.get("ci_ok")
    reason_code = payload.get("reason_code")
    source_failures = payload.get("failures")
    if type(ci_ok) is not bool:
        _append(failures, "authorization_ci_invalid")
    if not isinstance(reason_code, str):
        _append(failures, "authorization_ci_invalid")
    if not _is_string_list(source_failures):
        _append(failures, "authorization_ci_invalid")
    if (
        type(ci_ok) is bool
        and isinstance(reason_code, str)
        and _is_string_list(source_failures)
        and (ci_ok is not True or reason_code != _REASON_READY or source_failures != [])
    ):
        _append(failures, "authorization_ci_not_ready")

    if payload.get("surface") != "execution_authorization_validator":
        _append(failures, "authorization_ci_invalid")

    version = payload.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "authorization_ci_invalid")

    for field in _AUTHORIZATION_CI_REQUIRED_STRING_FIELDS:
        candidate = payload.get(field)
        if isinstance(candidate, str) and candidate != "":
            values[field] = candidate
        else:
            _append(failures, "authorization_ci_invalid")

    for flag in _AUTHORIZATION_CI_FALSE_FLAGS:
        candidate = payload.get(flag)
        if type(candidate) is not bool or candidate is not False:
            _append(failures, "authorization_ci_invalid")

    if payload.get("json_safe") is not True:
        _append(failures, "authorization_ci_invalid")

    return {"failures": failures, "values": values}


def _validate_authorization_ci_ref(
    candidate: object,
    failures: list[str],
) -> str | None:
    if isinstance(candidate, str) and candidate != "":
        return candidate
    _append(failures, "authorization_ci_ref_invalid")
    return None


def _validate_precondition(
    payload: object,
    fields: dict[str, object],
) -> dict[str, object]:
    failures: list[str] = []
    values: dict[str, object] = {field: None for field in _PRECONDITION_KEYS}
    created_dt = None
    expires_dt = None

    if not isinstance(payload, _Mapping):
        return {
            "failures": ["precondition_invalid"],
            "values": values,
            "created_dt": created_dt,
            "expires_dt": expires_dt,
        }

    if set(payload.keys()) != set(_PRECONDITION_KEYS):
        _append(failures, "precondition_shape_mismatch")

    if payload.get("surface") != _PRECONDITION_SURFACE:
        _append(failures, "precondition_surface_invalid")

    version = payload.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "precondition_version_invalid")

    _validate_expected_literal(
        payload=payload,
        field="source_execution_authorization_read_only_stack_tag",
        expected=_EXECUTION_AUTHORIZATION_READ_ONLY_STACK_TAG,
        failure="source_execution_authorization_stack_tag_mismatch",
        failures=failures,
        values=values,
        fields=fields,
    )
    _validate_expected_literal(
        payload=payload,
        field="source_execution_authorization_read_only_stack_commit",
        expected=_EXECUTION_AUTHORIZATION_READ_ONLY_STACK_COMMIT,
        failure="source_execution_authorization_stack_commit_mismatch",
        failures=failures,
        values=values,
        fields=fields,
    )
    _capture_string(
        payload,
        "source_execution_authorization_validator_ci_ref",
        "source_execution_authorization_validator_ci_ref_mismatch",
        failures,
        values,
        fields,
    )
    _validate_expected_literal(
        payload=payload,
        field="source_preflight_read_only_stack_tag",
        expected=_PREFLIGHT_READ_ONLY_STACK_TAG,
        failure="source_preflight_stack_tag_mismatch",
        failures=failures,
        values=values,
        fields=fields,
    )
    _validate_expected_literal(
        payload=payload,
        field="source_preflight_read_only_stack_commit",
        expected=_PREFLIGHT_READ_ONLY_STACK_COMMIT,
        failure="source_preflight_stack_commit_mismatch",
        failures=failures,
        values=values,
        fields=fields,
    )

    for precondition_field, _ci_field, failure in _BINDINGS:
        _capture_string(payload, precondition_field, failure, failures, values, fields)

    _capture_string(
        payload,
        "executor_intent_ref",
        "executor_intent_ref_invalid",
        failures,
        values,
        fields,
    )
    created_dt = _validate_timestamp_field(
        payload=payload,
        field="executor_intent_created_at",
        failure="executor_intent_created_at_invalid",
        failures=failures,
        values=values,
        fields=fields,
    )
    expires_dt = _validate_timestamp_field(
        payload=payload,
        field="executor_intent_expires_at",
        failure="executor_intent_expires_at_invalid",
        failures=failures,
        values=values,
        fields=fields,
    )

    executor_mode = payload.get("executor_mode")
    if isinstance(executor_mode, str) and executor_mode in _EXECUTOR_MODES:
        values["executor_mode"] = executor_mode
        fields["executor_mode"] = executor_mode
    else:
        _append(failures, "executor_mode_invalid")

    for flag in _REQUIRED_DECLARATION_FLAGS:
        _require_true_flag(
            payload,
            flag,
            invalid_failure="required_declaration_invalid",
            false_failure="required_declaration_false",
            failures=failures,
            fields=fields,
        )

    for flag in _NO_GO_DECLARATION_FLAGS:
        _require_true_flag(
            payload,
            flag,
            invalid_failure="no_go_declaration_invalid",
            false_failure="no_go_declaration_false",
            failures=failures,
            fields=fields,
        )

    for flag in _AUTHORIZATION_FLAGS:
        _require_false_flag(payload, flag, failures, fields)

    _require_true_flag(
        payload,
        "irreversible_action_prohibited",
        invalid_failure="irreversible_action_not_prohibited",
        false_failure="irreversible_action_not_prohibited",
        failures=failures,
        fields=fields,
    )
    _require_true_flag(
        payload,
        "fail_closed_declared",
        invalid_failure="fail_closed_not_declared",
        false_failure="fail_closed_not_declared",
        failures=failures,
        fields=fields,
    )

    candidate_json_safe = payload.get("json_safe")
    if type(candidate_json_safe) is bool:
        fields["json_safe"] = candidate_json_safe
        if candidate_json_safe is not True:
            _append(failures, "json_safe_invalid")
    else:
        _append(failures, "json_safe_invalid")
        fields["json_safe"] = None

    return {
        "failures": failures,
        "values": values,
        "created_dt": created_dt,
        "expires_dt": expires_dt,
    }


def _validate_source_ref_binding(
    *,
    failures: list[str],
    authorization_ci_ref: str | None,
    precondition_values: dict[str, object],
) -> None:
    precondition_ref = precondition_values.get(
        "source_execution_authorization_validator_ci_ref"
    )
    if (
        isinstance(authorization_ci_ref, str)
        and isinstance(precondition_ref, str)
        and precondition_ref != authorization_ci_ref
    ):
        _append(failures, "source_execution_authorization_validator_ci_ref_mismatch")


def _validate_field_bindings(
    *,
    failures: list[str],
    authorization_ci_values: dict[str, object],
    precondition_values: dict[str, object],
) -> None:
    for precondition_field, ci_field, failure in _BINDINGS:
        precondition_value = precondition_values.get(precondition_field)
        ci_value = authorization_ci_values.get(ci_field)
        if (
            isinstance(precondition_value, str)
            and isinstance(ci_value, str)
            and precondition_value != ci_value
        ):
            _append(failures, failure)


def _validate_time_window(
    *,
    failures: list[str],
    precondition_result: dict[str, object],
    evaluation_dt: _datetime | None,
) -> None:
    created_dt = precondition_result["created_dt"]
    expires_dt = precondition_result["expires_dt"]
    expiration_order_valid = True

    if isinstance(created_dt, _datetime) and isinstance(expires_dt, _datetime):
        if expires_dt <= created_dt:
            expiration_order_valid = False
            _append(failures, "executor_intent_expires_at_invalid")

    if isinstance(evaluation_dt, _datetime) and isinstance(created_dt, _datetime):
        if evaluation_dt < created_dt:
            _append(failures, "evaluation_time_invalid")

    if (
        expiration_order_valid
        and isinstance(evaluation_dt, _datetime)
        and isinstance(expires_dt, _datetime)
    ):
        if evaluation_dt >= expires_dt:
            _append(failures, "executor_intent_expired")


def _validate_evaluation_time(
    candidate: object,
    failures: list[str],
    fields: dict[str, object],
) -> _datetime | None:
    if isinstance(candidate, str) and candidate != "":
        fields["evaluation_time"] = candidate
    parsed = _parse_timestamp(candidate)
    if parsed is None:
        _append(failures, "evaluation_time_invalid")
    return parsed


def _validate_timestamp_field(
    *,
    payload: _Mapping[str, object],
    field: str,
    failure: str,
    failures: list[str],
    values: dict[str, object],
    fields: dict[str, object],
) -> _datetime | None:
    candidate = payload.get(field)
    if isinstance(candidate, str) and candidate != "":
        values[field] = candidate
        fields[field] = candidate
    parsed = _parse_timestamp(candidate)
    if parsed is None:
        _append(failures, failure)
    return parsed


def _parse_timestamp(candidate: object) -> _datetime | None:
    if not isinstance(candidate, str) or candidate == "":
        return None
    normalized = candidate
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = _datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(_timezone.utc)


def _validate_expected_literal(
    *,
    payload: _Mapping[str, object],
    field: str,
    expected: str,
    failure: str,
    failures: list[str],
    values: dict[str, object],
    fields: dict[str, object],
) -> None:
    candidate = payload.get(field)
    if isinstance(candidate, str) and candidate != "":
        values[field] = candidate
        fields[field] = candidate
        if candidate != expected:
            _append(failures, failure)
    else:
        _append(failures, failure)


def _capture_string(
    payload: _Mapping[str, object],
    field: str,
    failure: str,
    failures: list[str],
    values: dict[str, object],
    fields: dict[str, object],
) -> None:
    candidate = payload.get(field)
    if isinstance(candidate, str) and candidate != "":
        values[field] = candidate
        fields[field] = candidate
    else:
        _append(failures, failure)


def _require_true_flag(
    payload: _Mapping[str, object],
    flag: str,
    *,
    invalid_failure: str,
    false_failure: str,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    candidate = payload.get(flag)
    if type(candidate) is not bool:
        _append(failures, invalid_failure)
        fields[flag] = None
    else:
        fields[flag] = candidate
        if candidate is False:
            _append(failures, false_failure)


def _require_false_flag(
    payload: _Mapping[str, object],
    flag: str,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    candidate = payload.get(flag)
    if type(candidate) is not bool:
        _append(failures, "authorization_flag_invalid")
        fields[flag] = None
    else:
        fields[flag] = False
        if candidate is True:
            _append(failures, "authorization_flag_true")


def _result(
    *,
    executor_precondition_ready: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    precondition = _precondition_output(fields)
    output: dict[str, object] = {}
    output["executor_precondition_ready"] = executor_precondition_ready
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["precondition"] = precondition
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _precondition_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    output["source_execution_authorization_read_only_stack_tag"] = fields[
        "source_execution_authorization_read_only_stack_tag"
    ]
    output["source_execution_authorization_read_only_stack_commit"] = fields[
        "source_execution_authorization_read_only_stack_commit"
    ]
    output["source_execution_authorization_validator_ci_ref"] = fields[
        "source_execution_authorization_validator_ci_ref"
    ]
    output["source_preflight_read_only_stack_tag"] = fields[
        "source_preflight_read_only_stack_tag"
    ]
    output["source_preflight_read_only_stack_commit"] = fields[
        "source_preflight_read_only_stack_commit"
    ]
    output["approved_task_id"] = fields["approved_task_id"]
    output["approved_operation_kind"] = fields["approved_operation_kind"]
    output["idempotency_key"] = fields["idempotency_key"]
    output["projected_action"] = fields["projected_action"]
    output["projected_evidence_ref"] = fields["projected_evidence_ref"]
    output["human_approval_ref"] = fields["human_approval_ref"]
    output["operator_confirmation_ref"] = fields["operator_confirmation_ref"]
    output["authorization_issuer"] = fields["authorization_issuer"]
    output["authorization_reason"] = fields["authorization_reason"]
    output["executor_intent_ref"] = fields["executor_intent_ref"]
    output["executor_intent_created_at"] = fields["executor_intent_created_at"]
    output["executor_intent_expires_at"] = fields["executor_intent_expires_at"]
    output["executor_mode"] = fields["executor_mode"]
    output["evaluation_time"] = fields["evaluation_time"]
    output["dry_run_required"] = fields["dry_run_required"]
    output["transaction_plan_required"] = fields["transaction_plan_required"]
    output["rollback_plan_required"] = fields["rollback_plan_required"]
    output["idempotency_reservation_required"] = fields[
        "idempotency_reservation_required"
    ]
    output["before_evidence_capture_required"] = fields[
        "before_evidence_capture_required"
    ]
    output["after_evidence_capture_required"] = fields[
        "after_evidence_capture_required"
    ]
    output["audit_append_required"] = fields["audit_append_required"]
    output["evidence_append_required"] = fields["evidence_append_required"]
    output["expected_rejection_policy_required"] = fields[
        "expected_rejection_policy_required"
    ]
    output["no_schema_migration_required"] = fields[
        "no_schema_migration_required"
    ]
    output[_NO_DAEMON_SERVER_QUEUE_REQUIRED] = fields[
        _NO_DAEMON_SERVER_QUEUE_REQUIRED
    ]
    output["no_cli_required"] = fields["no_cli_required"]
    output["no_db_repair_required"] = fields["no_db_repair_required"]
    output["irreversible_action_prohibited"] = fields[
        "irreversible_action_prohibited"
    ]
    output["executor_implementation_authorized"] = fields[
        "executor_implementation_authorized"
    ]
    output["restore_execution_authorized"] = fields[
        "restore_execution_authorized"
    ]
    output["write_side_recovery_authorized"] = fields[
        "write_side_recovery_authorized"
    ]
    output["cli_execution_authorized"] = fields["cli_execution_authorized"]
    output["schema_migration_authorized"] = fields[
        "schema_migration_authorized"
    ]
    output["daemon_server_queue_authorized"] = fields[
        "daemon_server_queue_authorized"
    ]
    output["db_repair_authorized"] = fields["db_repair_authorized"]
    output["fail_closed_declared"] = fields["fail_closed_declared"]
    output["json_safe"] = fields["json_safe"]
    output["executes_plan"] = False
    output["durable_writes"] = False
    assert tuple(output.keys()) == _PRECONDITION_OUTPUT_KEYS
    return output


def _empty_precondition_fields() -> dict[str, object]:
    return {
        "source_execution_authorization_read_only_stack_tag": None,
        "source_execution_authorization_read_only_stack_commit": None,
        "source_execution_authorization_validator_ci_ref": None,
        "source_preflight_read_only_stack_tag": None,
        "source_preflight_read_only_stack_commit": None,
        "approved_task_id": None,
        "approved_operation_kind": None,
        "idempotency_key": None,
        "projected_action": None,
        "projected_evidence_ref": None,
        "human_approval_ref": None,
        "operator_confirmation_ref": None,
        "authorization_issuer": None,
        "authorization_reason": None,
        "executor_intent_ref": None,
        "executor_intent_created_at": None,
        "executor_intent_expires_at": None,
        "executor_mode": None,
        "evaluation_time": None,
        "dry_run_required": None,
        "transaction_plan_required": None,
        "rollback_plan_required": None,
        "idempotency_reservation_required": None,
        "before_evidence_capture_required": None,
        "after_evidence_capture_required": None,
        "audit_append_required": None,
        "evidence_append_required": None,
        "expected_rejection_policy_required": None,
        "no_schema_migration_required": None,
        _NO_DAEMON_SERVER_QUEUE_REQUIRED: None,
        "no_cli_required": None,
        "no_db_repair_required": None,
        "irreversible_action_prohibited": None,
        "executor_implementation_authorized": None,
        "restore_execution_authorized": None,
        "write_side_recovery_authorized": None,
        "cli_execution_authorized": None,
        "schema_migration_authorized": None,
        "daemon_server_queue_authorized": None,
        "db_repair_authorized": None,
        "fail_closed_declared": None,
        "json_safe": None,
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
