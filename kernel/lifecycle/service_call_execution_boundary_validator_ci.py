"""Read-only CI consumer for rendered service call boundary validation."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_call_execution_boundary_validator_ci_manifest",
    "consume_service_call_execution_boundary_validator_ci",
]

_SURFACE = "service_call_execution_boundary_validator_ci"
_VERSION = 1
_INPUT_SHAPE = (
    "already_rendered_service_call_execution_boundary_validator_output_v1"
)

_VALIDATOR_SURFACE = "service_call_execution_boundary_validator"
_VALIDATOR_VERSION = 1
_VALIDATOR_TAG = "service-call-execution-boundary-validator-v1"
_VALIDATOR_COMMIT = "9712ad6ba5d7574e10e1008fa2001017c8da4493"
_VALIDATOR_CHECKPOINT = {
    "tag": _VALIDATOR_TAG,
    "commit": _VALIDATOR_COMMIT,
}

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_VALIDATOR_REASON_INVALID = "invalid_service_call_execution_boundary_payload"
_VALIDATOR_REASON_CODES = (
    _VALIDATOR_REASON_INVALID,
    _REASON_NOT_READY,
    _REASON_READY,
)

_PAYLOAD_KEYS = (
    "service_call_execution_boundary_ready",
    "reason_code",
    "failures",
    "boundary",
)

_BOUNDARY_KEYS = (
    "surface",
    "version",
    "validator_checkpoint",
    "source_refs",
    "declaration_groups",
    "required_false_authority_flags",
    "required_true_declarations",
    "json_safe",
    "authority",
)

_SOURCE_REFS = {
    "read-only-governance-layer-v1": (
        "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
    ),
    "write-side-precondition-checker-v1": (
        "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
    ),
    "write-side-precondition-ci-v1": (
        "05c81541ad3d7deee20023843142f702937f6c3f"
    ),
    "write-side-recovery-spec-only-v1": (
        "ad560cc2dab135f2c1d56d948410ae47586d118e"
    ),
    "restore-dry-run-read-only-stack-v1": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
    "preflight-read-only-stack-v1": (
        "662b6161253c35204b437e88809c5bab21908c6d"
    ),
    "execution-authorization-read-only-stack-v1": (
        "d586aeb60620010c900df7be1a88621ab2cb8dc1"
    ),
    "executor-precondition-read-only-stack-v1": (
        "cb3948eb843866dcc961b6a074038c13db64d017"
    ),
    "write-path-read-only-stack-v1": (
        "8ffd4679aca8f593415089748df35df42af8f015"
    ),
    "repository-uow-allowlist-read-only-stack-v1": (
        "bec2d04eab1922594dcbfbe35971f4efe0fe4849"
    ),
    "evidence-audit-append-read-only-stack-v1": (
        "62db8a586efa9375d2c77cf7c6335ccf5ef11279"
    ),
    "append-runtime-authority-service-boundary-read-only-stack-v1": (
        "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039"
    ),
    "service-adapter-boundary-read-only-stack-v1": (
        "8698ea42c78cbe79231698be8839b9d2c246cfdf"
    ),
    "service-method-authority-read-only-stack-v1": (
        "db2f628cc79df0dc7b4f1306cbe24d880693188b"
    ),
    "service-call-execution-boundary-spec-only-v1": (
        "f3c9bd637c586dab45c3626e3d29353b00eadb4d"
    ),
}

_DECLARATION_GROUPS = (
    "service_call_attempt_boundary",
    "authority_input_binding",
    "method_authority_ci_binding",
    "execution_authorization_binding",
    "human_approval_binding",
    "operator_confirmation_binding",
    "idempotency_key_binding",
    "transaction_placement_binding",
    "evidence_audit_bookkeeping_boundary",
    "service_result_intake_boundary",
    "service_result_ref_binding",
    "failure_incident_classification",
    "rollback_compensation_boundary",
    "forbidden_direct_service_call_boundary",
    "forbidden_db_repository_uow_boundary",
    "forbidden_executor_boundary",
    "runtime_checker_enforcer_future_requirement",
    "revocation_expiry_boundary",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "service_call_execution_authorized",
    "service_adapter_runtime_authorized",
    "service_adapter_implementation_authorized",
    "service_method_call_authorized",
    "service_side_effect_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "audit_service_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "append_runtime_authorized",
    "repository_uow_writes_authorized",
    "direct_db_writes_authorized",
    "raw_sqlite_authorized",
    "ad_hoc_sql_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "runtime_allowlist_authorized",
    "runtime_checker_authorized",
    "runtime_enforcer_authorized",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "filesystem_side_effects_authorized",
    "external_network_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
    "db_repair_authorized",
)

_REQUIRED_TRUE_DECLARATIONS = (
    "spec_only_non_executable",
    "service_call_execution_forbidden",
    "service_adapter_implementation_forbidden",
    "service_calls_forbidden",
    "direct_service_call_forbidden",
    "exact_service_identity_required",
    "exact_service_class_name_required",
    "exact_service_method_name_required",
    "service_method_authority_ci_required",
    "execution_authorization_ci_required",
    "human_approval_required",
    "operator_confirmation_required",
    "authority_ref_required",
    "authority_ref_source_bound_required",
    "authority_ref_operation_bound_required",
    "idempotency_key_required",
    "idempotency_key_source_bound_required",
    "idempotency_key_operation_bound_required",
    "transaction_placement_required",
    "kernel_owned_transaction_required_for_future_runtime",
    "service_transaction_ownership_forbidden_by_default",
    "uncontrolled_nested_transaction_forbidden",
    "evidence_pre_bookkeeping_required",
    "audit_pre_bookkeeping_required",
    "evidence_post_bookkeeping_required",
    "audit_post_bookkeeping_required",
    "service_result_contract_required",
    "service_result_json_safe_required",
    "service_result_bounded_required",
    "service_result_no_runtime_handles_required",
    "service_result_to_evidence_ref_binding_required",
    "service_result_to_audit_ref_binding_required",
    "fabricated_refs_forbidden",
    "implicit_append_success_forbidden",
    "implicit_audit_success_forbidden",
    "failure_incident_separation_required",
    "forbidden_service_call_fail_closed",
    "missing_authority_fail_closed",
    "revoked_authority_fail_closed",
    "expired_authority_fail_closed",
    "idempotency_mismatch_fail_closed",
    "transaction_violation_incident_class",
    "post_service_failure_incident_class",
    "append_failure_after_service_incident_class",
    "rollback_failure_incident_class",
    "partial_success_forbidden",
    "silent_success_forbidden",
    "runtime_checker_required_for_future_runtime",
    "runtime_enforcer_required_for_future_runtime",
    "future_validator_required",
    "future_ci_required",
)

_AUTHORITY_SUMMARY_FLAGS = {
    "service_call_execution_authorized": False,
    "service_adapter_runtime_authorized": False,
    "service_method_call_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "repository_uow_writes_authorized": False,
    "transaction_runtime_authorized": False,
    "idempotency_reservation_authorized": False,
    "rollback_runtime_authorized": False,
    "runtime_checker_authorized": False,
    "runtime_enforcer_authorized": False,
    "executor_implementation_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
}

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "declaration_group_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "validator_checkpoint_invalid",
    "validator_readiness_invalid",
    "validator_reason_code_invalid",
    "validator_failures_invalid",
    "validator_failure_unknown",
    "source_ref_mismatch",
    "declaration_group_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "boundary",
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "expected_top_level_keys": list(_PAYLOAD_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_validator_checkpoint": deepcopy(_VALIDATOR_CHECKPOINT),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_declaration_groups": list(_DECLARATION_GROUPS),
    "required_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "required_true_declarations": list(_REQUIRED_TRUE_DECLARATIONS),
    "required_authority_summary_flags": list(_AUTHORITY_SUMMARY_FLAGS),
    "validator_failure_taxonomy": list(_VALIDATOR_FAILURE_TAXONOMY),
    "ci_failure_taxonomy": list(_FAILURE_ORDER),
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "non_authority": {
        "ci_ok_authorizes_service_call_execution": False,
        "ci_ok_authorizes_service_adapter_runtime": False,
        "ci_ok_authorizes_service_method_calls": False,
        "ci_ok_authorizes_evidence_audit_append": False,
        "ci_ok_authorizes_db_repository_uow_writes": False,
        "ci_ok_authorizes_transaction_runtime": False,
        "ci_ok_authorizes_idempotency_reservation_runtime": False,
        "ci_ok_authorizes_rollback_runtime": False,
        "ci_ok_authorizes_checker_enforcer": False,
        "ci_ok_authorizes_executor_restore_cli_schema_daemon": False,
        "ci_ok_authorizes_durable_writes": False,
        "ci_ok_authorizes_irreversible_actions": False,
    },
    "json_safe": True,
}


def service_call_execution_boundary_validator_ci_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def consume_service_call_execution_boundary_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_boundary_fields()

    if not isinstance(payload, Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("service_call_execution_boundary_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    boundary = payload.get("boundary")

    ready_is_bool = (
        "service_call_execution_boundary_ready" in payload
        and type(ready_value) is bool
    )
    if (
        "service_call_execution_boundary_ready" in payload
        and not ready_is_bool
    ):
        _append(failures, "validator_readiness_invalid")

    reason_is_valid = False
    if "reason_code" in payload:
        if isinstance(reason_value, str):
            reason_is_valid = reason_value in _VALIDATOR_REASON_CODES
        if not reason_is_valid:
            _append(failures, "validator_reason_code_invalid")

    source_failures_valid = False
    source_failures_known = False
    if "failures" in payload:
        source_failures_valid = _is_string_list(source_failures)
        if not source_failures_valid:
            _append(failures, "validator_failures_invalid")
        else:
            source_failures_known = True
            assert isinstance(source_failures, list)
            for failure in source_failures:
                if failure not in _VALIDATOR_FAILURE_TAXONOMY:
                    source_failures_known = False
                    _append(failures, "validator_failure_unknown")

    if ready_is_bool and reason_is_valid and source_failures_valid:
        assert isinstance(source_failures, list)
        if ready_value is True:
            if reason_value != _REASON_READY or source_failures != []:
                _append(failures, "validator_readiness_invalid")
        else:
            if reason_value not in (
                _REASON_NOT_READY,
                _VALIDATOR_REASON_INVALID,
            ):
                _append(failures, "validator_readiness_invalid")
            if source_failures == []:
                _append(failures, "validator_readiness_invalid")

    if not isinstance(boundary, Mapping):
        if "boundary" in payload:
            _append(failures, "boundary_not_mapping")
    else:
        _validate_boundary(boundary, failures, fields)

    ordered_failures = _ordered_failures(failures)
    safe_source_failures = (
        _ordered_validator_failures(source_failures)
        if source_failures_valid and source_failures_known
        else []
    )

    if ordered_failures:
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=ordered_failures,
            fields=fields,
        )

    if ready_value is True:
        return _result(
            ci_ok=True,
            reason_code=_REASON_READY,
            failures=[],
            fields=fields,
        )

    return _result(
        ci_ok=False,
        reason_code=_REASON_NOT_READY,
        failures=safe_source_failures,
        fields=fields,
    )


def _validate_boundary(
    boundary: Mapping[object, object],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if set(boundary.keys()) != set(_BOUNDARY_KEYS):
        _append(failures, "boundary_shape_mismatch")

    if boundary.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "validator_surface_invalid")

    version = boundary.get("version")
    if (
        type(version) is bool
        or type(version) is not int
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "validator_version_invalid")

    _validate_validator_checkpoint(
        boundary.get("validator_checkpoint"),
        failures,
    )
    _validate_source_refs(boundary.get("source_refs"), failures)
    _validate_declaration_groups(
        boundary.get("declaration_groups"),
        failures,
        fields,
    )
    _validate_false_authority_flags(
        boundary.get("required_false_authority_flags"),
        failures,
    )
    _validate_true_declarations(
        boundary.get("required_true_declarations"),
        failures,
        fields,
    )
    _validate_authority(boundary.get("authority"), failures)

    json_safe = boundary.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _validate_validator_checkpoint(
    candidate: object,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "validator_checkpoint_invalid")
        return

    if set(candidate.keys()) != set(_VALIDATOR_CHECKPOINT.keys()):
        _append(failures, "validator_checkpoint_invalid")
        return

    for field, expected in _VALIDATOR_CHECKPOINT.items():
        if candidate.get(field) != expected:
            _append(failures, "validator_checkpoint_invalid")
            return


def _validate_source_refs(candidate: object, failures: list[str]) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "source_ref_mismatch")
        return

    if set(candidate.keys()) != set(_SOURCE_REFS.keys()):
        _append(failures, "source_ref_mismatch")
        return

    for field, expected in _SOURCE_REFS.items():
        if candidate.get(field) != expected:
            _append(failures, "source_ref_mismatch")
            return


def _validate_declaration_groups(
    candidate: object,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "declaration_group_invalid")
        return

    if set(candidate.keys()) != set(_DECLARATION_GROUPS):
        _append(failures, "declaration_group_invalid")

    declaration_groups = fields["declaration_groups"]
    assert isinstance(declaration_groups, dict)

    for group in _DECLARATION_GROUPS:
        group_candidate = candidate.get(group)
        if not isinstance(group_candidate, Mapping):
            _append(failures, "declaration_group_invalid")
            continue

        safe_group: dict[str, bool] = {}
        group_invalid = False
        for key, value in group_candidate.items():
            if not isinstance(key, str) or type(value) is not bool:
                group_invalid = True
            else:
                safe_group[key] = value

        if group_invalid:
            _append(failures, "declaration_group_invalid")
        declaration_groups[group] = safe_group


def _validate_false_authority_flags(
    candidate: object,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "authorization_flag_invalid")
        return

    if set(candidate.keys()) != set(_REQUIRED_FALSE_AUTHORITY_FLAGS):
        _append(failures, "authorization_flag_invalid")

    for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS:
        value = candidate.get(flag)
        if type(value) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif value is True:
            _append(failures, "authorization_flag_true")


def _validate_true_declarations(
    candidate: object,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "required_declaration_invalid")
        return

    if set(candidate.keys()) != set(_REQUIRED_TRUE_DECLARATIONS):
        _append(failures, "required_declaration_invalid")

    required_true_declarations = fields["required_true_declarations"]
    assert isinstance(required_true_declarations, dict)

    for declaration in _REQUIRED_TRUE_DECLARATIONS:
        value = candidate.get(declaration)
        if type(value) is not bool:
            _append(failures, "required_declaration_invalid")
        else:
            required_true_declarations[declaration] = value
            if value is False:
                _append(failures, "required_declaration_false")


def _validate_authority(candidate: object, failures: list[str]) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "authorization_flag_invalid")
        return

    if set(candidate.keys()) != set(_AUTHORITY_SUMMARY_FLAGS):
        _append(failures, "authorization_flag_invalid")

    for flag in _AUTHORITY_SUMMARY_FLAGS:
        value = candidate.get(flag)
        if type(value) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif value is True:
            _append(failures, "authorization_flag_true")


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["boundary"] = _boundary_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _boundary_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    output["validator_checkpoint"] = deepcopy(_VALIDATOR_CHECKPOINT)
    output["source_refs"] = deepcopy(fields["source_refs"])
    output["declaration_groups"] = deepcopy(fields["declaration_groups"])
    output["required_false_authority_flags"] = {
        flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
    }
    output["required_true_declarations"] = deepcopy(
        fields["required_true_declarations"]
    )
    output["json_safe"] = True
    output["authority"] = deepcopy(_AUTHORITY_SUMMARY_FLAGS)
    assert tuple(output.keys()) == _BOUNDARY_KEYS
    return output


def _empty_boundary_fields() -> dict[str, object]:
    return {
        "source_refs": deepcopy(_SOURCE_REFS),
        "declaration_groups": {group: {} for group in _DECLARATION_GROUPS},
        "required_true_declarations": {
            declaration: None for declaration in _REQUIRED_TRUE_DECLARATIONS
        },
    }


def _is_string_list(candidate: object) -> bool:
    if not isinstance(candidate, list):
        return False
    for item in candidate:
        if not isinstance(item, str):
            return False
    return True


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _ordered_validator_failures(candidate: object) -> list[str]:
    if not isinstance(candidate, list):
        return []
    return [
        failure
        for failure in _VALIDATOR_FAILURE_TAXONOMY
        if failure in candidate
    ]
