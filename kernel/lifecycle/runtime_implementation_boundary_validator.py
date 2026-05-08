"""Read-only validator for RuntimeImplementationBoundaryV1 declarations."""

from collections.abc import Mapping
from copy import deepcopy

__all__ = [
    "runtime_implementation_boundary_validator_manifest",
    "validate_runtime_implementation_boundary",
]

_SURFACE = "runtime_implementation_boundary_validator"
_CONTRACT_NAME = "RuntimeImplementationBoundaryV1"
_VERSION = 1

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_PAYLOAD = "invalid_runtime_implementation_boundary_payload"

_INPUT_KEY = "runtime_implementation_boundary"
_INPUT_KEYS = (_INPUT_KEY,)

_BOUNDARY_KEYS = (
    "surface",
    "version",
    "source_refs",
    "runtime_implementation_boundary_model",
    "required_runtime_boundaries",
    "false_authority_flags",
    "true_declarations",
    "json_safety",
    "future_validator_requirements",
    "future_ci_requirements",
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
    "runtime-authority-checker-enforcer-read-only-stack-v1": (
        "a749545998e94aceee52775d363f9b8bb43e26a4"
    ),
    "runtime-authority-grant-object-read-only-stack-v1": (
        "4acbddba3e0897d16bcfc74007ecd094817faa11"
    ),
    "service-call-admission-gate-read-only-stack-v1": (
        "c581c027bfcf29a220b9f0de75bb6c7b2e8f97b0"
    ),
    "runtime-final-eligibility-gate-read-only-stack-v1": (
        "395346a96ca6ecf229a40127fe13cff1172079ac"
    ),
    "runtime-implementation-boundary-spec-only-v1": (
        "aa8d394571a613a47c5b7256912a8b297db88785"
    ),
}

_RUNTIME_IMPLEMENTATION_BOUNDARY_MODEL = (
    "non_executable",
    "pre_implementation_boundary_model_only",
    "future_runtime_segments_require_separately_frozen_boundaries",
    "runtime_blocked_until_all_boundary_contracts_frozen",
    "validator_ci_read_only_stack_required_before_runtime_reconsideration",
    "readiness_is_not_runtime_authority",
    "authorization_is_not_execution",
    "default_deny_required",
    "fail_closed_required",
)

