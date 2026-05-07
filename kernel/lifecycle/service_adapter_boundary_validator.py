"""Pure validator for rendered service adapter boundary declarations."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_adapter_boundary_validator_manifest",
    "validate_service_adapter_boundary",
]

_SURFACE = "service_adapter_boundary_validator"
_BOUNDARY_SURFACE = "ServiceAdapterBoundaryV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_service_adapter_boundary_v1"

_REASON_INVALID = "invalid_service_adapter_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_INPUT_KEY = "service_adapter_boundary"
_INPUT_KEYS = (_INPUT_KEY,)

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
    + (_SERVICE_IDENTITIES_FIELD, _KNOWN_FORBIDDEN_METHODS_FIELD)
    + _REQUIRED_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + (_JSON_SAFE_FIELD,)
)

_OUTPUT_KEYS = (
    "service_adapter_ready",
    "reason_code",
    "failures",
    "boundary",
)

_FAILURE_ORDER = (
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

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "boundary_not_mapping",
        "boundary_shape_mismatch",
        "boundary_surface_invalid",
        "boundary_version_invalid",
        "source_ref_mismatch",
        "service_identity_invalid",
        "forbidden_service_method_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
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
    "service_adapter_ready_authorizes_service_calls": False,
    "service_adapter_ready_authorizes_runtime": False,
    "service_adapter_ready_authorizes_write": False,
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


def service_adapter_boundary_validator_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def validate_service_adapter_boundary(payload: object) -> dict[str, object]:
    fields = _empty_boundary_fields()

    if not isinstance(payload, Mapping):
        return _result(
            ready=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    boundary = payload.get(_INPUT_KEY)
    _validate_boundary(boundary, failures, fields)

    ordered_failures = _ordered_failures(failures)
    ready = ordered_failures == []
    if ready:
        reason_code = _REASON_READY
    elif _has_structural_failure(ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ready=ready,
        reason_code=reason_code,
        failures=ordered_failures,
        fields=fields,
    )


def _validate_boundary(
    boundary: object,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not isinstance(boundary, Mapping):
        _append(failures, "boundary_not_mapping")
        return

    if set(boundary.keys()) != set(_BOUNDARY_KEYS):
        _append(failures, "boundary_shape_mismatch")

    if boundary.get("surface") != _BOUNDARY_SURFACE:
        _append(failures, "boundary_surface_invalid")

    version = boundary.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "boundary_version_invalid")

    for field, expected in _SOURCE_BINDINGS:
        candidate = boundary.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "source_ref_mismatch")
        else:
            _append(failures, "source_ref_mismatch")

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
    ready: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["service_adapter_ready"] = ready
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["boundary"] = _boundary_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _boundary_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for name, _expected in _SOURCE_BINDINGS:
        output[name] = fields[name]
    output[_SERVICE_IDENTITIES_FIELD] = deepcopy(
        fields[_SERVICE_IDENTITIES_FIELD]
    )
    output[_KNOWN_FORBIDDEN_METHODS_FIELD] = deepcopy(
        fields[_KNOWN_FORBIDDEN_METHODS_FIELD]
    )
    for name in _REQUIRED_DECLARATIONS:
        output[name] = fields[name]
    for name in _AUTHORIZATION_FLAGS:
        output[name] = False
    output[_JSON_SAFE_FIELD] = True
    assert tuple(output.keys()) == _BOUNDARY_KEYS
    return output


def _empty_boundary_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, _expected in _SOURCE_BINDINGS:
        fields[name] = None
    fields[_SERVICE_IDENTITIES_FIELD] = []
    fields[_KNOWN_FORBIDDEN_METHODS_FIELD] = []
    for name in _REQUIRED_DECLARATIONS:
        fields[name] = None
    return fields


def _has_structural_failure(ordered_failures: list[str]) -> bool:
    for failure in ordered_failures:
        if failure in _STRUCTURAL_FAILURES:
            return True
    return False


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
