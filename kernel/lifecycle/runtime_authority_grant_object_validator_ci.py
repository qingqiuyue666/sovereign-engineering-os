"""Read-only CI consumer for rendered runtime authority grant validation."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "runtime_authority_grant_object_validator_ci_manifest",
    "consume_runtime_authority_grant_object_validator_ci",
]


_SURFACE = "runtime_authority_grant_object_validator_ci"
_VERSION = 1
_CONTRACT_NAME = "RuntimeAuthorityGrantObjectV1"
_VALIDATOR_PACKAGE = "runtime-authority-grant-object-validator-v1"
_VALIDATOR_CHECKPOINT_TAG = "runtime-authority-grant-object-validator-v1"
_VALIDATOR_CHECKPOINT_COMMIT = (
    "ed31e3c92a7bd3d35e411dd4e559038023a2f8d9"
)
_VALIDATOR_SURFACE = "runtime_authority_grant_object_validator"
_VALIDATOR_VERSION = 1

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_CI_PAYLOAD = "invalid_ci_payload"
_INVALID_GRANT_PAYLOAD = "invalid_runtime_authority_grant_payload"

_PAYLOAD_KEYS = (
    "runtime_authority_grant_object_ready",
    "reason_code",
    "failures",
    "contract",
    "authority_grant_object",
    "authority",
    "json_safe",
    "validator_checkpoint_tag",
    "validator_checkpoint_commit",
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "validator_checkpoint",
    "contract",
    "authority_grant_object",
    "authority",
    "non_authority",
    "json_safe",
)

_VALIDATOR_INPUT_KEYS = ("runtime_authority_grant_object",)

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

_GRANT_OBJECT_FIELDS = (
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

_AUTHORITY_REF_FIELDS = (
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

_VALIDATOR_FAILURE_TAXONOMY = (
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

_CI_FAILURE_TAXONOMY = (
    "ci_payload_not_mapping",
    "ci_payload_shape_mismatch",
    "validator_checkpoint_invalid",
    "readiness_invalid",
    "reason_code_invalid",
    "failure_list_invalid",
    "unknown_validator_failure",
    "contract_summary_invalid",
    "authority_grant_object_summary_invalid",
    "authority_summary_invalid",
    "non_authority_summary_invalid",
    "json_safe_invalid",
)

_VALIDATOR_REASON_CODES = (_READY, _NOT_READY, _INVALID_GRANT_PAYLOAD)
_CI_REASON_CODES = (_READY, _NOT_READY, _INVALID_CI_PAYLOAD)

_VALIDATOR_NON_AUTHORITY_SUMMARY = {
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

_AUTHORITY_SUMMARY = {
    flag: False for flag in _AUTHORITY_SUMMARY_FLAGS
}

_EXPECTED_CONTRACT = {
    "surface": _VALIDATOR_SURFACE,
    "version": _VALIDATOR_VERSION,
    "contract_name": _CONTRACT_NAME,
    "expected_top_level_keys": list(_VALIDATOR_INPUT_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "failure_taxonomy": list(_VALIDATOR_FAILURE_TAXONOMY),
    "allowed_reason_codes": list(_VALIDATOR_REASON_CODES),
    "non_authority_summary": deepcopy(_VALIDATOR_NON_AUTHORITY_SUMMARY),
}

_EXPECTED_GRANT_OBJECT = {
    "surface": _CONTRACT_NAME,
    "version": _VERSION,
    "source_refs": deepcopy(_SOURCE_REFS),
    "object_fields": list(_GRANT_OBJECT_FIELDS),
    "authority_ref_fields": list(_AUTHORITY_REF_FIELDS),
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

_EXPECTED_VALIDATOR_CHECKPOINT = {
    "tag": _VALIDATOR_CHECKPOINT_TAG,
    "commit": _VALIDATOR_CHECKPOINT_COMMIT,
}

_NON_AUTHORITY_SUMMARY = {
    "ci_ok_proves": (
        "already_rendered_validator_output_structurally_suitable_for_"
        "read_only_consolidation_only"
    ),
    "runtime_authority_authorized": False,
    "runtime_authority_grant_usage_authorized": False,
    "authority_ref_runtime_authorized": False,
    "runtime_checker_authorized": False,
    "runtime_enforcer_authorized": False,
    "service_call_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "db_repository_uow_write_authorized": False,
    "transaction_runtime_authorized": False,
    "idempotency_reservation_authorized": False,
    "rollback_runtime_authorized": False,
    "executor_dispatch_authorized": False,
    "durable_write_authorized": False,
    "irreversible_action_authorized": False,
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
    "validator/checker/CI modules",
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
    "runtime_allowlist",
    "service_call_admission_gate",
    "executor_dispatch",
    "restore",
    "cli_schema_daemon",
    "durable_writes",
    "irreversible_actions",
    "git_shell_out",
)

_MAX_DEPTH = 8
_MAX_MAPPING_ITEMS = 128
_MAX_LIST_ITEMS = 128
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
    "expected_contract_summary": deepcopy(_EXPECTED_CONTRACT),
    "expected_authority_grant_object_summary": deepcopy(
        _EXPECTED_GRANT_OBJECT
    ),
    "validator_failure_taxonomy": list(_VALIDATOR_FAILURE_TAXONOMY),
    "ci_failure_taxonomy": list(_CI_FAILURE_TAXONOMY),
    "allowed_reason_codes": list(_CI_REASON_CODES),
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY),
    "non_authority_summary": deepcopy(_NON_AUTHORITY_SUMMARY),
    "public_api": list(__all__),
    "import_boundary": list(_IMPORT_BOUNDARY),
    "forbidden_imports": list(_FORBIDDEN_IMPORTS),
    "forbidden_surfaces": list(_FORBIDDEN_SURFACES),
    "json_safe": True,
}


def runtime_authority_grant_object_validator_ci_manifest():
    """Return bounded metadata for the read-only validator CI consumer."""

    return deepcopy(_MANIFEST)


def consume_runtime_authority_grant_object_validator_ci(payload):
    """Consume already-rendered validator output without invoking runtime."""

    if not isinstance(payload, Mapping):
        return _result(
            ci_ok=False,
            reason_code=_INVALID_CI_PAYLOAD,
            failures=("ci_payload_not_mapping",),
        )

    failures = []
    if not _has_exact_keys(payload, _PAYLOAD_KEYS):
        _append_failure(failures, "ci_payload_shape_mismatch")

    _validate_checkpoint(payload, failures)
    validator_failures = _validate_readiness_reason_failures(payload, failures)
    _validate_contract_summary(payload.get("contract"), failures)
    _validate_exact_summary(
        payload.get("authority_grant_object"),
        _EXPECTED_GRANT_OBJECT,
        "authority_grant_object_summary_invalid",
        failures,
    )
    _validate_authority_summary(payload.get("authority"), failures)

    if payload.get("json_safe") is not True:
        _append_failure(failures, "json_safe_invalid")

    ordered_failures = _ordered_failures(failures, _CI_FAILURE_TAXONOMY)
    if ordered_failures:
        return _result(False, _INVALID_CI_PAYLOAD, ordered_failures)

    if payload.get("runtime_authority_grant_object_ready") is True:
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
    ready = payload.get("runtime_authority_grant_object_ready")
    reason = payload.get("reason_code")
    source_failures = payload.get("failures")
    validator_failures = ()

    ready_valid = type(ready) is bool
    if not ready_valid and "runtime_authority_grant_object_ready" in payload:
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
        if len(validator_failures) != len(tuple(dict.fromkeys(source_failures))):
            _append_failure(failures, "unknown_validator_failure")

    if ready_valid and reason_valid and failure_list_valid:
        if ready is True:
            if reason != _READY:
                _append_failure(failures, "reason_code_invalid")
            if source_failures != []:
                _append_failure(failures, "readiness_invalid")
        else:
            if reason not in (_NOT_READY, _INVALID_GRANT_PAYLOAD):
                _append_failure(failures, "reason_code_invalid")
            if source_failures == []:
                _append_failure(failures, "readiness_invalid")

    return validator_failures


def _validate_contract_summary(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, "contract_summary_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, "contract_summary_invalid")
        _append_failure(failures, "json_safe_invalid")
        return

    expected_keys = set(_EXPECTED_CONTRACT.keys())
    candidate_keys = _string_key_set(candidate)
    if candidate_keys != expected_keys:
        _append_failure(failures, "contract_summary_invalid")
        return

    if candidate.get("non_authority_summary") != _VALIDATOR_NON_AUTHORITY_SUMMARY:
        _append_failure(failures, "non_authority_summary_invalid")

    comparable = dict(candidate)
    comparable["non_authority_summary"] = deepcopy(
        _VALIDATOR_NON_AUTHORITY_SUMMARY
    )
    if comparable != _EXPECTED_CONTRACT:
        _append_failure(failures, "contract_summary_invalid")


def _validate_exact_summary(candidate, expected, failure, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, failure)
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, failure)
        _append_failure(failures, "json_safe_invalid")
        return
    if candidate != expected:
        _append_failure(failures, failure)


def _validate_authority_summary(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, "authority_summary_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, "authority_summary_invalid")
        _append_failure(failures, "json_safe_invalid")
        return
    if candidate != _AUTHORITY_SUMMARY:
        _append_failure(failures, "authority_summary_invalid")
        return
    for flag in _AUTHORITY_SUMMARY_FLAGS:
        if candidate.get(flag) is not False:
            _append_failure(failures, "authority_summary_invalid")
            return


def _result(ci_ok, reason_code, failures):
    result = {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "validator_checkpoint": deepcopy(_EXPECTED_VALIDATOR_CHECKPOINT),
        "contract": deepcopy(_EXPECTED_CONTRACT),
        "authority_grant_object": deepcopy(_EXPECTED_GRANT_OBJECT),
        "authority": deepcopy(_AUTHORITY_SUMMARY),
        "non_authority": deepcopy(_NON_AUTHORITY_SUMMARY),
        "json_safe": True,
    }
    return {key: result[key] for key in _OUTPUT_KEYS}


def _has_exact_keys(candidate, expected):
    return _string_key_set(candidate) == set(expected)


def _string_key_set(candidate):
    if not isinstance(candidate, Mapping):
        return None
    keys = list(candidate.keys())
    for key in keys:
        if type(key) is not str:
            return None
    return set(keys)


def _is_string_list(value):
    return isinstance(value, list) and all(type(item) is str for item in value)


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


def _append_failure(failures, failure):
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures, taxonomy):
    present = tuple(dict.fromkeys(failures))
    return tuple(failure for failure in taxonomy if failure in present)
