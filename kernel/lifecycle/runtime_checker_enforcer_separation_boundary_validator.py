"""Read-only validator for RuntimeCheckerEnforcerSeparationBoundaryV1."""

from collections.abc import Mapping
from copy import deepcopy

__all__ = (
    "runtime_checker_enforcer_separation_boundary_validator_manifest",
    "validate_runtime_checker_enforcer_separation_boundary",
)

_SURFACE = "runtime_checker_enforcer_separation_boundary_validator"
_CONTRACT_NAME = "RuntimeCheckerEnforcerSeparationBoundaryV1"
_VERSION = 1

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_PAYLOAD = (
    "invalid_runtime_checker_enforcer_separation_boundary_payload"
)

_INPUT_KEY = "runtime_checker_enforcer_separation_boundary"
_INPUT_KEYS = (_INPUT_KEY,)

_BOUNDARY_KEYS = (
    "surface",
    "version",
    "source_refs",
    "checker_enforcer_separation_boundary_model",
    "false_authority_flags",
    "true_declarations",
    "json_safety",
    "future_validator_requirements",
    "future_ci_requirements",
    "json_safe",
)

_SOURCE_REFS = {
    "runtime-checker-enforcer-separation-boundary-spec-only-v1": (
        "e0ea518869d1b3381dfe6e084820504014eb372f"
    ),
    "runtime-enforcer-implementation-boundary-read-only-stack-v1": (
        "80261bbf320300c09fe1da63b78126ad8a6e811d"
    ),
    "runtime-enforcer-implementation-boundary-spec-only-v1": (
        "82509ffa3cfee9999e5eff2052f93bf72bde60a1"
    ),
    "runtime-enforcer-implementation-boundary-validator-v1": (
        "84db914b906b6fb863407c0cc75350b6246f339a"
    ),
    "runtime-enforcer-implementation-boundary-validator-ci-v1": (
        "80261bbf320300c09fe1da63b78126ad8a6e811d"
    ),
    "runtime-checker-implementation-boundary-read-only-stack-v1": (
        "2a7523b86e47a8cb63e9e3c624f6d79275802928"
    ),
    "runtime-checker-implementation-boundary-spec-only-v1": (
        "44c9fa733b1eaa8c2d9c000a769ebe0fe67a1882"
    ),
    "runtime-checker-implementation-boundary-validator-v1": (
        "7a5aa16f55fbb61980baf560dfcb0267b5462dcb"
    ),
    "runtime-checker-implementation-boundary-validator-ci-v1": (
        "2a7523b86e47a8cb63e9e3c624f6d79275802928"
    ),
    "runtime-implementation-boundary-read-only-stack-v1": (
        "c7cdf9b991ad7480cfb38d1cf4e600cd711e40c9"
    ),
    "runtime-implementation-boundary-spec-only-v1": (
        "aa8d394571a613a47c5b7256912a8b297db88785"
    ),
    "runtime-implementation-boundary-validator-v1": (
        "c79b5dd1e59909b9cc6d8719ff89c7e401b118bd"
    ),
    "runtime-implementation-boundary-validator-ci-v1": (
        "c7cdf9b991ad7480cfb38d1cf4e600cd711e40c9"
    ),
    "runtime-final-eligibility-gate-read-only-stack-v1": (
        "395346a96ca6ecf229a40127fe13cff1172079ac"
    ),
    "service-call-admission-gate-read-only-stack-v1": (
        "c581c027bfcf29a220b9f0de75bb6c7b2e8f97b0"
    ),
    "runtime-authority-grant-object-read-only-stack-v1": (
        "4acbddba3e0897d16bcfc74007ecd094817faa11"
    ),
    "runtime-authority-checker-enforcer-read-only-stack-v1": (
        "a749545998e94aceee52775d363f9b8bb43e26a4"
    ),
    "service-call-execution-boundary-read-only-stack-v1": (
        "2a82b78665541d2e408113646ea11fbda4b62037"
    ),
    "service-method-authority-read-only-stack-v1": (
        "db2f628cc79df0dc7b4f1306cbe24d880693188b"
    ),
    "service-adapter-boundary-read-only-stack-v1": (
        "8698ea42c78cbe79231698be8839b9d2c246cfdf"
    ),
    "append-runtime-authority-service-boundary-read-only-stack-v1": (
        "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039"
    ),
    "evidence-audit-append-read-only-stack-v1": (
        "62db8a586efa9375d2c77cf7c6335ccf5ef11279"
    ),
    "repository-uow-allowlist-read-only-stack-v1": (
        "bec2d04eab1922594dcbfbe35971f4efe0fe4849"
    ),
    "write-path-read-only-stack-v1": (
        "8ffd4679aca8f593415089748df35df42af8f015"
    ),
    "executor-precondition-read-only-stack-v1": (
        "cb3948eb843866dcc961b6a074038c13db64d017"
    ),
    "execution-authorization-read-only-stack-v1": (
        "d586aeb60620010c900df7be1a88621ab2cb8dc1"
    ),
    "preflight-read-only-stack-v1": (
        "662b6161253c35204b437e88809c5bab21908c6d"
    ),
    "restore-dry-run-read-only-stack-v1": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
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
}

