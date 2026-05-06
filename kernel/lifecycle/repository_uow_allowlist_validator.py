"""Pure validator for already-rendered repository/UoW allowlist declarations."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "repository_uow_allowlist_validator_manifest",
    "validate_repository_uow_allowlist",
]


_SURFACE = "repository_uow_allowlist_validator"
_ALLOWLIST_SURFACE = "RepositoryUoWAllowlistV1"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_repository_uow_allowlist"

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
_REPOSITORY_UOW_ALLOWLIST_SPEC_ONLY_TAG = (
    "repository-uow-allowlist-spec-only-v1"
)
_REPOSITORY_UOW_ALLOWLIST_SPEC_ONLY_COMMIT = (
    "cb2942919a2dbceee4af38777900db5768f6f916"
)

_REASON_INVALID = "invalid_allowlist_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_INPUT_KEYS = ("repository_uow_allowlist",)

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
        "source_repository_uow_allowlist_spec_only_tag",
        _REPOSITORY_UOW_ALLOWLIST_SPEC_ONLY_TAG,
        "source_repository_uow_allowlist_spec_tag_mismatch",
    ),
    (
        "source_repository_uow_allowlist_spec_only_commit",
        _REPOSITORY_UOW_ALLOWLIST_SPEC_ONLY_COMMIT,
        "source_repository_uow_allowlist_spec_commit_mismatch",
    ),
)

_ENTRY_KEYS = (
    "repository_class",
    "method_name",
    "method_owner",
    "read_write_classification",
    "allowed_for_executor",
    "allowed_for_restore",
    "allowed_for_write_side_recovery",
    "required_uow_context",
    "required_transaction_owner",
    "required_idempotency_binding",
    "required_evidence_output_fields",
    "required_mutation_summary_fields",
    "rollback_behavior",
    "allowed_failure_modes",
    "forbidden_side_effects",
    "json_safe_result_required",
    "filesystem_side_effects_forbidden",
    "external_network_forbidden",
    "services_forbidden",
    "schema_migration_forbidden",
    "db_repair_forbidden",
)

_ENTRY_STRING_FAILURES = (
    ("repository_class", "repository_class_invalid"),
    ("method_name", "method_name_invalid"),
    ("method_owner", "method_owner_invalid"),
    ("required_uow_context", "required_uow_context_invalid"),
    ("required_transaction_owner", "required_transaction_owner_invalid"),
    ("rollback_behavior", "rollback_behavior_invalid"),
)

_REQUIRED_UOW_CONTEXT = "kernel_owned_attempt_uow"
_REQUIRED_TRANSACTION_OWNER = "kernel"
_ROLLBACK_BEHAVIOR = "declared_only_runtime_unauthorized"

_ENTRY_EXACT_STRING_VALUES = {
    "required_uow_context": _REQUIRED_UOW_CONTEXT,
    "required_transaction_owner": _REQUIRED_TRANSACTION_OWNER,
    "rollback_behavior": _ROLLBACK_BEHAVIOR,
}

_ENTRY_AUTHORIZATION_FLAGS = (
    "allowed_for_executor",
    "allowed_for_restore",
    "allowed_for_write_side_recovery",
)

_ENTRY_REQUIRED_TRUE_FLAGS = (
    "json_safe_result_required",
    "filesystem_side_effects_forbidden",
    "external_network_forbidden",
    "services_forbidden",
    "schema_migration_forbidden",
    "db_repair_forbidden",
)

_READ_WRITE_CLASSIFICATIONS = (
    "read_only",
    "mutation_declared_but_not_authorized",
    "future_write_candidate",
)

_REQUIRED_EVIDENCE_OUTPUT_FIELDS = (
    "target_artifact_id",
    "target_task_id",
    "mutation_summary",
    "affected_rows_or_entities",
    "before_ref",
    "after_ref_requirement",
    "journal_ref_requirement",
    "idempotency_key",
    "operation_kind",
    "result_classification",
)

_REQUIRED_MUTATION_SUMMARY_FIELDS = (
    "mutation_summary_required",
    "changed_entity_types",
    "changed_entity_ids",
    "before_state_ref_or_reason",
    "after_state_ref_or_requirement",
    "expected_rejection_summary",
    "unexpected_failure_summary",
    "rollback_summary_requirement",
)

_ALLOWED_FAILURE_MODES = (
    "expected_rejection",
    "unexpected_failure",
)

_FORBIDDEN_SIDE_EFFECTS = (
    "filesystem",
    "external_network",
    "services",
    "schema_migration",
    "db_repair",
    "raw_sql",
    "direct_sqlite",
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

_ALLOWLIST_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + ("allowlist_entries",)
    + _REQUIRED_TRUE_FLAGS
    + _AUTHORIZATION_FLAGS
    + ("json_safe",)
)

_ALLOWLIST_OUTPUT_KEYS = (
    ("surface", "version")
    + tuple(name for name, _expected, _failure in _SOURCE_BINDINGS)
    + (
        "allowlist_entry_count",
        "read_only_entry_count",
        "mutation_declared_but_not_authorized_entry_count",
        "future_write_candidate_entry_count",
        "allowlist_entries",
    )
    + _REQUIRED_TRUE_FLAGS
    + _AUTHORIZATION_FLAGS
    + (
        "json_safe",
        "allowlist_ready",
        "executes_plan",
        "opens_db",
        "calls_repository",
        "calls_uow",
        "calls_services",
        "appends_evidence",
    )
)

_OUTPUT_KEYS = (
    "allowlist_ready",
    "reason_code",
    "failures",
    "allowlist",
)

_FAILURE_ORDER = (
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

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "allowlist_not_mapping",
        "allowlist_shape_mismatch",
        "allowlist_surface_invalid",
        "allowlist_version_invalid",
        "allowlist_entries_invalid",
        "allowlist_entry_not_mapping",
        "allowlist_entry_shape_mismatch",
        "allowlist_entry_method_forbidden",
        "repository_class_invalid",
        "method_name_invalid",
        "method_owner_invalid",
        "read_write_classification_invalid",
        "entry_authorization_flag_invalid",
        "required_uow_context_invalid",
        "required_transaction_owner_invalid",
        "required_idempotency_binding_invalid",
        "required_evidence_output_fields_invalid",
        "required_mutation_summary_fields_invalid",
        "rollback_behavior_invalid",
        "allowed_failure_modes_invalid",
        "forbidden_side_effects_invalid",
        "json_safe_result_required_invalid",
        "entry_required_declaration_invalid",
        "allowlist_entry_duplicate",
        "required_declaration_invalid",
        "authorization_flag_invalid",
        "json_safe_invalid",
    }
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "repository_uow_allowlist_spec_only": (
            _REPOSITORY_UOW_ALLOWLIST_SPEC_ONLY_TAG
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
    "allowlist_ready_authorizes_repository_uow_writes": False,
    "allowlist_ready_authorizes_direct_db": False,
    "allowlist_ready_authorizes_executor": False,
    "allowlist_ready_authorizes_restore": False,
    "allowlist_ready_authorizes_evidence": False,
    "executes_plan": False,
    "opens_db": False,
    "calls_repository": False,
    "calls_uow": False,
    "calls_services": False,
    "appends_evidence": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


def repository_uow_allowlist_validator_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def validate_repository_uow_allowlist(payload: object) -> dict[str, object]:
    fields = _empty_allowlist_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            ready=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            fields=fields,
        )

    failures: list[str] = []
    semantic_failures: list[str] = []
    exact_string_shape_failures: list[str] = []
    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    allowlist = payload.get("repository_uow_allowlist")
    _validate_allowlist(
        allowlist,
        failures,
        fields,
        semantic_failures,
        exact_string_shape_failures,
    )

    ordered_failures = _ordered_failures(failures)
    ready = ordered_failures == []
    if ready:
        reason_code = _REASON_READY
    elif _has_structural_failure(
        ordered_failures,
        semantic_failures,
        exact_string_shape_failures,
    ):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ready=ready,
        reason_code=reason_code,
        failures=ordered_failures,
        fields=fields,
    )


def _validate_allowlist(
    allowlist: object,
    failures: list[str],
    fields: dict[str, object],
    semantic_failures: list[str],
    exact_string_shape_failures: list[str],
) -> None:
    if not isinstance(allowlist, _Mapping):
        _append(failures, "allowlist_not_mapping")
        return

    if set(allowlist.keys()) != set(_ALLOWLIST_KEYS):
        _append(failures, "allowlist_shape_mismatch")

    if allowlist.get("surface") != _ALLOWLIST_SURFACE:
        _append(failures, "allowlist_surface_invalid")

    version = allowlist.get("version")
    if type(version) is bool or type(version) is not int or version != _VERSION:
        _append(failures, "allowlist_version_invalid")

    for field, expected, failure in _SOURCE_BINDINGS:
        candidate = allowlist.get(field)
        if isinstance(candidate, str) and candidate != "":
            fields[field] = candidate
            if candidate != expected:
                _append(failures, failure)
        else:
            _append(failures, failure)

    fields["allowlist_entries"] = _validate_entries(
        allowlist.get("allowlist_entries"),
        failures,
        semantic_failures,
        exact_string_shape_failures,
    )

    for flag in _REQUIRED_TRUE_FLAGS:
        candidate = allowlist.get(flag)
        if type(candidate) is not bool:
            fields[flag] = None
            _append(failures, "required_declaration_invalid")
        else:
            fields[flag] = candidate
            if candidate is False:
                _append(failures, "required_declaration_false")

    for flag in _AUTHORIZATION_FLAGS:
        candidate = allowlist.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    json_safe = allowlist.get("json_safe")
    if type(json_safe) is not bool:
        fields["json_safe"] = None
        _append(failures, "json_safe_invalid")
    else:
        fields["json_safe"] = json_safe
        if json_safe is False:
            _append(failures, "json_safe_invalid")


def _validate_entries(
    entries: object,
    failures: list[str],
    semantic_failures: list[str],
    exact_string_shape_failures: list[str],
) -> list[dict[str, object]]:
    if not isinstance(entries, list):
        _append(failures, "allowlist_entries_invalid")
        return []
    if entries == []:
        _append(failures, "allowlist_entries_invalid")
        return []

    normalized_entries: list[dict[str, object]] = []
    seen_methods = set()

    for entry in entries:
        if not isinstance(entry, _Mapping):
            _append(failures, "allowlist_entry_not_mapping")
            continue

        if set(entry.keys()) != set(_ENTRY_KEYS):
            _append(failures, "allowlist_entry_shape_mismatch")

        normalized = _normalize_entry(
            entry,
            failures,
            semantic_failures,
            exact_string_shape_failures,
        )
        pair = (normalized["repository_class"], normalized["method_name"])
        if isinstance(pair[0], str) and isinstance(pair[1], str):
            if pair in seen_methods:
                _append(failures, "allowlist_entry_duplicate")
            else:
                seen_methods.add(pair)
        normalized_entries.append(normalized)

    return normalized_entries


def _normalize_entry(
    entry: _Mapping[str, object],
    failures: list[str],
    semantic_failures: list[str],
    exact_string_shape_failures: list[str],
) -> dict[str, object]:
    normalized: dict[str, object] = {}

    for field, failure in _ENTRY_STRING_FAILURES:
        candidate = entry.get(field)
        if isinstance(candidate, str) and candidate != "":
            normalized[field] = candidate
            expected = _ENTRY_EXACT_STRING_VALUES.get(field)
            if expected is not None and candidate != expected:
                _append(failures, failure)
                _append(semantic_failures, failure)
        else:
            normalized[field] = None
            _append(failures, failure)
            if field in _ENTRY_EXACT_STRING_VALUES:
                _append(exact_string_shape_failures, failure)

    method_name = normalized["method_name"]
    repository_class = normalized["repository_class"]
    if isinstance(method_name, str):
        if "*" in method_name or method_name.startswith("_"):
            _append(failures, "allowlist_entry_method_forbidden")
    if isinstance(repository_class, str) and "*" in repository_class:
        _append(failures, "allowlist_entry_method_forbidden")

    classification = entry.get("read_write_classification")
    if classification in _READ_WRITE_CLASSIFICATIONS:
        normalized["read_write_classification"] = classification
    else:
        normalized["read_write_classification"] = None
        _append(failures, "read_write_classification_invalid")

    for field in _ENTRY_AUTHORIZATION_FLAGS:
        candidate = entry.get(field)
        if type(candidate) is bool:
            normalized[field] = candidate
            if candidate is True:
                _append(failures, "entry_authorization_flag_true")
        else:
            normalized[field] = None
            _append(failures, "entry_authorization_flag_invalid")

    idempotency_binding = entry.get("required_idempotency_binding")
    if type(idempotency_binding) is not bool:
        normalized["required_idempotency_binding"] = None
        _append(failures, "required_idempotency_binding_invalid")
    else:
        normalized["required_idempotency_binding"] = idempotency_binding
        if idempotency_binding is False:
            _append(failures, "required_idempotency_binding_false")

    json_safe_result = entry.get("json_safe_result_required")
    if type(json_safe_result) is not bool:
        normalized["json_safe_result_required"] = None
        _append(failures, "json_safe_result_required_invalid")
    else:
        normalized["json_safe_result_required"] = json_safe_result
        if json_safe_result is False:
            _append(failures, "json_safe_result_required_false")

    for field in _ENTRY_REQUIRED_TRUE_FLAGS:
        if field == "json_safe_result_required":
            continue
        candidate = entry.get(field)
        if type(candidate) is bool:
            normalized[field] = candidate
            if candidate is False:
                _append(failures, "entry_required_declaration_false")
        else:
            normalized[field] = None
            _append(failures, "entry_required_declaration_invalid")

    _validate_entry_list(
        normalized,
        entry,
        "required_evidence_output_fields",
        _REQUIRED_EVIDENCE_OUTPUT_FIELDS,
        "required_evidence_output_fields_invalid",
        failures,
    )
    _validate_entry_list(
        normalized,
        entry,
        "required_mutation_summary_fields",
        _REQUIRED_MUTATION_SUMMARY_FIELDS,
        "required_mutation_summary_fields_invalid",
        failures,
    )
    _validate_entry_list(
        normalized,
        entry,
        "allowed_failure_modes",
        _ALLOWED_FAILURE_MODES,
        "allowed_failure_modes_invalid",
        failures,
    )
    _validate_entry_list(
        normalized,
        entry,
        "forbidden_side_effects",
        _FORBIDDEN_SIDE_EFFECTS,
        "forbidden_side_effects_invalid",
        failures,
    )

    output: dict[str, object] = {}
    for field in _ENTRY_KEYS:
        output[field] = normalized[field]
    return output


def _validate_entry_list(
    normalized: dict[str, object],
    entry: _Mapping[str, object],
    field: str,
    expected: tuple[str, ...],
    failure: str,
    failures: list[str],
) -> None:
    candidate = entry.get(field)
    if _is_string_list(candidate):
        assert isinstance(candidate, list)
        normalized[field] = list(candidate)
        if not _same_string_items(candidate, expected):
            _append(failures, failure)
    else:
        normalized[field] = []
        _append(failures, failure)


def _is_string_list(candidate: object) -> bool:
    if not isinstance(candidate, list):
        return False
    return all(isinstance(item, str) and item != "" for item in candidate)


def _same_string_items(candidate: list[object], expected: tuple[str, ...]) -> bool:
    if len(candidate) != len(expected):
        return False
    for item in candidate:
        if item not in expected:
            return False
    for item in expected:
        if item not in candidate:
            return False
    return True


def _result(
    *,
    ready: bool,
    reason_code: str,
    failures: list[str],
    fields: dict[str, object],
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["allowlist_ready"] = ready
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["allowlist"] = _allowlist_output(fields, ready)
    assert tuple(output.keys()) == _OUTPUT_KEYS
    return output


def _allowlist_output(
    fields: dict[str, object],
    ready: bool,
) -> dict[str, object]:
    entries = _deepcopy(fields["allowlist_entries"])
    assert isinstance(entries, list)

    output: dict[str, object] = {}
    output["surface"] = _SURFACE
    output["version"] = _VERSION
    for name, _expected, _failure in _SOURCE_BINDINGS:
        output[name] = fields[name]
    output["allowlist_entry_count"] = len(entries)
    output["read_only_entry_count"] = _classification_count(
        entries,
        "read_only",
    )
    output["mutation_declared_but_not_authorized_entry_count"] = (
        _classification_count(
            entries,
            "mutation_declared_but_not_authorized",
        )
    )
    output["future_write_candidate_entry_count"] = _classification_count(
        entries,
        "future_write_candidate",
    )
    output["allowlist_entries"] = entries
    for name in _REQUIRED_TRUE_FLAGS:
        output[name] = fields[name]
    for name in _AUTHORIZATION_FLAGS:
        output[name] = False
    output["json_safe"] = fields["json_safe"]
    output["allowlist_ready"] = ready
    output["executes_plan"] = False
    output["opens_db"] = False
    output["calls_repository"] = False
    output["calls_uow"] = False
    output["calls_services"] = False
    output["appends_evidence"] = False
    assert tuple(output.keys()) == _ALLOWLIST_OUTPUT_KEYS
    return output


def _classification_count(
    entries: list[object],
    classification: str,
) -> int:
    count = 0
    for entry in entries:
        if isinstance(entry, _Mapping):
            if entry.get("read_write_classification") == classification:
                count = count + 1
    return count


def _empty_allowlist_fields() -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, _expected, _failure in _SOURCE_BINDINGS:
        fields[name] = None
    fields["allowlist_entries"] = []
    for name in _REQUIRED_TRUE_FLAGS:
        fields[name] = None
    fields["json_safe"] = None
    return fields


def _has_structural_failure(
    ordered_failures: list[str],
    semantic_failures: list[str],
    exact_string_shape_failures: list[str],
) -> bool:
    for failure in ordered_failures:
        if failure not in _STRUCTURAL_FAILURES:
            continue
        if failure in exact_string_shape_failures:
            return True
        if failure in semantic_failures:
            continue
        return True
    return False


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]
