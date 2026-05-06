"""Pure validator for already-rendered EvidenceAuditAppendContractV1 declarations."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "evidence_audit_append_contract_validator_manifest",
    "validate_evidence_audit_append_contract",
]


_SURFACE = "evidence_audit_append_contract_validator"
_CONTRACT_SURFACE = "EvidenceAuditAppendContractV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_evidence_audit_append_contract"

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

_REASON_INVALID = "invalid_contract_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_INPUT_KEYS = ("evidence_audit_append_contract",)

_SOURCE_BINDINGS = (
    (
        "source_read_only_governance_layer_tag",
        _READ_ONLY_GOVERNANCE_LAYER_TAG,
        "source_read_only_governance_layer_tag_mismatch",
    ),
    (
        "source_read_only_governance_layer_commit",
        _READ_ONLY_GOVERNANCE_LAYER_COMMIT,
        "source_read_only_governance_layer_commit_mismatch",
    ),
    (
        "source_write_side_precondition_checker_tag",
        _WRITE_SIDE_PRECONDITION_CHECKER_TAG,
        "source_write_side_precondition_checker_tag_mismatch",
    ),
    (
        "source_write_side_precondition_checker_commit",
        _WRITE_SIDE_PRECONDITION_CHECKER_COMMIT,
        "source_write_side_precondition_checker_commit_mismatch",
    ),
    (
        "source_write_side_precondition_ci_tag",
        _WRITE_SIDE_PRECONDITION_CI_TAG,
        "source_write_side_precondition_ci_tag_mismatch",
    ),
    (
        "source_write_side_precondition_ci_commit",
        _WRITE_SIDE_PRECONDITION_CI_COMMIT,
        "source_write_side_precondition_ci_commit_mismatch",
    ),
    (
        "source_write_side_recovery_spec_only_tag",
        _WRITE_SIDE_RECOVERY_SPEC_ONLY_TAG,
        "source_write_side_recovery_spec_only_tag_mismatch",
    ),
    (
        "source_write_side_recovery_spec_only_commit",
        _WRITE_SIDE_RECOVERY_SPEC_ONLY_COMMIT,
        "source_write_side_recovery_spec_only_commit_mismatch",
    ),
    (
        "source_restore_dry_run_read_only_stack_tag",
        _RESTORE_DRY_RUN_READ_ONLY_STACK_TAG,
        "source_restore_dry_run_stack_tag_mismatch",
    ),
    (
        "source_restore_dry_run_read_only_stack_commit",
        _RESTORE_DRY_RUN_READ_ONLY_STACK_COMMIT,
        "source_restore_dry_run_stack_commit_mismatch",
    ),
    (
        "source_preflight_read_only_stack_tag",
        _PREFLIGHT_READ_ONLY_STACK_TAG,
        "source_preflight_stack_tag_mismatch",
    ),
    (
        "source_preflight_read_only_stack_commit",
        _PREFLIGHT_READ_ONLY_STACK_COMMIT,
        "source_preflight_stack_commit_mismatch",
    ),
    (
        "source_execution_authorization_read_only_stack_tag",
        _EXECUTION_AUTHORIZATION_READ_ONLY_STACK_TAG,
        "source_execution_authorization_stack_tag_mismatch",
    ),
    (
        "source_execution_authorization_read_only_stack_commit",
        _EXECUTION_AUTHORIZATION_READ_ONLY_STACK_COMMIT,
        "source_execution_authorization_stack_commit_mismatch",
    ),
    (
        "source_executor_precondition_read_only_stack_tag",
        _EXECUTOR_PRECONDITION_READ_ONLY_STACK_TAG,
        "source_executor_precondition_stack_tag_mismatch",
    ),
    (
        "source_executor_precondition_read_only_stack_commit",
        _EXECUTOR_PRECONDITION_READ_ONLY_STACK_COMMIT,
        "source_executor_precondition_stack_commit_mismatch",
    ),
    (
        "source_write_path_read_only_stack_tag",
        _WRITE_PATH_READ_ONLY_STACK_TAG,
        "source_write_path_stack_tag_mismatch",
    ),
    (
        "source_write_path_read_only_stack_commit",
        _WRITE_PATH_READ_ONLY_STACK_COMMIT,
        "source_write_path_stack_commit_mismatch",
    ),
    (
        "source_repository_uow_allowlist_read_only_stack_tag",
        _REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_TAG,
        "source_repository_uow_allowlist_stack_tag_mismatch",
    ),
    (
        "source_repository_uow_allowlist_read_only_stack_commit",
        _REPOSITORY_UOW_ALLOWLIST_READ_ONLY_STACK_COMMIT,
        "source_repository_uow_allowlist_stack_commit_mismatch",
    ),
    (
        "source_evidence_audit_append_contract_spec_only_tag",
        _EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_TAG,
        "source_evidence_audit_append_contract_spec_only_tag_mismatch",
    ),
    (
        "source_evidence_audit_append_contract_spec_only_commit",
        _EVIDENCE_AUDIT_APPEND_CONTRACT_SPEC_ONLY_COMMIT,
        "source_evidence_audit_append_contract_spec_only_commit_mismatch",
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

_EVIDENCE_REF_SET_FIELD = "evidence_ref_set"
_AUDIT_REF_SET_FIELD = "audit_ref_set"

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

_DETERMINISTIC_APPEND_ORDER_FIELD = "deterministic_append_order"
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

_JSON_SAFE_FIELD = "json_safe"

_BOOL_DECLARATION_GROUPS = (
    (_APPEND_PHASE_DECLARATIONS, "append_phase_declaration_invalid", "append_phase_declaration_false"),
    (_EVIDENCE_CATEGORY_DECLARATIONS, "evidence_category_invalid", "evidence_category_false"),
    (_AUDIT_CATEGORY_DECLARATIONS, "audit_category_invalid", "audit_category_false"),
    (_FAILURE_POLICY_DECLARATIONS, "failure_policy_invalid", "failure_policy_false"),
    (_IDEMPOTENCY_DECLARATIONS, "idempotency_binding_invalid", "idempotency_binding_false"),
    (_BOUNDARY_DECLARATIONS, "boundary_declaration_invalid", "boundary_declaration_false"),
)

_CONTRACT_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + _OPERATION_REFS
    + (_EVIDENCE_REF_SET_FIELD, _AUDIT_REF_SET_FIELD)
    + _APPEND_PHASE_DECLARATIONS
    + _EVIDENCE_CATEGORY_DECLARATIONS
    + _AUDIT_CATEGORY_DECLARATIONS
    + (_DETERMINISTIC_APPEND_ORDER_FIELD,)
    + _FAILURE_POLICY_DECLARATIONS
    + _IDEMPOTENCY_DECLARATIONS
    + _BOUNDARY_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + (_JSON_SAFE_FIELD,)
)

_OUTPUT_KEYS = (
    "append_contract_ready",
    "reason_code",
    "failures",
    "contract",
)

_CONTRACT_OUTPUT_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + _OPERATION_REFS
    + (_EVIDENCE_REF_SET_FIELD, _AUDIT_REF_SET_FIELD)
    + _APPEND_PHASE_DECLARATIONS
    + _EVIDENCE_CATEGORY_DECLARATIONS
    + _AUDIT_CATEGORY_DECLARATIONS
    + (_DETERMINISTIC_APPEND_ORDER_FIELD,)
    + _FAILURE_POLICY_DECLARATIONS
    + _IDEMPOTENCY_DECLARATIONS
    + _BOUNDARY_DECLARATIONS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + (_JSON_SAFE_FIELD, "append_contract_ready")
)

_FAILURE_ORDER = (
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

_STRUCTURAL_FAILURES = frozenset(
    {
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
    }
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
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


def evidence_audit_append_contract_validator_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def validate_evidence_audit_append_contract(payload: object) -> dict[str, object]:
    fields = _empty_contract_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            ready=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    contract = payload.get("evidence_audit_append_contract")
    _validate_contract(contract, failures, fields)

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


def _validate_contract(
    contract: object,
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if not isinstance(contract, _Mapping):
        _append(failures, "contract_not_mapping")
        return

    if set(contract.keys()) != set(_CONTRACT_KEYS):
        _append(failures, "contract_shape_mismatch")

    if contract.get("surface") != _CONTRACT_SURFACE:
        _append(failures, "contract_surface_invalid")

    version = contract.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "contract_version_invalid")

    for field, expected, failure in _SOURCE_BINDINGS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, failure)
        else:
            _append(failures, failure)

    for field in _OPERATION_REFS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "operation_ref_invalid")

    fields[_EVIDENCE_REF_SET_FIELD] = _validate_ref_set(
        contract.get(_EVIDENCE_REF_SET_FIELD),
        failures,
        "evidence_ref_set_invalid",
    )
    fields[_AUDIT_REF_SET_FIELD] = _validate_ref_set(
        contract.get(_AUDIT_REF_SET_FIELD),
        failures,
        "audit_ref_set_invalid",
    )

    for group, invalid_failure, false_failure in _BOOL_DECLARATION_GROUPS:
        for field in group:
            candidate = contract.get(field)
            if type(candidate) is not bool:
                fields[field] = None
                _append(failures, invalid_failure)
            else:
                fields[field] = candidate
                if candidate is False:
                    _append(failures, false_failure)

    fields[_DETERMINISTIC_APPEND_ORDER_FIELD] = _validate_deterministic_order(
        contract.get(_DETERMINISTIC_APPEND_ORDER_FIELD),
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

    json_safe = contract.get(_JSON_SAFE_FIELD)
    if type(json_safe) is not bool:
        fields[_JSON_SAFE_FIELD] = None
        _append(failures, "json_safe_invalid")
    else:
        fields[_JSON_SAFE_FIELD] = json_safe
        if json_safe is False:
            _append(failures, "json_safe_invalid")


def _validate_ref_set(
    candidate: object,
    failures: list[str],
    failure: str,
) -> list[str]:
    if not isinstance(candidate, list):
        _append(failures, failure)
        return []
    if candidate == []:
        _append(failures, failure)
        return []
    seen: list[str] = []
    invalid = False
    for item in candidate:
        if type(item) is bool:
            invalid = True
            continue
        if not isinstance(item, str) or item == "":
            invalid = True
            continue
        if item in seen:
            invalid = True
            continue
        seen.append(item)
    if invalid:
        _append(failures, failure)
        return []
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
    ready: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["append_contract_ready"] = ready
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["contract"] = _contract_output(fields, ready)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _contract_output(
    fields: dict[str, object],
    ready: bool,
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for name, _expected, _failure in _SOURCE_BINDINGS:
        output[name] = fields[name]
    for name in _OPERATION_REFS:
        output[name] = fields[name]
    output[_EVIDENCE_REF_SET_FIELD] = _deepcopy(fields[_EVIDENCE_REF_SET_FIELD])
    output[_AUDIT_REF_SET_FIELD] = _deepcopy(fields[_AUDIT_REF_SET_FIELD])
    for name in _APPEND_PHASE_DECLARATIONS:
        output[name] = fields[name]
    for name in _EVIDENCE_CATEGORY_DECLARATIONS:
        output[name] = fields[name]
    for name in _AUDIT_CATEGORY_DECLARATIONS:
        output[name] = fields[name]
    output[_DETERMINISTIC_APPEND_ORDER_FIELD] = _deepcopy(
        fields[_DETERMINISTIC_APPEND_ORDER_FIELD]
    )
    for name in _FAILURE_POLICY_DECLARATIONS:
        output[name] = fields[name]
    for name in _IDEMPOTENCY_DECLARATIONS:
        output[name] = fields[name]
    for name in _BOUNDARY_DECLARATIONS:
        output[name] = fields[name]
    for name in _AUTHORIZATION_FLAGS:
        output[name] = False
    for name in _RUNTIME_FLAGS:
        output[name] = False
    output[_JSON_SAFE_FIELD] = True
    output["append_contract_ready"] = ready
    assert tuple(output.keys()) == _CONTRACT_OUTPUT_KEYS
    return output


def _empty_contract_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, _expected, _failure in _SOURCE_BINDINGS:
        fields[name] = None
    for name in _OPERATION_REFS:
        fields[name] = None
    fields[_EVIDENCE_REF_SET_FIELD] = []
    fields[_AUDIT_REF_SET_FIELD] = []
    for group, _invalid, _false in _BOOL_DECLARATION_GROUPS:
        for name in group:
            fields[name] = None
    fields[_DETERMINISTIC_APPEND_ORDER_FIELD] = []
    fields[_JSON_SAFE_FIELD] = None
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