_CHECKER_ENFORCER_SEPARATION_BOUNDARY_MODEL = (
    "checker_output_boundary",
    "checker_readiness_boundary",
    "checker_to_enforcer_non_authority_boundary",
    "checker_to_enforcer_handoff_future_boundary",
    "enforcer_readiness_boundary",
    "enforcer_output_boundary",
    "enforcer_to_execution_non_authority_boundary",
    "enforcer_to_service_admission_non_authority_boundary",
    "enforcer_to_service_call_non_authority_boundary",
    "enforcer_to_db_write_non_authority_boundary",
    "enforcer_to_append_non_authority_boundary",
    "enforcer_to_executor_non_authority_boundary",
    "enforcer_to_durable_write_non_authority_boundary",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "runtime_checker_enforcer_separation_authorized",
    "runtime_checker_to_enforcer_handoff_authorized",
    "runtime_checker_output_as_enforcer_authority_authorized",
    "runtime_enforcer_output_as_execution_authorized",
    "runtime_enforcer_output_as_service_admission_authorized",
    "runtime_enforcer_output_as_service_call_authorized",
    "runtime_enforcer_output_as_db_write_authorized",
    "runtime_enforcer_output_as_append_authorized",
    "runtime_enforcer_output_as_executor_dispatch_authorized",
    "runtime_enforcer_output_as_durable_write_authorized",
    "runtime_checker_runtime_authorized",
    "runtime_checker_implementation_authorized",
    "runtime_checker_decision_authorized",
    "runtime_enforcer_runtime_authorized",
    "runtime_enforcer_implementation_authorized",
    "runtime_enforcer_decision_authorized",
    "runtime_enforcer_action_authorized",
    "runtime_authority_grant_usage_authorized",
    "authority_ref_runtime_usage_authorized",
    "service_call_admission_runtime_authorized",
    "admission_decision_runtime_authorized",
    "service_call_runtime_binding_authorized",
    "service_call_execution_authorized",
    "service_adapter_runtime_authorized",
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
    "executor_service_dispatch_authorized",
    "restore_execution_authorized",
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
    "checker_enforcer_separation_required",
    "checker_output_is_not_enforcer_authority",
    "checker_readiness_is_not_enforcer_authority",
    "checker_output_is_not_service_admission",
    "checker_output_is_not_service_call",
    "checker_output_is_not_db_write",
    "checker_output_is_not_append",
    "checker_output_is_not_executor_dispatch",
    "enforcer_readiness_is_not_execution_authority",
    "enforcer_output_is_not_execution",
    "enforcer_output_is_not_service_admission",
    "enforcer_output_is_not_service_call",
    "enforcer_output_is_not_db_write",
    "enforcer_output_is_not_append",
    "enforcer_output_is_not_executor_dispatch",
    "enforcer_output_is_not_durable_write_authorization",
    "runtime_authority_grant_usage_boundary_required",
    "authority_ref_runtime_usage_boundary_required",
    "service_call_admission_runtime_boundary_required",
    "admission_decision_runtime_boundary_required",
    "transaction_idempotency_boundary_required",
    "evidence_audit_bookkeeping_boundary_required",
    "executor_dispatch_boundary_required",
    "durable_write_final_authorization_boundary_required",
    "missing_checker_enforcer_separation_fail_closed",
    "malformed_checker_enforcer_separation_fail_closed",
    "mismatched_checker_enforcer_separation_fail_closed",
    "silent_checker_enforcer_success_forbidden",
    "implicit_runtime_escalation_forbidden",
    "implicit_authority_escalation_forbidden",
    "service_calls_forbidden",
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
    "runtime_object_handles",
    "checker_runtime_objects",
    "enforcer_runtime_objects",
    "db_handles",
    "service_objects",
    "repository_uow_session_connection_objects",
    "exception_objects",
    "callable_objects",
    "subprocess_handles",
    "mutable_runtime_state",
    "implicit_object_identity",
    "filesystem_handles",
    "network_handles",
    "raw_repr_leakage",
)

