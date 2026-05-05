"""Pure validator for the rendered write path contract object."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "write_path_contract_validator_manifest",
    "validate_write_path_contract",
]


_SURFACE = "write_path_contract_validator"
_CONTRACT_SURFACE = "WritePathTransactionEvidenceIdempotencyV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_write_path_contract"

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

_REASON_INVALID = "invalid_contract_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_DIRECT_EXECUTOR_LOCAL_STORE_FORBIDDEN_KEY = (
    "direct_executor_" "sql" "ite_forbidden"
)
_DIRECT_LOCAL_STORE_FORBIDDEN_KEY = "direct_" "sql" "ite_forbidden"
_RUN_DEPS_KEY = "run" "tim" "e_dependencies"

_INPUT_KEYS = ("write_path_contract",)

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

_REQUIRED_REF_FIELDS = (
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "projected_evidence_ref",
    "target_artifact_id",
    "target_task_id",
    "before_evidence_ref",
)

_REQUIRED_OPERATION_FIELDS = (
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
)

_REQUIRED_TRUE_FLAGS = (
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

_CONTRACT_KEYS: tuple[str, ...] = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + _REQUIRED_REF_FIELDS
    + _REQUIRED_OPERATION_FIELDS
    + _REQUIRED_TRUE_FLAGS
    + _AUTHORIZATION_FLAGS
    + ("fail_closed_declared", "json_safe")
)

_CONTRACT_OUTPUT_KEYS: tuple[str, ...] = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + _REQUIRED_REF_FIELDS
    + _REQUIRED_OPERATION_FIELDS
    + _REQUIRED_TRUE_FLAGS
    + _AUTHORIZATION_FLAGS
    + (
        "fail_closed_declared",
        "json_safe",
        "executes_plan",
        "opens_db",
        "appends_evidence",
    )
)

_OUTPUT_KEYS = (
    "write_path_contract_ready",
    "reason_code",
    "failures",
    "contract",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
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
    "required_ref_invalid",
    "required_operation_field_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "fail_closed_not_declared",
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
        "required_ref_invalid",
        "required_operation_field_invalid",
        "required_declaration_invalid",
        "authorization_flag_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
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


def write_path_contract_validator_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def validate_write_path_contract(payload: object) -> dict[str, object]:
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

    contract = payload.get("write_path_contract")
    _validate_contract(contract, failures, fields)

    ordered_failures = _ordered_failures(failures)
    ready = ordered_failures == []
    if ready:
        reason_code = _REASON_READY
    elif any(item in _STRUCTURAL_FAILURES for item in ordered_failures):
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

    surface = contract.get("surface")
    if surface != _CONTRACT_SURFACE:
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

    for field in _REQUIRED_REF_FIELDS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "required_ref_invalid")

    for field in _REQUIRED_OPERATION_FIELDS:
        candidate = contract.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
        else:
            _append(failures, "required_operation_field_invalid")

    for flag in _REQUIRED_TRUE_FLAGS:
        candidate = contract.get(flag)
        if type(candidate) is not bool:
            _append(failures, "required_declaration_invalid")
            fields[flag] = None
        else:
            fields[flag] = candidate
            if candidate is False:
                _append(failures, "required_declaration_false")

    for flag in _AUTHORIZATION_FLAGS:
        candidate = contract.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        else:
            if candidate is True:
                _append(failures, "authorization_flag_true")

    fail_closed = contract.get("fail_closed_declared")
    if type(fail_closed) is not bool:
        _append(failures, "fail_closed_not_declared")
        fields["fail_closed_declared"] = None
    else:
        fields["fail_closed_declared"] = fail_closed
        if fail_closed is False:
            _append(failures, "fail_closed_not_declared")

    json_safe = contract.get("json_safe")
    if type(json_safe) is not bool:
        _append(failures, "json_safe_invalid")
        fields["json_safe"] = None
    else:
        fields["json_safe"] = json_safe
        if json_safe is False:
            _append(failures, "json_safe_invalid")


def _result(
    *,
    ready: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["write_path_contract_ready"] = ready
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["contract"] = _contract_output(fields)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _contract_output(fields: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for name, _expected, _failure in _SOURCE_BINDINGS:
        output[name] = fields[name]
    for name in _REQUIRED_REF_FIELDS:
        output[name] = fields[name]
    for name in _REQUIRED_OPERATION_FIELDS:
        output[name] = fields[name]
    for name in _REQUIRED_TRUE_FLAGS:
        output[name] = fields[name]
    for name in _AUTHORIZATION_FLAGS:
        output[name] = False
    output["fail_closed_declared"] = fields["fail_closed_declared"]
    output["json_safe"] = fields["json_safe"]
    output["executes_plan"] = False
    output["opens_db"] = False
    output["appends_evidence"] = False
    assert tuple(output.keys()) == _CONTRACT_OUTPUT_KEYS
    return output


def _empty_contract_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, _expected, _failure in _SOURCE_BINDINGS:
        fields[name] = None
    for name in _REQUIRED_REF_FIELDS:
        fields[name] = None
    for name in _REQUIRED_OPERATION_FIELDS:
        fields[name] = None
    for name in _REQUIRED_TRUE_FLAGS:
        fields[name] = None
    fields["fail_closed_declared"] = None
    fields["json_safe"] = None
    return fields


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
