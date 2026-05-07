"""Read-only CI consumer for rendered service method authority validation."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_method_authority_contract_validator_ci_manifest",
    "consume_service_method_authority_contract_validator_ci",
]


_SURFACE = "service_method_authority_contract_validator_ci"
_VERSION = 1
_INPUT_SHAPE = (
    "already_rendered_service_method_authority_contract_validator_v1_output"
)

_VALIDATOR_SURFACE = "service_method_authority_contract_validator"
_VALIDATOR_VERSION = 1
_VALIDATOR_TAG = "service-method-authority-contract-validator-v1"
_VALIDATOR_COMMIT = "d8de484f845571c6bf31276ccee12b97b8b9cec8"

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_VALIDATOR_REASON_INVALID = "invalid_method_authority_payload"
_VALIDATOR_REASON_CODES = (
    _VALIDATOR_REASON_INVALID,
    _REASON_NOT_READY,
    _REASON_READY,
)

_PAYLOAD_KEYS = (
    "method_authority_ready",
    "reason_code",
    "failures",
    "contract",
)

_SOURCE_BINDINGS = (
    (
        "source_read_only_governance_layer_tag",
        "read-only-governance-layer-v1",
    ),
    (
        "source_read_only_governance_layer_commit",
        "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
    ),
    (
        "source_write_side_precondition_checker_tag",
        "write-side-precondition-checker-v1",
    ),
    (
        "source_write_side_precondition_checker_commit",
        "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6",
    ),
    (
        "source_write_side_precondition_ci_tag",
        "write-side-precondition-ci-v1",
    ),
    (
        "source_write_side_precondition_ci_commit",
        "05c81541ad3d7deee20023843142f702937f6c3f",
    ),
    (
        "source_write_side_recovery_spec_only_tag",
        "write-side-recovery-spec-only-v1",
    ),
    (
        "source_write_side_recovery_spec_only_commit",
        "ad560cc2dab135f2c1d56d948410ae47586d118e",
    ),
    (
        "source_restore_dry_run_read_only_stack_tag",
        "restore-dry-run-read-only-stack-v1",
    ),
    (
        "source_restore_dry_run_read_only_stack_commit",
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b",
    ),
    (
        "source_preflight_read_only_stack_tag",
        "preflight-read-only-stack-v1",
    ),
    (
        "source_preflight_read_only_stack_commit",
        "662b6161253c35204b437e88809c5bab21908c6d",
    ),
    (
        "source_execution_authorization_read_only_stack_tag",
        "execution-authorization-read-only-stack-v1",
    ),
    (
        "source_execution_authorization_read_only_stack_commit",
        "d586aeb60620010c900df7be1a88621ab2cb8dc1",
    ),
    (
        "source_executor_precondition_read_only_stack_tag",
        "executor-precondition-read-only-stack-v1",
    ),
    (
        "source_executor_precondition_read_only_stack_commit",
        "cb3948eb843866dcc961b6a074038c13db64d017",
    ),
    (
        "source_write_path_read_only_stack_tag",
        "write-path-read-only-stack-v1",
    ),
    (
        "source_write_path_read_only_stack_commit",
        "8ffd4679aca8f593415089748df35df42af8f015",
    ),
    (
        "source_repository_uow_allowlist_read_only_stack_tag",
        "repository-uow-allowlist-read-only-stack-v1",
    ),
    (
        "source_repository_uow_allowlist_read_only_stack_commit",
        "bec2d04eab1922594dcbfbe35971f4efe0fe4849",
    ),
    (
        "source_evidence_audit_append_read_only_stack_tag",
        "evidence-audit-append-read-only-stack-v1",
    ),
    (
        "source_evidence_audit_append_read_only_stack_commit",
        "62db8a586efa9375d2c77cf7c6335ccf5ef11279",
    ),
    (
        "source_append_runtime_authority_"
        "service_boundary_read_only_stack_tag",
        "append-runtime-authority-service-boundary-read-only-stack-v1",
    ),
    (
        "source_append_runtime_authority_"
        "service_boundary_read_only_stack_commit",
        "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039",
    ),
    (
        "source_service_adapter_boundary_read_only_stack_tag",
        "service-adapter-boundary-read-only-stack-v1",
    ),
    (
        "source_service_adapter_boundary_read_only_stack_commit",
        "8698ea42c78cbe79231698be8839b9d2c246cfdf",
    ),
    (
        "source_service_method_authority_contract_spec_only_tag",
        "service-method-authority-contract-spec-only-v1",
    ),
    (
        "source_service_method_authority_contract_spec_only_commit",
        "ffe284468215f3cfdc7c3de39b2708da1e653e42",
    ),
)

_VALIDATOR_CHECKPOINT_BINDINGS = (
    ("validator_checkpoint_tag", _VALIDATOR_TAG),
    ("validator_checkpoint_commit", _VALIDATOR_COMMIT),
)

_SERVICE_IDENTITIES_FIELD = "service_identities"
_REQUIRED_SERVICE_IDENTITIES = (
    "evidence_service",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "audit_service_future_adapter",
)

_REQUIRED_TRUE_DECLARATIONS = (
    "spec_only_non_executable",
    "service_adapter_implementation_forbidden",
    "service_calls_forbidden",
    "evidence_service_call_forbidden",
    "approval_service_call_forbidden",
    "review_service_call_forbidden",
    "revision_seal_service_call_forbidden",
    "audit_service_call_forbidden",
    "future_validator_required",
    "future_ci_required",
)

_DECLARATION_GROUPS = (
    (
        "method_authority_declarations",
        (
            "exact_service_identity_required",
            "exact_service_class_name_required",
            "exact_service_method_name_required",
            "exact_operation_kind_required",
            "exact_authority_scope_required",
            "exact_phase_required",
            "exact_input_contract_ref_required",
            "exact_output_contract_ref_required",
            "exact_idempotency_binding_ref_required",
            "exact_transaction_placement_ref_required",
            "exact_failure_incident_policy_ref_required",
            "exact_evidence_audit_ref_binding_required",
            "exact_authority_grant_ref_required",
            "exact_revocation_ref_required",
        ),
    ),
    (
        "method_allowlist_declarations",
        (
            "service_method_allowlist_required",
            "wildcard_method_authority_forbidden",
            "class_level_authority_forbidden",
            "module_level_authority_forbidden",
            "dynamic_service_resolution_forbidden",
            "runtime_method_lookup_forbidden",
            "reflection_method_discovery_forbidden",
            "inferred_method_authority_forbidden",
            "service_object_passthrough_forbidden",
            "raw_callable_passthrough_forbidden",
        ),
    ),
    (
        "result_contract_declarations",
        (
            "service_result_contract_required",
            "service_result_json_safe_required",
            "service_result_bounded_required",
            "service_result_deterministic_required",
            "explicit_success_failure_state_required",
            "explicit_reason_code_required",
            "explicit_failure_taxonomy_required",
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
            "fabricated_evidence_audit_refs_forbidden",
            "no_success_without_required_refs",
        ),
    ),
    (
        "idempotency_replay_declarations",
        (
            "service_idempotency_binding_required",
            "service_idempotency_source_bound_required",
            "service_idempotency_operation_bound_required",
            "service_idempotency_service_identity_bound_required",
            "service_idempotency_method_bound_required",
            "service_idempotency_authority_ref_bound_required",
            "service_idempotency_evidence_audit_ref_bound_required",
            "service_replay_classification_required",
            "same_key_same_binding_safe_replay_only",
            "same_key_different_binding_fail_closed",
            "ambiguous_replay_incident_class",
            "idempotency_reservation_runtime_not_authorized",
        ),
    ),
    (
        "transaction_placement_declarations",
        (
            "kernel_owned_transaction_required_for_future_runtime",
            "service_transaction_ownership_forbidden_by_default",
            "service_commit_forbidden",
            "service_rollback_forbidden",
            "uncontrolled_nested_transaction_forbidden",
            "in_transaction_service_call_requires_separate_authority",
            "out_of_band_service_call_policy_required",
            "commit_after_required_bookkeeping_only",
            "rollback_on_unexpected_exception_required",
            "rollback_failure_incident_class",
            "transaction_runtime_not_authorized",
        ),
    ),
    (
        "failure_incident_declarations",
        (
            "expected_rejection_defined",
            "forbidden_service_call_fail_closed",
            "method_not_allowlisted_fail_closed",
            "malformed_service_result_fail_closed",
            "missing_ref_fail_closed",
            "mismatched_ref_fail_closed",
            "idempotency_mismatch_fail_closed",
            "ambiguous_replay_incident_class",
            "transaction_violation_incident_class",
            "post_mutation_service_failure_incident_class",
            "rollback_failure_incident_class",
            "failure_incident_separation_required",
            "partial_success_forbidden",
            "silent_success_forbidden",
            "incident_class_conditions_defined",
            "fail_closed_behavior_required",
        ),
    ),
    (
        "evidence_audit_ref_declarations",
        (
            "evidence_audit_refs_source_bound_required",
            "evidence_audit_refs_operation_bound_required",
            "evidence_audit_refs_method_bound_required",
            "evidence_audit_refs_authority_bound_required",
            "evidence_audit_refs_json_safe_required",
            "fabricated_evidence_audit_refs_forbidden",
            "undeclared_ref_forbidden",
            "missing_ref_fail_closed",
            "mismatched_ref_fail_closed",
            "implicit_append_success_forbidden",
            "implicit_audit_emission_forbidden",
        ),
    ),
    (
        "authority_grant_declarations",
        (
            "authority_source_bound_required",
            "authority_operation_bound_required",
            "authority_service_identity_bound_required",
            "authority_method_bound_required",
            "authority_phase_bound_required",
            "authority_result_contract_bound_required",
            "authority_idempotency_bound_required",
            "authority_transaction_placement_bound_required",
            "authority_failure_policy_bound_required",
            "authority_evidence_audit_ref_bound_required",
            "authority_human_approval_bound_required",
            "authority_operator_confirmation_bound_required",
            "authority_expiration_bound_required",
            "authority_issuer_bound_required",
            "authority_revocation_bound_required",
            "authority_narrow_required",
            "wildcard_authority_forbidden",
            "durable_authority_forbidden_by_default",
        ),
    ),
    (
        "revocation_declarations",
        (
            "revocation_ref_required",
            "revoked_authority_fails_closed",
            "expired_authority_fails_closed",
            "mismatched_authority_fails_closed",
            "missing_authority_fails_closed",
            "read_only_validation_does_not_imply_authority",
            "ci_success_does_not_imply_authority",
            "tag_existence_does_not_imply_authority",
        ),
    ),
    ("required_true_declarations", _REQUIRED_TRUE_DECLARATIONS),
)

_AUTHORITY_FLAGS = (
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
    "runtime_allowlist_authorized",
    "runtime_checker_authorized",
    "runtime_enforcer_authorized",
    "executor_implementation_authorized",
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

_JSON_SAFE_FIELD = "json_safe"

_CONTRACT_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected in _SOURCE_BINDINGS)
    + tuple(name for name, _expected in _VALIDATOR_CHECKPOINT_BINDINGS)
    + (_SERVICE_IDENTITIES_FIELD,)
    + tuple(name for name, _fields in _DECLARATION_GROUPS)
    + _AUTHORITY_FLAGS
    + (_JSON_SAFE_FIELD,)
)

_AUTHORITY_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected in _SOURCE_BINDINGS)
    + tuple(name for name, _expected in _VALIDATOR_CHECKPOINT_BINDINGS)
    + (_SERVICE_IDENTITIES_FIELD,)
    + tuple(name for name, _fields in _DECLARATION_GROUPS)
    + _AUTHORITY_FLAGS
    + (_JSON_SAFE_FIELD,)
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
    "contract_not_mapping",
    "contract_shape_mismatch",
    "contract_surface_invalid",
    "contract_version_invalid",
    "source_ref_mismatch",
    "service_identity_invalid",
    "method_authority_declaration_invalid",
    "method_allowlist_declaration_invalid",
    "result_contract_declaration_invalid",
    "idempotency_replay_declaration_invalid",
    "transaction_placement_declaration_invalid",
    "failure_incident_declaration_invalid",
    "evidence_audit_ref_declaration_invalid",
    "authority_grant_declaration_invalid",
    "revocation_declaration_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "validator_checkpoint_invalid",
    "validator_readiness_invalid",
    "validator_reason_code_invalid",
    "validator_failures_invalid",
    "validator_failure_unknown",
    "source_ref_mismatch",
    "service_identity_invalid",
    "declaration_group_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "service_method_authority_contract_validator": _VALIDATOR_TAG,
        "service_method_authority_contract_spec_only": (
            "service-method-authority-contract-spec-only-v1"
        ),
        "service_adapter_boundary_read_only_stack": (
            "service-adapter-boundary-read-only-stack-v1"
        ),
        "append_runtime_authority_service_boundary_read_only_stack": (
            "append-runtime-authority-service-boundary-read-only-stack-v1"
        ),
        "evidence_audit_append_read_only_stack": (
            "evidence-audit-append-read-only-stack-v1"
        ),
        "repository_uow_allowlist_read_only_stack": (
            "repository-uow-allowlist-read-only-stack-v1"
        ),
        "write_path_read_only_stack": "write-path-read-only-stack-v1",
        "executor_precondition_read_only_stack": (
            "executor-precondition-read-only-stack-v1"
        ),
        "execution_authorization_read_only_stack": (
            "execution-authorization-read-only-stack-v1"
        ),
        "preflight_read_only_stack": "preflight-read-only-stack-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "ci_ok_authorizes_service_calls": False,
    "ci_ok_authorizes_runtime": False,
    "ci_ok_authorizes_write": False,
    **{name: False for name in _AUTHORITY_FLAGS},
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def service_method_authority_contract_validator_ci_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def consume_service_method_authority_contract_validator_ci(
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

    ready_value = payload.get("method_authority_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    contract = payload.get("contract")

    ready_is_bool = (
        "method_authority_ready" in payload and type(ready_value) is bool
    )
    if "method_authority_ready" in payload and not ready_is_bool:
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

    if not isinstance(contract, Mapping):
        _append(failures, "contract_not_mapping")
    else:
        _validate_contract(contract, failures, fields)

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


def _validate_contract(
    contract: Mapping[object, object],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not _keys_match(contract, _CONTRACT_KEYS):
        _append(failures, "contract_shape_mismatch")

    if contract.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "validator_surface_invalid")

    version = contract.get("version")
    if (
        type(version) is bool
        or type(version) is not int
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "validator_version_invalid")

    for field, expected in _SOURCE_BINDINGS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "source_ref_mismatch")
        else:
            _append(failures, "source_ref_mismatch")

    for field, expected in _VALIDATOR_CHECKPOINT_BINDINGS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "validator_checkpoint_invalid")
        else:
            _append(failures, "validator_checkpoint_invalid")

    fields[_SERVICE_IDENTITIES_FIELD] = _validate_exact_list(
        contract.get(_SERVICE_IDENTITIES_FIELD),
        _REQUIRED_SERVICE_IDENTITIES,
        failures,
        "service_identity_invalid",
    )

    for group_name, group_fields in _DECLARATION_GROUPS:
        fields[group_name] = _validate_declaration_group(
            contract.get(group_name),
            group_fields,
            failures,
        )

    for field in _AUTHORITY_FLAGS:
        candidate = contract.get(field)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    json_safe = contract.get(_JSON_SAFE_FIELD)
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _validate_declaration_group(
    candidate: object,
    expected_fields: tuple[str, ...],
    failures: list[str],
) -> dict[str, object]:
    output = {field: None for field in expected_fields}
    if not isinstance(candidate, Mapping):
        _append(failures, "declaration_group_invalid")
        return output

    if not _keys_match(candidate, expected_fields):
        _append(failures, "declaration_group_invalid")

    for field in expected_fields:
        value = candidate.get(field)
        if type(value) is not bool or value is not True:
            _append(failures, "declaration_group_invalid")
        output[field] = value if type(value) is bool else None
    return output


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
    output["authority"] = _authority_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _authority_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for field, _expected in _SOURCE_BINDINGS:
        output[field] = fields[field]
    for field, _expected in _VALIDATOR_CHECKPOINT_BINDINGS:
        output[field] = fields[field]
    output[_SERVICE_IDENTITIES_FIELD] = deepcopy(
        fields[_SERVICE_IDENTITIES_FIELD]
    )
    for group_name, _group_fields in _DECLARATION_GROUPS:
        output[group_name] = deepcopy(fields[group_name])
    for field in _AUTHORITY_FLAGS:
        output[field] = False
    output[_JSON_SAFE_FIELD] = True
    assert tuple(output.keys()) == _AUTHORITY_KEYS
    return output


def _empty_authority_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for field, _expected in _SOURCE_BINDINGS:
        fields[field] = None
    for field, _expected in _VALIDATOR_CHECKPOINT_BINDINGS:
        fields[field] = None
    fields[_SERVICE_IDENTITIES_FIELD] = []
    for group_name, group_fields in _DECLARATION_GROUPS:
        fields[group_name] = {field: None for field in group_fields}
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