_REQUIRED_RUNTIME_BOUNDARIES = (
    "runtime_checker_implementation_boundary",
    "runtime_enforcer_implementation_boundary",
    "runtime_checker_enforcer_separation_boundary",
    "runtime_authority_grant_usage_boundary",
    "authority_ref_runtime_usage_boundary",
    "service_call_admission_runtime_boundary",
    "admission_decision_runtime_boundary",
    "service_call_runtime_binding",
    "human_approval_runtime_binding",
    "operator_confirmation_runtime_binding",
    "execution_authorization_runtime_binding",
    "method_authority_runtime_binding",
    "service_call_execution_runtime_binding",
    "authority_expiry_runtime_check",
    "authority_revocation_runtime_check",
    "idempotency_reservation_runtime_boundary",
    "idempotency_replay_classifier_boundary",
    "transaction_runtime_boundary",
    "kernel_owned_transaction_binding",
    "evidence_pre_bookkeeping_runtime_boundary",
    "audit_pre_bookkeeping_runtime_boundary",
    "evidence_post_bookkeeping_runtime_boundary",
    "audit_post_bookkeeping_runtime_boundary",
    "service_result_intake_runtime_boundary",
    "service_result_to_evidence_audit_binding",
    "failure_incident_classifier_boundary",
    "rollback_compensation_runtime_boundary",
    "executor_service_dispatch_binding",
    "durable_write_final_authorization_gate",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "runtime_implementation_authorized",
    "runtime_implementation_boundary_authorized",
    "runtime_checker_implementation_authorized",
    "runtime_enforcer_implementation_authorized",
    "runtime_checker_enforcer_separation_authorized",
    "runtime_authority_grant_usage_authorized",
    "authority_ref_runtime_usage_authorized",
    "service_call_admission_runtime_authorized",
    "admission_decision_runtime_authorized",
    "service_call_runtime_binding_authorized",
    "human_approval_runtime_binding_authorized",
    "operator_confirmation_runtime_binding_authorized",
    "execution_authorization_runtime_binding_authorized",
    "method_authority_runtime_binding_authorized",
    "service_call_execution_runtime_binding_authorized",
    "authority_expiry_runtime_check_authorized",
    "authority_revocation_runtime_check_authorized",
    "idempotency_reservation_runtime_authorized",
    "idempotency_replay_classifier_authorized",
    "transaction_runtime_authorized",
    "kernel_owned_transaction_binding_authorized",
    "evidence_pre_bookkeeping_runtime_authorized",
    "audit_pre_bookkeeping_runtime_authorized",
    "evidence_post_bookkeeping_runtime_authorized",
    "audit_post_bookkeeping_runtime_authorized",
    "service_result_intake_runtime_authorized",
    "service_result_to_evidence_audit_binding_authorized",
    "failure_incident_classifier_authorized",
    "rollback_compensation_runtime_authorized",
    "executor_service_dispatch_binding_authorized",
    "durable_write_final_authorization_gate_authorized",
    "runtime_final_eligibility_runtime_authorized",
    "runtime_final_gate_authorized",
    "service_call_admission_gate_authorized",
    "service_call_admission_decision_authorized",
    "runtime_authority_grant_runtime_authorized",
    "runtime_authority_ref_runtime_authorized",
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
    "runtime_implementation_forbidden",
    "runtime_implementation_boundary_is_not_runtime",
    "read_only_stack_readiness_is_not_runtime_authority",
    "runtime_final_eligibility_readiness_is_not_runtime_authority",
    "service_call_admission_readiness_is_not_runtime_authority",
    "runtime_authority_grant_object_readiness_is_not_runtime_authority",
    "runtime_authority_checker_enforcer_readiness_is_not_runtime_authority",
    "service_call_execution_boundary_is_not_runtime_authority",
    "service_method_authority_is_not_runtime_authority",
    "service_adapter_boundary_is_not_runtime_authority",
    "execution_authorization_is_not_execution",
    "approval_is_not_authority",
    "preflight_is_not_runtime_authority",
    "restore_dry_run_is_not_restore_execution",
    "tag_existence_is_not_authority",
    "runtime_checker_implementation_boundary_required",
    "runtime_enforcer_implementation_boundary_required",
    "runtime_checker_enforcer_separation_boundary_required",
    "runtime_authority_grant_usage_boundary_required",
    "authority_ref_runtime_usage_boundary_required",
    "service_call_admission_runtime_boundary_required",
    "admission_decision_runtime_boundary_required",
    "service_call_runtime_binding_required",
    "human_approval_runtime_binding_required",
    "operator_confirmation_runtime_binding_required",
    "execution_authorization_runtime_binding_required",
    "method_authority_runtime_binding_required",
    "service_call_execution_runtime_binding_required",
    "authority_expiry_runtime_check_required",
    "authority_revocation_runtime_check_required",
    "idempotency_reservation_runtime_required",
    "idempotency_replay_classifier_required",
    "transaction_runtime_boundary_required",
    "kernel_owned_transaction_binding_required",
    "evidence_pre_bookkeeping_runtime_required",
    "audit_pre_bookkeeping_runtime_required",
    "evidence_post_bookkeeping_runtime_required",
    "audit_post_bookkeeping_runtime_required",
    "service_result_intake_runtime_required",
    "service_result_to_evidence_audit_binding_required",
    "failure_incident_classifier_required",
    "rollback_compensation_runtime_required",
    "executor_service_dispatch_binding_required",
    "durable_write_final_authorization_gate_required",
    "runtime_final_eligibility_gate_required",
    "missing_runtime_boundary_fail_closed",
    "malformed_runtime_boundary_fail_closed",
    "mismatched_runtime_boundary_fail_closed",
    "expired_authority_fail_closed",
    "revoked_authority_fail_closed",
    "ambiguous_authority_incident_class",
    "admission_mismatch_incident_class",
    "silent_runtime_success_forbidden",
    "implicit_runtime_escalation_forbidden",
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

_JSON_SAFETY_REQUIREMENTS = (
    "bounded_json_safe_declarations_required",
    "runtime_object_handles_forbidden",
    "db_handles_forbidden",
    "service_objects_forbidden",
    "exception_objects_forbidden",
    "callable_objects_forbidden",
    "subprocess_handles_forbidden",
    "mutable_runtime_state_forbidden",
    "raw_uow_session_connection_objects_forbidden",
    "implicit_object_identity_forbidden",
    "filesystem_handles_forbidden",
    "network_handles_forbidden",
    "raw_repr_leakage_forbidden",
)

_FUTURE_VALIDATOR_REQUIREMENTS = (
    "consumes_already_rendered_runtime_implementation_boundary_declarations_only",
    "read_only",
    "validates_exact_source_refs",
    "validates_required_runtime_boundary_items",
    "validates_false_authority_flags",
    "validates_true_declarations",
    "validates_json_safety",
    "authorizes_no_runtime",
    "calls_no_services",
    "opens_no_db",
    "imports_no_repository_uow",
    "appends_no_evidence_audit",
    "imports_only_mapping_and_deepcopy",
)

_FUTURE_CI_REQUIREMENTS = (
    "consumes_already_rendered_validator_output_only",
    "read_only",
    "does_not_import_or_call_validator",
    "validates_checkpoint_binding",
    "validates_validator_output_shape",
    "validates_failure_taxonomy",
    "validates_hard_false_authority_output",
    "validates_json_safety",
    "authorizes_no_runtime",
    "calls_no_services",
    "opens_no_db",
    "imports_no_repository_uow",
    "appends_no_evidence_audit",
    "imports_only_mapping_and_deepcopy",
)

_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "runtime_boundary_model_invalid",
    "required_runtime_boundary_invalid",
    "required_runtime_boundary_missing",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "required_declaration_invalid",
    "required_declaration_false",
    "json_safety_invalid",
    "future_validator_requirement_invalid",
    "future_ci_requirement_invalid",
    "json_safe_invalid",
)

