"""Pure validator for rendered runtime authority boundary declarations."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "runtime_authority_checker_enforcer_boundary_validator_manifest",
    "validate_runtime_authority_checker_enforcer_boundary",
]


_SURFACE = "runtime_authority_checker_enforcer_boundary_validator"
_BOUNDARY_SURFACE = "RuntimeAuthorityCheckerEnforcerBoundaryV1"
_VERSION = 1

_REASON_INVALID = "invalid_runtime_authority_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_INPUT_KEY = "runtime_authority_checker_enforcer_boundary"
_INPUT_KEYS = (_INPUT_KEY,)

_BOUNDARY_KEYS = (
    "surface",
    "version",
    "source_refs",
    "readiness_signals",
    "authority_input_model",
    "authority_grant_ref_model",
    "checker_boundary",
    "enforcer_boundary",
    "checker_enforcer_separation",
    "revocation_expiry_model",
    "denial_fail_closed_behavior",
    "incident_classification",
    "required_false_authority_flags",
    "required_true_declarations",
    "json_safe",
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
    "service-call-execution-boundary-read-only-stack-v1": (
        "2a82b78665541d2e408113646ea11fbda4b62037"
    ),
    "runtime-authority-checker-enforcer-boundary-spec-only-v1": (
        "9bd776b4178ce627e28eb430ea07d6b7a2a002ce"
    ),
}

_READINESS_SIGNALS = (
    "service_adapter_ready",
    "method_authority_ready",
    "service_call_execution_boundary_ready",
    "runtime_authority_ready",
    "ci_ok",
    "preflight_readiness",
    "execution_authorization_readiness",
    "executor_precondition_readiness",
    "write_path_readiness",
    "repository_uow_allowlist_readiness",
    "evidence_audit_append_readiness",
    "restore_dry_run_readiness",
)

_BOUNDARY_MODEL_GROUPS = {
    "authority_input_model": (
        "source_bound",
        "operation_bound",
        "revocable",
        "expiring",
        "fail_closed",
        "json_safe",
        "authority_grant_ref_required",
        "readiness_inputs_only",
    ),
    "authority_grant_ref_model": (
        "explicit_grant_object_required",
        "explicit_authority_ref_required",
        "source_refs_required",
        "operation_refs_required",
        "target_surface_required",
        "permitted_action_class_required",
        "forbidden_action_class_required",
        "issuer_required",
        "expiry_required",
        "revocation_required",
        "operator_confirmation_ref_required",
        "human_approval_ref_required",
        "idempotency_key_ref_required",
        "evidence_audit_refs_required",
        "fail_closed_required",
    ),
    "checker_boundary": (
        "future_only",
        "forbidden_now",
        "already_rendered_declarations_only",
        "bounded_json_safe_decision_only",
        "no_service_calls",
        "no_db",
        "no_append",
        "no_mutation",
        "no_idempotency_reservation",
        "no_transaction",
        "no_rollback",
        "no_executor_dispatch",
        "no_durable_writes",
    ),
    "enforcer_boundary": (
        "future_only",
        "forbidden_now",
        "checker_output_only",
        "denial_fail_closed_only",
        "no_service_calls",
        "no_db",
        "no_append",
        "no_mutation",
        "no_idempotency_reservation",
        "no_transaction",
        "no_rollback",
        "no_executor_dispatch",
        "no_durable_writes",
    ),
    "checker_enforcer_separation": (
        "checker_separate_from_enforcer",
        "checker_separate_from_execution",
        "enforcer_separate_from_execution",
        "append_separate_from_checker",
        "db_write_separate_from_checker",
        "executor_dispatch_separate_from_checker",
        "no_combined_checker_enforcer_executor_service_call",
    ),
    "revocation_expiry_model": (
        "missing_authority_fail_closed",
        "malformed_authority_fail_closed",
        "expired_authority_fail_closed",
        "revoked_authority_fail_closed",
        "mismatched_authority_fail_closed",
        "ambiguous_authority_incident_class",
        "unverifiable_authority_fail_closed",
    ),
    "denial_fail_closed_behavior": (
        "default_denial",
        "no_silent_success",
        "no_partial_success",
        "no_implicit_authority_escalation",
        "no_readiness_to_runtime_promotion",
        "post_denial_execution_incident_class",
        "runtime_write_without_authority_incident_class",
        "service_call_without_authority_incident_class",
    ),
    "incident_classification": (
        "ambiguous_authority_incident_class",
        "checker_enforcer_disagreement_incident_class",
        "revoked_authority_use_attempt_incident_class",
        "expired_authority_use_attempt_fail_closed",
        "malformed_authority_fail_closed",
        "post_denial_execution_attempt_incident_class",
        "runtime_write_without_authority_incident_class",
        "service_call_without_authority_incident_class",
    ),
}

_GROUP_FAILURES = {
    "authority_input_model": "authority_input_model_invalid",
    "authority_grant_ref_model": "authority_grant_ref_model_invalid",
    "checker_boundary": "checker_boundary_invalid",
    "enforcer_boundary": "enforcer_boundary_invalid",
    "checker_enforcer_separation": "checker_enforcer_separation_invalid",
    "revocation_expiry_model": "revocation_expiry_model_invalid",
    "denial_fail_closed_behavior": "denial_fail_closed_behavior_invalid",
    "incident_classification": "incident_classification_invalid",
}

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "runtime_authority_checker_authorized",
    "runtime_authority_enforcer_authorized",
    "runtime_authority_runtime_authorized",
    "runtime_allowlist_authorized",
    "runtime_checker_authorized",
    "runtime_enforcer_authorized",
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
    "executor_implementation_authorized",
    "executor_service_dispatch_authorized",
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
    "runtime_authority_checker_forbidden",
    "runtime_authority_enforcer_forbidden",
    "runtime_authority_runtime_forbidden",
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "authority_source_bound_required",
    "authority_operation_bound_required",
    "authority_revocable_required",
    "authority_expiry_required",
    "authority_fail_closed_required",
    "authority_grant_object_required_for_future_runtime",
    "authority_grant_schema_required_for_future_runtime",
    "authority_ref_required",
    "authority_ref_source_bound_required",
    "authority_ref_operation_bound_required",
    "authority_ref_revocation_checked_required",
    "authority_ref_expiry_checked_required",
    "checker_enforcer_separation_required",
    "checker_output_json_safe_required",
    "checker_output_bounded_required",
    "enforcer_input_json_safe_required",
    "enforcer_denial_fail_closed_required",
    "missing_authority_fail_closed",
    "malformed_authority_fail_closed",
    "mismatched_authority_fail_closed",
    "expired_authority_fail_closed",
    "revoked_authority_fail_closed",
    "ambiguous_authority_incident_class",
    "silent_authority_success_forbidden",
    "implicit_authority_escalation_forbidden",
    "service_calls_forbidden",
    "service_call_execution_forbidden",
    "service_adapter_implementation_forbidden",
    "db_repository_uow_writes_forbidden",
    "evidence_append_forbidden",
    "audit_append_forbidden",
    "transaction_runtime_forbidden",
    "idempotency_reservation_forbidden",
    "rollback_runtime_forbidden",
    "executor_dispatch_forbidden",
    "durable_writes_forbidden",
    "irreversible_actions_forbidden",
    "future_validator_required",
    "future_ci_required",
)

_AUTHORITY_SUMMARY_FLAGS = {
    "runtime_authority_checker_authorized": False,
    "runtime_authority_enforcer_authorized": False,
    "runtime_authority_runtime_authorized": False,
    "service_call_execution_authorized": False,
    "service_adapter_runtime_authorized": False,
    "service_method_call_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "repository_uow_writes_authorized": False,
    "transaction_runtime_authorized": False,
    "idempotency_reservation_authorized": False,
    "rollback_runtime_authorized": False,
    "executor_service_dispatch_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
}

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "readiness_signal_invalid",
    "authority_input_model_invalid",
    "authority_grant_ref_model_invalid",
    "checker_boundary_invalid",
    "enforcer_boundary_invalid",
    "checker_enforcer_separation_invalid",
    "revocation_expiry_model_invalid",
    "denial_fail_closed_behavior_invalid",
    "incident_classification_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "required_declaration_invalid",
    "required_declaration_false",
    "json_safe_invalid",
)

_INVALID_PAYLOAD_FAILURES = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
)

_NON_AUTHORITY_STATEMENT = {
    "runtime_authority_boundary_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "runtime_authority_boundary_ready_authorizes_runtime": False,
    "runtime_authority_boundary_ready_authorizes_checker_runtime": False,
    "runtime_authority_boundary_ready_authorizes_enforcer_runtime": False,
    "runtime_authority_boundary_ready_authorizes_service_calls": False,
    "runtime_authority_boundary_ready_authorizes_evidence_append": False,
    "runtime_authority_boundary_ready_authorizes_audit_append": False,
    "runtime_authority_boundary_ready_authorizes_repository_uow_writes": False,
    "runtime_authority_boundary_ready_authorizes_transaction_runtime": False,
    "runtime_authority_boundary_ready_authorizes_idempotency": False,
    "runtime_authority_boundary_ready_authorizes_rollback": False,
    "runtime_authority_boundary_ready_authorizes_executor_dispatch": False,
    "runtime_authority_boundary_ready_authorizes_durable_writes": False,
    "runtime_authority_boundary_ready_authorizes_irreversible_actions": False,
}

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "expected_top_level_keys": list(_INPUT_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_readiness_signals": {
        signal: False for signal in _READINESS_SIGNALS
    },
    "expected_boundary_model_groups": {
        group: list(fields)
        for group, fields in _BOUNDARY_MODEL_GROUPS.items()
    },
    "expected_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "expected_true_declarations": list(_REQUIRED_TRUE_DECLARATIONS),
    "failure_taxonomy": list(_FAILURE_ORDER),
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY_FLAGS),
    "non_authority_statement": deepcopy(_NON_AUTHORITY_STATEMENT),
}


def runtime_authority_checker_enforcer_boundary_validator_manifest(
) -> dict[str, object]:
    return deepcopy(_MANIFEST)


def validate_runtime_authority_checker_enforcer_boundary(
    payload: object,
) -> dict[str, object]:
    failures: list[str] = []

    if not isinstance(payload, Mapping):
        _append(failures, "payload_not_mapping")
        return _result(failures)

    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")
        return _result(failures)

    boundary = payload.get(_INPUT_KEY)
    if not isinstance(boundary, Mapping):
        _append(failures, "boundary_not_mapping")
        return _result(failures)

    if set(boundary.keys()) != set(_BOUNDARY_KEYS):
        _append(failures, "boundary_shape_mismatch")
        return _result(failures)

    _validate_boundary(boundary, failures)
    return _result(failures)


def _validate_boundary(
    boundary: Mapping[object, object],
    failures: list[str],
) -> None:
    if boundary.get("surface") != _BOUNDARY_SURFACE:
        _append(failures, "boundary_surface_invalid")

    version = boundary.get("version")
    if type(version) is not int or version != _VERSION:
        _append(failures, "boundary_version_invalid")

    _validate_source_refs(boundary.get("source_refs"), failures)
    _validate_readiness_signals(
        boundary.get("readiness_signals"),
        failures,
    )

    for group, fields in _BOUNDARY_MODEL_GROUPS.items():
        _validate_true_group(
            boundary.get(group),
            fields,
            _GROUP_FAILURES[group],
            failures,
        )

    _validate_false_authority_flags(
        boundary.get("required_false_authority_flags"),
        failures,
    )
    _validate_true_declarations(
        boundary.get("required_true_declarations"),
        failures,
    )

    json_safe = boundary.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _validate_source_refs(
    candidate: object,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "source_ref_mismatch")
        return
    if set(candidate.keys()) != set(_SOURCE_REFS.keys()):
        _append(failures, "source_ref_mismatch")
        return
    for name, expected in _SOURCE_REFS.items():
        value = candidate.get(name)
        if type(value) is not str or value != expected:
            _append(failures, "source_ref_mismatch")
            return


def _validate_readiness_signals(
    candidate: object,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "readiness_signal_invalid")
        return
    if set(candidate.keys()) != set(_READINESS_SIGNALS):
        _append(failures, "readiness_signal_invalid")
        return
    for signal in _READINESS_SIGNALS:
        value = candidate.get(signal)
        if type(value) is not bool or value is not False:
            _append(failures, "readiness_signal_invalid")
            return


def _validate_true_group(
    candidate: object,
    expected_fields: tuple[str, ...],
    failure: str,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, failure)
        return
    if set(candidate.keys()) != set(expected_fields):
        _append(failures, failure)
        return
    for field in expected_fields:
        value = candidate.get(field)
        if type(value) is not bool or value is not True:
            _append(failures, failure)
            return


def _validate_false_authority_flags(
    candidate: object,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "authorization_flag_invalid")
        return
    if set(candidate.keys()) != set(_REQUIRED_FALSE_AUTHORITY_FLAGS):
        _append(failures, "authorization_flag_invalid")
        return

    true_found = False
    for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS:
        value = candidate.get(flag)
        if type(value) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif value is True:
            true_found = True
    if true_found:
        _append(failures, "authorization_flag_true")


def _validate_true_declarations(
    candidate: object,
    failures: list[str],
) -> None:
    if not isinstance(candidate, Mapping):
        _append(failures, "required_declaration_invalid")
        return
    if set(candidate.keys()) != set(_REQUIRED_TRUE_DECLARATIONS):
        _append(failures, "required_declaration_invalid")
        return

    false_found = False
    for declaration in _REQUIRED_TRUE_DECLARATIONS:
        value = candidate.get(declaration)
        if type(value) is not bool:
            _append(failures, "required_declaration_invalid")
        elif value is False:
            false_found = True
    if false_found:
        _append(failures, "required_declaration_false")


def _result(failures: list[str]) -> dict[str, object]:
    ordered_failures = _ordered_failures(failures)
    ready = not ordered_failures
    if ready:
        reason_code = _REASON_READY
    elif _has_invalid_payload_failure(ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return {
        "runtime_authority_boundary_ready": ready,
        "reason_code": reason_code,
        "failures": ordered_failures,
        "boundary": _boundary_output(),
        "authority": deepcopy(_AUTHORITY_SUMMARY_FLAGS),
    }


def _boundary_output() -> dict[str, object]:
    output = {
        "surface": _BOUNDARY_SURFACE,
        "version": _VERSION,
        "source_refs": deepcopy(_SOURCE_REFS),
        "readiness_signals": {
            signal: False for signal in _READINESS_SIGNALS
        },
    }
    for group, fields in _BOUNDARY_MODEL_GROUPS.items():
        output[group] = {field: True for field in fields}
    output["required_false_authority_flags"] = {
        flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
    }
    output["required_true_declarations"] = {
        declaration: True for declaration in _REQUIRED_TRUE_DECLARATIONS
    }
    output["json_safe"] = True
    return output


def _has_invalid_payload_failure(failures: list[str]) -> bool:
    return any(failure in _INVALID_PAYLOAD_FAILURES for failure in failures)


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