_FUTURE_VALIDATOR_REQUIREMENTS = (
    "consumes_already_rendered_declaration_only",
    "validates_exact_source_refs",
    "validates_boundary_model",
    "validates_false_authority_flags",
    "validates_true_declarations",
    "validates_json_safety",
    "emits_bounded_json_safe_output",
    "emits_hard_false_authority_summary",
    "imports_only_mapping_deepcopy",
    "calls_no_services",
    "opens_no_db",
    "imports_no_repository_uow",
    "appends_no_evidence_audit",
    "implements_no_runtime",
    "authorizes_no_runtime",
    "checker_output_not_enough_for_enforcer_action",
    "checker_to_enforcer_handoff_remains_future_boundary",
    "future_execution_context_binding_boundary_required",
    "context_drift_must_fail_closed",
    "final_pre_dispatch_context_validation_future_boundary",
    "payload_environment_filesystem_state_binding_not_implemented_here",
    "bool_tag_readiness_ci_ok_checker_output_enforcer_output_not_authority",
    "stale_dead_intent_authority_must_fail_closed",
    "ghost_authority_forbidden",
    "runtime_authority_grant_usage_boundary_required",
    "authority_ref_runtime_usage_boundary_required",
    "single_use_capability_consumption_remains_future_boundary",
    "forensic_binding_boundary_required",
    "evidence_audit_bookkeeping_boundary_required",
    "transaction_idempotency_boundary_required",
    "executor_dispatch_boundary_required",
    "durable_write_final_authorization_boundary_required",
    "physical_enforcement_not_implemented",
)

_FUTURE_CI_REQUIREMENTS = (
    "consumes_already_rendered_validator_output_only",
    "must_not_import_or_call_validator",
    "validates_validator_checkpoint_binding",
    "validates_readiness_reason_failure_consistency",
    "validates_failure_taxonomy",
    "validates_boundary_summary",
    "validates_authority_summary",
    "validates_non_authority_summary",
    "validates_json_safety",
    "emits_bounded_json_safe_output",
    "emits_hard_false_authority_summary",
    "imports_only_mapping_deepcopy",
    "calls_no_services",
    "opens_no_db",
    "imports_no_repository_uow",
    "appends_no_evidence_audit",
    "implements_no_runtime",
    "authorizes_no_runtime",
)

_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "checker_enforcer_separation_boundary_model_invalid",
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
)

