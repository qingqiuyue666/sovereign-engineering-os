"""Read-only CI consumer for already-rendered append contract validator output."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "evidence_audit_append_contract_validator_ci_manifest",
    "consume_evidence_audit_append_contract_validator_ci",
]


_SURFACE = "evidence_audit_append_contract_validator_ci"
_VERSION = 1
_INPUT_SHAPE = (
    "already_rendered_evidence_audit_append_contract_validator_output"
)

_VALIDATOR_SURFACE = "evidence_audit_append_contract_validator"
_VALIDATOR_VERSION = 1
_VALIDATOR_TAG = "evidence-audit-append-contract-validator-v1"

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
_EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_TAG = (
    "evidence-audit-append-contract-spec-only-v1"
)
_EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_COMMIT = (
    "a601acec242e578e52005e53ad46281f90eace63"
)

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_VALIDATOR_REASON_INVALID = "invalid_contract_payload"
_VALIDATOR_REASON_CODES = frozenset(
    {
        _VALIDATOR_REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    }
)

_PAYLOAD_KEYS = (
    "append_contract_ready",
    "reason_code",
    "failures",
    "contract",
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
        "source_evidence_audit_append_contract_spec_only_tag",
        _EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_TAG,
    ),
    (
        "source_evidence_audit_append_contract_spec_only_commit",
        _EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_COMMIT,
    ),
)

_OPERATION_REFS = (
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "target_artifact_id",
    "target_task_id",
    "human_approval_ref",
    "operator_confirmation_ref",
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "write_path_contract_validator_ci_ref",
    "repository_uow_allowlist_validator_ci_ref",
    "append_contract_ref",
    "append_idempotency_key",
)

_REF_SET_FIELDS = (
    ("evidence_ref_set", "evidence_ref_set_invalid"),
    ("audit_ref_set", "audit_ref_set_invalid"),
)

_APPEND_PHASE_DECLARATIONS = (
    "before_evidence_required",
    "mutation_intent_evidence_required",
    "after_evidence_required",
    "rejection_evidence_policy_required",
    "failure_evidence_policy_required",
    "rollback_evidence_policy_required",
    "audit_event_required",
    "deterministic_append_order_required",
    "final_append_set_declaration_required",
)

_EVIDENCE_CATEGORY_DECLARATIONS = (
    "before_evidence_declared",
    "mutation_intent_evidence_declared",
    "after_evidence_declared",
    "rejection_evidence_declared",
    "failure_evidence_declared",
    "rollback_evidence_declared",
    "incident_evidence_declared",
    "post_mutation_append_failure_evidence_declared",
)

_AUDIT_CATEGORY_DECLARATIONS = (
    "write_attempt_audit_declared",
    "append_set_declaration_audit_declared",
    "rejection_audit_declared",
    "failure_audit_declared",
    "rollback_audit_declared",
    "duplicate_replay_audit_declared",
    "ambiguous_replay_audit_declared",
    "incident_audit_declared",
)

_DETERMINISTIC_APPEND_ORDER = (
    "validate_read_only_prerequisites",
    "bind_operation_refs",
    "declare_append_idempotency_key",
    "declare_before_evidence",
    "declare_mutation_intent_evidence",
    "keep_mutation_execution_unauthorized",
    "declare_after_evidence",
    "declare_audit_event",
    "declare_rejection_failure_rollback_evidence_policies",
    "declare_final_append_set",
    "keep_all_append_execution_unauthorized",
)

_FAILURE_POLICY_DECLARATIONS = (
    "expected_rejection_policy_declared",
    "unexpected_failure_policy_declared",
    "post_mutation_append_failure_policy_declared",
    "rollback_evidence_policy_declared",
    "rollback_failure_incident_class_declared",
)

_IDEMPOTENCY_DECLARATIONS = (
    "append_idempotency_key_binding_required",
    "duplicate_append_same_binding_policy_declared",
    "duplicate_append_different_binding_fail_closed",
    "ambiguous_append_fail_closed",
)

_BOUNDARY_DECLARATIONS = (
    "evidence_service_forbidden",
    "approval_service_forbidden",
    "review_service_forbidden",
    "revision_seal_service_forbidden",
    "db_open_forbidden",
    "db_write_forbidden",
    "repository_uow_import_forbidden",
    "repository_uow_call_forbidden",
    "direct_sql_forbidden",
    "raw_sqlite_forbidden",
    "runtime_allowlist_forbidden",
    "checker_forbidden",
    "executor_forbidden",
    "restore_forbidden",
    "restore_cli_forbidden",
    "schema_migration_forbidden",
    "daemon_server_queue_forbidden",
    "external_network_forbidden",
    "filesystem_side_channel_forbidden",
    "irreversible_action_forbidden",
)

_TRUE_DECLARATION_GROUPS = (
    (_APPEND_PHASE_DECLARATIONS, "append_phase_declaration_invalid"),
    (_EVIDENCE_CATEGORY_DECLARATIONS, "evidence_category_invalid"),
    (_AUDIT_CATEGORY_DECLARATIONS, "audit_category_invalid"),
    (_IDEMPOTENCY_DECLARATIONS, "idempotency_binding_invalid"),
    (_FAILURE_POLICY_DECLARATIONS, "failure_policy_invalid"),
    (_BOUNDARY_DECLARATIONS, "boundary_declaration_invalid"),
)

_AUTHORIZATION_FLAGS = (
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
)

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "contract_surface_invalid",
    "contract_version_invalid",
    "source_read_only_governance_layer_tag_mismatch",
    "source_read_only_governance_layer_commit_mismatch",
    "source_write_side_precondition_checker_tag_mismatch",
    "source_write_side_precondition_checker_commit_mismatch",
    "source_write_side_precondition_ci_tag_mismatch",
    "source_write_side_precondition_ci_commit_mismatch",
    "source_write_side_recovery_spec_only_tag_mismatch",
    "source_write_side_recovery_spec_only_commit_mismatch",
    "source_restore_dry_run_stack_tag_mismatch",
    "source_restore_dry_run_stack_commit_mismatch",
    "source_preflight_stack_tag_mismatch",
    "source_preflight_stack_commit_mismatch",
    "source_execution_authorization_stack_tag_mismatch",
    "source_execution_authorization_stack_commit_mismatch",
    "source_executor_precondition_stack_tag_mismatch",
    "source_executor_precondition_stack_commit_mismatch",
    "source_write_path_stack_tag_mismatch",
    "source_write_path_stack_commit_mismatch",
    "source_repository_uow_allowlist_stack_tag_mismatch",
    "source_repository_uow_allowlist_stack_commit_mismatch",
    "source_evidence_audit_append_contract_spec_only_tag_mismatch",
    "source_evidence_audit_append_contract_spec_only_commit_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "append_phase_declaration_invalid",
    "append_phase_declaration_false",
    "evidence_category_invalid",
    "evidence_category_false",
    "audit_category_invalid",
    "audit_category_false",
    "deterministic_append_order_invalid",
    "idempotency_binding_invalid",
    "idempotency_binding_false",
    "failure_policy_invalid",
    "failure_policy_false",
    "boundary_declaration_invalid",
    "boundary_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
)
_VALIDATOR_FAILURE_TAXONOMY_SET = frozenset(_VALIDATOR_FAILURE_TAXONOMY)

_CONTRACT_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected in _SOURCE_BINDINGS)
    + _OPERATION_REFS
    + ("evidence_ref_set", "audit_ref_set")
    + _APPEND_PHASE_DECLARATIONS
    + _EVIDENCE_CATEGORY_DECLARATIONS
    + _AUDIT_CATEGORY_DECLARATIONS
    + ("deterministic_append_order",)
    + _FAILURE_POLICY_DECLARATIONS
    + _IDEMPOTENCY_DECLARATIONS
    + _BOUNDARY_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + ("json_safe", "append_contract_ready")
)

_APPEND_CONTRACT_OUTPUT_KEYS = (
    (
        "surface",
        "version",
        "append_contract_ready",
        "append_contract_reason_code",
        "append_contract_failures",
    )
    + tuple(name for name, _expected in _SOURCE_BINDINGS)
    + _OPERATION_REFS
    + ("evidence_ref_set", "audit_ref_set")
    + _APPEND_PHASE_DECLARATIONS
    + _EVIDENCE_CATEGORY_DECLARATIONS
    + _AUDIT_CATEGORY_DECLARATIONS
    + ("deterministic_append_order",)
    + _FAILURE_POLICY_DECLARATIONS
    + _IDEMPOTENCY_DECLARATIONS
    + _BOUNDARY_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + ("json_safe",)
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "append_contract",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "append_contract_ready_invalid",
    "append_contract_reason_code_invalid",
    "append_contract_failures_invalid",
    "append_contract_failure_unknown",
    "readiness_reason_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "source_ref_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "append_phase_declaration_invalid",
    "evidence_category_invalid",
    "audit_category_invalid",
    "deterministic_append_order_invalid",
    "idempotency_binding_invalid",
    "failure_policy_invalid",
    "boundary_declaration_invalid",
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
        "evidence_audit_append_contract_validator": _VALIDATOR_TAG,
        "evidence_audit_append_contract_spec_only": (
            _EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_TAG
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
        "write_side_recovery_spec_only": (
            _WRITE_SIDE_RECOVERY_SPEC_ONLY_TAG
        ),
        "write_side_precondition_ci": _WRITE_SIDE_PRECONDITION_CI_TAG,
        "write_side_precondition_checker": (
            _WRITE_SIDE_PRECONDITION_CHECKER_TAG
        ),
        "read_only_governance_layer": _READ_ONLY_GOVERNANCE_LAYER_TAG,
    },
    "appends_evidence": False,
    "appends_audit": False,
    "calls_evidence_service": False,
    "calls_services": False,
    "opens_db": False,
    "calls_repository": False,
    "calls_uow": False,
    "executes_plan": False,
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


def evidence_audit_append_contract_validator_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_evidence_audit_append_contract_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            source_ready=False,
            source_reason_code=_VALIDATOR_REASON_INVALID,
            source_failures=[],
            fields=fields,
        )

    failures: list[str] = []
    if not _keys_match(payload, _PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("append_contract_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    contract = payload.get("contract")

    ready_is_bool = (
        "append_contract_ready" in payload and type(ready_value) is bool
    )
    if "append_contract_ready" in payload and not ready_is_bool:
        _append(failures, "append_contract_ready_invalid")

    reason_is_valid = False
    if "reason_code" in payload:
        if isinstance(reason_value, str):
            reason_is_valid = reason_value in _VALIDATOR_REASON_CODES
        if not reason_is_valid:
            _append(failures, "append_contract_reason_code_invalid")

    source_failures_valid = False
    source_failures_known = False
    if "failures" in payload:
        source_failures_valid = _is_string_list(source_failures)
        if not source_failures_valid:
            _append(failures, "append_contract_failures_invalid")
        else:
            source_failures_known = True
            assert isinstance(source_failures, list)
            for item in source_failures:
                if item not in _VALIDATOR_FAILURE_TAXONOMY_SET:
                    source_failures_known = False
                    _append(failures, "append_contract_failure_unknown")

    if ready_is_bool and reason_is_valid and source_failures_valid:
        assert isinstance(source_failures, list)
        if ready_value is True:
            if reason_value != _REASON_READY or source_failures != []:
                _append(failures, "readiness_reason_mismatch")
        else:
            if reason_value not in (
                _REASON_NOT_READY,
                _VALIDATOR_REASON_INVALID,
            ):
                _append(failures, "readiness_reason_mismatch")
            if source_failures == []:
                _append(failures, "readiness_reason_mismatch")

    if not isinstance(contract, _Mapping):
        if "contract" in payload:
            _append(failures, "contract_not_mapping")
    else:
        _validate_contract(
            contract,
            failures,
            fields,
            ready_value if ready_is_bool else None,
        )

    ordered_failures = _ordered_failures(failures)
    source_ready = ready_value if ready_is_bool else False
    source_reason_code = (
        reason_value if reason_is_valid else _VALIDATOR_REASON_INVALID
    )
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
            source_ready=source_ready,
            source_reason_code=source_reason_code,
            source_failures=safe_source_failures,
            fields=fields,
        )
    if source_ready is True:
        return _result(
            ci_ok=True,
            reason_code=_REASON_READY,
            failures=[],
            source_ready=True,
            source_reason_code=source_reason_code,
            source_failures=[],
            fields=fields,
        )
    return _result(
        ci_ok=False,
        reason_code=_REASON_NOT_READY,
        failures=safe_source_failures,
        source_ready=False,
        source_reason_code=source_reason_code,
        source_failures=safe_source_failures,
        fields=fields,
    )


def _validate_contract(
    contract: _Mapping[object, object],
    failures: list[str],
    fields: dict[str, object],
    source_ready: object,
) -> None:
    if not _keys_match(contract, _CONTRACT_KEYS):
        _append(failures, "contract_shape_mismatch")

    if contract.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "validator_surface_invalid")

    version = contract.get("version")
    if (
        type(version) is not int
        or type(version) is bool
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "validator_version_invalid")

    nested_ready = contract.get("append_contract_ready")
    if type(nested_ready) is not bool:
        _append(failures, "append_contract_ready_invalid")
    elif source_ready is not None and nested_ready != source_ready:
        _append(failures, "readiness_reason_mismatch")

    for field, expected in _SOURCE_BINDINGS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, "source_ref_mismatch")
        else:
            _append(failures, "source_ref_mismatch")

    for field in _OPERATION_REFS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "operation_ref_invalid")

    for field, failure in _REF_SET_FIELDS:
        fields[field] = _validate_ref_set(contract.get(field), failures, failure)

    for group, failure in _TRUE_DECLARATION_GROUPS:
        for field in group:
            candidate = contract.get(field)
            if type(candidate) is not bool:
                fields[field] = None
                _append(failures, failure)
            else:
                fields[field] = candidate
                if candidate is False:
                    _append(failures, failure)

    fields["deterministic_append_order"] = _validate_deterministic_order(
        contract.get("deterministic_append_order"),
        failures,
    )

    for field in _AUTHORIZATION_FLAGS:
        candidate = contract.get(field)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    for field in _RUNTIME_FLAGS:
        candidate = contract.get(field)
        if type(candidate) is not bool:
            _append(failures, "runtime_flag_invalid")
        elif candidate is True:
            _append(failures, "runtime_flag_true")

    json_safe = contract.get("json_safe")
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
    for item in candidate:
        if type(item) is not str or item == "" or item in seen:
            _append(failures, failure)
            return []
        seen.append(item)
    return list(seen)


def _validate_deterministic_order(
    candidate: object,
    failures: list[str],
) -> list[str]:
    if not isinstance(candidate, list):
        _append(failures, "deterministic_append_order_invalid")
        return []
    if len(candidate) != len(_DETERMINISTIC_APPEND_ORDER):
        _append(failures, "deterministic_append_order_invalid")
        return []
    for index, expected in enumerate(_DETERMINISTIC_APPEND_ORDER):
        actual = candidate[index]
        if not isinstance(actual, str) or actual != expected:
            _append(failures, "deterministic_append_order_invalid")
            return []
    return list(_DETERMINISTIC_APPEND_ORDER)


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    source_ready: bool,
    source_reason_code: str,
    source_failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["append_contract"] = _append_contract_output(
        source_ready=source_ready,
        source_reason_code=source_reason_code,
        source_failures=source_failures,
        fields=fields,
    )
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _append_contract_output(
    *,
    source_ready: bool,
    source_reason_code: str,
    source_failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    output["append_contract_ready"] = source_ready
    output["append_contract_reason_code"] = source_reason_code
    output["append_contract_failures"] = list(source_failures)
    for field, _expected in _SOURCE_BINDINGS:
        output[field] = fields[field]
    for field in _OPERATION_REFS:
        output[field] = fields[field]
    for field, _failure in _REF_SET_FIELDS:
        output[field] = _deepcopy(fields[field])
    for field in _APPEND_PHASE_DECLARATIONS:
        output[field] = fields[field]
    for field in _EVIDENCE_CATEGORY_DECLARATIONS:
        output[field] = fields[field]
    for field in _AUDIT_CATEGORY_DECLARATIONS:
        output[field] = fields[field]
    output["deterministic_append_order"] = _deepcopy(
        fields["deterministic_append_order"]
    )
    for field in _FAILURE_POLICY_DECLARATIONS:
        output[field] = fields[field]
    for field in _IDEMPOTENCY_DECLARATIONS:
        output[field] = fields[field]
    for field in _BOUNDARY_DECLARATIONS:
        output[field] = fields[field]
    for field in _AUTHORIZATION_FLAGS:
        output[field] = False
    for field in _RUNTIME_FLAGS:
        output[field] = False
    output["json_safe"] = True
    assert tuple(output.keys()) == _APPEND_CONTRACT_OUTPUT_KEYS
    return output


def _empty_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for field, _expected in _SOURCE_BINDINGS:
        fields[field] = None
    for field in _OPERATION_REFS:
        fields[field] = None
    for field, _failure in _REF_SET_FIELDS:
        fields[field] = []
    for group, _failure in _TRUE_DECLARATION_GROUPS:
        for field in group:
            fields[field] = None
    fields["deterministic_append_order"] = []
    return fields


def _keys_match(candidate: _Mapping[object, object], keys: tuple[str, ...]) -> bool:
    try:
        return set(candidate.keys()) == set(keys)
    except TypeError:
        return False


def _is_string_list(candidate: object) -> bool:
    if not isinstance(candidate, list):
        return False
    for item in candidate:
        if not isinstance(item, str):
            return False
    return True


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
