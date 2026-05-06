"""Read-only CI consumer for already-rendered repository/UoW allowlist validator output."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "repository_uow_allowlist_validator_ci_manifest",
    "consume_repository_uow_allowlist_validator_ci",
]


_SURFACE = "repository_uow_allowlist_validator_ci"
_VERSION = 1
_INPUT_SHAPE = (
    "already_rendered_repository_uow_allowlist_validator_output"
)

_VALIDATOR_SURFACE = "repository_uow_allowlist_validator"
_VALIDATOR_VERSION = 1

_VALIDATOR_TAG = "repository-uow-allowlist-validator-v1"
_SPEC_ONLY_TAG = "repository-uow-allowlist-spec-only-v1"

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
_WRITE_SIDE_RECOVERY_SPEC_ONLY_TAG = (
    "write-side-recovery-spec-only-v1"
)
_WRITE_SIDE_RECOVERY_SPEC_ONLY_COMMIT = (
    "ad560cc2dab135f2c1d56d948410ae47586d118e"
)
_RESTORE_DRY_RUN_READ_ONLY_STACK_TAG = (
    "restore-dry-run-read-only-stack-v1"
)
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

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_VALIDATOR_REASON_INVALID = "invalid_allowlist_payload"
_VALIDATOR_REASON_NOT_READY = "not_ready"
_VALIDATOR_REASON_READY = "ready"


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
)

_ENTRY_COUNT_FIELDS = (
    "allowlist_entry_count",
    "read_only_entry_count",
    "mutation_declared_but_not_authorized_entry_count",
    "future_write_candidate_entry_count",
)

_REQUIRED_TRUE_FLAGS = (
    "direct_sql_forbidden",
    "raw_sqlite_forbidden",
    "ad_hoc_sql_forbidden",
    "raw_connection_forbidden",
    "runtime_method_introspection_forbidden",
    "wildcard_methods_forbidden",
    "dynamic_method_resolution_forbidden",
    "class_level_allow_forbidden",
    "module_level_allow_forbidden",
    "private_internal_methods_forbidden_unless_named",
    "filesystem_side_channels_forbidden",
    "external_network_forbidden",
    "services_forbidden",
    "schema_migration_forbidden",
    "db_repair_forbidden",
    "restore_recovery_orchestrator_forbidden",
    "evidence_audit_append_forbidden",
    "exactly_one_kernel_owned_uow_boundary_required",
    "executor_transaction_ownership_forbidden",
    "uncontrolled_nested_uow_forbidden",
    "long_lived_uow_forbidden",
    "daemon_queue_crossing_uow_forbidden",
    "fail_closed_declared",
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
    "direct_db_writes_authorized",
    "raw_sqlite_authorized",
    "ad_hoc_sql_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "evidence_service_authorized",
    "filesystem_side_effects_authorized",
    "external_network_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
)

_RUNTIME_FLAGS = (
    "opens_db",
    "calls_repository",
    "calls_uow",
    "calls_services",
    "appends_evidence",
    "executes_plan",
)

_INPUT_KEYS = (
    (
        "allowlist_ready",
        "reason_code",
        "failures",
        "surface",
        "version",
    )
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + _ENTRY_COUNT_FIELDS
    + _REQUIRED_TRUE_FLAGS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + ("json_safe",)
)

_OUTPUT_KEYS = (
    (
        "ci_ok",
        "reason_code",
        "failures",
        "surface",
        "version",
    )
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + (
        "allowlist_ready",
        "allowlist_reason_code",
        "allowlist_failures",
    )
    + _ENTRY_COUNT_FIELDS
    + _REQUIRED_TRUE_FLAGS
    + _AUTHORIZATION_FLAGS
    + _RUNTIME_FLAGS
    + ("json_safe",)
)


_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "allowlist_not_mapping",
    "allowlist_shape_mismatch",
    "allowlist_surface_invalid",
    "allowlist_version_invalid",
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
    "source_repository_uow_allowlist_spec_tag_mismatch",
    "source_repository_uow_allowlist_spec_commit_mismatch",
    "allowlist_entries_invalid",
    "allowlist_entry_not_mapping",
    "allowlist_entry_shape_mismatch",
    "allowlist_entry_method_forbidden",
    "repository_class_invalid",
    "method_name_invalid",
    "method_owner_invalid",
    "read_write_classification_invalid",
    "entry_authorization_flag_invalid",
    "entry_authorization_flag_true",
    "required_uow_context_invalid",
    "required_transaction_owner_invalid",
    "required_idempotency_binding_invalid",
    "required_idempotency_binding_false",
    "required_evidence_output_fields_invalid",
    "required_mutation_summary_fields_invalid",
    "rollback_behavior_invalid",
    "allowed_failure_modes_invalid",
    "forbidden_side_effects_invalid",
    "json_safe_result_required_invalid",
    "json_safe_result_required_false",
    "entry_required_declaration_invalid",
    "entry_required_declaration_false",
    "allowlist_entry_duplicate",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

_VALIDATOR_FAILURE_TAXONOMY_SET = frozenset(_VALIDATOR_FAILURE_TAXONOMY)

_VALIDATOR_REASON_CODES = frozenset(
    {
        _VALIDATOR_REASON_READY,
        _VALIDATOR_REASON_NOT_READY,
        _VALIDATOR_REASON_INVALID,
    }
)


_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "allowlist_not_ready",
    "allowlist_reason_code_invalid",
    "allowlist_failures_invalid",
    "allowlist_failure_value_invalid",
    "validator_surface_invalid",
    "validator_version_invalid",
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
    "entry_count_invalid",
    "entry_count_mismatch",
    "required_declaration_invalid",
    "required_declaration_false",
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
        "allowlist_reason_code_invalid",
        "allowlist_failures_invalid",
        "allowlist_failure_value_invalid",
        "validator_surface_invalid",
        "validator_version_invalid",
        "entry_count_invalid",
        "required_declaration_invalid",
        "authorization_flag_invalid",
        "runtime_flag_invalid",
        "json_safe_invalid",
    }
)


_RUN_DEPS_KEY = "run" "ti" "me_dependencies"


_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "repository_uow_allowlist_validator": _VALIDATOR_TAG,
        "repository_uow_allowlist_spec_only": _SPEC_ONLY_TAG,
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
    "opens_db": False,
    "calls_repository": False,
    "calls_uow": False,
    "calls_services": False,
    "appends_evidence": False,
    "executes_plan": False,
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "repository_uow_writes_authorized": False,
    "direct_db_writes_authorized": False,
    "raw_sqlite_authorized": False,
    "ad_hoc_sql_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "approval_service_authorized": False,
    "review_service_authorized": False,
    "revision_seal_service_authorized": False,
    "evidence_service_authorized": False,
    "filesystem_side_effects_authorized": False,
    "external_network_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
    _RUN_DEPS_KEY: [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def repository_uow_allowlist_validator_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_repository_uow_allowlist_validator_ci(
    payload: object,
) -> dict[str, object]:
    fields = _empty_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            allowlist_ready=False,
            allowlist_reason_code=_VALIDATOR_REASON_INVALID,
            allowlist_failures=[],
            fields=fields,
        )

    failures: list[str] = []

    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    ready_value = payload.get("allowlist_ready")
    reason_value = payload.get("reason_code")
    source_failures = payload.get("failures")

    ready_in_payload = "allowlist_ready" in payload
    reason_in_payload = "reason_code" in payload
    failures_in_payload = "failures" in payload

    ready_is_bool = ready_in_payload and type(ready_value) is bool
    if ready_in_payload and not ready_is_bool:
        _append(failures, "payload_shape_mismatch")

    reason_is_string = reason_in_payload and isinstance(
        reason_value, str
    )
    if reason_in_payload and not reason_is_string:
        _append(failures, "allowlist_reason_code_invalid")
    elif reason_is_string and reason_value not in _VALIDATOR_REASON_CODES:
        _append(failures, "allowlist_reason_code_invalid")

    failures_is_list = failures_in_payload and isinstance(
        source_failures, list
    )
    failures_is_list_str = failures_is_list and _all_strings(
        source_failures
    )
    if failures_in_payload and not failures_is_list_str:
        _append(failures, "allowlist_failures_invalid")

    if ready_is_bool and reason_is_string:
        if ready_value is True:
            if reason_value != _VALIDATOR_REASON_READY:
                _append(failures, "allowlist_reason_code_invalid")
        else:
            if reason_value not in (
                _VALIDATOR_REASON_NOT_READY,
                _VALIDATOR_REASON_INVALID,
            ):
                _append(failures, "allowlist_reason_code_invalid")

    if ready_is_bool and failures_is_list_str:
        assert isinstance(source_failures, list)
        if ready_value is True and source_failures != []:
            _append(failures, "allowlist_failures_invalid")
        if ready_value is False and source_failures == []:
            _append(failures, "allowlist_failures_invalid")
        for item in source_failures:
            if item not in _VALIDATOR_FAILURE_TAXONOMY_SET:
                _append(failures, "allowlist_failure_value_invalid")

    if ready_is_bool and ready_value is False:
        _append(failures, "allowlist_not_ready")

    surface = payload.get("surface")
    if surface != _VALIDATOR_SURFACE:
        _append(failures, "validator_surface_invalid")

    version = payload.get("version")
    if (
        type(version) is not int
        or type(version) is bool
        or version != _VALIDATOR_VERSION
    ):
        _append(failures, "validator_version_invalid")

    for field, expected, failure in _SOURCE_BINDINGS:
        candidate = payload.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, failure)
        else:
            _append(failures, failure)

    entry_counts: dict[str, int] = {}
    for field in _ENTRY_COUNT_FIELDS:
        candidate = payload.get(field)
        if (
            type(candidate) is int
            and not isinstance(candidate, bool)
            and candidate >= 0
        ):
            fields[field] = candidate
            entry_counts[field] = candidate
        else:
            fields[field] = None
            _append(failures, "entry_count_invalid")

    if len(entry_counts) == len(_ENTRY_COUNT_FIELDS):
        total = entry_counts["allowlist_entry_count"]
        parts = (
            entry_counts["read_only_entry_count"]
            + entry_counts[
                "mutation_declared_but_not_authorized_entry_count"
            ]
            + entry_counts["future_write_candidate_entry_count"]
        )
        if total != parts:
            _append(failures, "entry_count_mismatch")
        if ready_is_bool and ready_value is True and total == 0:
            _append(failures, "entry_count_mismatch")

    for flag in _REQUIRED_TRUE_FLAGS:
        candidate = payload.get(flag)
        if type(candidate) is not bool:
            fields[flag] = None
            _append(failures, "required_declaration_invalid")
        else:
            fields[flag] = candidate
            if candidate is False:
                _append(failures, "required_declaration_false")

    for flag in _AUTHORIZATION_FLAGS:
        candidate = payload.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    for flag in _RUNTIME_FLAGS:
        candidate = payload.get(flag)
        if type(candidate) is not bool:
            _append(failures, "runtime_flag_invalid")
        elif candidate is True:
            _append(failures, "runtime_flag_true")

    json_safe = payload.get("json_safe")
    if type(json_safe) is not bool or json_safe is not True:
        _append(failures, "json_safe_invalid")

    ordered_failures = _ordered_failures(failures)

    if ordered_failures == []:
        ci_ok = True
        reason_code = _REASON_READY
    else:
        ci_ok = False
        if any(item in _STRUCTURAL_FAILURES for item in ordered_failures):
            reason_code = _REASON_INVALID
        else:
            reason_code = _REASON_NOT_READY

    allowlist_ready_out = ready_value if ready_is_bool else False
    allowlist_reason_out = (
        reason_value
        if reason_is_string and reason_value in _VALIDATOR_REASON_CODES
        else _VALIDATOR_REASON_INVALID
    )
    if failures_is_list_str:
        assert isinstance(source_failures, list)
        allowlist_failures_out = _deepcopy(source_failures)
    else:
        allowlist_failures_out = []

    return _result(
        ci_ok=ci_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        allowlist_ready=allowlist_ready_out,
        allowlist_reason_code=allowlist_reason_out,
        allowlist_failures=allowlist_failures_out,
        fields=fields,
    )


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    allowlist_ready: bool,
    allowlist_reason_code: str,
    allowlist_failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["surface"] = _VALIDATOR_SURFACE
    output["version"] = _VALIDATOR_VERSION
    for name, _expected, _failure in _SOURCE_BINDINGS:
        output[name] = fields[name]
    output["allowlist_ready"] = allowlist_ready
    output["allowlist_reason_code"] = allowlist_reason_code
    output["allowlist_failures"] = list(allowlist_failures)
    for name in _ENTRY_COUNT_FIELDS:
        output[name] = fields[name]
    for name in _REQUIRED_TRUE_FLAGS:
        output[name] = fields[name]
    for name in _AUTHORIZATION_FLAGS:
        output[name] = False
    for name in _RUNTIME_FLAGS:
        output[name] = False
    output["json_safe"] = True
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _empty_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, _expected, _failure in _SOURCE_BINDINGS:
        fields[name] = None
    for name in _ENTRY_COUNT_FIELDS:
        fields[name] = None
    for name in _REQUIRED_TRUE_FLAGS:
        fields[name] = None
    return fields


def _all_strings(value: object) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, str):
            return False
    return True


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