_AUTHORITY_DENIALS = (
    "runtime",
    "checker_runtime",
    "checker_implementation",
    "checker_decision",
    "enforcer_runtime",
    "enforcer_implementation",
    "enforcer_decision",
    "enforcer_action",
    "checker_to_enforcer_handoff",
    "runtime_authority_grant_usage",
    "authority_ref_runtime_usage",
    "service_call_admission",
    "admission_decision",
    "service_calls",
    "service_adapter_runtime",
    "evidence_approval_review_revision_audit_services",
    "evidence_audit_append",
    "db_repository_uow_writes",
    "transaction_idempotency_rollback",
    "executor_dispatch",
    "restore",
    "cli_schema_daemon",
    "durable_writes",
    "irreversible_actions",
    "toctou_physical_enforcement",
    "capability_token_work",
    "forensic_audit_binding",
)

_AUTHORITY_SUMMARY = {
    flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
}

_NON_AUTHORITY_SUMMARY = {
    "runtime_checker_enforcer_separation_boundary_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "runtime_checker_enforcer_separation_boundary_ready_authorizes": {
        denial: False for denial in _AUTHORITY_DENIALS
    },
    "readiness_is_runtime_authority": False,
    "validator_success_is_authority": False,
    "tag_existence_is_authority": False,
    "checker_readiness_is_enforcer_authority": False,
    "checker_output_is_enforcer_authority": False,
    "checker_output_is_service_admission": False,
    "checker_to_enforcer_handoff_is_authorized": False,
    "enforcer_readiness_is_execution_authority": False,
    "enforcer_output_is_execution": False,
    "enforcer_output_is_service_admission": False,
    "enforcer_output_is_service_call_permission": False,
    "enforcer_output_is_db_write_permission": False,
    "enforcer_output_is_append_permission": False,
    "enforcer_output_is_executor_dispatch_permission": False,
    "enforcer_output_is_durable_write_authorization": False,
    "toctou_physical_enforcement_is_implemented": False,
    "capability_token_work_is_implemented": False,
    "forensic_audit_binding_is_implemented": False,
}

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "contract_name": _CONTRACT_NAME,
    "package": "runtime-checker-enforcer-separation-boundary-validator-v1",
    "expected_top_level_keys": list(_INPUT_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_checker_enforcer_separation_boundary_model": list(
        _CHECKER_ENFORCER_SEPARATION_BOUNDARY_MODEL
    ),
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


def runtime_checker_enforcer_separation_boundary_validator_manifest():
    """Return bounded metadata for the read-only structural validator."""

    return deepcopy(_MANIFEST)


def validate_runtime_checker_enforcer_separation_boundary(payload):
    """Validate an already-rendered separation boundary declaration."""

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
        boundary.get("checker_enforcer_separation_boundary_model"),
        _CHECKER_ENFORCER_SEPARATION_BOUNDARY_MODEL,
        "checker_enforcer_separation_boundary_model_invalid",
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
        failures,
    )
    _validate_true_mapping(
        boundary.get("future_validator_requirements"),
        _FUTURE_VALIDATOR_REQUIREMENTS,
        "future_validator_requirement_invalid",
        failures,
    )
    _validate_true_mapping(
        boundary.get("future_ci_requirements"),
        _FUTURE_CI_REQUIREMENTS,
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


def _validate_true_mapping(candidate, expected_keys, invalid_failure, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, invalid_failure)
        return
    if not _has_exact_keys(candidate, expected_keys):
        _append(failures, invalid_failure)

    for key in expected_keys:
        value = candidate.get(key)
        if type(value) is not bool or value is not True:
            _append(failures, invalid_failure)


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
        "runtime_checker_enforcer_separation_boundary_ready": ready,
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
        "checker_enforcer_separation_boundary_model": {
            item: True
            for item in _CHECKER_ENFORCER_SEPARATION_BOUNDARY_MODEL
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