_INVALID_PAYLOAD_FAILURES = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "json_safe_invalid",
)

_AUTHORITY_DENIALS = (
    "runtime",
    "runtime_implementation",
    "checker_enforcer_runtime",
    "runtime_authority_grant_usage",
    "authority_ref_runtime_usage",
    "service_call_admission_runtime",
    "admission_decision_runtime",
    "service_calls",
    "db_repository_uow_writes",
    "evidence_audit_append",
    "transaction_idempotency_rollback",
    "executor_dispatch",
    "durable_writes",
    "irreversible_actions",
)

_AUTHORITY_SUMMARY = {
    flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
}

_NON_AUTHORITY_SUMMARY = {
    "runtime_implementation_boundary_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "runtime_implementation_boundary_ready_authorizes": {
        denial: False for denial in _AUTHORITY_DENIALS
    },
    "readiness_is_runtime_authority": False,
    "authorization_is_execution": False,
    "tag_existence_is_authority": False,
    "validator_success_is_authority": False,
}

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "contract_name": _CONTRACT_NAME,
    "expected_top_level_keys": list(_INPUT_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_runtime_implementation_boundary_model": list(
        _RUNTIME_IMPLEMENTATION_BOUNDARY_MODEL
    ),
    "required_runtime_boundaries": list(_REQUIRED_RUNTIME_BOUNDARIES),
    "required_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "required_true_declarations": list(_REQUIRED_TRUE_DECLARATIONS),
    "json_safety_requirements": list(_JSON_SAFETY_REQUIREMENTS),
    "future_validator_requirements": list(_FUTURE_VALIDATOR_REQUIREMENTS),
    "future_ci_requirements": list(_FUTURE_CI_REQUIREMENTS),
    "failure_taxonomy": list(_FAILURE_TAXONOMY),
    "allowed_reason_codes": [_READY, _NOT_READY, _INVALID_PAYLOAD],
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY),
    "non_authority_summary": deepcopy(_NON_AUTHORITY_SUMMARY),
    "public_api": list(__all__),
    "import_boundary": [
        "from collections.abc import Mapping",
        "from copy import deepcopy",
    ],
    "json_safe": True,
}

