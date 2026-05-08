"""Read-only CI consumer for rendered service call admission gate validation."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_call_admission_gate_validator_ci_manifest",
    "consume_service_call_admission_gate_validator_ci",
]


_SURFACE = "service_call_admission_gate_validator_ci"
_VERSION = 1
_CONTRACT_NAME = "ServiceCallAdmissionGateV1"
_VALIDATOR_PACKAGE = "service-call-admission-gate-validator-v1"
_VALIDATOR_CHECKPOINT_TAG = "service-call-admission-gate-validator-v1"
_VALIDATOR_CHECKPOINT_COMMIT = (
    "5499023b62617266cdcabc10996895cdbdd226f6"
)

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_CI_PAYLOAD = "invalid_ci_payload"
_INVALID_SERVICE_CALL_ADMISSION_PAYLOAD = (
    "invalid_service_call_admission_payload"
)

_PAYLOAD_KEYS = (
    "service_call_admission_gate_ready",
    "reason_code",
    "failures",
    "gate",
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
    "gate",
    "authority",
    "non_authority",
    "json_safe",
)

_GATE_KEYS = (
    "surface",
    "version",
    "source_refs",
    "admission_input",
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
    "runtime-authority-checker-enforcer-read-only-stack-v1": (
        "a749545998e94aceee52775d363f9b8bb43e26a4"
    ),
    "runtime-authority-grant-object-read-only-stack-v1": (
        "4acbddba3e0897d16bcfc74007ecd094817faa11"
    ),
    "service-call-admission-gate-spec-only-v1": (
        "47a86884718bdf215d2f1a7c706bf69de41ee7a9"
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
    "runtime-authority-grant-object-validator-v1": (
        "ed31e3c92a7bd3d35e411dd4e559038023a2f8d9"
    ),
    "runtime-authority-grant-object-validator-ci-v1": (
        "4acbddba3e0897d16bcfc74007ecd094817faa11"
    ),
}

_BINDING_GROUPS = {
    "service_identity_binding": (
        "service_identity",
        "service_class_name",
        "service_method_name",
        "operation_ref",
        "target_surface",
        "permitted_action_class",
        "forbidden_action_class",
    ),
    "authority_input_binding": (
        "runtime_authority_grant_object_ref",
        "authority_ref",
        "service_method_authority_ref",
        "service_call_execution_boundary_ref",
        "execution_authorization_ref",
        "human_approval_ref",
        "operator_confirmation_ref",
    ),
    "read_only_stack_binding": (
        "runtime_authority_checker_enforcer_stack_ref",
        "service_adapter_boundary_ref",
        "evidence_audit_append_boundary_ref",
        "repository_uow_allowlist_ref",
        "write_path_boundary_ref",
        "executor_precondition_ref",
    ),
    "evidence_idempotency_transaction_binding": (
        "idempotency_key_ref",
        "transaction_placement_ref",
        "evidence_pre_bookkeeping_ref",
        "audit_pre_bookkeeping_ref",
        "evidence_post_bookkeeping_ref",
        "audit_post_bookkeeping_ref",
    ),
    "expiry_revocation_binding": (
        "expiry_ref",
        "revocation_ref",
        "revocation_status_ref",
    ),
    "denial_incident_policy": (
        "admission_denial_policy",
        "incident_classification_policy",
    ),
}

_FORBIDDEN_IMPLICIT_AUTHORITY_SOURCES = (
    "tag existence",
    "readiness",
    "validator success",
    "CI success",
    "approval",
    "execution authorization",
    "method authority",
    "service call boundary",
    "runtime authority grant object readiness",
    "runtime authority checker/enforcer readiness",
    "evidence/audit ref existence",
    "idempotency key existence",
    "transaction placement declaration",
    "service adapter boundary declaration",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "service_call_admission_runtime_authorized",
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
    "service_call_admission_forbidden",
    "service_call_admission_runtime_forbidden",
    "service_call_admission_is_not_execution",
    "admission_decision_is_not_service_call",
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "approval_is_not_authority",
    "execution_authorization_is_not_execution",
    "method_authority_is_not_runtime_authority",
    "service_call_boundary_is_not_runtime_authority",
    "runtime_authority_stack_readiness_is_not_runtime_authority",
    "runtime_authority_grant_object_readiness_is_not_runtime_authority",
    "tag_existence_is_not_authority",
    "runtime_authority_grant_object_required",
    "authority_ref_required",
    "authority_ref_source_bound_required",
    "authority_ref_operation_bound_required",
    "authority_ref_target_bound_required",
    "authority_ref_revocation_checked_required",
    "authority_ref_expiry_checked_required",
    "service_method_authority_required",
    "service_call_execution_boundary_required",
    "execution_authorization_required",
    "human_approval_required",
    "operator_confirmation_required",
    "runtime_authority_checker_enforcer_stack_required",
    "service_adapter_boundary_required",
    "evidence_audit_append_boundary_required",
    "repository_uow_allowlist_required",
    "write_path_boundary_required",
    "executor_precondition_required",
    "exact_service_identity_required",
    "exact_service_class_name_required",
    "exact_service_method_name_required",
    "operation_bound_required",
    "target_surface_bound_required",
    "permitted_action_class_required",
    "forbidden_action_class_required",
    "idempotency_key_ref_required",
    "transaction_placement_ref_required",
    "evidence_pre_bookkeeping_ref_required",
    "audit_pre_bookkeeping_ref_required",
    "evidence_post_bookkeeping_ref_required",
    "audit_post_bookkeeping_ref_required",
    "denial_fail_closed_required",
    "missing_grant_fail_closed",
    "missing_authority_ref_fail_closed",
    "malformed_authority_ref_fail_closed",
    "mismatched_authority_ref_fail_closed",
    "expired_authority_fail_closed",
    "revoked_authority_fail_closed",
    "ambiguous_authority_incident_class",
    "admission_mismatch_incident_class",
    "silent_admission_success_forbidden",
    "implicit_admission_escalation_forbidden",
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

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "gate_not_mapping",
    "gate_shape_mismatch",
    "gate_surface_invalid",
    "gate_version_invalid",
    "source_ref_mismatch",
    "admission_input_invalid",
    "binding_group_invalid",
    "required_binding_invalid",
    "required_binding_false",
    "forbidden_implicit_authority_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "required_declaration_invalid",
    "required_declaration_false",
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
    "gate_summary_invalid",
    "authority_summary_invalid",
    "non_authority_summary_invalid",
    "json_safe_invalid",
)

_VALIDATOR_REASON_CODES = (
    _READY,
    _NOT_READY,
    _INVALID_SERVICE_CALL_ADMISSION_PAYLOAD,
)
_CI_REASON_CODES = (_READY, _NOT_READY, _INVALID_CI_PAYLOAD)

_AUTHORITY_SUMMARY = {
    flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
}

_VALIDATOR_NON_AUTHORITY_SUMMARY = {
    "service_call_admission_gate_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "service_call_admission_gate_ready_authorizes_service_call_admission_runtime": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_admission_decision_runtime": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_runtime_authority_grant_usage": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_authority_ref_runtime_usage": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_checker_enforcer_runtime": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_service_calls": False,
    "service_call_admission_gate_ready_authorizes_evidence_audit_append": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_db_repository_uow_writes": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_transaction_runtime": False,
    "service_call_admission_gate_ready_authorizes_idempotency_reservation": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_rollback_runtime": False,
    "service_call_admission_gate_ready_authorizes_executor_dispatch": False,
    "service_call_admission_gate_ready_authorizes_durable_writes": False,
    "service_call_admission_gate_ready_authorizes_irreversible_actions": False,
}

_CI_NON_AUTHORITY_SUMMARY = {
    "structural_declaration_validity_only": True,
    "no_service_call_admission_runtime_authorization": True,
    "no_admission_decision_runtime_authorization": True,
    "no_runtime_authority_grant_usage_authorization": True,
    "no_authority_ref_runtime_usage_authorization": True,
    "no_checker_enforcer_runtime_authorization": True,
    "no_service_call_authorization": True,
    "no_evidence_audit_append_authorization": True,
    "no_db_repository_uow_write_authorization": True,
    "no_transaction_runtime_authorization": True,
    "no_idempotency_reservation_runtime_authorization": True,
    "no_rollback_runtime_authorization": True,
    "no_executor_dispatch_authorization": True,
    "no_durable_write_authorization": True,
    "no_irreversible_action_authorization": True,
}

_ADMISSION_INPUT_SUMMARY = {
    group_name: list(fields) for group_name, fields in _BINDING_GROUPS.items()
}
_ADMISSION_INPUT_SUMMARY["forbidden_implicit_authority_sources"] = list(
    _FORBIDDEN_IMPLICIT_AUTHORITY_SOURCES
)

_EXPECTED_GATE = {
    "surface": _CONTRACT_NAME,
    "version": _VERSION,
    "source_refs": deepcopy(_SOURCE_REFS),
    "admission_input": deepcopy(_ADMISSION_INPUT_SUMMARY),
    "required_false_authority_flags": deepcopy(_AUTHORITY_SUMMARY),
    "required_true_declarations": {
        declaration: True for declaration in _REQUIRED_TRUE_DECLARATIONS
    },
    "json_safe": True,
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
    "upstream validators/checkers/CI",
)

_FORBIDDEN_SURFACES = (
    "validator import/call",
    "service-call admission runtime",
    "admission decision runtime",
    "runtime authority grant runtime",
    "authority ref runtime",
    "checker runtime",
    "enforcer runtime",
    "runtime authority",
    "runtime allowlist",
    "service-call execution",
    "service adapter runtime/implementation",
    "service method calls",
    "service side effects",
    "evidence/approval/review/revision-seal/audit service calls",
    "evidence append",
    "audit append",
    "repository/UoW writes",
    "DB writes",
    "raw sqlite",
    "ad hoc SQL",
    "transaction runtime",
    "idempotency reservation",
    "rollback runtime",
    "executor implementation/dispatch",
    "restore execution",
    "CLI/schema/migration/daemon",
    "filesystem side effects",
    "external network",
    "durable writes",
    "irreversible actions",
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
    "expected_gate_keys": list(_GATE_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_gate_summary": deepcopy(_EXPECTED_GATE),
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


def service_call_admission_gate_validator_ci_manifest():
    """Return bounded metadata for the read-only validator CI consumer."""

    return deepcopy(_MANIFEST)


def consume_service_call_admission_gate_validator_ci(payload):
    """Consume already-rendered validator output without invoking runtime."""

    if not isinstance(payload, Mapping):
        return _result(False, _INVALID_CI_PAYLOAD, ("ci_payload_not_mapping",))

    failures = []
    if not _has_exact_keys(payload, _PAYLOAD_KEYS):
        _append_failure(failures, "ci_payload_shape_mismatch")

    _validate_checkpoint(payload, failures)
    validator_failures = _validate_readiness_reason_failures(payload, failures)
    _validate_gate_summary(payload.get("gate"), failures)
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

    if payload.get("service_call_admission_gate_ready") is True:
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
    ready = payload.get("service_call_admission_gate_ready")
    reason = payload.get("reason_code")
    source_failures = payload.get("failures")
    validator_failures = ()

    ready_valid = type(ready) is bool
    if not ready_valid and "service_call_admission_gate_ready" in payload:
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
            if reason not in (
                _NOT_READY,
                _INVALID_SERVICE_CALL_ADMISSION_PAYLOAD,
            ):
                _append_failure(failures, "reason_code_invalid")
            if source_failures == []:
                _append_failure(failures, "readiness_invalid")

    return validator_failures


def _validate_gate_summary(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append_failure(failures, "gate_summary_invalid")
        return
    if not _is_json_safe(candidate, 0):
        _append_failure(failures, "gate_summary_invalid")
        _append_failure(failures, "json_safe_invalid")
        return
    if not _matches_exact_json(candidate, _EXPECTED_GATE):
        _append_failure(failures, "gate_summary_invalid")


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
        "gate": deepcopy(_EXPECTED_GATE),
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


def _matches_exact_json(candidate, expected):
    if type(expected) is bool:
        return type(candidate) is bool and candidate is expected
    if type(expected) is int:
        return type(candidate) is int and candidate == expected
    if type(expected) is str:
        return type(candidate) is str and candidate == expected
    if expected is None:
        return candidate is None
    if isinstance(expected, list):
        if not isinstance(candidate, list):
            return False
        if len(candidate) != len(expected):
            return False
        for index, expected_item in enumerate(expected):
            if not _matches_exact_json(candidate[index], expected_item):
                return False
        return True
    if isinstance(expected, Mapping):
        if not isinstance(candidate, Mapping):
            return False
        if _string_key_set(candidate) != set(expected.keys()):
            return False
        for key, expected_item in expected.items():
            if not _matches_exact_json(candidate.get(key), expected_item):
                return False
        return True
    return False


def _append_failure(failures, failure):
    if failure not in failures:
        failures[:] = failures + [failure]


def _ordered_failures(failures, taxonomy):
    present = tuple(dict.fromkeys(failures))
    return tuple(failure for failure in taxonomy if failure in present)
