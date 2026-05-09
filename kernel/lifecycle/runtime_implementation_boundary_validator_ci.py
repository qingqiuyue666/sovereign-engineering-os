"""Read-only CI consumer for rendered runtime implementation boundary output."""

from collections.abc import Mapping
from copy import deepcopy

__all__ = [
    "runtime_implementation_boundary_validator_ci_manifest",
    "consume_runtime_implementation_boundary_validator_ci",
]

_SURFACE = "runtime_implementation_boundary_validator_ci"
_VERSION = 1
_CONTRACT_NAME = "RuntimeImplementationBoundaryV1"
_VALIDATOR_PACKAGE = "runtime-implementation-boundary-validator-v1"
_VALIDATOR_CHECKPOINT_TAG = "runtime-implementation-boundary-validator-v1"
_VALIDATOR_CHECKPOINT_COMMIT = (
    "c79b5dd1e59909b9cc6d8719ff89c7e401b118bd"
)

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_CI_PAYLOAD = "invalid_ci_payload"
_INVALID_VALIDATOR_PAYLOAD = (
    "invalid_runtime_implementation_boundary_payload"
)

_PAYLOAD_KEYS = (
    "runtime_implementation_boundary_ready",
    "reason_code",
    "failures",
    "boundary",
    "authority",
    "non_authority",
    "json_safe",
    "validator_checkpoint_tag",
    "validator_checkpoint_commit",
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "validator_checkpoint",
    "boundary",
    "authority",
    "non_authority",
    "json_safe",
)

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

