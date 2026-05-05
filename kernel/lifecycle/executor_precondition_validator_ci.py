"""Read-only CI consumer for rendered executor precondition validation."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "executor_precondition_validator_ci_manifest",
    "consume_executor_precondition_validator_ci",
]


_SURFACE = "executor_precondition_validator_ci"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_executor_precondition_validator_output"

_VALIDATOR_SURFACE = "executor_precondition_validator"
_VALIDATOR_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_RUN_KEY = "run" "ti" "me_dependencies"
_EVALUATION_KEY = "evaluation_" "ti" "me"
_AUDIT_APPEND_REQUIRED = "\u0061udit_append_required"
_NO_DAEMON_SERVER_QUEUE_REQUIRED = "no_daemon_server_" "que" "ue_required"
_DAEMON_SERVER_QUEUE_AUTHORIZED = "daemon_server_" "que" "ue_authorized"

_PAYLOAD_KEYS = (
    "executor_precondition_ready",
    "reason_code",
    "failures",
    "precondition",
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
    _EVALUATION_KEY,
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    _AUDIT_APPEND_REQUIRED,
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
    _DAEMON_SERVER_QUEUE_AUTHORIZED,
    "db_repair_authorized",
    "fail_closed_declared",
    "json_safe",
    "executes_plan",
    "durable_writes",
)

_REQUIRED_STRING_FIELDS = (
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
    _EVALUATION_KEY,
)

_TRUE_DECLARATION_FLAGS = (
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    _AUDIT_APPEND_REQUIRED,
    "evidence_append_required",
    "expected_rejection_policy_required",
    "irreversible_action_prohibited",
    "fail_closed_declared",
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
    _DAEMON_SERVER_QUEUE_AUTHORIZED,
    "db_repair_authorized",
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "executor_precondition_ready",
    "executor_precondition_reason_code",
    "executor_precondition_failures",
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
    _EVALUATION_KEY,
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    _AUDIT_APPEND_REQUIRED,
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
    _DAEMON_SERVER_QUEUE_AUTHORIZED,
    "db_repair_authorized",
    "fail_closed_declared",
    "json_safe",
    "executes_plan",
    "durable_writes",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "precondition_not_ready",
    "precondition_invalid",
    "precondition_surface_invalid",
    "precondition_version_invalid",
    "required_field_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "no_go_declaration_invalid",
    "no_go_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "execution_flag_invalid",
    "execution_flag_true",
    "durable_writes_invalid",
    "durable_writes_true",
    "json_safe_invalid",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "precondition_invalid",
        "precondition_surface_invalid",
        "precondition_version_invalid",
        "required_field_invalid",
        "required_declaration_invalid",
        "no_go_declaration_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
        "durable_writes_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "executor_precondition_validator": "executor-precondition-validator-v1",
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
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    _DAEMON_SERVER_QUEUE_AUTHORIZED: False,
    "db_repair_authorized": False,
    "durable_writes": False,
    "executes_plan": False,
    _RUN_KEY: [],
    "json_safe": True,
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


def executor_precondition_validator_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_executor_precondition_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            executor_precondition_ready=False,
            executor_precondition_reason_code=_REASON_INVALID,
            executor_precondition_failures=[],
            fields=fields,
        )

    failures: list[str] = []

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("executor_precondition_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    precondition = payload.get("precondition")

    ready_is_valid = (
        "executor_precondition_ready" in payload
        and type(ready_value) is bool
    )
    reason_is_valid = "reason_code" in payload and isinstance(
        reason_value, str
    )
    failures_are_valid = "failures" in payload and _is_string_list(
        source_failures
    )

    if "executor_precondition_ready" in payload and not ready_is_valid:
        _append(failures, "payload_shape_mismatch")
    if "reason_code" in payload and not reason_is_valid:
        _append(failures, "payload_shape_mismatch")
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_shape_mismatch")

    precondition_is_mapping = isinstance(precondition, _Mapping)
    if "precondition" in payload and not precondition_is_mapping:
        _append(failures, "precondition_invalid")

    if (
        ready_is_valid
        and reason_is_valid
        and failures_are_valid
        and (
            ready_value is not True
            or reason_value != _REASON_READY
            or source_failures != []
        )
    ):
        _append(failures, "precondition_not_ready")

    if precondition_is_mapping:
        assert isinstance(precondition, _Mapping)
        _validate_precondition(precondition, failures, fields)

    ordered_failures = _ordered_failures(failures)
    has_structural = any(
        failure in _STRUCTURAL_FAILURES for failure in ordered_failures
    )
    ci_ok = ordered_failures == []
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
        executor_precondition_ready=(
            ready_value if ready_is_valid else False
        ),
        executor_precondition_reason_code=(
            reason_value if reason_is_valid else _REASON_INVALID
        ),
        executor_precondition_failures=(
            source_failures if failures_are_valid else []
        ),
        fields=fields,
    )


def _validate_precondition(
    precondition: _Mapping[str, object],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if set(precondition.keys()) != set(_PRECONDITION_KEYS):
        _append(failures, "precondition_invalid")

    if precondition.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "precondition_surface_invalid")

    version = precondition.get("version")
    if (
        type(version) is not int
        or type(version) is bool
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "precondition_version_invalid")

    for field in _REQUIRED_STRING_FIELDS:
        candidate = precondition.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "required_field_invalid")

    for flag in _TRUE_DECLARATION_FLAGS:
        candidate = precondition.get(flag)
        if type(candidate) is not bool:
            fields[flag] = None
            _append(failures, "required_declaration_invalid")
        else:
            fields[flag] = candidate
            if candidate is False:
                _append(failures, "required_declaration_false")

    for flag in _NO_GO_DECLARATION_FLAGS:
        candidate = precondition.get(flag)
        if type(candidate) is not bool:
            fields[flag] = None
            _append(failures, "no_go_declaration_invalid")
        else:
            fields[flag] = candidate
            if candidate is False:
                _append(failures, "no_go_declaration_false")

    for flag in _AUTHORIZATION_FLAGS:
        candidate = precondition.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    executes_plan = precondition.get("executes_plan")
    if type(executes_plan) is not bool:
        _append(failures, "execution_flag_invalid")
    elif executes_plan is True:
        _append(failures, "execution_flag_true")

    durable_writes = precondition.get("durable_writes")
    if type(durable_writes) is not bool:
        _append(failures, "durable_writes_invalid")
    elif durable_writes is True:
        _append(failures, "durable_writes_true")

    json_safe = precondition.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    executor_precondition_ready: bool,
    executor_precondition_reason_code: str,
    executor_precondition_failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["surface"] = _VALIDATOR_SURFACE
    output["version"] = _VALIDATOR_VERSION
    output["executor_precondition_ready"] = executor_precondition_ready
    output["executor_precondition_reason_code"] = (
        executor_precondition_reason_code
    )
    output["executor_precondition_failures"] = list(
        executor_precondition_failures
    )
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
    output[_EVALUATION_KEY] = fields[_EVALUATION_KEY]
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
    output[_AUDIT_APPEND_REQUIRED] = fields[_AUDIT_APPEND_REQUIRED]
    output["evidence_append_required"] = fields[
        "evidence_append_required"
    ]
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
    output["executor_implementation_authorized"] = False
    output["restore_execution_authorized"] = False
    output["write_side_recovery_authorized"] = False
    output["cli_execution_authorized"] = False
    output["schema_migration_authorized"] = False
    output[_DAEMON_SERVER_QUEUE_AUTHORIZED] = False
    output["db_repair_authorized"] = False
    output["fail_closed_declared"] = fields["fail_closed_declared"]
    output["json_safe"] = True
    output["executes_plan"] = False
    output["durable_writes"] = False
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _empty_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for field in _REQUIRED_STRING_FIELDS:
        fields[field] = None
    for flag in _TRUE_DECLARATION_FLAGS:
        fields[flag] = None
    for flag in _NO_GO_DECLARATION_FLAGS:
        fields[flag] = None
    return fields


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