_MAX_DEPTH = 8
_MAX_MAPPING_ITEMS = 512
_MAX_SEQUENCE_ITEMS = 512
_MAX_STRING_LENGTH = 4096


def runtime_implementation_boundary_validator_manifest():
    """Return bounded metadata for the read-only boundary validator."""

    return deepcopy(_MANIFEST)


def validate_runtime_implementation_boundary(payload):
    """Validate an already-rendered RuntimeImplementationBoundaryV1 mapping."""

    failures = []

    if not isinstance(payload, Mapping):
        _append(failures, "payload_not_mapping")
        return _result(failures)

    if not _has_exact_keys(payload, _INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    boundary = payload.get(_INPUT_KEY)
    if not isinstance(boundary, Mapping):
        _append(failures, "boundary_not_mapping")
        return _result(failures)

    if not _has_exact_keys(boundary, _BOUNDARY_KEYS):
        _append(failures, "boundary_shape_mismatch")

    _validate_boundary(boundary, failures)
    return _result(failures)


def _validate_boundary(boundary, failures):
    if boundary.get("surface") != _CONTRACT_NAME:
        _append(failures, "boundary_surface_invalid")

    version = boundary.get("version")
    if type(version) is not int or version != _VERSION:
        _append(failures, "boundary_version_invalid")

    _validate_source_refs(boundary.get("source_refs"), failures)
    _validate_true_mapping(
        boundary.get("runtime_implementation_boundary_model"),
        _RUNTIME_IMPLEMENTATION_BOUNDARY_MODEL,
        "runtime_boundary_model_invalid",
        "runtime_boundary_model_invalid",
        failures,
    )
    _validate_runtime_boundaries(
        boundary.get("required_runtime_boundaries"),
        failures,
    )
    _validate_false_authority_flags(
        boundary.get("false_authority_flags"),
        failures,
    )
    _validate_true_declarations(
        boundary.get("true_declarations"),
        failures,
    )
    _validate_true_mapping(
        boundary.get("json_safety"),
        _JSON_SAFETY_REQUIREMENTS,
        "json_safety_invalid",
        "json_safety_invalid",
        failures,
    )
    _validate_true_mapping(
        boundary.get("future_validator_requirements"),
        _FUTURE_VALIDATOR_REQUIREMENTS,
        "future_validator_requirement_invalid",
        "future_validator_requirement_invalid",
        failures,
    )
    _validate_true_mapping(
        boundary.get("future_ci_requirements"),
        _FUTURE_CI_REQUIREMENTS,
        "future_ci_requirement_invalid",
        "future_ci_requirement_invalid",
        failures,
    )

    json_safe = boundary.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")
    elif not _is_json_safe(boundary, 0):
        _append(failures, "json_safe_invalid")


def _validate_source_refs(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "source_ref_mismatch")
        return
    if not _has_exact_keys(candidate, _SOURCE_REFS.keys()):
        _append(failures, "source_ref_mismatch")
        return
    for name, expected in _SOURCE_REFS.items():
        value = candidate.get(name)
        if type(value) is not str or value != expected:
            _append(failures, "source_ref_mismatch")
            return


def _validate_runtime_boundaries(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "required_runtime_boundary_invalid")
        return

    keys = _string_key_set(candidate)
    if keys is None:
        _append(failures, "required_runtime_boundary_invalid")
        return

    expected = set(_REQUIRED_RUNTIME_BOUNDARIES)
    if keys != expected:
        if expected - keys:
            _append(failures, "required_runtime_boundary_missing")
        if keys - expected:
            _append(failures, "required_runtime_boundary_invalid")

    for boundary in _REQUIRED_RUNTIME_BOUNDARIES:
        value = candidate.get(boundary)
        if type(value) is not bool:
            _append(failures, "required_runtime_boundary_invalid")
        elif value is False:
            _append(failures, "required_runtime_boundary_missing")


def _validate_false_authority_flags(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "authorization_flag_invalid")
        return
    if not _has_exact_keys(candidate, _REQUIRED_FALSE_AUTHORITY_FLAGS):
        _append(failures, "authorization_flag_invalid")

    for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS:
        value = candidate.get(flag)
        if type(value) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif value is True:
            _append(failures, "authorization_flag_true")


def _validate_true_declarations(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "required_declaration_invalid")
        return
    if not _has_exact_keys(candidate, _REQUIRED_TRUE_DECLARATIONS):
        _append(failures, "required_declaration_invalid")

    for declaration in _REQUIRED_TRUE_DECLARATIONS:
        value = candidate.get(declaration)
        if type(value) is not bool:
            _append(failures, "required_declaration_invalid")
        elif value is False:
            _append(failures, "required_declaration_false")


def _validate_true_mapping(
    candidate,
    expected_keys,
    invalid_failure,
    false_failure,
    failures,
):
    if not isinstance(candidate, Mapping):
        _append(failures, invalid_failure)
        return
    if not _has_exact_keys(candidate, expected_keys):
        _append(failures, invalid_failure)

    for key in expected_keys:
        value = candidate.get(key)
        if type(value) is not bool:
            _append(failures, invalid_failure)
        elif value is False:
            _append(failures, false_failure)


def _result(failures):
    ordered_failures = _ordered_failures(failures)
    ready = not ordered_failures
    if ready:
        reason_code = _READY
    elif _has_invalid_payload_failure(ordered_failures):
        reason_code = _INVALID_PAYLOAD
    else:
        reason_code = _NOT_READY

    return {
        "runtime_implementation_boundary_ready": ready,
        "reason_code": reason_code,
        "failures": ordered_failures,
        "boundary": _boundary_output(),
        "authority": deepcopy(_AUTHORITY_SUMMARY),
        "non_authority": deepcopy(_NON_AUTHORITY_SUMMARY),
        "json_safe": True,
    }


def _boundary_output():
    return {
        "surface": _CONTRACT_NAME,
        "version": _VERSION,
        "source_refs": deepcopy(_SOURCE_REFS),
        "runtime_implementation_boundary_model": {
            item: True for item in _RUNTIME_IMPLEMENTATION_BOUNDARY_MODEL
        },
        "required_runtime_boundaries": {
            boundary: True for boundary in _REQUIRED_RUNTIME_BOUNDARIES
        },
        "false_authority_flags": {
            flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
        },
        "true_declarations": {
            declaration: True for declaration in _REQUIRED_TRUE_DECLARATIONS
        },
        "json_safety": {
            requirement: True for requirement in _JSON_SAFETY_REQUIREMENTS
        },
        "future_validator_requirements": {
            requirement: True for requirement in _FUTURE_VALIDATOR_REQUIREMENTS
        },
        "future_ci_requirements": {
            requirement: True for requirement in _FUTURE_CI_REQUIREMENTS
        },
        "json_safe": True,
    }


def _has_exact_keys(candidate, expected):
    keys = _string_key_set(candidate)
    return keys is not None and keys == set(expected)


def _string_key_set(candidate):
    keys = set()
    for key in candidate.keys():
        if type(key) is not str:
            return None
        keys.add(key)
    return keys


def _is_json_safe(value, depth):
    if depth > _MAX_DEPTH:
        return False
    if value is None or type(value) is bool or type(value) is int:
        return True
    if type(value) is str:
        return len(value) <= _MAX_STRING_LENGTH
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAPPING_ITEMS:
            return False
        for key, item in value.items():
            if type(key) is not str or len(key) > _MAX_STRING_LENGTH:
                return False
            if not _is_json_safe(item, depth + 1):
                return False
        return True
    if type(value) is list:
        if len(value) > _MAX_SEQUENCE_ITEMS:
            return False
        for item in value:
            if not _is_json_safe(item, depth + 1):
                return False
        return True
    return False


def _has_invalid_payload_failure(failures):
    for failure in failures:
        if failure in _INVALID_PAYLOAD_FAILURES:
            return True
    return False


def _append(failures, failure):
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures):
    seen = set(failures)
    return [failure for failure in _FAILURE_TAXONOMY if failure in seen]
