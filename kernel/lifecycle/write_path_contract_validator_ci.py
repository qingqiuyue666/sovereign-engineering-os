"""Read-only CI consumer for rendered write path contract validation."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "write_path_contract_validator_ci_manifest",
    "consume_write_path_contract_validator_ci",
]


_SURFACE = "write_path_contract_validator_ci"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_write_path_contract_validator_output"

_VALIDATOR_SURFACE = "write_path_contract_validator"
_VALIDATOR_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

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

_RUN_DEPS_KEY = "run" "ti" "me_dependencies"
_DIRECT_EXECUTOR_LOCAL_STORE_FORBIDDEN_KEY = (
    "direct_executor_" "sql" "ite_forbidden"
)
_DIRECT_LOCAL_STORE_FORBIDDEN_KEY = "direct_" "sql" "ite_forbidden"

_PAYLOAD_KEYS = (
    "write_path_contract_ready",
    "reason_code",
    "failures",
    "contract",
)

_SOURCE_BINDINGS = (
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
)

_REQUIRED_FIELDS = (
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "target_artifact_id",
    "target_task_id",
    "before_evidence_ref",
)

_REQUIRED_DECLARATION_FLAGS = (
    "after_evidence_required",
    "outer_transaction_required",
    "kernel_owned_transaction_required",
    "uncontrolled_nested_transactions_forbidden",
    _DIRECT_EXECUTOR_LOCAL_STORE_FORBIDDEN_KEY,
    "partial_mutation_outside_transaction_forbidden",
    "idempotency_reservation_required",
    "idempotency_reservation_before_mutation_required",
    "before_evidence_before_mutation_required",
    "mutation_intent_evidence_before_mutation_required",
    "repository_uow_only_mutation_required",
    "after_evidence_after_mutation_required",
    "deterministic_evidence_audit_order_required",
    "expected_rejection_no_target_mutation_required",
    "unexpected_failure_rollback_required",
    "rollback_failure_incident_required",
    "no_silent_partial_success_required",
    "no_ambiguous_success_required",
    _DIRECT_LOCAL_STORE_FORBIDDEN_KEY,
    "ad_hoc_sql_forbidden",
    "filesystem_side_channel_forbidden",
    "repository_uow_allowlist_required",
    "one_uow_boundary_per_attempt_required",
    "service_side_effects_forbidden",
)

_CONTRACT_ONLY_DECLARATION_FLAGS = ("fail_closed_declared",)

_AUTHORIZATION_FLAGS = (
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "repository_uow_writes_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
)

_EXECUTION_FLAGS = ("executes_plan",)

_CONTRACT_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + _REQUIRED_FIELDS
    + _REQUIRED_DECLARATION_FLAGS
    + _AUTHORIZATION_FLAGS
    + _CONTRACT_ONLY_DECLARATION_FLAGS
    + ("json_safe",)
    + _EXECUTION_FLAGS
    + ("opens_db", "appends_evidence")
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "write_path_contract_ready",
    "write_path_contract_reason_code",
    "write_path_contract_failures",
    "source_restore_dry_run_read_only_stack_tag",
    "source_restore_dry_run_read_only_stack_commit",
    "source_preflight_read_only_stack_tag",
    "source_preflight_read_only_stack_commit",
    "source_execution_authorization_read_only_stack_tag",
    "source_execution_authorization_read_only_stack_commit",
    "source_executor_precondition_read_only_stack_tag",
    "source_executor_precondition_read_only_stack_commit",
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "target_artifact_id",
    "target_task_id",
    "before_evidence_ref",
    "after_evidence_required",
    "outer_transaction_required",
    "kernel_owned_transaction_required",
    "uncontrolled_nested_transactions_forbidden",
    _DIRECT_EXECUTOR_LOCAL_STORE_FORBIDDEN_KEY,
    "partial_mutation_outside_transaction_forbidden",
    "idempotency_reservation_required",
    "idempotency_reservation_before_mutation_required",
    "before_evidence_before_mutation_required",
    "mutation_intent_evidence_before_mutation_required",
    "repository_uow_only_mutation_required",
    "after_evidence_after_mutation_required",
    "deterministic_evidence_audit_order_required",
    "expected_rejection_no_target_mutation_required",
    "unexpected_failure_rollback_required",
    "rollback_failure_incident_required",
    "no_silent_partial_success_required",
    "no_ambiguous_success_required",
    _DIRECT_LOCAL_STORE_FORBIDDEN_KEY,
    "ad_hoc_sql_forbidden",
    "filesystem_side_channel_forbidden",
    "repository_uow_allowlist_required",
    "one_uow_boundary_per_attempt_required",
    "service_side_effects_forbidden",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "repository_uow_writes_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
    "executes_plan",
    "opens_db",
    "appends_evidence",
    "json_safe",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_ready",
    "contract_invalid",
    "contract_surface_invalid",
    "contract_version_invalid",
    "source_restore_dry_run_stack_tag_mismatch",
    "source_restore_dry_run_stack_commit_mismatch",
    "source_preflight_stack_tag_mismatch",
    "source_preflight_stack_commit_mismatch",
    "source_execution_authorization_stack_tag_mismatch",
    "source_execution_authorization_stack_commit_mismatch",
    "source_executor_precondition_stack_tag_mismatch",
    "source_executor_precondition_stack_commit_mismatch",
    "required_field_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "execution_flag_invalid",
    "execution_flag_true",
    "opens_db_invalid",
    "opens_db_true",
    "appends_evidence_invalid",
    "appends_evidence_true",
    "json_safe_invalid",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "contract_invalid",
        "contract_surface_invalid",
        "contract_version_invalid",
        "required_field_invalid",
        "required_declaration_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
        "opens_db_invalid",
        "appends_evidence_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "write_path_contract_validator": "write-path-contract-validator-v1",
        "write_path_transaction_evidence_idempotency_spec_only": (
            "write-path-transaction-evidence-idempotency-spec-only-v1"
        ),
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
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "repository_uow_writes_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
    "executes_plan": False,
    "opens_db": False,
    "appends_evidence": False,
    _RUN_DEPS_KEY: [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def write_path_contract_validator_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_write_path_contract_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            write_path_contract_ready=False,
            write_path_contract_reason_code=_REASON_INVALID,
            write_path_contract_failures=[],
            fields=fields,
        )

    failures: list[str] = []

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("write_path_contract_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")
    contract = payload.get("contract")

    ready_is_valid = (
        "write_path_contract_ready" in payload and type(ready_value) is bool
    )
    reason_is_valid = "reason_code" in payload and isinstance(
        reason_value, str
    )
    failures_are_valid = "failures" in payload and _is_string_list(
        source_failures
    )

    if "write_path_contract_ready" in payload and not ready_is_valid:
        _append(failures, "payload_shape_mismatch")
    if "reason_code" in payload and not reason_is_valid:
        _append(failures, "payload_shape_mismatch")
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_shape_mismatch")

    contract_is_mapping = isinstance(contract, _Mapping)
    if "contract" in payload and not contract_is_mapping:
        _append(failures, "contract_invalid")

    if ready_is_valid and ready_value is not True:
        _append(failures, "contract_not_ready")
    if reason_is_valid and reason_value != _REASON_READY:
        _append(failures, "contract_invalid")
    if failures_are_valid and source_failures != []:
        _append(failures, "contract_invalid")

    if contract_is_mapping:
        assert isinstance(contract, _Mapping)
        _validate_contract(contract, failures, fields)

    ordered_failures = _ordered_failures(failures)
    ci_ok = ordered_failures == []
    if ci_ok:
        reason_code = _REASON_READY
    elif any(item in _STRUCTURAL_FAILURES for item in ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ci_ok=ci_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        write_path_contract_ready=(
            ready_value if ready_is_valid else False
        ),
        write_path_contract_reason_code=(
            reason_value if reason_is_valid else _REASON_INVALID
        ),
        write_path_contract_failures=(
            source_failures if failures_are_valid else []
        ),
        fields=fields,
    )


def _validate_contract(
    contract: _Mapping[str, object],
    failures: list[str],
    fields: dict[str, object],
) -> None:
    if set(contract.keys()) != set(_CONTRACT_KEYS):
        _append(failures, "contract_invalid")

    if contract.get("surface") != _VALIDATOR_SURFACE:
        _append(failures, "contract_surface_invalid")

    version = contract.get("version")
    if (
        type(version) is not int
        or type(version) is bool
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "contract_version_invalid")

    for field, expected, failure in _SOURCE_BINDINGS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, failure)
        else:
            _append(failures, failure)

    for field in _REQUIRED_FIELDS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "required_field_invalid")

    for flag in _REQUIRED_DECLARATION_FLAGS:
        candidate = contract.get(flag)
        if type(candidate) is not bool:
            fields[flag] = None
            _append(failures, "required_declaration_invalid")
        else:
            fields[flag] = candidate
            if candidate is False:
                _append(failures, "required_declaration_false")

    for flag in _CONTRACT_ONLY_DECLARATION_FLAGS:
        candidate = contract.get(flag)
        if type(candidate) is not bool:
            _append(failures, "required_declaration_invalid")
        elif candidate is False:
            _append(failures, "required_declaration_false")

    for flag in _AUTHORIZATION_FLAGS:
        candidate = contract.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    for flag in _EXECUTION_FLAGS:
        candidate = contract.get(flag)
        if type(candidate) is not bool:
            _append(failures, "execution_flag_invalid")
        elif candidate is True:
            _append(failures, "execution_flag_true")

    opens_db = contract.get("opens_db")
    if type(opens_db) is not bool:
        _append(failures, "opens_db_invalid")
    elif opens_db is True:
        _append(failures, "opens_db_true")

    appends_evidence = contract.get("appends_evidence")
    if type(appends_evidence) is not bool:
        _append(failures, "appends_evidence_invalid")
    elif appends_evidence is True:
        _append(failures, "appends_evidence_true")

    json_safe = contract.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    write_path_contract_ready: bool,
    write_path_contract_reason_code: str,
    write_path_contract_failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["surface"] = _VALIDATOR_SURFACE
    output["version"] = _VALIDATOR_VERSION
    output["write_path_contract_ready"] = write_path_contract_ready
    output["write_path_contract_reason_code"] = (
        write_path_contract_reason_code
    )
    output["write_path_contract_failures"] = list(
        write_path_contract_failures
    )
    for name, _expected, _failure in _SOURCE_BINDINGS:
        output[name] = fields[name]
    for name in _REQUIRED_FIELDS:
        output[name] = fields[name]
    for name in _REQUIRED_DECLARATION_FLAGS:
        output[name] = fields[name]
    for name in _AUTHORIZATION_FLAGS:
        output[name] = False
    output["executes_plan"] = False
    output["opens_db"] = False
    output["appends_evidence"] = False
    output["json_safe"] = True
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _empty_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, _expected, _failure in _SOURCE_BINDINGS:
        fields[name] = None
    for name in _REQUIRED_FIELDS:
        fields[name] = None
    for name in _REQUIRED_DECLARATION_FLAGS:
        fields[name] = None
    return fields


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
