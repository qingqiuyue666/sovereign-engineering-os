"""Pure validator for already-rendered execution authorization inputs."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy
from datetime import datetime as _datetime
from datetime import timezone as _timezone


__all__ = [
    "execution_authorization_validator_manifest",
    "validate_execution_authorization",
]


_SURFACE = "execution_authorization_validator"
_AUTHORIZATION_SURFACE = "ExecutionAuthorizationV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_preflight_summary_and_execution_authorization"

_REASON_INVALID = "invalid_authorization_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_PREFLIGHT_STACK_TAG = "preflight-read-only-stack-v1"
_PREFLIGHT_STACK_COMMIT = "662b6161253c35204b437e88809c5bab21908c6d"

_AUDIT_APPEND_REQUIRED = "\u0061udit_append_required"
_AUDIT_APPEND_NOT_REQUIRED = "\u0061udit_append_not_required"

_INPUT_KEYS = (
    "preflight_aggregate_summary",
    "preflight_aggregate_summary_ref",
    "execution_authorization",
    "evaluation_time",
)

_PREFLIGHT_TOP_LEVEL_KEYS = (
    "aggregate_ok",
    "reason_code",
    "failures",
    "summary",
)

_PREFLIGHT_SUMMARY_KEYS = (
    "surface",
    "version",
    "human_approval_ci_ok",
    "execution_preflight_ci_ok",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_ref",
    "actor_identity_approval",
    "actor_identity_confirmation",
    "actor_policy",
    "confirmation_digest",
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    "\u0061udit_evidence_envelope_declared",
    "before_after_evidence_declared",
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

_PREFLIGHT_STRING_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_ref",
    "actor_identity_approval",
    "actor_identity_confirmation",
    "actor_policy",
    "confirmation_digest",
)

_PREFLIGHT_DECLARATION_FLAGS = (
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    "\u0061udit_evidence_envelope_declared",
    "before_after_evidence_declared",
)

_PREFLIGHT_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_AUTHORIZATION_KEYS = (
    "surface",
    "version",
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
    "transaction_boundary_declared",
    "rollback_boundary_declared",
    "idempotency_boundary_declared",
    "before_evidence_ref",
    "after_evidence_required",
    _AUDIT_APPEND_REQUIRED,
    "evidence_append_required",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "cli_execution_authorized",
    "restore_authorized",
    "write_side_recovery_authorized",
    "irreversible_action_prohibited",
    "fail_closed_declared",
    "json_safe",
)

_AUTHORIZATION_FLAGS = (
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "cli_execution_authorized",
    "restore_authorized",
    "write_side_recovery_authorized",
)

_AUTHORIZATION_OUTPUT_KEYS = (
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
    _AUDIT_APPEND_REQUIRED,
    "evidence_append_required",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "irreversible_action_prohibited",
    "fail_closed_declared",
    "json_safe",
)

_ACTOR_POLICY_VALUES = ("same_actor_required", "dual_control_allowed")

_BINDINGS = (
    ("approved_task_id", "target_task_id", "task_id_mismatch"),
    (
        "approved_operation_kind",
        "operation_kind",
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
        "confirmation_ref",
        "operator_confirmation_ref_mismatch",
    ),
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "preflight_summary_invalid",
    "preflight_summary_not_ready",
    "preflight_ref_invalid",
    "authorization_invalid",
    "authorization_shape_mismatch",
    "authorization_surface_invalid",
    "authorization_version_invalid",
    "source_preflight_stack_tag_mismatch",
    "source_preflight_stack_commit_mismatch",
    "source_preflight_aggregate_ref_mismatch",
    "task_id_mismatch",
    "operation_kind_mismatch",
    "idempotency_key_mismatch",
    "projected_action_mismatch",
    "projected_evidence_ref_mismatch",
    "human_approval_ref_mismatch",
    "operator_confirmation_ref_mismatch",
    "actor_policy_invalid",
    "actor_identity_mismatch",
    "issuer_invalid",
    "authorization_reason_invalid",
    "evaluation_time_invalid",
    "authorization_created_at_invalid",
    "authorization_expires_at_invalid",
    "authorization_expired",
    "freshness_seconds_invalid",
    "authorization_stale",
    "transaction_boundary_not_declared",
    "rollback_boundary_not_declared",
    "idempotency_boundary_not_declared",
    "before_evidence_ref_invalid",
    "after_evidence_not_required",
    _AUDIT_APPEND_NOT_REQUIRED,
    "evidence_append_not_required",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "irreversible_action_not_prohibited",
    "fail_closed_not_declared",
    "execution_flag_invalid",
    "execution_flag_true",
    "json_safe_invalid",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "preflight_summary_invalid",
        "preflight_ref_invalid",
        "authorization_invalid",
        "authorization_shape_mismatch",
        "authorization_surface_invalid",
        "authorization_version_invalid",
        "actor_policy_invalid",
        "issuer_invalid",
        "authorization_reason_invalid",
        "evaluation_time_invalid",
        "authorization_created_at_invalid",
        "authorization_expires_at_invalid",
        "freshness_seconds_invalid",
        "before_evidence_ref_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "execution_authorization_spec_only": (
            "execution-authorization-spec-only-v1"
        ),
        "preflight_read_only_stack": _PREFLIGHT_STACK_TAG,
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


def execution_authorization_validator_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def validate_execution_authorization(payload: object) -> dict[str, object]:
    authorization_fields = _empty_authorization_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            authorization_ready=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            authorization_fields=authorization_fields,
        )

    failures: list[str] = []
    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    preflight_result = _validate_preflight_summary(
        payload.get("preflight_aggregate_summary")
    )
    for failure in preflight_result["failures"]:
        _append(failures, failure)

    preflight_ref = _validate_preflight_ref(
        payload.get("preflight_aggregate_summary_ref"), failures
    )

    authorization_result = _validate_authorization(
        payload.get("execution_authorization"),
        authorization_fields,
    )
    for failure in authorization_result["failures"]:
        _append(failures, failure)

    evaluation_dt = _validate_evaluation_time(
        payload.get("evaluation_time"),
        failures,
        authorization_fields,
    )

    preflight_values: dict[str, object] = preflight_result["values"]
    authorization_values: dict[str, object] = authorization_result["values"]

    _validate_source_ref_bindings(
        failures=failures,
        preflight_ref=preflight_ref,
        preflight_values=preflight_values,
        authorization_values=authorization_values,
    )
    _validate_field_bindings(
        failures=failures,
        preflight_values=preflight_values,
        authorization_values=authorization_values,
    )
    _validate_actor_bindings(
        failures=failures,
        preflight_values=preflight_values,
        authorization_values=authorization_values,
    )
    _validate_time_window(
        failures=failures,
        authorization_result=authorization_result,
        evaluation_dt=evaluation_dt,
    )

    ordered_failures = _ordered_failures(failures)
    authorization_ready = ordered_failures == []
    if authorization_ready:
        reason_code = _REASON_READY
    elif any(failure in _STRUCTURAL_FAILURES for failure in ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        authorization_ready=authorization_ready,
        reason_code=reason_code,
        failures=ordered_failures,
        authorization_fields=authorization_fields,
    )


def _validate_preflight_summary(payload: object) -> dict[str, object]:
    failures: list[str] = []
    values: dict[str, object] = {
        field: None for field in _PREFLIGHT_STRING_FIELDS
    }

    if not isinstance(payload, _Mapping):
        return {"failures": ["preflight_summary_invalid"], "values": values}

    if set(payload.keys()) != set(_PREFLIGHT_TOP_LEVEL_KEYS):
        _append(failures, "preflight_summary_invalid")

    _require_bool_value(
        payload,
        "aggregate_ok",
        invalid_failure="preflight_summary_invalid",
        false_failure="preflight_summary_not_ready",
        failures=failures,
    )
    _require_ready_reason(payload, failures)
    _require_empty_failures(payload, failures)

    summary = payload.get("summary")
    if not isinstance(summary, _Mapping):
        _append(failures, "preflight_summary_invalid")
        return {"failures": failures, "values": values}

    if set(summary.keys()) != set(_PREFLIGHT_SUMMARY_KEYS):
        _append(failures, "preflight_summary_invalid")

    if summary.get("surface") != "preflight_aggregate_summary":
        _append(failures, "preflight_summary_invalid")

    version = summary.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "preflight_summary_invalid")

    _require_bool_value(
        summary,
        "human_approval_ci_ok",
        invalid_failure="preflight_summary_invalid",
        false_failure="preflight_summary_not_ready",
        failures=failures,
    )
    _require_bool_value(
        summary,
        "execution_preflight_ci_ok",
        invalid_failure="preflight_summary_invalid",
        false_failure="preflight_summary_not_ready",
        failures=failures,
    )

    for field in _PREFLIGHT_STRING_FIELDS:
        candidate = summary.get(field)
        if isinstance(candidate, str) and candidate != "":
            values[field] = candidate
        elif field in summary and isinstance(candidate, str):
            _append(failures, "preflight_summary_not_ready")
        else:
            _append(failures, "preflight_summary_invalid")

    for field in _PREFLIGHT_DECLARATION_FLAGS:
        _require_bool_value(
            summary,
            field,
            invalid_failure="preflight_summary_invalid",
            false_failure="preflight_summary_not_ready",
            failures=failures,
        )

    for flag in _PREFLIGHT_AUTHORIZATION_FLAGS:
        _require_false_authorization_flag(summary, flag, failures)

    _require_false_execution_flag(summary, "executes_plan", failures)
    _require_json_safe(summary, failures)

    return {"failures": failures, "values": values}


def _validate_preflight_ref(
    candidate: object, failures: list[str]
) -> str | None:
    if isinstance(candidate, str) and candidate != "":
        return candidate
    _append(failures, "preflight_ref_invalid")
    return None


def _validate_authorization(
    payload: object,
    authorization_fields: dict[str, object],
) -> dict[str, object]:
    failures: list[str] = []
    values: dict[str, object] = {
        field: None for field in _AUTHORIZATION_KEYS
    }
    created_dt = None
    expires_dt = None
    freshness_seconds = None

    if not isinstance(payload, _Mapping):
        return {
            "failures": ["authorization_invalid"],
            "values": values,
            "created_dt": created_dt,
            "expires_dt": expires_dt,
            "freshness_seconds": freshness_seconds,
        }

    if set(payload.keys()) != set(_AUTHORIZATION_KEYS):
        _append(failures, "authorization_shape_mismatch")

    if payload.get("surface") != _AUTHORIZATION_SURFACE:
        _append(failures, "authorization_surface_invalid")

    version = payload.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "authorization_version_invalid")

    _validate_expected_literal(
        payload=payload,
        field="source_preflight_stack_tag",
        expected=_PREFLIGHT_STACK_TAG,
        failure="source_preflight_stack_tag_mismatch",
        failures=failures,
        values=values,
        authorization_fields=authorization_fields,
    )
    _validate_expected_literal(
        payload=payload,
        field="source_preflight_stack_commit",
        expected=_PREFLIGHT_STACK_COMMIT,
        failure="source_preflight_stack_commit_mismatch",
        failures=failures,
        values=values,
        authorization_fields=authorization_fields,
    )

    _capture_string(
        payload,
        "source_preflight_aggregate_ref",
        "source_preflight_aggregate_ref_mismatch",
        failures,
        values,
        authorization_fields,
    )
    for authorization_field, _summary_field, failure in _BINDINGS:
        _capture_string(
            payload,
            authorization_field,
            failure,
            failures,
            values,
            authorization_fields,
        )

    actor_policy = payload.get("actor_policy")
    if (
        isinstance(actor_policy, str)
        and actor_policy in _ACTOR_POLICY_VALUES
    ):
        values["actor_policy"] = actor_policy
        authorization_fields["actor_policy"] = actor_policy
    else:
        _append(failures, "actor_policy_invalid")

    for field in ("approval_actor_identity", "confirmation_actor_identity"):
        _capture_string(
            payload,
            field,
            "actor_identity_mismatch",
            failures,
            values,
            authorization_fields,
        )

    _capture_string(
        payload,
        "authorization_issuer",
        "issuer_invalid",
        failures,
        values,
        authorization_fields,
    )
    _capture_string(
        payload,
        "authorization_reason",
        "authorization_reason_invalid",
        failures,
        values,
        authorization_fields,
    )

    created_dt = _validate_authorization_time(
        payload=payload,
        field="authorization_created_at",
        failure="authorization_created_at_invalid",
        failures=failures,
        values=values,
        authorization_fields=authorization_fields,
    )
    expires_dt = _validate_authorization_time(
        payload=payload,
        field="authorization_expires_at",
        failure="authorization_expires_at_invalid",
        failures=failures,
        values=values,
        authorization_fields=authorization_fields,
    )

    freshness = payload.get("freshness_seconds")
    if type(freshness) is bool or type(freshness) is not int:
        _append(failures, "freshness_seconds_invalid")
    else:
        authorization_fields["freshness_seconds"] = freshness
        values["freshness_seconds"] = freshness
        if freshness <= 0:
            _append(failures, "freshness_seconds_invalid")
        else:
            freshness_seconds = freshness

    _require_true_authorization_flag(
        payload,
        "transaction_boundary_declared",
        "transaction_boundary_not_declared",
        failures,
        authorization_fields,
    )
    _require_true_authorization_flag(
        payload,
        "rollback_boundary_declared",
        "rollback_boundary_not_declared",
        failures,
        authorization_fields,
    )
    _require_true_authorization_flag(
        payload,
        "idempotency_boundary_declared",
        "idempotency_boundary_not_declared",
        failures,
        authorization_fields,
    )

    _capture_string(
        payload,
        "before_evidence_ref",
        "before_evidence_ref_invalid",
        failures,
        values,
        authorization_fields,
    )

    _require_true_authorization_flag(
        payload,
        "after_evidence_required",
        "after_evidence_not_required",
        failures,
        authorization_fields,
    )
    _require_true_authorization_flag(
        payload,
        _AUDIT_APPEND_REQUIRED,
        _AUDIT_APPEND_NOT_REQUIRED,
        failures,
        authorization_fields,
    )
    _require_true_authorization_flag(
        payload,
        "evidence_append_required",
        "evidence_append_not_required",
        failures,
        authorization_fields,
    )

    for flag in _AUTHORIZATION_FLAGS:
        _validate_authorization_flag(payload, flag, failures, authorization_fields)

    _require_true_authorization_flag(
        payload,
        "irreversible_action_prohibited",
        "irreversible_action_not_prohibited",
        failures,
        authorization_fields,
    )
    _require_true_authorization_flag(
        payload,
        "fail_closed_declared",
        "fail_closed_not_declared",
        failures,
        authorization_fields,
    )
    _validate_authorization_json_safe(payload, failures, authorization_fields)

    return {
        "failures": failures,
        "values": values,
        "created_dt": created_dt,
        "expires_dt": expires_dt,
        "freshness_seconds": freshness_seconds,
    }


def _validate_source_ref_bindings(
    *,
    failures: list[str],
    preflight_ref: str | None,
    preflight_values: dict[str, object],
    authorization_values: dict[str, object],
) -> None:
    summary_ref = preflight_values.get("aggregate_summary_ref")
    authorization_ref = authorization_values.get("source_preflight_aggregate_ref")
    if (
        isinstance(preflight_ref, str)
        and isinstance(summary_ref, str)
        and preflight_ref != summary_ref
    ):
        _append(failures, "source_preflight_aggregate_ref_mismatch")
    if (
        isinstance(preflight_ref, str)
        and isinstance(authorization_ref, str)
        and authorization_ref != preflight_ref
    ):
        _append(failures, "source_preflight_aggregate_ref_mismatch")


def _validate_field_bindings(
    *,
    failures: list[str],
    preflight_values: dict[str, object],
    authorization_values: dict[str, object],
) -> None:
    for authorization_field, summary_field, failure in _BINDINGS:
        authorization_value = authorization_values.get(authorization_field)
        summary_value = preflight_values.get(summary_field)
        if (
            isinstance(authorization_value, str)
            and isinstance(summary_value, str)
            and authorization_value != summary_value
        ):
            _append(failures, failure)


def _validate_actor_bindings(
    *,
    failures: list[str],
    preflight_values: dict[str, object],
    authorization_values: dict[str, object],
) -> None:
    authorization_policy = authorization_values.get("actor_policy")
    preflight_policy = preflight_values.get("actor_policy")
    approval_actor = authorization_values.get("approval_actor_identity")
    confirmation_actor = authorization_values.get("confirmation_actor_identity")
    preflight_approval_actor = preflight_values.get("actor_identity_approval")
    preflight_confirmation_actor = preflight_values.get(
        "actor_identity_confirmation"
    )

    if (
        isinstance(authorization_policy, str)
        and isinstance(preflight_policy, str)
        and authorization_policy != preflight_policy
    ):
        _append(failures, "actor_policy_invalid")

    if (
        isinstance(approval_actor, str)
        and isinstance(preflight_approval_actor, str)
        and approval_actor != preflight_approval_actor
    ):
        _append(failures, "actor_identity_mismatch")

    if (
        isinstance(confirmation_actor, str)
        and isinstance(preflight_confirmation_actor, str)
        and confirmation_actor != preflight_confirmation_actor
    ):
        _append(failures, "actor_identity_mismatch")

    if (
        authorization_policy == "same_actor_required"
        and isinstance(approval_actor, str)
        and isinstance(confirmation_actor, str)
        and approval_actor != confirmation_actor
    ):
        _append(failures, "actor_identity_mismatch")


def _validate_time_window(
    *,
    failures: list[str],
    authorization_result: dict[str, object],
    evaluation_dt: _datetime | None,
) -> None:
    created_dt = authorization_result["created_dt"]
    expires_dt = authorization_result["expires_dt"]
    freshness_seconds = authorization_result["freshness_seconds"]
    expiration_order_valid = True

    if isinstance(created_dt, _datetime) and isinstance(expires_dt, _datetime):
        if expires_dt <= created_dt:
            expiration_order_valid = False
            _append(failures, "authorization_expires_at_invalid")

    if isinstance(evaluation_dt, _datetime) and isinstance(created_dt, _datetime):
        if evaluation_dt < created_dt:
            _append(failures, "evaluation_time_invalid")

    if (
        expiration_order_valid
        and isinstance(evaluation_dt, _datetime)
        and isinstance(expires_dt, _datetime)
    ):
        if evaluation_dt >= expires_dt:
            _append(failures, "authorization_expired")

    if (
        isinstance(evaluation_dt, _datetime)
        and isinstance(created_dt, _datetime)
        and isinstance(freshness_seconds, int)
        and evaluation_dt >= created_dt
    ):
        elapsed = (evaluation_dt - created_dt).total_seconds()
        if elapsed > freshness_seconds:
            _append(failures, "authorization_stale")


def _validate_evaluation_time(
    candidate: object,
    failures: list[str],
    authorization_fields: dict[str, object],
) -> _datetime | None:
    if isinstance(candidate, str) and candidate != "":
        authorization_fields["evaluation_time"] = candidate
    parsed = _parse_timestamp(candidate)
    if parsed is None:
        _append(failures, "evaluation_time_invalid")
    return parsed


def _validate_authorization_time(
    *,
    payload: _Mapping[str, object],
    field: str,
    failure: str,
    failures: list[str],
    values: dict[str, object],
    authorization_fields: dict[str, object],
) -> _datetime | None:
    candidate = payload.get(field)
    if isinstance(candidate, str) and candidate != "":
        values[field] = candidate
        authorization_fields[field] = candidate
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


def _require_ready_reason(
    payload: _Mapping[str, object], failures: list[str]
) -> None:
    candidate = payload.get("reason_code")
    if not isinstance(candidate, str):
        _append(failures, "preflight_summary_invalid")
    elif candidate != _REASON_READY:
        _append(failures, "preflight_summary_not_ready")


def _require_empty_failures(
    payload: _Mapping[str, object], failures: list[str]
) -> None:
    candidate = payload.get("failures")
    if not _is_string_list(candidate):
        _append(failures, "preflight_summary_invalid")
    elif candidate != []:
        _append(failures, "preflight_summary_not_ready")


def _require_bool_value(
    payload: _Mapping[str, object],
    field: str,
    *,
    invalid_failure: str,
    false_failure: str,
    failures: list[str],
) -> None:
    candidate = payload.get(field)
    if type(candidate) is not bool:
        _append(failures, invalid_failure)
    elif candidate is False:
        _append(failures, false_failure)


def _require_false_authorization_flag(
    payload: _Mapping[str, object], field: str, failures: list[str]
) -> None:
    candidate = payload.get(field)
    if type(candidate) is not bool:
        _append(failures, "authorization_flag_invalid")
    elif candidate is True:
        _append(failures, "authorization_flag_true")


def _require_false_execution_flag(
    payload: _Mapping[str, object], field: str, failures: list[str]
) -> None:
    candidate = payload.get(field)
    if type(candidate) is not bool:
        _append(failures, "execution_flag_invalid")
    elif candidate is True:
        _append(failures, "execution_flag_true")


def _require_json_safe(
    payload: _Mapping[str, object], failures: list[str]
) -> None:
    candidate = payload.get("json_safe")
    if type(candidate) is not bool or candidate is False:
        _append(failures, "json_safe_invalid")


def _validate_expected_literal(
    *,
    payload: _Mapping[str, object],
    field: str,
    expected: str,
    failure: str,
    failures: list[str],
    values: dict[str, object],
    authorization_fields: dict[str, object],
) -> None:
    candidate = payload.get(field)
    if isinstance(candidate, str) and candidate != "":
        values[field] = candidate
        authorization_fields[field] = candidate
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
    authorization_fields: dict[str, object],
) -> None:
    candidate = payload.get(field)
    if isinstance(candidate, str) and candidate != "":
        values[field] = candidate
        authorization_fields[field] = candidate
    else:
        _append(failures, failure)


def _require_true_authorization_flag(
    payload: _Mapping[str, object],
    field: str,
    failure: str,
    failures: list[str],
    authorization_fields: dict[str, object],
) -> None:
    candidate = payload.get(field)
    if type(candidate) is bool:
        authorization_fields[field] = candidate
    if candidate is not True:
        _append(failures, failure)


def _validate_authorization_flag(
    payload: _Mapping[str, object],
    field: str,
    failures: list[str],
    authorization_fields: dict[str, object],
) -> None:
    candidate = payload.get(field)
    if type(candidate) is not bool:
        _append(failures, "authorization_flag_invalid")
        authorization_fields[field] = None
    elif candidate is True:
        _append(failures, "authorization_flag_true")
        authorization_fields[field] = False
    else:
        authorization_fields[field] = False


def _validate_authorization_json_safe(
    payload: _Mapping[str, object],
    failures: list[str],
    authorization_fields: dict[str, object],
) -> None:
    candidate = payload.get("json_safe")
    if type(candidate) is bool:
        authorization_fields["json_safe"] = candidate
    if type(candidate) is not bool or candidate is False:
        _append(failures, "json_safe_invalid")


def _empty_authorization_fields() -> dict[str, object]:
    fields: dict[str, object] = {field: None for field in _AUTHORIZATION_OUTPUT_KEYS}
    fields["executes_plan"] = False
    fields["durable_writes"] = False
    return fields


def _result(
    *,
    authorization_ready: bool,
    reason_code: str,
    failures: list[str],
    authorization_fields: dict[str, object],
) -> dict[str, object]:
    authorization: dict[str, object] = {}
    authorization["surface"] = _SURFACE
    authorization["version"] = _VERSION
    for field in _AUTHORIZATION_OUTPUT_KEYS:
        authorization[field] = authorization_fields[field]
    authorization["executes_plan"] = False
    authorization["durable_writes"] = False
    return {
        "authorization_ready": authorization_ready,
        "reason_code": reason_code,
        "failures": list(failures),
        "authorization": authorization,
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
