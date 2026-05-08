"""Pure validator for rendered runtime authority grant declarations."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "runtime_authority_grant_object_validator_manifest",
    "validate_runtime_authority_grant_object",
]


_SURFACE = "runtime_authority_grant_object_validator"
_CONTRACT_NAME = "RuntimeAuthorityGrantObjectV1"
_VERSION = 1

_REASON_READY = "ready"
_REASON_NOT_READY = "not_ready"
_REASON_INVALID = "invalid_runtime_authority_grant_payload"

_INPUT_KEY = "runtime_authority_grant_object"
_INPUT_KEYS = (_INPUT_KEY,)

_GRANT_OBJECT_KEYS = (
    "surface",
    "version",
    "source_refs",
    "authority_grant_id",
    "authority_ref",
    "authority_subject",
    "authority_issuer",
    "operation_binding",
    "target_surface_binding",
    "action_class_binding",
    "human_approval_binding",
    "operator_confirmation_binding",
    "execution_authorization_binding",
    "method_authority_binding",
    "service_call_boundary_binding",
    "runtime_authority_stack_binding",
    "evidence_audit_ref_binding",
    "idempotency_key_binding",
    "transaction_placement_binding",
    "expiry",
    "revocation",
    "revocation_status",
    "fail_closed_policy",
    "incident_policy",
    "required_false_authority_flags",
    "required_true_declarations",
    "json_safe",
)

_AUTHORITY_REF_KEYS = (
    "authority_ref_id",
    "authority_grant_id",
    "source_ref",
    "operation_ref",
    "target_surface",
    "permitted_action_class",
    "forbidden_action_class",
    "issuer_ref",
    "subject_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "execution_authorization_ref",
    "method_authority_ref",
    "service_call_boundary_ref",
    "runtime_authority_stack_ref",
    "evidence_ref",
    "audit_ref",
    "idempotency_key_ref",
    "transaction_placement_ref",
    "expiry_ref",
    "revocation_ref",
    "revocation_status_ref",
)

_OBJECT_MODEL_FIELDS = (
    "authority_subject",
    "authority_issuer",
    "expiry",
    "revocation",
    "revocation_status",
    "fail_closed_policy",
    "incident_policy",
)

_BINDING_MODEL_FIELDS = (
    "operation_binding",
    "target_surface_binding",
    "action_class_binding",
    "human_approval_binding",
    "operator_confirmation_binding",
    "execution_authorization_binding",
    "method_authority_binding",
    "service_call_boundary_binding",
    "runtime_authority_stack_binding",
    "evidence_audit_ref_binding",
    "idempotency_key_binding",
    "transaction_placement_binding",
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
    "runtime-authority-checker-enforcer-boundary-spec-only-v1": (
        "9bd776b4178ce627e28eb430ea07d6b7a2a002ce"
    ),
    "runtime-authority-checker-enforcer-boundary-validator-v1": (
        "b2627216e5efb803ebe673dc38b3167db7a8e3db"
    ),
    "runtime-authority-checker-enforcer-boundary-validator-ci-v1": (
        "a749545998e94aceee52775d363f9b8bb43e26a4"
    ),
    "runtime-authority-grant-object-spec-only-v1": (
        "3910680b973a7bfb9fa89b2ab52a213d402fbdae"
    ),
}

_BINDING_DECLARATIONS = (
    "authority_grant_object_required_for_future_runtime",
    "authority_ref_required_for_future_runtime",
    "authority_source_bound_required",
    "authority_operation_bound_required",
    "authority_target_surface_required",
    "authority_permitted_action_class_required",
    "authority_forbidden_action_class_required",
    "authority_issuer_required",
    "authority_subject_required",
    "human_approval_ref_required",
    "operator_confirmation_ref_required",
    "execution_authorization_ref_required",
    "method_authority_ref_required",
    "service_call_boundary_ref_required",
    "runtime_authority_stack_ref_required",
    "evidence_audit_refs_required",
    "idempotency_key_ref_required",
    "transaction_placement_ref_required",
    "authority_expiry_required",
    "authority_revocation_required",
    "authority_revocation_status_required",
    "authority_revocation_checked_required",
    "authority_expiry_checked_required",
    "authority_fail_closed_required",
)

_NON_AUTHORITY_DECLARATIONS = (
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "approval_is_not_authority",
    "execution_authorization_is_not_execution",
    "method_authority_is_not_runtime_authority",
    "service_call_boundary_is_not_runtime_authority",
    "checker_enforcer_readiness_is_not_runtime_authority",
    "tag_existence_is_not_authority",
    "validator_success_is_not_authority",
    "ci_success_is_not_authority",
    "preflight_success_is_not_authority",
    "restore_dry_run_success_is_not_authority",
    "repository_allowlist_success_is_not_authority",
    "write_path_readiness_is_not_authority",
    "executor_precondition_success_is_not_authority",
)

_FORBIDDEN_IMPLICIT_AUTHORITY_DECLARATIONS = (
    "approval_is_not_authority",
    "execution_authorization_is_not_execution",
    "method_authority_is_not_runtime_authority",
    "service_call_boundary_is_not_runtime_authority",
    "checker_enforcer_readiness_is_not_runtime_authority",
    "tag_existence_is_not_authority",
    "validator_success_is_not_authority",
    "ci_success_is_not_authority",
    "preflight_success_is_not_authority",
    "restore_dry_run_success_is_not_authority",
    "repository_allowlist_success_is_not_authority",
    "write_path_readiness_is_not_authority",
    "executor_precondition_success_is_not_authority",
    "silent_authority_success_forbidden",
    "implicit_authority_escalation_forbidden",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
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
    "runtime_authority_grant_forbidden",
    "runtime_authority_ref_runtime_forbidden",
    "runtime_authority_checker_forbidden",
    "runtime_authority_enforcer_forbidden",
    "runtime_authority_runtime_forbidden",
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "approval_is_not_authority",
    "execution_authorization_is_not_execution",
    "method_authority_is_not_runtime_authority",
    "service_call_boundary_is_not_runtime_authority",
    "checker_enforcer_readiness_is_not_runtime_authority",
    "tag_existence_is_not_authority",
    "validator_success_is_not_authority",
    "ci_success_is_not_authority",
    "preflight_success_is_not_authority",
    "restore_dry_run_success_is_not_authority",
    "repository_allowlist_success_is_not_authority",
    "write_path_readiness_is_not_authority",
    "executor_precondition_success_is_not_authority",
    "authority_grant_object_required_for_future_runtime",
    "authority_ref_required_for_future_runtime",
    "authority_source_bound_required",
    "authority_operation_bound_required",
    "authority_target_surface_required",
    "authority_permitted_action_class_required",
    "authority_forbidden_action_class_required",
    "authority_issuer_required",
    "authority_subject_required",
    "human_approval_ref_required",
    "operator_confirmation_ref_required",
    "execution_authorization_ref_required",
    "method_authority_ref_required",
    "service_call_boundary_ref_required",
    "runtime_authority_stack_ref_required",
    "evidence_audit_refs_required",
    "idempotency_key_ref_required",
    "transaction_placement_ref_required",
    "authority_expiry_required",
    "authority_revocation_required",
    "authority_revocation_status_required",
    "authority_revocation_checked_required",
    "authority_expiry_checked_required",
    "authority_fail_closed_required",
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

_AUTHORITY_SUMMARY_FLAGS = (
    "runtime_authority_grant_runtime_authorized",
    "runtime_authority_ref_runtime_authorized",
    "runtime_authority_checker_authorized",
    "runtime_authority_enforcer_authorized",
    "runtime_authority_runtime_authorized",
    "service_call_execution_authorized",
    "service_adapter_runtime_authorized",
    "service_method_call_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "repository_uow_writes_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "executor_service_dispatch_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "grant_object_not_mapping",
    "grant_object_shape_mismatch",
    "surface_invalid",
    "version_invalid",
    "source_refs_invalid",
    "authority_ref_invalid",
    "object_model_invalid",
    "binding_model_invalid",
    "non_authority_model_invalid",
    "forbidden_implicit_authority_invalid",
    "required_false_authority_flags_invalid",
    "required_true_declarations_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_REASON_CODES = (_REASON_READY, _REASON_NOT_READY, _REASON_INVALID)
_INVALID_PAYLOAD_FAILURES = (
    "payload_not_mapping",
    "payload_shape_mismatch",
)

_NON_AUTHORITY_SUMMARY = {
    "runtime_authority_grant_object_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "runtime_authority_grant_object_ready_authorizes_runtime": False,
    "runtime_authority_grant_object_ready_authorizes_grant_usage": False,
    "runtime_authority_grant_object_ready_authorizes_authority_ref_runtime": (
        False
    ),
    "runtime_authority_grant_object_ready_authorizes_checker_runtime": False,
    "runtime_authority_grant_object_ready_authorizes_enforcer_runtime": False,
    "runtime_authority_grant_object_ready_authorizes_service_calls": False,
    "runtime_authority_grant_object_ready_authorizes_evidence_append": False,
    "runtime_authority_grant_object_ready_authorizes_audit_append": False,
    "runtime_authority_grant_object_ready_authorizes_repository_uow_writes": (
        False
    ),
    "runtime_authority_grant_object_ready_authorizes_transaction_runtime": (
        False
    ),
    "runtime_authority_grant_object_ready_authorizes_idempotency": False,
    "runtime_authority_grant_object_ready_authorizes_rollback": False,
    "runtime_authority_grant_object_ready_authorizes_executor_dispatch": False,
    "runtime_authority_grant_object_ready_authorizes_durable_writes": False,
    "runtime_authority_grant_object_ready_authorizes_irreversible_actions": (
        False
    ),
}

_IMPORT_BOUNDARY = (
    "from collections.abc import Mapping",
    "from copy import deepcopy",
)

_FORBIDDEN_IMPORTS = (
    "datetime",
    "time",
    "os",
    "pathlib",
    "sqlite3",
    "subprocess",
    "threading",
    "asyncio",
    "hashlib",
    "hmac",
    "secrets",
    "inspect",
    "importlib",
    "services",
    "repositories",
    "UoW",
    "recovery",
    "CLI",
    "validators/checkers/CI modules",
)

_FORBIDDEN_SURFACES = (
    "runtime_authority_grant_runtime",
    "authority_ref_runtime",
    "checker_runtime",
    "enforcer_runtime",
    "runtime_authority",
    "service_calls",
    "service_adapter_runtime",
    "db_repository_uow",
    "evidence_append",
    "audit_append",
    "transaction_runtime",
    "idempotency_reservation",
    "rollback_runtime",
    "executor_dispatch",
    "restore",
    "cli_schema_daemon",
    "durable_writes",
    "irreversible_actions",
)

_MAX_DEPTH = 8
_MAX_MAPPING_ITEMS = 128
_MAX_LIST_ITEMS = 64
_MAX_STRING_LENGTH = 4096

_AUTHORITY_SUMMARY = {
    flag: False for flag in _AUTHORITY_SUMMARY_FLAGS
}

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "contract_name": _CONTRACT_NAME,
    "expected_top_level_keys": list(_INPUT_KEYS),
    "expected_grant_object_keys": list(_GRANT_OBJECT_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_authority_ref_fields": list(_AUTHORITY_REF_KEYS),
    "expected_object_model_fields": list(_OBJECT_MODEL_FIELDS),
    "expected_binding_model_fields": list(_BINDING_MODEL_FIELDS),
    "required_binding_declarations": list(_BINDING_DECLARATIONS),
    "required_non_authority_declarations": list(
        _NON_AUTHORITY_DECLARATIONS
    ),
    "forbidden_implicit_authority_declarations": list(
        _FORBIDDEN_IMPLICIT_AUTHORITY_DECLARATIONS
    ),
    "required_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "required_true_declarations": list(_REQUIRED_TRUE_DECLARATIONS),
    "failure_taxonomy": list(_FAILURE_ORDER),
    "allowed_reason_codes": list(_REASON_CODES),
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY),
    "non_authority_summary": deepcopy(_NON_AUTHORITY_SUMMARY),
    "public_api": list(__all__),
    "import_boundary": list(_IMPORT_BOUNDARY),
    "forbidden_imports": list(_FORBIDDEN_IMPORTS),
    "forbidden_surfaces": list(_FORBIDDEN_SURFACES),
    "json_safe": True,
}


def runtime_authority_grant_object_validator_manifest():
    """Return bounded metadata for the read-only grant object validator."""

    return deepcopy(_MANIFEST)


def validate_runtime_authority_grant_object(payload):
    """Validate an already-rendered grant object declaration only."""

    failures = []

    if not isinstance(payload, Mapping):
        _append(failures, "payload_not_mapping")
        return _result(failures)

    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")
        return _result(failures)

    grant_object = payload.get(_INPUT_KEY)
    if not isinstance(grant_object, Mapping):
        _append(failures, "grant_object_not_mapping")
        return _result(failures)

    if set(grant_object.keys()) != set(_GRANT_OBJECT_KEYS):
        _append(failures, "grant_object_shape_mismatch")

    _validate_grant_object(grant_object, failures)
    return _result(failures)


def _validate_grant_object(grant_object, failures):
    if grant_object.get("surface") != _CONTRACT_NAME:
        _append(failures, "surface_invalid")

    version = grant_object.get("version")
    if type(version) is not int or version != _VERSION:
        _append(failures, "version_invalid")

    _validate_source_refs(grant_object.get("source_refs"), failures)
    _validate_authority_ref(grant_object.get("authority_ref"), failures)
    _validate_grant_identifier(grant_object.get("authority_grant_id"), failures)
    _validate_mapping_fields(
        grant_object,
        _OBJECT_MODEL_FIELDS,
        "object_model_invalid",
        failures,
    )
    _validate_mapping_fields(
        grant_object,
        _BINDING_MODEL_FIELDS,
        "binding_model_invalid",
        failures,
    )

    declarations = grant_object.get("required_true_declarations")
    _validate_true_subset(
        declarations,
        _BINDING_DECLARATIONS,
        "binding_model_invalid",
        failures,
    )
    _validate_true_subset(
        declarations,
        _NON_AUTHORITY_DECLARATIONS,
        "non_authority_model_invalid",
        failures,
    )
    _validate_true_subset(
        declarations,
        _FORBIDDEN_IMPLICIT_AUTHORITY_DECLARATIONS,
        "forbidden_implicit_authority_invalid",
        failures,
    )

    _validate_false_authority_flags(
        grant_object.get("required_false_authority_flags"),
        failures,
    )
    _validate_true_declarations(declarations, failures)

    if grant_object.get("json_safe") is not True:
        _append(failures, "json_safe_invalid")
    elif not _is_json_safe(grant_object, 0):
        _append(failures, "json_safe_invalid")


def _validate_source_refs(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "source_refs_invalid")
        return
    if set(candidate.keys()) != set(_SOURCE_REFS.keys()):
        _append(failures, "source_refs_invalid")
        return
    for name, expected in _SOURCE_REFS.items():
        value = candidate.get(name)
        if type(value) is not str or value != expected:
            _append(failures, "source_refs_invalid")
            return


def _validate_authority_ref(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "authority_ref_invalid")
        return
    if set(candidate.keys()) != set(_AUTHORITY_REF_KEYS):
        _append(failures, "authority_ref_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append(failures, "authority_ref_invalid")


def _validate_grant_identifier(candidate, failures):
    if type(candidate) is not str or not candidate:
        _append(failures, "object_model_invalid")
        return
    if len(candidate) > _MAX_STRING_LENGTH:
        _append(failures, "object_model_invalid")


def _validate_mapping_fields(grant_object, fields, failure, failures):
    for field in fields:
        candidate = grant_object.get(field)
        if not isinstance(candidate, Mapping):
            _append(failures, failure)
            return
        if not _is_json_safe(candidate, 0):
            _append(failures, failure)
            return


def _validate_true_subset(candidate, required, failure, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, failure)
        return
    for name in required:
        value = candidate.get(name)
        if type(value) is not bool or value is not True:
            _append(failures, failure)
            return


def _validate_false_authority_flags(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "required_false_authority_flags_invalid")
        return
    if set(candidate.keys()) != set(_REQUIRED_FALSE_AUTHORITY_FLAGS):
        _append(failures, "required_false_authority_flags_invalid")
        return

    true_found = False
    for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS:
        value = candidate.get(flag)
        if type(value) is not bool:
            _append(failures, "required_false_authority_flags_invalid")
        elif value is True:
            true_found = True
    if true_found:
        _append(failures, "authorization_flag_true")


def _validate_true_declarations(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "required_true_declarations_invalid")
        return
    if set(candidate.keys()) != set(_REQUIRED_TRUE_DECLARATIONS):
        _append(failures, "required_true_declarations_invalid")
        return

    for declaration in _REQUIRED_TRUE_DECLARATIONS:
        value = candidate.get(declaration)
        if type(value) is not bool or value is not True:
            _append(failures, "required_true_declarations_invalid")
            return


def _result(failures):
    ordered_failures = _ordered_failures(failures)
    ready = not ordered_failures
    if ready:
        reason_code = _REASON_READY
    elif _has_invalid_payload_failure(ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return {
        "runtime_authority_grant_object_ready": ready,
        "reason_code": reason_code,
        "failures": ordered_failures,
        "contract": _contract_output(),
        "authority_grant_object": _grant_object_output(),
        "authority": deepcopy(_AUTHORITY_SUMMARY),
        "json_safe": True,
    }


def _contract_output():
    return {
        "surface": _SURFACE,
        "version": _VERSION,
        "contract_name": _CONTRACT_NAME,
        "expected_top_level_keys": list(_INPUT_KEYS),
        "expected_source_refs": deepcopy(_SOURCE_REFS),
        "failure_taxonomy": list(_FAILURE_ORDER),
        "allowed_reason_codes": list(_REASON_CODES),
        "non_authority_summary": deepcopy(_NON_AUTHORITY_SUMMARY),
    }


def _grant_object_output():
    return {
        "surface": _CONTRACT_NAME,
        "version": _VERSION,
        "source_refs": deepcopy(_SOURCE_REFS),
        "object_fields": list(_GRANT_OBJECT_KEYS),
        "authority_ref_fields": list(_AUTHORITY_REF_KEYS),
        "object_model_fields": list(_OBJECT_MODEL_FIELDS),
        "binding_model_fields": list(_BINDING_MODEL_FIELDS),
        "required_false_authority_flags": {
            flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
        },
        "required_true_declarations": {
            declaration: True for declaration in _REQUIRED_TRUE_DECLARATIONS
        },
        "json_safe": True,
    }


def _is_json_safe(value, depth):
    if depth > _MAX_DEPTH:
        return False
    if value is None:
        return True
    if type(value) is bool:
        return True
    if type(value) is int:
        return True
    if type(value) is str:
        return len(value) <= _MAX_STRING_LENGTH
    if isinstance(value, list):
        if len(value) > _MAX_LIST_ITEMS:
            return False
        for item in value:
            if not _is_json_safe(item, depth + 1):
                return False
        return True
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAPPING_ITEMS:
            return False
        for key, item in value.items():
            if type(key) is not str or len(key) > _MAX_STRING_LENGTH:
                return False
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
    return [failure for failure in _FAILURE_ORDER if failure in failures]
