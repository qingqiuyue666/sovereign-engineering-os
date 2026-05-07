"""Pure validator for already-rendered service call boundary declarations."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_call_execution_boundary_validator_manifest",
    "validate_service_call_execution_boundary",
]

_SURFACE = "service_call_execution_boundary_validator"
_BOUNDARY_SURFACE = "ServiceCallExecutionBoundaryV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_service_call_execution_boundary_v1"

_REASON_INVALID = "invalid_service_call_execution_boundary_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_INPUT_KEY = "service_call_execution_boundary"
_INPUT_KEYS = (_INPUT_KEY,)

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

_DECLARATION_GROUPS = {
    "service_call_attempt_boundary": (
        "exact_service_identity_required",
        "exact_service_class_name_required",
        "exact_service_method_name_required",
        "operation_kind_required",
        "phase_required",
        "task_ref_binding_required",
        "authority_ref_required",
        "method_authority_ci_required",
        "execution_authorization_ci_required",
        "human_approval_required",
        "operator_confirmation_required",
        "idempotency_key_required",
        "transaction_placement_required",
        "evidence_pre_bookkeeping_required",
        "audit_pre_bookkeeping_required",
        "evidence_post_bookkeeping_required",
        "audit_post_bookkeeping_required",
        "service_result_contract_required",
        "failure_policy_required",
        "revocation_expiry_required",
        "json_safety_required",
        "service_call_attempt_not_created_by_spec",
        "service_call_attempt_not_executed_by_spec",
    ),
    "authority_input_binding": (
        "authority_ref_required",
        "authority_ref_source_bound_required",
        "authority_ref_operation_bound_required",
        "missing_authority_fail_closed",
        "mismatched_authority_fail_closed",
        "revoked_authority_fail_closed",
        "expired_authority_fail_closed",
        "authority_ref_does_not_authorize_runtime",
    ),
    "method_authority_ci_binding": (
        "service_method_authority_ci_required",
        "service_method_authority_lineage_required",
        "method_authority_ready_is_prerequisite_only",
        "method_authority_ci_ok_is_prerequisite_only",
        "method_authority_does_not_authorize_service_call",
    ),
    "execution_authorization_binding": (
        "execution_authorization_ci_required",
        "execution_authorization_readiness_is_not_execution",
        "executor_remains_unauthorized",
    ),
    "human_approval_binding": (
        "human_approval_required",
        "human_approval_ref_required",
        "missing_human_approval_fail_closed",
        "mismatched_human_approval_fail_closed",
        "human_approval_does_not_bypass_boundary",
    ),
    "operator_confirmation_binding": (
        "operator_confirmation_required",
        "operator_confirmation_ref_required",
        "missing_operator_confirmation_fail_closed",
        "mismatched_operator_confirmation_fail_closed",
        "operator_confirmation_does_not_bypass_boundary",
    ),
    "idempotency_key_binding": (
        "idempotency_key_required",
        "idempotency_key_source_bound_required",
        "idempotency_key_operation_bound_required",
        "same_key_same_binding_replay_classification_only",
        "same_key_different_binding_fail_closed",
        "ambiguous_idempotency_state_incident_class",
        "idempotency_reservation_runtime_not_authorized",
    ),
    "transaction_placement_binding": (
        "transaction_placement_required",
        "kernel_owned_transaction_required_for_future_runtime",
        "service_transaction_ownership_forbidden_by_default",
        "uncontrolled_nested_transaction_forbidden",
        "out_of_band_service_call_requires_future_declaration",
        "transaction_runtime_not_authorized",
    ),
    "evidence_audit_bookkeeping_boundary": (
        "evidence_pre_bookkeeping_required",
        "audit_pre_bookkeeping_required",
        "evidence_post_bookkeeping_required",
        "audit_post_bookkeeping_required",
        "missing_pre_bookkeeping_blocks_future_call",
        "missing_post_bookkeeping_after_service_result_incident_class",
        "evidence_append_not_authorized",
        "audit_append_not_authorized",
    ),
    "service_result_intake_boundary": (
        "service_result_contract_required",
        "service_result_json_safe_required",
        "service_result_bounded_required",
        "service_result_no_runtime_handles_required",
        "service_result_no_service_objects_required",
        "service_result_no_db_handles_required",
        "service_result_no_repository_uow_handles_required",
        "service_result_no_exception_objects_required",
        "service_result_no_raw_repr_required",
        "implicit_append_success_forbidden",
        "implicit_audit_success_forbidden",
    ),
    "service_result_ref_binding": (
        "service_result_to_evidence_ref_binding_required",
        "service_result_to_audit_ref_binding_required",
        "fabricated_refs_forbidden",
        "missing_refs_fail_closed_before_call",
        "missing_refs_after_service_result_incident_class",
        "result_cannot_create_refs_without_authorized_append_runtime",
    ),
    "failure_incident_classification": (
        "expected_refusal_is_not_execution_failure",
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
    ),
    "rollback_compensation_boundary": (
        "future_rollback_compensation_policy_required",
        "rollback_runtime_not_authorized",
        "compensation_runtime_not_authorized",
        "rollback_failure_incident_class",
    ),
    "forbidden_direct_service_call_boundary": (
        "direct_service_call_forbidden",
        "dynamic_lookup_forbidden",
        "wildcard_service_authority_forbidden",
        "class_level_service_authority_forbidden",
        "module_level_service_authority_forbidden",
        "executor_owned_direct_service_call_forbidden",
    ),
    "forbidden_db_repository_uow_boundary": (
        "db_open_write_forbidden",
        "repository_uow_import_call_forbidden",
        "direct_sql_raw_sqlite_forbidden",
        "service_owned_uow_forbidden",
        "service_adapter_transaction_ownership_forbidden",
    ),
    "forbidden_executor_boundary": (
        "executor_implementation_forbidden",
        "executor_owned_service_call_forbidden",
        "restore_execution_forbidden",
        "cli_execution_forbidden",
    ),
    "runtime_checker_enforcer_future_requirement": (
        "runtime_checker_required_for_future_runtime",
        "runtime_enforcer_required_for_future_runtime",
        "runtime_checker_not_implemented_by_spec",
        "runtime_enforcer_not_implemented_by_spec",
        "runtime_checker_authority_false",
        "runtime_enforcer_authority_false",
    ),
    "revocation_expiry_boundary": (
        "revocation_required",
        "expiry_required",
        "revoked_authority_fail_closed",
        "expired_authority_fail_closed",
        "missing_revocation_status_fail_closed",
        "missing_expiry_status_fail_closed",
    ),
}

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

_BOUNDARY_KEYS = (
    "surface",
    "version",
    "source_refs",
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
    "required_false_authority_flags",
    "required_true_declarations",
    "json_safe",
)

_OUTPUT_KEYS = (
    "service_call_execution_boundary_ready",
    "reason_code",
    "failures",
    "boundary",
)

_BOUNDARY_OUTPUT_KEYS = (
    "surface",
    "version",
    "source_refs",
    "declaration_groups",
    "required_false_authority_flags",
    "required_true_declarations",
    "json_safe",
    "authority",
)

_FAILURE_ORDER = (
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

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "boundary_not_mapping",
        "boundary_shape_mismatch",
        "boundary_surface_invalid",
        "boundary_version_invalid",
        "source_ref_mismatch",
        "declaration_group_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "expected_top_level_keys": list(_INPUT_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_declaration_groups": {
        group: list(declarations)
        for group, declarations in _DECLARATION_GROUPS.items()
    },
    "required_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "required_true_declarations": list(_REQUIRED_TRUE_DECLARATIONS),
    "failure_taxonomy": list(_FAILURE_ORDER),
    "authority_summary_flags": deepcopy(_AUTHORITY_SUMMARY_FLAGS),
    "non_authority": {
        "ready_authorizes_service_call_execution": False,
        "ready_authorizes_service_adapter_runtime": False,
        "ready_authorizes_service_method_calls": False,
        "ready_authorizes_evidence_audit_append": False,
        "ready_authorizes_db_repository_uow_writes": False,
        "ready_authorizes_transaction_runtime": False,
        "ready_authorizes_idempotency_reservation_runtime": False,
        "ready_authorizes_rollback_runtime": False,
        "ready_authorizes_checker_enforcer": False,
        "ready_authorizes_executor_restore_cli_schema_daemon": False,
        "ready_authorizes_durable_writes": False,
        "ready_authorizes_irreversible_actions": False,
    },
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "json_safe": True,
}


def service_call_execution_boundary_validator_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def validate_service_call_execution_boundary(
    payload: object,
) -> dict[str, object]:
    fields = _empty_boundary_fields()

    if not isinstance(payload, Mapping):
        return _result(
            ready=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    boundary = payload.get(_INPUT_KEY)
    _validate_boundary(boundary, failures, fields)

    ordered_failures = _ordered_failures(failures)
    ready = ordered_failures == []
    if ready:
        reason_code = _REASON_READY
    elif _has_structural_failure(ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ready=ready,
        reason_code=reason_code,
        failures=ordered_failures,
        fields=fields,
    )


def _validate_boundary(
    boundary: object,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not isinstance(boundary, Mapping):
        _append(failures, "boundary_not_mapping")
        return

    if set(boundary.keys()) != set(_BOUNDARY_KEYS):
        _append(failures, "boundary_shape_mismatch")

    if boundary.get("surface") != _BOUNDARY_SURFACE:
        _append(failures, "boundary_surface_invalid")

    version = boundary.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "boundary_version_invalid")

    _validate_source_refs(boundary.get("source_refs"), failures, fields)

    for group_name, expected_declarations in _DECLARATION_GROUPS.items():
        _validate_declaration_group(
            group_name,
            boundary.get(group_name),
            expected_declarations,
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

    json_safe = boundary.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _validate_source_refs(
    candidate: object,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "source_ref_mismatch")
        return

    fields["source_refs"] = dict(candidate)
    if set(candidate.keys()) != set(_SOURCE_REFS.keys()):
        _append(failures, "source_ref_mismatch")
        return

    for name, expected in _SOURCE_REFS.items():
        if candidate.get(name) != expected:
            _append(failures, "source_ref_mismatch")
            return


def _validate_declaration_group(
    group_name: str,
    candidate: object,
    expected_declarations: tuple[str, ...],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    group_fields = {
        declaration: None for declaration in expected_declarations
    }
    fields["declaration_groups"][group_name] = group_fields

    if not isinstance(candidate, Mapping):
        _append(failures, "declaration_group_invalid")
        return

    if set(candidate.keys()) != set(expected_declarations):
        _append(failures, "declaration_group_invalid")

    for declaration in expected_declarations:
        value = candidate.get(declaration)
        if type(value) is not bool:
            _append(failures, "required_declaration_invalid")
        else:
            group_fields[declaration] = value
            if value is False:
                _append(failures, "required_declaration_false")


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

    for declaration in _REQUIRED_TRUE_DECLARATIONS:
        value = candidate.get(declaration)
        if type(value) is not bool:
            _append(failures, "required_declaration_invalid")
        else:
            fields["required_true_declarations"][declaration] = value
            if value is False:
                _append(failures, "required_declaration_false")


def _result(
    *,
    ready: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["service_call_execution_boundary_ready"] = ready
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["boundary"] = _boundary_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _boundary_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
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
    assert tuple(output.keys()) == _BOUNDARY_OUTPUT_KEYS
    return output


def _empty_boundary_fields() -> dict[str, object]:
    return {
        "source_refs": deepcopy(_SOURCE_REFS),
        "declaration_groups": {
            group: {
                declaration: None for declaration in declarations
            }
            for group, declarations in _DECLARATION_GROUPS.items()
        },
        "required_true_declarations": {
            declaration: None
            for declaration in _REQUIRED_TRUE_DECLARATIONS
        },
    }


def _has_structural_failure(ordered_failures: list[str]) -> bool:
    for failure in ordered_failures:
        if failure in _STRUCTURAL_FAILURES:
            return True
    return False


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