_VALIDATOR_FAILURE_TAXONOMY = (
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

_CI_FAILURE_TAXONOMY = (
    "ci_payload_not_mapping",
    "ci_payload_shape_mismatch",
    "validator_checkpoint_invalid",
    "readiness_invalid",
    "reason_code_invalid",
    "failure_list_invalid",
    "unknown_validator_failure",
    "boundary_summary_invalid",
    "authority_summary_invalid",
    "non_authority_summary_invalid",
    "json_safe_invalid",
)

_VALIDATOR_REASON_CODES = (
    _READY,
    _NOT_READY,
    _INVALID_VALIDATOR_PAYLOAD,
)
_CI_REASON_CODES = (_READY, _NOT_READY, _INVALID_CI_PAYLOAD)

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

_EXPECTED_BOUNDARY = {
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

_VALIDATOR_NON_AUTHORITY_SUMMARY = {
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

_CI_NON_AUTHORITY_SUMMARY = {
    "ci_ok_proves": (
        "already_rendered_runtime_implementation_boundary_validator_output_"
        "structurally_valid_for_read_only_consolidation_only"
    ),
    "ci_ok_authorizes": {denial: False for denial in _AUTHORITY_DENIALS},
    "readiness_is_runtime_authority": False,
    "authorization_is_execution": False,
    "tag_existence_is_authority": False,
    "validator_success_is_authority": False,
    "ci_success_is_runtime_authority": False,
}

_EXPECTED_VALIDATOR_CHECKPOINT = {
    "tag": _VALIDATOR_CHECKPOINT_TAG,
    "commit": _VALIDATOR_CHECKPOINT_COMMIT,
}

_IMPORT_BOUNDARY = (
    "from collections.abc import Mapping",
    "from copy import deepcopy",
)

_FORBIDDEN_IMPORTS = (
    "datetime",
    "time",
    "hashlib",
    "hmac",
    "secrets",
    "inspect",
    "importlib",
    "os",
    "pathlib",
    "sqlite3",
    "subprocess",
    "threading",
    "asyncio",
    "services",
    "repositories",
    "unit_of_work",
    "validator modules",
    "runtime checker/enforcer",
    "executor",
    "restore",
    "CLI/schema/daemon",
)

_FORBIDDEN_SURFACES = (
    "validator import/call",
    "runtime",
    "runtime implementation",
    "checker runtime",
    "enforcer runtime",
    "runtime authority grant usage",
    "authority ref runtime usage",
    "service-call admission runtime",
    "admission decision runtime",
    "service calls",
    "service adapter runtime",
    "evidence/approval/review/revision/audit service calls",
    "evidence append",
    "audit append",
    "repository/UoW writes",
    "DB writes",
    "transaction runtime",
    "idempotency reservation",
    "rollback runtime",
    "executor dispatch",
    "restore execution",
    "CLI/schema/migration/daemon",
    "filesystem side effects",
    "external network",
    "durable writes",
    "irreversible actions",
)

_MAX_DEPTH = 8
_MAX_MAPPING_ITEMS = 512
_MAX_SEQUENCE_ITEMS = 512
_MAX_STRING_LENGTH = 4096

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "validator_checkpoint_tag": _VALIDATOR_CHECKPOINT_TAG,
    "validator_checkpoint_commit": _VALIDATOR_CHECKPOINT_COMMIT,
    "expected_validator_checkpoint": deepcopy(_EXPECTED_VALIDATOR_CHECKPOINT),
    "expected_contract_name": _CONTRACT_NAME,
    "expected_validator_package": _VALIDATOR_PACKAGE,
    "expected_input_keys": list(_PAYLOAD_KEYS),
    "expected_output_keys": list(_OUTPUT_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_boundary": deepcopy(_EXPECTED_BOUNDARY),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "required_runtime_boundaries": list(_REQUIRED_RUNTIME_BOUNDARIES),
    "required_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "validator_failure_taxonomy": list(_VALIDATOR_FAILURE_TAXONOMY),
    "ci_failure_taxonomy": list(_CI_FAILURE_TAXONOMY),
    "allowed_validator_reason_codes": list(_VALIDATOR_REASON_CODES),
    "allowed_reason_codes": list(_CI_REASON_CODES),
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY),
    "expected_validator_non_authority_summary": deepcopy(
        _VALIDATOR_NON_AUTHORITY_SUMMARY
    ),
    "non_authority_summary": deepcopy(_CI_NON_AUTHORITY_SUMMARY),
    "public_api": list(__all__),
    "import_boundary": list(_IMPORT_BOUNDARY),
    "forbidden_imports": list(_FORBIDDEN_IMPORTS),
    "forbidden_surfaces": list(_FORBIDDEN_SURFACES),
    "json_safe": True,
}


def runtime_implementation_boundary_validator_ci_manifest():
    """Return bounded metadata for the read-only validator CI consumer."""

    return deepcopy(_MANIFEST)


def consume_runtime_implementation_boundary_validator_ci(payload):
    """Consume already-rendered validator output without invoking runtime."""

    if not isinstance(payload, Mapping):
        return _result(False, _INVALID_CI_PAYLOAD, ("ci_payload_not_mapping",))

    failures = []
    if not _has_exact_keys(payload, _PAYLOAD_KEYS):
        _append_failure(failures, "ci_payload_shape_mismatch")

    _validate_checkpoint(payload, failures)
    validator_failures = _validate_readiness_reason_failures(payload, failures)
    _validate_boundary_summary(payload.get("boundary"), failures)
    _validate_authority_summary(payload.get("authority"), failures)
    _validate_validator_non_authority_summary(
        payload.get("non_authority"),
        failures,
    )

    if payload.get("json_safe") is not True:
        _append_failure(failures, "json_safe_invalid")

    ordered_failures = _ordered_failures(failures, _CI_FAILURE_TAXONOMY)
    if ordered_failures:
        return _result(False, _INVALID_CI_PAYLOAD, ordered_failures)

    if payload.get("runtime_implementation_boundary_ready") is True:
        return _result(True, _READY, ())

    return _result(False, _NOT_READY, validator_failures)


def _validate_checkpoint(payload, failures):
    if (
        payload.get("validator_checkpoint_tag")
        != _VALIDATOR_CHECKPOINT_TAG
        or payload.get("validator_checkpoint_commit")
        != _VALIDATOR_CHECKPOINT_COMMIT
    ):
        _append_failure(failures, "validator_checkpoint_invalid")


def _validate_readiness_reason_failures(payload, failures):
    ready = payload.get("runtime_implementation_boundary_ready")
    reason = payload.get("reason_code")
    source_failures = payload.get("failures")
    validator_failures = ()

    ready_valid = type(ready) is bool
    if not ready_valid and "runtime_implementation_boundary_ready" in payload:
        _append_failure(failures, "readiness_invalid")

    reason_valid = type(reason) is str and reason in _VALIDATOR_REASON_CODES
    if not reason_valid and "reason_code" in payload:
        _append_failure(failures, "reason_code_invalid")

    failure_list_valid = _is_string_list(source_failures)
    if not failure_list_valid and "failures" in payload:
        _append_failure(failures, "failure_list_invalid")

    if failure_list_valid:
        validator_failures = _ordered_failures(
            source_failures,
            _VALIDATOR_FAILURE_TAXONOMY,
        )
        unique_source_failures = tuple(dict.fromkeys(source_failures))
        if len(validator_failures) != len(unique_source_failures):
            _append_failure(failures, "unknown_validator_failure")

    if ready_valid and reason_valid and failure_list_valid:
        if ready is True:
            if reason != _READY:
                _append_failure(failures, "reason_code_invalid")
            if source_failures != []:
                _append_failure(failures, "readiness_invalid")
        else:
            if reason not in (_NOT_READY, _INVALID_VALIDATOR_PAYLOAD):
                _append_failure(failures, "reason_code_invalid")
            if source_failures == []:
                _append_failure(failures, "readiness_invalid")

    return validator_failures


def _validate_boundary_summary(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, "boundary_summary_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, "boundary_summary_invalid")
        _append_failure(failures, "json_safe_invalid")
        return
    if not _matches_exact_json(candidate, _EXPECTED_BOUNDARY):
        _append_failure(failures, "boundary_summary_invalid")


def _validate_authority_summary(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, "authority_summary_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, "authority_summary_invalid")
        _append_failure(failures, "json_safe_invalid")
        return
    if not _matches_exact_json(candidate, _AUTHORITY_SUMMARY):
        _append_failure(failures, "authority_summary_invalid")


def _validate_validator_non_authority_summary(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, "non_authority_summary_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, "non_authority_summary_invalid")
        _append_failure(failures, "json_safe_invalid")
        return
    if not _matches_exact_json(candidate, _VALIDATOR_NON_AUTHORITY_SUMMARY):
        _append_failure(failures, "non_authority_summary_invalid")


def _result(ci_ok, reason_code, failures):
    result = {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "validator_checkpoint": deepcopy(_EXPECTED_VALIDATOR_CHECKPOINT),
        "boundary": deepcopy(_EXPECTED_BOUNDARY),
        "authority": deepcopy(_AUTHORITY_SUMMARY),
        "non_authority": deepcopy(_CI_NON_AUTHORITY_SUMMARY),
        "json_safe": True,
    }
    return {key: result[key] for key in _OUTPUT_KEYS}


def _has_exact_keys(candidate, expected):
    return _string_key_set(candidate) == set(expected)


def _string_key_set(candidate):
    if not isinstance(candidate, Mapping):
        return None
    keys = set()
    for key in candidate.keys():
        if type(key) is not str:
            return None
        keys.add(key)
    return keys


def _is_string_list(candidate):
    if type(candidate) is not list:
        return False
    for item in candidate:
        if type(item) is not str:
            return False
    return True


def _matches_exact_json(candidate, expected):
    if type(expected) is bool:
        return type(candidate) is bool and candidate is expected
    if type(expected) is int:
        return type(candidate) is int and candidate == expected
    if type(expected) is str:
        return type(candidate) is str and candidate == expected
    if type(expected) is list:
        if type(candidate) is not list or len(candidate) != len(expected):
            return False
        for index, item in enumerate(expected):
            if not _matches_exact_json(candidate[index], item):
                return False
        return True
    if isinstance(expected, Mapping):
        if not isinstance(candidate, Mapping):
            return False
        if not _has_exact_keys(candidate, expected.keys()):
            return False
        for key, item in expected.items():
            if not _matches_exact_json(candidate.get(key), item):
                return False
        return True
    return candidate is expected


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


def _append_failure(failures, failure):
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures, taxonomy):
    seen = set(failures)
    return tuple(failure for failure in taxonomy if failure in seen)
