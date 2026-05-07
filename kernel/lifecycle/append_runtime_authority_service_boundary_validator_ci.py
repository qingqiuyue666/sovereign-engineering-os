"""Read-only CI consumer for rendered append authority boundary validation."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "append_runtime_authority_service_boundary_validator_ci_manifest",
    "consume_append_runtime_authority_service_boundary_validator_ci",
]


_SURFACE = "append_runtime_authority_service_boundary_validator_ci"
_VERSION = 1
_INPUT_SHAPE = (
    "already_rendered_append_runtime_authority_service_boundary_validator_"
    "output_v1"
)

_VALIDATOR_SURFACE = "append_runtime_authority_service_boundary_validator"
_VALIDATOR_VERSION = 1
_VALIDATOR_TAG = "append-runtime-authority-service-boundary-validator-v1"
_VALIDATOR_COMMIT = "19af3abba5be4ae44ff2aa58a883ee2c99da6cb0"

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_VALIDATOR_REASON_INVALID = "invalid_authority_payload"
_VALIDATOR_REASON_CODES = (
    _VALIDATOR_REASON_INVALID,
    _REASON_NOT_READY,
    _REASON_READY,
)

_PAYLOAD_KEYS = (
    "runtime_authority_ready",
    "reason_code",
    "failures",
    "authority",
)

_READ_ONLY_GOVERNANCE_LAYER_TAG = "read-only-governance-layer-v1"
_READ_ONLY_GOVERNANCE_LAYER_COMMIT = (
    "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
)
_WRITE_SIDE_PRECONDITION_CHECKER_TAG = (
    "write-side-precondition-checker-v1"
)
_WRITE_SIDE_PRECONDITION_CHECKER_COMMIT = (
    "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
)
_WRITE_SIDE_PRECONDITION_CI_TAG = "write-side-precondition-ci-v1"
_WRITE_SIDE_PRECONDITION_CI_COMMIT = (
    "05c81541ad3d7deee20023843142f702937f6c3f"
)
_WRITE_SIDE_RECOVERY_SPEC_ONLY_TAG = "write-side-recovery-spec-only-v1"
_WRITE_SIDE_RECOVERY_SPEC_ONLY_COMMIT = (
    "ad560cc2dab135f2c1d56d948410ae47586d118e"
)
_RESTORE_DRY_RUN_READ_ONLY_STACK_TAG = "restore-dry-run-read-only-stack-v1"
_RESTORE_DRY_RUN_READ_ONLY_STACK_COMMIT = (
    "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
)
_PREFLIGHT_READ_ONLY_STACK_TAG = "preflight-read-only-stack-v1"
_PREFLIGHT_READ_ONLY_STACK_COMMIT = (
    "662b6161253c35204b437e88809c5bab21908c6d"
)
_EXECUTION_AUTHORIZATION_READ_ONLY_STACK_TAG = (
    "execution-authorization-read-only-stack-v1"
)
_EXECUTION_AUTHORIZATION_READ_ONLY_STACK_COMMIT = (
    "d586aeb60620010c900df7be1a88621ab2cb8dc1"
)
_EXECUTOR_PRECONDITION_READ_ONLY_STACK_TAG = (
    "executor-precondition-read-only-stack-v1"
)
_EXECUTOR_PRECONDITION_READ_ONLY_STACK_COMMIT = (
    "cb3948eb843866dcc961b6a074038c13db64d017"
)
_WRITE_PATH_READ_ONLY_STACK_TAG = "write-path-read-only-stack-v1"
_WRITE_PATH_READ_ONLY_STACK_COMMIT = (
    "8ffd4679aca8f593415089748df35df42af8f015"
)
_REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_TAG = (
    "repository-uow-allowlist-read-only-stack-v1"
)
_REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_COMMIT = (
    "bec2d04eab1922594dcbfbe35971f4efe0fe4849"
)
_EVIDENCE_AUDIT_APPEND_READ_ONLY_STACK_TAG = (
    "evidence-audit-append-read-only-stack-v1"
)
_EVIDENCE_AUDIT_APPEND_READ_ONLY_STACK_COMMIT = (
    "62db8a586efa9375d2c77cf7c6335ccf5ef11279"
)
_AUTHORITY_SPEC_ONLY_TAG = (
    "append-runtime-authority-service-boundary-spec-only-v1"
)
_AUTHORITY_SPEC_ONLY_COMMIT = (
    "5b48c6537702ee9d9dc52b39f28399166096754b"
)

_SOURCE_BINDINGS = (
    (
        "source_read_only_governance_layer_tag",
        _READ_ONLY_GOVERNANCE_LAYER_TAG,
    ),
    (
        "source_read_only_governance_layer_commit",
        _READ_ONLY_GOVERNANCE_LAYER_COMMIT,
    ),
    (
        "source_write_side_precondition_checker_tag",
        _WRITE_SIDE_PRECONDITION_CHECKER_TAG,
    ),
    (
        "source_write_side_precondition_checker_commit",
        _WRITE_SIDE_PRECONDITION_CHECKER_COMMIT,
    ),
    (
        "source_write_side_precondition_ci_tag",
        _WRITE_SIDE_PRECONDITION_CI_TAG,
    ),
    (
        "source_write_side_precondition_ci_commit",
        _WRITE_SIDE_PRECONDITION_CI_COMMIT,
    ),
    (
        "source_write_side_recovery_spec_only_tag",
        _WRITE_SIDE_RECOVERY_SPEC_ONLY_TAG,
    ),
    (
        "source_write_side_recovery_spec_only_commit",
        _WRITE_SIDE_RECOVERY_SPEC_ONLY_COMMIT,
    ),
    (
        "source_restore_dry_run_read_only_stack_tag",
        _RESTORE_DRY_RUN_READ_ONLY_STACK_TAG,
    ),
    (
        "source_restore_dry_run_read_only_stack_commit",
        _RESTORE_DRY_RUN_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_preflight_read_only_stack_tag",
        _PREFLIGHT_READ_ONLY_STACK_TAG,
    ),
    (
        "source_preflight_read_only_stack_commit",
        _PREFLIGHT_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_execution_authorization_read_only_stack_tag",
        _EXECUTION_AUTHORIZATION_READ_ONLY_STACK_TAG,
    ),
    (
        "source_execution_authorization_read_only_stack_commit",
        _EXECUTION_AUTHORIZATION_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_executor_precondition_read_only_stack_tag",
        _EXECUTOR_PRECONDITION_READ_ONLY_STACK_TAG,
    ),
    (
        "source_executor_precondition_read_only_stack_commit",
        _EXECUTOR_PRECONDITION_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_write_path_read_only_stack_tag",
        _WRITE_PATH_READ_ONLY_STACK_TAG,
    ),
    (
        "source_write_path_read_only_stack_commit",
        _WRITE_PATH_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_repository_uow_allowlist_read_only_stack_tag",
        _REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_TAG,
    ),
    (
        "source_repository_uow_allowlist_read_only_stack_commit",
        _REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_evidence_audit_append_read_only_stack_tag",
        _EVIDENCE_AUDIT_APPEND_READ_ONLY_STACK_TAG,
    ),
    (
        "source_evidence_audit_append_read_only_stack_commit",
        _EVIDENCE_AUDIT_APPEND_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_append_"
        "runtime_authority_service_boundary_spec_only_tag",
        _AUTHORITY_SPEC_ONLY_TAG,
    ),
    (
        "source_append_"
        "runtime_authority_service_boundary_spec_only_commit",
        _AUTHORITY_SPEC_ONLY_COMMIT,
    ),
)

_VALIDATOR_BINDINGS = (
    (
        "source_append_"
        "runtime_authority_service_boundary_validator_tag",
        _VALIDATOR_TAG,
    ),
    (
        "source_append_"
        "runtime_authority_service_boundary_validator_commit",
        _VALIDATOR_COMMIT,
    ),
)

_OPERATION_REFS = (
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "append_contract_ref",
    "append_idempotency_key",
    "human_approval_ref",
    "operator_confirmation_ref",
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "write_path_contract_validator_ci_ref",
    "repository_uow_allowlist_validator_ci_ref",
    "evidence_audit_append_contract_validator_ci_ref",
    "append_" "runtime_authority_contract_ref",
)

_EVIDENCE_REF_SET_FIELD = "evidence_ref_set"
_AUDIT_REF_SET_FIELD = "audit_ref_set"

_RUNTIME_AUTHORITY_DECLARATIONS = (
    "append_authority_explicit_only",
    "evidence_append_authority_explicit_only",
    "audit_append_authority_explicit_only",
    "service_authority_explicit_only",
    "db_authority_explicit_only",
    "repository_uow_authority_explicit_only",
    "transaction_authority_explicit_only",
    "idempotency_reservation_authority_explicit_only",
    "rollback_authority_explicit_only",
    "executor_authority_explicit_only",
    "read_only_success_grants_no_runtime_authority",
    "authority_source_bound_required",
    "authority_operation_bound_required",
    "authority_narrow_required",
    "authority_revocable_required",
    "authority_fail_closed_required",
)

_SERVICE_BOUNDARY_DECLARATIONS = (
    "evidence_service_append_forbidden",
    "approval_service_forbidden",
    "review_service_forbidden",
    "revision_seal_service_forbidden",
    "service_adapter_required_for_future_runtime",
    "service_method_allowlist_required",
    "service_result_contract_required",
    "service_transaction_ownership_forbidden_by_default",
    "evidence_audit_ref_fabrication_forbidden",
    "service_calls_forbidden_in_spec_only_package",
)

_DB_REPOSITORY_UOW_BOUNDARY_DECLARATIONS = (
    "direct_sqlite_forbidden",
    "ad_hoc_sql_forbidden",
    "repository_uow_import_forbidden",
    "repository_uow_call_forbidden",
    "kernel_owned_uow_required_for_future_runtime",
    "repository_method_allowlist_required",
    "repository_result_contract_required",
    "evidence_bearing_result_required",
    "executor_transaction_ownership_forbidden",
    "uncontrolled_nested_transaction_forbidden",
)

_IDEMPOTENCY_DECLARATIONS = (
    "idempotency_reservation_required_before_mutation_or_append",
    "append_idempotency_key_binding_required",
    "same_key_same_binding_safe_replay_only",
    "same_key_different_binding_fail_closed",
    "ambiguous_reservation_incident_class",
    "replay_classification_required",
    "idempotency_runtime_not_authorized",
)

_TRANSACTION_DECLARATIONS = (
    "one_outer_kernel_owned_transaction_required",
    "append_mutation_order_required",
    "commit_after_required_bookkeeping_only",
    "rollback_on_unexpected_exception_required",
    "rollback_failure_incident_class",
    "out_of_band_append_requires_explicit_declaration",
    "transaction_runtime_not_authorized",
)

_APPEND_PHASE_AUTHORITY_DECLARATIONS = (
    "before_evidence_append_authority_required",
    "mutation_intent_evidence_append_authority_required",
    "after_evidence_append_authority_required",
    "rejection_evidence_append_authority_required",
    "failure_evidence_append_authority_required",
    "rollback_evidence_append_authority_required",
    "audit_event_append_authority_required",
    "duplicate_replay_audit_append_authority_required",
    "ambiguous_replay_audit_append_authority_required",
    "incident_audit_append_authority_required",
    "per_phase_authorization_required",
)

_FAILURE_INCIDENT_DECLARATIONS = (
    "expected_rejection_is_not_execution_failure",
    "unexpected_exception_requires_rollback",
    "append_failure_before_mutation_blocks_mutation",
    "append_failure_after_mutation_is_incident_class",
    "rollback_failure_is_incident_class",
    "duplicate_mismatched_idempotency_is_incident_class",
    "ambiguous_append_or_replay_is_incident_class",
    "partial_success_forbidden",
    "success_requires_all_required_append_bookkeeping",
    "silent_success_forbidden",
)

_FUTURE_VALIDATOR_DECLARATIONS = (
    "future_validator_consumes_already_rendered_declaration_only",
    "future_validator_validates_source_bindings",
    "future_validator_validates_operation_bindings",
    "future_validator_validates_service_boundaries",
    "future_validator_validates_db_repository_uow_boundaries",
    "future_validator_validates_idempotency_declarations",
    "future_validator_validates_transaction_declarations",
    "future_validator_validates_rollback_failure_incident_declarations",
    "future_validator_validates_append_phase_authority_declarations",
    "future_validator_validates_false_authority_flags",
    "future_validator_validates_json_safety",
    "future_validator_calls_no_services",
    "future_validator_opens_no_db",
    "future_validator_imports_no_repository_uow",
    "future_validator_appends_no_evidence_audit",
    "future_validator_implements_no_runtime",
)

_FUTURE_CI_DECLARATIONS = (
    "future_ci_consumes_already_rendered_validator_output_only",
    "future_ci_calls_no_validator",
    "future_ci_validates_bounded_shape",
    "future_ci_validates_false_authority_flags",
    "future_ci_validates_json_safety",
    "future_ci_calls_no_services",
    "future_ci_opens_no_db",
    "future_ci_imports_no_repository_uow",
    "future_ci_appends_no_evidence_audit",
    "future_ci_implements_no_runtime",
)

_DECLARATION_GROUPS = (
    _RUNTIME_AUTHORITY_DECLARATIONS,
    _SERVICE_BOUNDARY_DECLARATIONS,
    _DB_REPOSITORY_UOW_BOUNDARY_DECLARATIONS,
    _IDEMPOTENCY_DECLARATIONS,
    _TRANSACTION_DECLARATIONS,
    _APPEND_PHASE_AUTHORITY_DECLARATIONS,
    _FAILURE_INCIDENT_DECLARATIONS,
    _FUTURE_VALIDATOR_DECLARATIONS,
    _FUTURE_CI_DECLARATIONS,
)

_AUTHORIZATION_FLAGS = (
    "append_runtime_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "repository_uow_writes_authorized",
    "direct_db_writes_authorized",
    "raw_sqlite_authorized",
    "ad_hoc_sql_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)

_RUNTIME_FLAGS = (
    "appends_evidence",
    "appends_audit",
    "calls_evidence_service",
    "calls_services",
    "opens_db",
    "calls_repository",
    "calls_uow",
    "executes_plan",
    "opens_transaction",
    "reserves_idempotency",
    "performs_rollback",
    "performs_runtime_append",
)

_AUTHORITY_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected in _SOURCE_BINDINGS)
    + tuple(name for name, _expected in _VALIDATOR_BINDINGS)
    + _OPERATION_REFS
    + (_EVIDENCE_REF_SET_FIELD, _AUDIT_REF_SET_FIELD)
    + _RUNTIME_AUTHORITY_DECLARATIONS
    + _SERVICE_BOUNDARY_DECLARATIONS
    + _DB_REPOSITORY_UOW_BOUNDARY_DECLARATIONS
    + _IDEMPOTENCY_DECLARATIONS
    + _TRANSACTION_DECLARATIONS
    + _APPEND_PHASE_AUTHORITY_DECLARATIONS
    + _FAILURE_INCIDENT_DECLARATIONS
    + _FUTURE_VALIDATOR_DECLARATIONS
    + _FUTURE_CI_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + ("json_safe",)
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "authority",
)

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "authority_not_mapping",
    "authority_shape_mismatch",
    "authority_surface_invalid",
    "authority_version_invalid",
    "source_ref_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "authority_not_mapping",
    "authority_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "validator_readiness_invalid",
    "validator_reason_code_invalid",
    "validator_failures_invalid",
    "validator_failure_unknown",
    "source_ref_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "append_runtime_authority_service_boundary_validator": (
            _VALIDATOR_TAG
        ),
        "append_runtime_authority_service_boundary_spec_only": (
            _AUTHORITY_SPEC_ONLY_TAG
        ),
        "evidence_audit_append_read_only_stack": (
            _EVIDENCE_AUDIT_APPEND_READ_ONLY_STACK_TAG
        ),
        "repository_uow_allowlist_read_only_stack": (
            _REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_TAG
        ),
        "write_path_read_only_stack": _WRITE_PATH_READ_ONLY_STACK_TAG,
        "executor_precondition_read_only_stack": (
            _EXECUTOR_PRECONDITION_READ_ONLY_STACK_TAG
        ),
        "execution_authorization_read_only_stack": (
            _EXECUTION_AUTHORIZATION_READ_ONLY_STACK_TAG
        ),
        "preflight_read_only_stack": _PREFLIGHT_READ_ONLY_STACK_TAG,
        "restore_dry_run_read_only_stack": (
            _RESTORE_DRY_RUN_READ_ONLY_STACK_TAG
        ),
        "write_side_recovery_spec_only": _WRITE_SIDE_RECOVERY_SPEC_ONLY_TAG,
        "write_side_precondition_ci": _WRITE_SIDE_PRECONDITION_CI_TAG,
        "write_side_precondition_checker": (
            _WRITE_SIDE_PRECONDITION_CHECKER_TAG
        ),
        "read_only_governance_layer": _READ_ONLY_GOVERNANCE_LAYER_TAG,
    },
    "ci_ok_authorizes_append": False,
    "ci_ok_authorizes_write": False,
    "append_runtime_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "evidence_service_authorized": False,
    "approval_service_authorized": False,
    "review_service_authorized": False,
    "revision_seal_service_authorized": False,
    "repository_uow_writes_authorized": False,
    "direct_db_writes_authorized": False,
    "raw_sqlite_authorized": False,
    "ad_hoc_sql_authorized": False,
    "transaction_runtime_authorized": False,
    "idempotency_reservation_authorized": False,
    "rollback_runtime_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "appends_evidence": False,
    "appends_audit": False,
    "calls_evidence_service": False,
    "calls_services": False,
    "opens_db": False,
    "calls_repository": False,
    "calls_uow": False,
    "executes_plan": False,
    "opens_transaction": False,
    "reserves_idempotency": False,
    "performs_rollback": False,
    "performs_runtime_append": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def append_runtime_authority_service_boundary_validator_ci_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def consume_append_runtime_authority_service_boundary_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_authority_fields()

    if not isinstance(payload, Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    if not _keys_match(payload, _PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("runtime_authority_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    authority = payload.get("authority")

    ready_is_bool = (
        "runtime_authority_ready" in payload and type(ready_value) is bool
    )
    if "runtime_authority_ready" in payload and not ready_is_bool:
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

    if not isinstance(authority, Mapping):
        if "authority" in payload:
            _append(failures, "authority_not_mapping")
    else:
        _validate_authority(authority, failures, fields)

    ordered_failures = _ordered_failures(failures)
    safe_source_failures = (
        list(source_failures)
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


def _validate_authority(
    authority: Mapping[object, object],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not _keys_match(authority, _AUTHORITY_KEYS):
        _append(failures, "authority_shape_mismatch")

    if authority.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "validator_surface_invalid")

    version = authority.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "validator_version_invalid")

    for field, expected in _SOURCE_BINDINGS + _VALIDATOR_BINDINGS:
        candidate = authority.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "source_ref_mismatch")
        else:
            _append(failures, "source_ref_mismatch")

    for field in _OPERATION_REFS:
        candidate = authority.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "operation_ref_invalid")

    fields[_EVIDENCE_REF_SET_FIELD] = _validate_ref_set(
        authority.get(_EVIDENCE_REF_SET_FIELD),
        failures,
        "evidence_ref_set_invalid",
    )
    fields[_AUDIT_REF_SET_FIELD] = _validate_ref_set(
        authority.get(_AUDIT_REF_SET_FIELD),
        failures,
        "audit_ref_set_invalid",
    )

    for group in _DECLARATION_GROUPS:
        for field in group:
            candidate = authority.get(field)
            if type(candidate) is not bool:
                fields[field] = None
                _append(failures, "required_declaration_invalid")
            else:
                fields[field] = candidate
                if candidate is False:
                    _append(failures, "required_declaration_false")

    for field in _AUTHORIZATION_FLAGS:
        candidate = authority.get(field)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    for field in _RUNTIME_FLAGS:
        candidate = authority.get(field)
        if type(candidate) is not bool:
            _append(failures, "runtime_flag_invalid")
        elif candidate is True:
            _append(failures, "runtime_flag_true")

    json_safe = authority.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _validate_ref_set(
    candidate: object,
    failures: list[str],
    failure: str,
) -> list[str]:
    if not isinstance(candidate, list) or candidate == []:
        _append(failures, failure)
        return []

    seen: list[str] = []
    invalid = False
    for item in candidate:
        if type(item) is not str or item == "" or item in seen:
            invalid = True
            continue
        seen.append(item)
    if invalid:
        _append(failures, failure)
        return []
    return list(seen)


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
    output["authority"] = _authority_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _authority_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for field, _expected in _SOURCE_BINDINGS + _VALIDATOR_BINDINGS:
        output[field] = fields[field]
    for field in _OPERATION_REFS:
        output[field] = fields[field]
    output[_EVIDENCE_REF_SET_FIELD] = deepcopy(
        fields[_EVIDENCE_REF_SET_FIELD]
    )
    output[_AUDIT_REF_SET_FIELD] = deepcopy(fields[_AUDIT_REF_SET_FIELD])
    for group in _DECLARATION_GROUPS:
        for field in group:
            output[field] = fields[field]
    for field in _AUTHORIZATION_FLAGS:
        output[field] = False
    for field in _RUNTIME_FLAGS:
        output[field] = False
    output["json_safe"] = True
    assert tuple(output.keys()) == _AUTHORITY_KEYS
    return output


def _empty_authority_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for field, _expected in _SOURCE_BINDINGS + _VALIDATOR_BINDINGS:
        fields[field] = None
    for field in _OPERATION_REFS:
        fields[field] = None
    fields[_EVIDENCE_REF_SET_FIELD] = []
    fields[_AUDIT_REF_SET_FIELD] = []
    for group in _DECLARATION_GROUPS:
        for field in group:
            fields[field] = None
    return fields


def _keys_match(candidate: Mapping[object, object], keys: tuple[str, ...]) -> bool:
    try:
        return set(candidate.keys()) == set(keys)
    except TypeError:
        return False


def _is_string_list(candidate: object) -> bool:
    if not isinstance(candidate, list):
        return False
    for item in candidate:
        if type(item) is not str:
            return False
    return True


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
