"""Read-only CI consumer for rendered execution authorization validation."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "execution_authorization_validator_ci_manifest",
    "consume_execution_authorization_validator_ci",
]


_SURFACE = "execution_authorization_validator_ci"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_execution_authorization_validator_output"

_VALIDATOR_SURFACE = "execution_authorization_validator"
_VALIDATOR_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_APPEND_REQUIRED_KEY = "\u0061udit_append_required"

_PAYLOAD_KEYS = (
    "authorization_ready",
    "reason_code",
    "failures",
    "authorization",
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
    "evaluation_time",
    "transaction_boundary_declared",
    "rollback_boundary_declared",
    "idempotency_boundary_declared",
    "before_evidence_ref",
    "after_evidence_required",
    _APPEND_REQUIRED_KEY,
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
    "executes_plan",
    "durable_writes",
)

_REQUIRED_STRING_FIELDS = (
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
    "evaluation_time",
    "before_evidence_ref",
)

_TRUE_BOUNDARY_FLAGS = (
    "transaction_boundary_declared",
    "rollback_boundary_declared",
    "idempotency_boundary_declared",
    "after_evidence_required",
    _APPEND_REQUIRED_KEY,
    "evidence_append_required",
    "irreversible_action_prohibited",
    "fail_closed_declared",
)

_FALSE_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)

_OUTPUT_KEYS = (
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
    _APPEND_REQUIRED_KEY,
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

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "authorization_not_ready",
    "authorization_invalid",
    "authorization_surface_invalid",
    "authorization_version_invalid",
    "required_field_invalid",
    "freshness_seconds_invalid",
    "boundary_flag_invalid",
    "boundary_flag_false",
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
        "authorization_invalid",
        "authorization_surface_invalid",
        "authorization_version_invalid",
        "required_field_invalid",
        "freshness_seconds_invalid",
        "boundary_flag_invalid",
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


def execution_authorization_validator_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_execution_authorization_validator_ci(
    payload: object,
) -> dict[str, object]:
    string_fields = _empty_string_fields()
    boundary_flags = _empty_boundary_flags()
    freshness_seconds: int | None = None

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            authorization_ready=False,
            authorization_reason_code=_REASON_INVALID,
            authorization_failures=[],
            string_fields=string_fields,
            freshness_seconds=freshness_seconds,
            boundary_flags=boundary_flags,
        )

    failures: list[str] = []

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("authorization_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    authorization = payload.get("authorization")

    ready_is_valid = (
        "authorization_ready" in payload and type(ready_value) is bool
    )
    reason_is_valid = "reason_code" in payload and isinstance(reason_value, str)
    failures_are_valid = "failures" in payload and _is_string_list(
        source_failures
    )

    if "authorization_ready" in payload and not ready_is_valid:
        _append(failures, "payload_shape_mismatch")
    if "reason_code" in payload and not reason_is_valid:
        _append(failures, "payload_shape_mismatch")
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_shape_mismatch")

    authorization_is_mapping = isinstance(authorization, _Mapping)
    if "authorization" in payload and not authorization_is_mapping:
        _append(failures, "authorization_invalid")

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
        _append(failures, "authorization_not_ready")

    if authorization_is_mapping:
        assert isinstance(authorization, _Mapping)
        freshness_seconds = _validate_authorization(
            authorization=authorization,
            failures=failures,
            string_fields=string_fields,
            boundary_flags=boundary_flags,
        )

    ordered_failures = _ordered_failures(failures)
    has_structural = any(
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
        authorization_ready=ready_value if ready_is_valid else False,
        authorization_reason_code=reason_value if reason_is_valid else _REASON_INVALID,
        authorization_failures=source_failures if failures_are_valid else [],
        string_fields=string_fields,
        freshness_seconds=freshness_seconds,
        boundary_flags=boundary_flags,
    )


def _validate_authorization(
    *,
    authorization: _Mapping[str, object],
    failures: list[str],
    string_fields: dict[str, str | None],
    boundary_flags: dict[str, bool | None],
) -> int | None:
    if set(authorization.keys()) != set(_AUTHORIZATION_KEYS):
        _append(failures, "authorization_invalid")

    surface = authorization.get("surface")
    if surface != _VALIDATOR_SURFACE:
        _append(failures, "authorization_surface_invalid")

    version = authorization.get("version")
    if (
        type(version) is not int
        or type(version) is bool
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "authorization_version_invalid")

    for field in _REQUIRED_STRING_FIELDS:
        candidate = authorization.get(field)
        if isinstance(candidate, str) and candidate != "":
            string_fields[field] = candidate
        else:
            _append(failures, "required_field_invalid")

    freshness_seconds = _validate_freshness_seconds(authorization, failures)

    for flag in _TRUE_BOUNDARY_FLAGS:
        candidate = authorization.get(flag)
        if type(candidate) is not bool:
            _append(failures, "boundary_flag_invalid")
            boundary_flags[flag] = None
        else:
            boundary_flags[flag] = candidate
            if candidate is False:
                _append(failures, "boundary_flag_false")

    for flag in _FALSE_AUTHORIZATION_FLAGS:
        candidate = authorization.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    executes_plan = authorization.get("executes_plan")
    if type(executes_plan) is not bool:
        _append(failures, "execution_flag_invalid")
    elif executes_plan is True:
        _append(failures, "execution_flag_true")

    durable_writes = authorization.get("durable_writes")
    if type(durable_writes) is not bool:
        _append(failures, "durable_writes_invalid")
    elif durable_writes is True:
        _append(failures, "durable_writes_true")

    json_safe = authorization.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")

    return freshness_seconds


def _validate_freshness_seconds(
    authorization: _Mapping[str, object],
    failures: list[str],
) -> int | None:
    candidate = authorization.get("freshness_seconds")
    if type(candidate) is bool or type(candidate) is not int:
        _append(failures, "freshness_seconds_invalid")
        return None
    if candidate <= 0:
        _append(failures, "freshness_seconds_invalid")
        return None
    return candidate


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    authorization_ready: bool,
    authorization_reason_code: str,
    authorization_failures: list[str],
    string_fields: dict[str, str | None],
    freshness_seconds: int | None,
    boundary_flags: dict[str, bool | None],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["surface"] = _VALIDATOR_SURFACE
    output["version"] = _VALIDATOR_VERSION
    output["authorization_ready"] = authorization_ready
    output["authorization_reason_code"] = authorization_reason_code
    output["authorization_failures"] = list(authorization_failures)
    output["source_preflight_stack_tag"] = string_fields[
        "source_preflight_stack_tag"
    ]
    output["source_preflight_stack_commit"] = string_fields[
        "source_preflight_stack_commit"
    ]
    output["source_preflight_aggregate_ref"] = string_fields[
        "source_preflight_aggregate_ref"
    ]
    output["approved_task_id"] = string_fields["approved_task_id"]
    output["approved_operation_kind"] = string_fields[
        "approved_operation_kind"
    ]
    output["idempotency_key"] = string_fields["idempotency_key"]
    output["projected_action"] = string_fields["projected_action"]
    output["projected_evidence_ref"] = string_fields["projected_evidence_ref"]
    output["human_approval_ref"] = string_fields["human_approval_ref"]
    output["operator_confirmation_ref"] = string_fields[
        "operator_confirmation_ref"
    ]
    output["actor_policy"] = string_fields["actor_policy"]
    output["approval_actor_identity"] = string_fields[
        "approval_actor_identity"
    ]
    output["confirmation_actor_identity"] = string_fields[
        "confirmation_actor_identity"
    ]
    output["authorization_issuer"] = string_fields["authorization_issuer"]
    output["authorization_reason"] = string_fields["authorization_reason"]
    output["authorization_created_at"] = string_fields[
        "authorization_created_at"
    ]
    output["authorization_expires_at"] = string_fields[
        "authorization_expires_at"
    ]
    output["freshness_seconds"] = freshness_seconds
    output["evaluation_time"] = string_fields["evaluation_time"]
    output["transaction_boundary_declared"] = boundary_flags[
        "transaction_boundary_declared"
    ]
    output["rollback_boundary_declared"] = boundary_flags[
        "rollback_boundary_declared"
    ]
    output["idempotency_boundary_declared"] = boundary_flags[
        "idempotency_boundary_declared"
    ]
    output["before_evidence_ref"] = string_fields["before_evidence_ref"]
    output["after_evidence_required"] = boundary_flags[
        "after_evidence_required"
    ]
    output[_APPEND_REQUIRED_KEY] = boundary_flags[_APPEND_REQUIRED_KEY]
    output["evidence_append_required"] = boundary_flags[
        "evidence_append_required"
    ]
    output["restore_authorized"] = False
    output["write_side_recovery_authorized"] = False
    output["cli_execution_authorized"] = False
    output["schema_migration_authorized"] = False
    output["daemon_server_queue_authorized"] = False
    output["db_repair_authorized"] = False
    output["durable_writes"] = False
    output["executes_plan"] = False
    output["json_safe"] = True
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _empty_string_fields() -> dict[str, str | None]:
    return {field: None for field in _REQUIRED_STRING_FIELDS}


def _empty_boundary_flags() -> dict[str, bool | None]:
    return {flag: None for flag in _TRUE_BOUNDARY_FLAGS}


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
