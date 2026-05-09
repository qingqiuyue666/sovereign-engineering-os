"""Read-only CI consumer for rendered runtime enforcer boundary output."""

from collections.abc import Mapping
from copy import deepcopy

__all__ = [
    "runtime_enforcer_implementation_boundary_validator_ci_manifest",
    "consume_runtime_enforcer_implementation_boundary_validator_ci",
]

_SURFACE = "runtime_enforcer_implementation_boundary_validator_ci"
_VERSION = 1
_CONTRACT_NAME = "RuntimeEnforcerImplementationBoundaryV1"
_VALIDATOR_CHECKPOINT_TAG = (
    "runtime-enforcer-implementation-boundary-validator-v1"
)
_VALIDATOR_CHECKPOINT_COMMIT = (
    "84db914b906b6fb863407c0cc75350b6246f339a"
)

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_CI_PAYLOAD = "invalid_ci_payload"
_INVALID_VALIDATOR_PAYLOAD = (
    "invalid_runtime_enforcer_implementation_boundary_payload"
)

_PAYLOAD_KEYS = (
    "runtime_enforcer_implementation_boundary_ready",
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
    "runtime_enforcer_implementation_boundary_model",
    "checker_enforcer_separation_model",
    "forbidden_implicit_authority_sources",
    "false_authority_flags",
    "true_declarations",
    "json_safety",
    "future_validator_requirements",
    "future_ci_requirements",
    "json_safe",
)

