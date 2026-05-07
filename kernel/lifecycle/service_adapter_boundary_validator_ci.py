"""Read-only CI consumer for rendered service adapter boundary validation."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_adapter_boundary_validator_ci_manifest",
    "consume_service_adapter_boundary_validator_ci",
]


_SURFACE = "service_adapter_boundary_validator_ci"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_service_adapter_boundary_validator_output_v1"

_VALIDATOR_SURFACE = "service_adapter_boundary_validator"
_VALIDATOR_VERSION = 1
_VALIDATOR_TAG = "service-adapter-boundary-validator-v1"
_VALIDATOR_COMMIT = "124359832c8e83412a54ff740073640cc92082e1"

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_VALIDATOR_REASON_INVALID = "invalid_service_adapter_payload"
_VALIDATOR_REASON_CODES = (
    _VALIDATOR_REASON_INVALID,
    _REASON_NOT_READY,
    _REASON_READY,
)

_PAYLOAD_KEYS = (
    "service_adapter_ready",
    "reason_code",
    "failures",
    "boundary",
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
_APPEND_AUTHORITY_BOUNDARY_READ_ONLY_STACK_TAG = (
    "append-runtime-authority-service-boundary-read-only-stack-v1"
)
_APPEND_AUTHORITY_BOUNDARY_READ_ONLY_STACK_COMMIT = (
    "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039"
)
_SERVICE_ADAPTER_BOUNDARY_SPEC_ONLY_TAG = "service-adapter-boundary-spec-only-v1"
_SERVICE_ADAPTER_BOUNDARY_SPEC_ONLY_COMMIT = (
    "d03a3e258dae6f12a14f12e4bbc12d21e78e8d5d"
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
        "source_append_runtime_authority_"
        "service_boundary_read_only_stack_tag",
        _APPEND_AUTHORITY_BOUNDARY_READ_ONLY_STACK_TAG,
    ),
    (
        "source_append_runtime_authority_"
        "service_boundary_read_only_stack_commit",
        _APPEND_AUTHORITY_BOUNDARY_READ_ONLY_STACK_COMMIT,
    ),
    (
        "source_service_adapter_boundary_spec_only_tag",
        _SERVICE_ADAPTER_BOUNDARY_SPEC_ONLY_TAG,
    ),
    (
        "source_service_adapter_boundary_spec_only_commit",
        _SERVICE_ADAPTER_BOUNDARY_SPEC_ONLY_COMMIT,
    ),
)

_VALIDATOR_BINDINGS = (
    (
        "source_service_adapter_boundary_validator_tag",
        _VALIDATOR_TAG,
    ),
    (
        "source_service_adapter_boundary_validator_commit",
        _VALIDATOR_COMMIT,
    ),
)

_SERVICE_IDENTITIES_FIELD = "service_identities"
_KNOWN_FORBIDDEN_METHODS_FIELD = "known_forbidden_service_methods"

_REQUIRED_SERVICE_IDENTITIES = (
    "evidence_service",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "audit_service_future_adapter",
)

_KNOWN_FORBIDDEN_SERVICE_METHODS = (
    "EvidenceService." "close_" "evidence",
    "ApprovalService." "evaluate_" "barrier",
    "ApprovalService." "reverify_" "for_seal",
    "ReviewService." "render_" "review",
    "RevisionSealService." "seal_" "revision",
)

_REQUIRED_DECLARATIONS = (
    "service_adapter_implementation_forbidden",
    "service_calls_forbidden",
    "evidence_service_call_forbidden",
    "approval_service_call_forbidden",
    "review_service_call_forbidden",
    "revision_seal_service_call_forbidden",
    "audit_service_call_forbidden",
    "unnamed_service_forbidden",
    "dynamic_service_resolution_forbidden",
    "wildcard_service_authority_forbidden",
    "class_level_service_authority_forbidden",
    "module_level_service_authority_forbidden",
    "service_method_allowlist_required",
    "exact_service_identity_required",
    "exact_service_class_name_required",
    "exact_service_method_name_required",
    "service_result_contract_required",
    "service_result_json_safe_required",
    "service_result_bounded_required",
    "service_result_deterministic_required",
    "service_result_no_runtime_handles_required",
    "service_result_no_raw_repr_required",
    "service_object_leakage_forbidden",
    "db_handle_leakage_forbidden",
    "repository_uow_handle_leakage_forbidden",
    "exception_object_leakage_forbidden",
    "filesystem_network_handle_leakage_forbidden",
    "raw_service_result_passthrough_forbidden",
    "implicit_append_success_forbidden",
    "implicit_audit_emission_forbidden",
    "service_transaction_ownership_forbidden_by_default",
    "kernel_owned_transaction_required_for_future_runtime",
    "uncontrolled_nested_transaction_forbidden",
    "in_transaction_service_call_requires_separate_authority",
    "out_of_band_service_call_policy_required",
    "commit_after_required_bookkeeping_only",
    "post_mutation_service_failure_incident_class",
    "service_idempotency_binding_required",
    "service_replay_classification_required",
    "same_key_same_binding_safe_replay_only",
    "same_key_different_binding_fail_closed",
    "ambiguous_replay_incident_class",
    "evidence_audit_ref_fabrication_forbidden",
    "undeclared_ref_forbidden",
    "missing_ref_fail_closed",
    "mismatched_ref_fail_closed",
    "evidence_audit_refs_source_bound_required",
    "evidence_audit_refs_operation_bound_required",
    "evidence_audit_refs_json_safe_required",
    "adapter_output_cannot_imply_append_success_without_authority",
    "adapter_output_cannot_imply_audit_emission_without_authority",
    "adapter_output_cannot_create_refs_without_authority",
    "forbidden_service_call_fail_closed",
    "method_not_allowlisted_fail_closed",
    "malformed_service_result_fail_closed",
    "idempotency_mismatch_fail_closed",
    "transaction_violation_incident_class",
    "rollback_failure_incident_class",
    "partial_success_forbidden",
    "silent_success_forbidden",
    "future_validator_required",
    "future_ci_required",
)

_AUTHORIZATION_FLAGS = (
    "service_adapter_" "runtime_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "audit_service_authorized",
    "service_method_" "call_authorized",
    "service_side_effect_authorized",
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

_JSON_SAFE_FIELD = "json_safe"

_BOUNDARY_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected in _SOURCE_BINDINGS)
    + tuple(name for name, _expected in _VALIDATOR_BINDINGS)
    + (_SERVICE_IDENTITIES_FIELD, _KNOWN_FORBIDDEN_METHODS_FIELD)
    + _REQUIRED_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + (_JSON_SAFE_FIELD,)
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "boundary",
)

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "service_identity_invalid",
    "forbidden_service_method_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "validator_checkpoint_mismatch",
    "validator_readiness_invalid",
    "validator_reason_code_invalid",
    "validator_failures_invalid",
    "validator_failure_unknown",
    "source_ref_mismatch",
    "service_identity_invalid",
    "forbidden_service_method_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "service_adapter_boundary_validator": _VALIDATOR_TAG,
        "service_adapter_boundary_spec_only": (
            _SERVICE_ADAPTER_BOUNDARY_SPEC_ONLY_TAG
        ),
        "append_runtime_authority_service_boundary_read_only_stack": (
            _APPEND_AUTHORITY_BOUNDARY_READ_ONLY_STACK_TAG
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
    "ci_ok_authorizes_service_calls": False,
    "ci_ok_authorizes_runtime": False,
    "ci_ok_authorizes_write": False,
    "service_adapter_runtime_authorized": False,
    "evidence_service_authorized": False,
    "approval_service_authorized": False,
    "review_service_authorized": False,
    "revision_seal_service_authorized": False,
    "audit_service_authorized": False,
    "service_method_call_authorized": False,
    "service_side_effect_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "append_runtime_authorized": False,
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
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def service_adapter_boundary_validator_ci_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def consume_service_adapter_boundary_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_boundary_fields()

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

    ready_value = payload.get("service_adapter_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    boundary = payload.get("boundary")

    ready_is_bool = (
        "service_adapter_ready" in payload and type(ready_value) is bool
    )
    if "service_adapter_ready" in payload and not ready_is_bool:
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

    if not isinstance(boundary, Mapping):
        if "boundary" in payload:
            _append(failures, "boundary_not_mapping")
    else:
        _validate_boundary(boundary, failures, fields)

    ordered_failures = _ordered_failures(failures)
    safe_source_failures = (
        _ordered_validator_failures(source_failures)
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


def _validate_boundary(
    boundary: Mapping[object, object],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not _keys_match(boundary, _BOUNDARY_KEYS):
        _append(failures, "boundary_shape_mismatch")

    if boundary.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "validator_surface_invalid")

    version = boundary.get("version")
    if (
        type(version) is bool
        or type(version) is not int
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "validator_version_invalid")

    for field, expected in _SOURCE_BINDINGS:
        candidate = boundary.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "source_ref_mismatch")
        else:
            _append(failures, "source_ref_mismatch")

    for field, expected in _VALIDATOR_BINDINGS:
        candidate = boundary.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "validator_checkpoint_mismatch")
        else:
            _append(failures, "validator_checkpoint_mismatch")

    fields[_SERVICE_IDENTITIES_FIELD] = _validate_exact_list(
        boundary.get(_SERVICE_IDENTITIES_FIELD),
        _REQUIRED_SERVICE_IDENTITIES,
        failures,
        "service_identity_invalid",
    )
    fields[_KNOWN_FORBIDDEN_METHODS_FIELD] = _validate_exact_list(
        boundary.get(_KNOWN_FORBIDDEN_METHODS_FIELD),
        _KNOWN_FORBIDDEN_SERVICE_METHODS,
        failures,
        "forbidden_service_method_invalid",
    )

    for field in _REQUIRED_DECLARATIONS:
        candidate = boundary.get(field)
        if type(candidate) is not bool:
            fields[field] = None
            _append(failures, "required_declaration_invalid")
        else:
            fields[field] = candidate
            if candidate is False:
                _append(failures, "required_declaration_false")

    for field in _AUTHORIZATION_FLAGS:
        candidate = boundary.get(field)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    json_safe = boundary.get(_JSON_SAFE_FIELD)
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _validate_exact_list(
    candidate: object,
    expected: tuple[str, ...],
    failures: list[str],
    failure: str,
) -> list[str]:
    if not isinstance(candidate, list):
        _append(failures, failure)
        return []
    if candidate != list(expected):
        _append(failures, failure)
        return []
    return list(candidate)


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
    output["boundary"] = _boundary_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _boundary_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for field, _expected in _SOURCE_BINDINGS + _VALIDATOR_BINDINGS:
        output[field] = fields[field]
    output[_SERVICE_IDENTITIES_FIELD] = deepcopy(
        fields[_SERVICE_IDENTITIES_FIELD]
    )
    output[_KNOWN_FORBIDDEN_METHODS_FIELD] = deepcopy(
        fields[_KNOWN_FORBIDDEN_METHODS_FIELD]
    )
    for field in _REQUIRED_DECLARATIONS:
        output[field] = fields[field]
    for field in _AUTHORIZATION_FLAGS:
        output[field] = False
    output[_JSON_SAFE_FIELD] = True
    assert tuple(output.keys()) == _BOUNDARY_KEYS
    return output


def _empty_boundary_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for field, _expected in _SOURCE_BINDINGS + _VALIDATOR_BINDINGS:
        fields[field] = None
    fields[_SERVICE_IDENTITIES_FIELD] = []
    fields[_KNOWN_FORBIDDEN_METHODS_FIELD] = []
    for field in _REQUIRED_DECLARATIONS:
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


def _ordered_validator_failures(candidate: object) -> list[str]:
    assert isinstance(candidate, list)
    return [
        failure
        for failure in _VALIDATOR_FAILURE_TAXONOMY
        if failure in candidate
    ]