_SOURCE_REFS = {
    "runtime-enforcer-implementation-boundary-spec-only-v1": (
        "82509ffa3cfee9999e5eff2052f93bf72bde60a1"
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

_RUNTIME_ENFORCER_IMPLEMENTATION_BOUNDARY_MODEL = (
    "runtime_enforcer_implementation_boundary",
    "runtime_enforcer_runtime_boundary",
    "runtime_enforcer_decision_boundary",
    "runtime_enforcer_action_boundary",
    "checker_to_enforcer_non_authority_boundary",
    "enforcer_to_service_admission_non_authority_boundary",
    "enforcer_to_service_call_non_authority_boundary",
    "enforcer_to_db_write_non_authority_boundary",
    "enforcer_to_append_non_authority_boundary",
    "enforcer_to_executor_non_authority_boundary",
)

_CHECKER_ENFORCER_SEPARATION_MODEL = (
    "checker_is_not_enforcer",
    "checker_output_is_not_enforcer_authority",
    "checker_readiness_is_not_enforcer_authority",
    "enforcer_is_not_checker",
    "enforcer_output_is_not_checker_evidence",
    "enforcer_output_is_not_service_call_admission",
    "enforcer_output_is_not_execution",
    "enforcer_output_is_not_transaction_authority",
    "enforcer_output_is_not_durable_write_authorization",
)

_FORBIDDEN_IMPLICIT_AUTHORITY_SOURCES = (
    "tag_existence",
    "read_only_stack_readiness",
    "validator_ready",
    "ci_ok",
    "checker_ready",
    "checker_output",
    "enforcer_ready",
    "enforcer_output",
    "service_call_admission_ready",
    "execution_authorization_ready",
    "preflight_ready",
    "approval_ready",
    "human_approval_present",
    "operator_confirmation_present",
    "method_authority_present",
    "service_adapter_boundary_present",
    "repository_allowlist_present",
    "write_path_present",
    "executor_precondition_present",
    "restore_dry_run_ready",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "runtime_enforcer_implementation_authorized",
    "runtime_enforcer_runtime_authorized",
    "runtime_enforcer_decision_authorized",
    "runtime_enforcer_action_authorized",
    "runtime_checker_implementation_authorized",
    "runtime_checker_runtime_authorized",
    "runtime_checker_decision_authorized",
    "runtime_checker_enforcer_combined_authorized",
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
    "runtime_enforcer_implementation_forbidden",
    "runtime_enforcer_boundary_is_not_runtime",
    "runtime_enforcer_is_not_checker",
    "enforcer_readiness_is_not_authority",
    "enforcer_output_is_not_execution",
    "enforcer_output_is_not_service_admission",
    "enforcer_output_is_not_service_call",
    "enforcer_output_is_not_db_write",
    "enforcer_output_is_not_append",
    "enforcer_output_is_not_executor_dispatch",
    "checker_output_is_not_enforcer_authority",
    "runtime_authority_grant_usage_boundary_required",
    "authority_ref_runtime_usage_boundary_required",
    "service_call_admission_runtime_boundary_required",
    "admission_decision_runtime_boundary_required",
    "transaction_idempotency_boundary_required",
    "evidence_audit_bookkeeping_boundary_required",
    "executor_dispatch_boundary_required",
    "durable_write_final_authorization_boundary_required",
    "missing_enforcer_boundary_fail_closed",
    "malformed_enforcer_boundary_fail_closed",
    "mismatched_enforcer_boundary_fail_closed",
    "silent_enforcer_success_forbidden",
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
    "db_handles",
    "service_objects",
    "exception_objects",
    "callable_objects",
    "subprocess_handles",
    "mutable_runtime_state",
    "raw_uow_session_connection_objects",
    "implicit_object_identity",
    "filesystem_handles",
    "network_handles",
    "raw_repr_leakage",
)

_FUTURE_VALIDATOR_REQUIREMENTS = (
    "remain_read_only",
    "consume_already_rendered_runtime_enforcer_implementation_boundary_only",
    "validate_exact_source_refs",
    "validate_runtime_enforcer_implementation_boundary_model",
    "validate_checker_enforcer_separation_model",
    "validate_forbidden_implicit_authority_sources",
    "validate_required_false_authority_flags",
    "validate_required_true_declarations",
    "validate_json_safety",
    "return_bounded_json_safe_output",
    "output_hard_false_authority_summary",
    "authorize_no_runtime",
    "authorize_no_service_call",
    "import_only_mapping_and_deepcopy",
)

_FUTURE_CI_REQUIREMENTS = (
    "remain_read_only",
    "consume_already_rendered_validator_output_only",
    "does_not_import_or_call_validator",
    "validate_exact_validator_checkpoint_binding",
    "validate_readiness_reason_failure_consistency",
    "validate_frozen_validator_failure_taxonomy",
    "reject_unknown_validator_failures",
    "validate_boundary_summary",
    "validate_authority_summary_hard_false",
    "validate_non_authority_summary",
    "return_bounded_json_safe_output",
    "authorize_no_runtime",
    "authorize_no_service_call",
    "import_only_mapping_and_deepcopy",
)

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "enforcer_boundary_model_invalid",
    "checker_enforcer_separation_invalid",
    "forbidden_implicit_authority_invalid",
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

_VALIDATOR_AUTHORITY_DENIALS = (
    "runtime",
    "runtime_eligibility",
    "checker_runtime",
    "checker_implementation",
    "checker_decision",
    "enforcer_runtime",
    "enforcer_implementation",
    "enforcer_decision",
    "enforcer_action",
    "runtime_authority_grant_usage",
    "authority_ref_runtime_usage",
    "service_call_admission_runtime",
    "admission_decision_runtime",
    "service_calls",
    "db_repository_uow_writes",
    "evidence_audit_append",
    "transaction_idempotency_rollback",
    "executor_dispatch",
    "restore_execution",
    "durable_writes",
    "irreversible_actions",
)

_AUTHORITY_SUMMARY = {
    flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
}

_VALIDATOR_NON_AUTHORITY_SUMMARY = {
    "runtime_enforcer_implementation_boundary_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "runtime_enforcer_implementation_boundary_ready_authorizes": {
        denial: False for denial in _VALIDATOR_AUTHORITY_DENIALS
    },
    "readiness_is_runtime_authority": False,
    "validator_ready_is_runtime_authority": False,
    "validator_ready_is_enforcer_authority": False,
    "checker_output_is_enforcer_authority": False,
    "enforcer_output_is_service_admission": False,
    "enforcer_output_is_execution_permission": False,
    "enforcer_output_is_service_call_permission": False,
    "enforcer_output_is_db_write_permission": False,
    "enforcer_output_is_append_permission": False,
    "enforcer_output_is_executor_dispatch_permission": False,
    "enforcer_output_is_durable_write_authorization": False,
}

_CI_DENIALS = (
    "runtime",
    "runtime_eligibility",
    "checker_runtime",
    "checker_implementation",
    "checker_decision",
    "enforcer_runtime",
    "enforcer_implementation",
    "enforcer_decision",
    "enforcer_action",
    "runtime_authority_grant_usage",
    "authority_ref_runtime_usage",
    "service_call_admission_runtime",
    "admission_decision_runtime",
    "service_calls",
    "db_repository_uow_writes",
    "evidence_audit_append",
    "transaction_idempotency_rollback",
    "executor_dispatch",
    "restore_execution",
    "durable_writes",
    "irreversible_actions",
)

_CI_NON_AUTHORITY_SUMMARY = {
    "ci_ok_proves": (
        "already_rendered_runtime_enforcer_implementation_boundary_"
        "validator_output_structurally_valid_for_read_only_consolidation_only"
    ),
    "ci_ok_authorizes": {denial: False for denial in _CI_DENIALS},
    "ci_success_is_runtime_authority": False,
    "ci_success_is_checker_runtime_authority": False,
    "ci_success_is_checker_implementation_authority": False,
    "ci_success_is_checker_decision_authority": False,
    "ci_success_is_enforcer_runtime_authority": False,
    "ci_success_is_enforcer_implementation_authority": False,
    "ci_success_is_enforcer_decision_authority": False,
    "ci_success_is_enforcer_action_authority": False,
    "ci_success_is_service_call_authority": False,
    "ci_success_is_db_write_authority": False,
    "ci_success_is_append_authority": False,
    "ci_success_is_transaction_idempotency_rollback_authority": False,
    "ci_success_is_executor_authority": False,
    "ci_success_is_durable_write_authority": False,
    "ci_success_is_irreversible_action_authority": False,
}

_EXPECTED_VALIDATOR_CHECKPOINT = {
    "tag": _VALIDATOR_CHECKPOINT_TAG,
    "commit": _VALIDATOR_CHECKPOINT_COMMIT,
}

_EXPECTED_BOUNDARY = {
    "surface": _CONTRACT_NAME,
    "version": _VERSION,
    "source_refs": deepcopy(_SOURCE_REFS),
    "runtime_enforcer_implementation_boundary_model": {
        item: True
        for item in _RUNTIME_ENFORCER_IMPLEMENTATION_BOUNDARY_MODEL
    },
    "checker_enforcer_separation_model": {
        item: True for item in _CHECKER_ENFORCER_SEPARATION_MODEL
    },
    "forbidden_implicit_authority_sources": {
        item: True for item in _FORBIDDEN_IMPLICIT_AUTHORITY_SOURCES
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

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "contract_name": _CONTRACT_NAME,
    "validator_checkpoint_tag": _VALIDATOR_CHECKPOINT_TAG,
    "validator_checkpoint_commit": _VALIDATOR_CHECKPOINT_COMMIT,
    "expected_validator_checkpoint": deepcopy(
        _EXPECTED_VALIDATOR_CHECKPOINT
    ),
    "expected_input_keys": list(_PAYLOAD_KEYS),
    "expected_output_keys": list(_OUTPUT_KEYS),
    "expected_boundary_keys": list(_BOUNDARY_KEYS),
    "expected_boundary": deepcopy(_EXPECTED_BOUNDARY),
    "validator_failure_taxonomy": list(_VALIDATOR_FAILURE_TAXONOMY),
    "ci_failure_taxonomy": list(_CI_FAILURE_TAXONOMY),
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY),
    "expected_validator_non_authority_summary": deepcopy(
        _VALIDATOR_NON_AUTHORITY_SUMMARY
    ),
    "non_authority_summary": deepcopy(_CI_NON_AUTHORITY_SUMMARY),
    "public_api": list(__all__),
    "import_boundary": [
        "from collections.abc import Mapping",
        "from copy import deepcopy",
    ],
    "json_safe": True,
}

_MAX_DEPTH = 10
_MAX_MAPPING_ITEMS = 512
_MAX_SEQUENCE_ITEMS = 512
_MAX_STRING_LENGTH = 4096


def runtime_enforcer_implementation_boundary_validator_ci_manifest():
    """Return bounded metadata for the read-only CI consumer."""

    return deepcopy(_MANIFEST)


def consume_runtime_enforcer_implementation_boundary_validator_ci(payload):
    """Consume an already-rendered validator output without calling it."""

    ci_failures = []
    validator_failures = []
    ready = False

    if not isinstance(payload, Mapping):
        _append_failure(ci_failures, "ci_payload_not_mapping")
        return _result(False, ci_failures, validator_failures)

    if not _has_exact_keys(payload, _PAYLOAD_KEYS):
        _append_failure(ci_failures, "ci_payload_shape_mismatch")

    if (
        payload.get("validator_checkpoint_tag") != _VALIDATOR_CHECKPOINT_TAG
        or payload.get("validator_checkpoint_commit")
        != _VALIDATOR_CHECKPOINT_COMMIT
    ):
        _append_failure(ci_failures, "validator_checkpoint_invalid")

    readiness = payload.get("runtime_enforcer_implementation_boundary_ready")
    if type(readiness) is not bool:
        _append_failure(ci_failures, "readiness_invalid")
    else:
        ready = readiness

    _validate_reason_and_failures(
        payload.get("reason_code"),
        payload.get("failures"),
        ready,
        ci_failures,
        validator_failures,
    )
    _validate_boundary(payload.get("boundary"), ci_failures)
    _validate_authority(payload.get("authority"), ci_failures)
    _validate_non_authority(payload.get("non_authority"), ci_failures)
    _validate_json_safety(payload, ci_failures)

    return _result(ready, ci_failures, validator_failures)


def _validate_reason_and_failures(
    reason_code,
    failures,
    ready,
    ci_failures,
    validator_failures,
):
    if ready:
        if reason_code != _READY:
            _append_failure(ci_failures, "reason_code_invalid")
    elif reason_code not in (_NOT_READY, _INVALID_VALIDATOR_PAYLOAD):
        _append_failure(ci_failures, "reason_code_invalid")

    valid_failure_list = _validate_failure_list(failures, ci_failures)
    if not valid_failure_list:
        return

    for failure in failures:
        if failure not in _VALIDATOR_FAILURE_TAXONOMY:
            _append_failure(ci_failures, "unknown_validator_failure")
        else:
            _append_failure(validator_failures, failure)

    if ready and failures:
        _append_failure(ci_failures, "readiness_invalid")
    if not ready and not failures:
        _append_failure(ci_failures, "readiness_invalid")


def _validate_failure_list(failures, ci_failures):
    if type(failures) is not list:
        _append_failure(ci_failures, "failure_list_invalid")
        return False
    if len(failures) > _MAX_SEQUENCE_ITEMS:
        _append_failure(ci_failures, "failure_list_invalid")
        return False
    for failure in failures:
        if type(failure) is not str or len(failure) > _MAX_STRING_LENGTH:
            _append_failure(ci_failures, "failure_list_invalid")
            return False
    return True


def _validate_boundary(boundary, ci_failures):
    if not _matches_exact_json(boundary, _EXPECTED_BOUNDARY):
        _append_failure(ci_failures, "boundary_summary_invalid")


def _validate_authority(authority, ci_failures):
    if not _matches_exact_json(authority, _AUTHORITY_SUMMARY):
        _append_failure(ci_failures, "authority_summary_invalid")


def _validate_non_authority(non_authority, ci_failures):
    if not _matches_exact_json(
        non_authority,
        _VALIDATOR_NON_AUTHORITY_SUMMARY,
    ):
        _append_failure(ci_failures, "non_authority_summary_invalid")


def _validate_json_safety(payload, ci_failures):
    if payload.get("json_safe") is not True:
        _append_failure(ci_failures, "json_safe_invalid")
        return
    if not _is_json_safe(payload, 0):
        _append_failure(ci_failures, "json_safe_invalid")


def _result(ready, ci_failures, validator_failures):
    ordered_ci_failures = _ordered_failures(ci_failures, _CI_FAILURE_TAXONOMY)
    if ordered_ci_failures:
        ci_ok = False
        reason_code = _INVALID_CI_PAYLOAD
        failures = ordered_ci_failures
    else:
        ci_ok = ready
        reason_code = _READY if ready else _NOT_READY
        failures = _ordered_failures(
            validator_failures,
            _VALIDATOR_FAILURE_TAXONOMY,
        )

    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": failures,
        "validator_checkpoint": deepcopy(_EXPECTED_VALIDATOR_CHECKPOINT),
        "boundary": deepcopy(_EXPECTED_BOUNDARY),
        "authority": deepcopy(_AUTHORITY_SUMMARY),
        "non_authority": deepcopy(_CI_NON_AUTHORITY_SUMMARY),
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


def _matches_exact_json(candidate, expected):
    if type(expected) is bool:
        return type(candidate) is bool and candidate is expected
    if type(expected) is int:
        return type(candidate) is int and candidate == expected
    if type(expected) is str:
        return type(candidate) is str and candidate == expected
    if expected is None:
        return candidate is None
    if type(expected) is list:
        if type(candidate) is not list or len(candidate) != len(expected):
            return False
        for index, expected_item in enumerate(expected):
            if not _matches_exact_json(candidate[index], expected_item):
                return False
        return True
    if isinstance(expected, Mapping):
        if not isinstance(candidate, Mapping):
            return False
        if not _has_exact_keys(candidate, expected.keys()):
            return False
        for key, expected_item in expected.items():
            if not _matches_exact_json(candidate.get(key), expected_item):
                return False
        return True
    return False


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
    return [failure for failure in taxonomy if failure in seen]
