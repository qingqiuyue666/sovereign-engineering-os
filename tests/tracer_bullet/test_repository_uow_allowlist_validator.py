"""Tracer-bullet tests for the repository/UoW allowlist validator."""

from __future__ import annotations

import copy
import inspect
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

import kernel.lifecycle.repository_uow_allowlist_validator as validator_module
from kernel.lifecycle.repository_uow_allowlist_validator import (
    repository_uow_allowlist_validator_manifest,
    validate_repository_uow_allowlist,
)


SOURCE_BINDING_VALUES = {
    "source_read_only_governance_layer_tag": (
        "read-only-governance-layer-v1"
    ),
    "source_read_only_governance_layer_commit": (
        "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
    ),
    "source_write_side_precondition_checker_tag": (
        "write-side-precondition-checker-v1"
    ),
    "source_write_side_precondition_checker_commit": (
        "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
    ),
    "source_write_side_precondition_ci_tag": (
        "write-side-precondition-ci-v1"
    ),
    "source_write_side_precondition_ci_commit": (
        "05c81541ad3d7deee20023843142f702937f6c3f"
    ),
    "source_write_side_recovery_spec_only_tag": (
        "write-side-recovery-spec-only-v1"
    ),
    "source_write_side_recovery_spec_only_commit": (
        "ad560cc2dab135f2c1d56d948410ae47586d118e"
    ),
    "source_restore_dry_run_read_only_stack_tag": (
        "restore-dry-run-read-only-stack-v1"
    ),
    "source_restore_dry_run_read_only_stack_commit": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
    "source_preflight_read_only_stack_tag": "preflight-read-only-stack-v1",
    "source_preflight_read_only_stack_commit": (
        "662b6161253c35204b437e88809c5bab21908c6d"
    ),
    "source_execution_authorization_read_only_stack_tag": (
        "execution-authorization-read-only-stack-v1"
    ),
    "source_execution_authorization_read_only_stack_commit": (
        "d586aeb60620010c900df7be1a88621ab2cb8dc1"
    ),
    "source_executor_precondition_read_only_stack_tag": (
        "executor-precondition-read-only-stack-v1"
    ),
    "source_executor_precondition_read_only_stack_commit": (
        "cb3948eb843866dcc961b6a074038c13db64d017"
    ),
    "source_write_path_read_only_stack_tag": (
        "write-path-read-only-stack-v1"
    ),
    "source_write_path_read_only_stack_commit": (
        "8ffd4679aca8f593415089748df35df42af8f015"
    ),
    "source_repository_uow_allowlist_spec_only_tag": (
        "repository-uow-allowlist-spec-only-v1"
    ),
    "source_repository_uow_allowlist_spec_only_commit": (
        "cb2942919a2dbceee4af38777900db5768f6f916"
    ),
}

SOURCE_BINDING_FAILURES = {
    "source_read_only_governance_layer_tag": (
        "source_read_only_governance_layer_tag_mismatch"
    ),
    "source_read_only_governance_layer_commit": (
        "source_read_only_governance_layer_commit_mismatch"
    ),
    "source_write_side_precondition_checker_tag": (
        "source_write_side_precondition_checker_tag_mismatch"
    ),
    "source_write_side_precondition_checker_commit": (
        "source_write_side_precondition_checker_commit_mismatch"
    ),
    "source_write_side_precondition_ci_tag": (
        "source_write_side_precondition_ci_tag_mismatch"
    ),
    "source_write_side_precondition_ci_commit": (
        "source_write_side_precondition_ci_commit_mismatch"
    ),
    "source_write_side_recovery_spec_only_tag": (
        "source_write_side_recovery_spec_only_tag_mismatch"
    ),
    "source_write_side_recovery_spec_only_commit": (
        "source_write_side_recovery_spec_only_commit_mismatch"
    ),
    "source_restore_dry_run_read_only_stack_tag": (
        "source_restore_dry_run_stack_tag_mismatch"
    ),
    "source_restore_dry_run_read_only_stack_commit": (
        "source_restore_dry_run_stack_commit_mismatch"
    ),
    "source_preflight_read_only_stack_tag": (
        "source_preflight_stack_tag_mismatch"
    ),
    "source_preflight_read_only_stack_commit": (
        "source_preflight_stack_commit_mismatch"
    ),
    "source_execution_authorization_read_only_stack_tag": (
        "source_execution_authorization_stack_tag_mismatch"
    ),
    "source_execution_authorization_read_only_stack_commit": (
        "source_execution_authorization_stack_commit_mismatch"
    ),
    "source_executor_precondition_read_only_stack_tag": (
        "source_executor_precondition_stack_tag_mismatch"
    ),
    "source_executor_precondition_read_only_stack_commit": (
        "source_executor_precondition_stack_commit_mismatch"
    ),
    "source_write_path_read_only_stack_tag": (
        "source_write_path_stack_tag_mismatch"
    ),
    "source_write_path_read_only_stack_commit": (
        "source_write_path_stack_commit_mismatch"
    ),
    "source_repository_uow_allowlist_spec_only_tag": (
        "source_repository_uow_allowlist_spec_tag_mismatch"
    ),
    "source_repository_uow_allowlist_spec_only_commit": (
        "source_repository_uow_allowlist_spec_commit_mismatch"
    ),
}

ENTRY_KEYS = (
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

ENTRY_STRING_FAILURES = {
    "repository_class": "repository_class_invalid",
    "method_name": "method_name_invalid",
    "method_owner": "method_owner_invalid",
    "required_uow_context": "required_uow_context_invalid",
    "required_transaction_owner": "required_transaction_owner_invalid",
    "rollback_behavior": "rollback_behavior_invalid",
}

ENTRY_AUTHORIZATION_FLAGS = (
    "allowed_for_executor",
    "allowed_for_restore",
    "allowed_for_write_side_recovery",
)

ENTRY_REQUIRED_TRUE_FLAGS = (
    "json_safe_result_required",
    "filesystem_side_effects_forbidden",
    "external_network_forbidden",
    "services_forbidden",
    "schema_migration_forbidden",
    "db_repair_forbidden",
)

REQUIRED_EVIDENCE_OUTPUT_FIELDS = [
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
]

REQUIRED_MUTATION_SUMMARY_FIELDS = [
    "mutation_summary_required",
    "changed_entity_types",
    "changed_entity_ids",
    "before_state_ref_or_reason",
    "after_state_ref_or_requirement",
    "expected_rejection_summary",
    "unexpected_failure_summary",
    "rollback_summary_requirement",
]

ALLOWED_FAILURE_MODES = [
    "expected_rejection",
    "unexpected_failure",
]

FORBIDDEN_SIDE_EFFECTS = [
    "filesystem",
    "external_network",
    "services",
    "schema_migration",
    "db_repair",
    "raw_sql",
    "direct_sqlite",
]

REQUIRED_TRUE_FLAGS = (
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

AUTHORIZATION_FLAGS = (
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

FAILURE_ORDER = [
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
]

EXPECTED_MANIFEST = {
    "surface": "repository_uow_allowlist_validator",
    "version": 1,
    "input_shape": "already_rendered_repository_uow_allowlist",
    "depends_on": {
        "repository_uow_allowlist_spec_only": (
            "repository-uow-allowlist-spec-only-v1"
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
        "invalid_allowlist_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": FAILURE_ORDER,
}

EXPECTED_OUTPUT_KEYS = [
    "allowlist_ready",
    "reason_code",
    "failures",
    "allowlist",
]

EXPECTED_ALLOWLIST_OUTPUT_KEYS = (
    ["surface", "version"]
    + list(SOURCE_BINDING_VALUES.keys())
    + [
        "allowlist_entry_count",
        "read_only_entry_count",
        "mutation_declared_but_not_authorized_entry_count",
        "future_write_candidate_entry_count",
        "allowlist_entries",
    ]
    + list(REQUIRED_TRUE_FLAGS)
    + list(AUTHORIZATION_FLAGS)
    + [
        "json_safe",
        "allowlist_ready",
        "executes_plan",
        "opens_db",
        "calls_repository",
        "calls_uow",
        "calls_services",
        "appends_evidence",
    ]
)

REPR_MARKERS = (
    "RepositoryUoWAllowlist(",
    " object at 0x",
    "<sqlite3.",
)

FORBIDDEN_SOURCE_MARKERS = (
    "datetime.now",
    "time.time",
    "time.monotonic",
    "hashlib",
    "hmac",
    "secrets",
    "sha256",
    "blake2",
    "open(",
    "Path(",
    "os.environ",
    "subprocess",
    "threading",
    "asyncio",
    "socket",
    "argparse",
    "click",
    "inspect.",
    "getattr(",
    "callable(",
    "dir(",
    "hasattr(",
    "importlib",
    "open_connection",
    "UnitOfWork",
    "KernelUnitOfWork",
    "approval_service.",
    "review_service.",
    "revision_seal_service.",
    "evidence_service.",
    "append_audit",
    "append_evidence",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "signable_path_orchestrator",
    "apply_migrations",
    "validate_write_path_contract",
    "write_path_contract_validator_manifest",
    "validate_executor_precondition",
    "executor_precondition_validator_manifest",
    "consume_executor_precondition_validator_ci",
    "executor_precondition_validator_ci_manifest",
    "consume_execution_authorization_validator_ci",
    "execution_authorization_validator_ci_manifest",
    "validate_execution_authorization",
    "execution_authorization_validator_manifest",
    "summarize_preflight_readiness",
    "preflight_aggregate_summary_manifest",
    "consume_execution_preflight_ci",
    "execution_preflight_ci_manifest",
    "validate_execution_preflight",
    "execution_preflight_manifest",
    "validate_human_approval_readiness",
    "human_approval_readiness_ci_manifest",
    "summarize_restore_dry_run_readiness",
    "restore_dry_run_aggregate_summary_manifest",
    "governance_readiness_aggregator",
)

ALLOWED_SOURCE_FIELD_STRINGS = (
    "repository_uow_allowlist_validator_manifest",
    "validate_repository_uow_allowlist",
    "repository_uow_allowlist_validator",
    "RepositoryUoWAllowlistV1",
    "repository-uow-allowlist-spec-only-v1",
    "write-path-read-only-stack-v1",
    "executor-precondition-read-only-stack-v1",
    "execution-authorization-read-only-stack-v1",
    "preflight-read-only-stack-v1",
    "restore-dry-run-read-only-stack-v1",
    "required_evidence_output_fields",
    "required_mutation_summary_fields",
    "evidence_append_authorized",
    "audit_append_authorized",
    "evidence_audit_append_forbidden",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "evidence_service_authorized",
    "daemon_server_queue_authorized",
)


def _entry(**overrides: object) -> dict[str, object]:
    base = {
        "repository_class": "TaskLifecycleRepository",
        "method_name": "record_kernel_decision",
        "method_owner": "kernel",
        "read_write_classification": "future_write_candidate",
        "allowed_for_executor": False,
        "allowed_for_restore": False,
        "allowed_for_write_side_recovery": False,
        "required_uow_context": "kernel_owned_uow",
        "required_transaction_owner": "kernel",
        "required_idempotency_binding": True,
        "required_evidence_output_fields": list(
            REQUIRED_EVIDENCE_OUTPUT_FIELDS
        ),
        "required_mutation_summary_fields": list(
            REQUIRED_MUTATION_SUMMARY_FIELDS
        ),
        "rollback_behavior": "rollback_required",
        "allowed_failure_modes": [
            "expected_rejection",
            "unexpected_failure",
        ],
        "forbidden_side_effects": [
            "filesystem",
            "external_network",
            "services",
            "schema_migration",
            "db_repair",
            "raw_sql",
            "direct_sqlite",
        ],
        "json_safe_result_required": True,
        "filesystem_side_effects_forbidden": True,
        "external_network_forbidden": True,
        "services_forbidden": True,
        "schema_migration_forbidden": True,
        "db_repair_forbidden": True,
    }
    base.update(overrides)
    return base


def _allowlist(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "RepositoryUoWAllowlistV1",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        base[name] = value
    base["allowlist_entries"] = [_entry()]
    for flag in REQUIRED_TRUE_FLAGS:
        base[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        base[flag] = False
    base["json_safe"] = True
    base.update(overrides)
    return base


def _payload(**overrides: object) -> dict[str, object]:
    allowlist = overrides.pop("allowlist", None)
    if allowlist is None:
        allowlist = _allowlist()
    payload: dict[str, object] = {"repository_uow_allowlist": allowlist}
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    allowlist: dict[str, object] = {
        "surface": "repository_uow_allowlist_validator",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        allowlist[name] = value
    allowlist["allowlist_entry_count"] = 1
    allowlist["read_only_entry_count"] = 0
    allowlist["mutation_declared_but_not_authorized_entry_count"] = 0
    allowlist["future_write_candidate_entry_count"] = 1
    allowlist["allowlist_entries"] = [_entry()]
    for flag in REQUIRED_TRUE_FLAGS:
        allowlist[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        allowlist[flag] = False
    allowlist["json_safe"] = True
    allowlist["allowlist_ready"] = True
    allowlist["executes_plan"] = False
    allowlist["opens_db"] = False
    allowlist["calls_repository"] = False
    allowlist["calls_uow"] = False
    allowlist["calls_services"] = False
    allowlist["appends_evidence"] = False
    return {
        "allowlist_ready": True,
        "reason_code": "ready",
        "failures": [],
        "allowlist": allowlist,
    }


def _recursive_values(payload: object) -> list[object]:
    values: list[object] = [payload]
    if isinstance(payload, dict):
        for key, value in payload.items():
            values.extend(_recursive_values(key))
            values.extend(_recursive_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_recursive_values(value))
    return values


def _assert_json_safe(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    if decoded != payload:
        raise AssertionError("payload did not round-trip through JSON")
    for value in _recursive_values(payload):
        if isinstance(value, (set, frozenset, tuple)):
            raise AssertionError(
                f"payload leaked runtime collection {type(value).__name__}"
            )


def _assert_no_runtime_repr(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    for marker in REPR_MARKERS:
        if marker in encoded:
            raise AssertionError(f"runtime repr marker leaked: {marker}")


def _scrubbed_source() -> str:
    source = inspect.getsource(validator_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


def _assert_rejected_with(
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = validate_repository_uow_allowlist(payload)
    if result["allowlist_ready"] is not False:
        raise AssertionError("allowlist unexpectedly ready")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = validate_repository_uow_allowlist(_payload())
        self.assertEqual(result, _expected_happy_output())

    def test_ready_does_not_authorize_writes_executor_restore_or_evidence(
        self,
    ) -> None:
        result = validate_repository_uow_allowlist(_payload())
        allowlist = result["allowlist"]

        self.assertTrue(result["allowlist_ready"])
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(allowlist[flag], False)
        self.assertIs(allowlist["executes_plan"], False)
        self.assertIs(allowlist["opens_db"], False)
        self.assertIs(allowlist["calls_repository"], False)
        self.assertIs(allowlist["calls_uow"], False)
        self.assertIs(allowlist["calls_services"], False)
        self.assertIs(allowlist["appends_evidence"], False)

    def test_output_shape_exact(self) -> None:
        result = validate_repository_uow_allowlist(_payload())
        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertEqual(
            list(result["allowlist"].keys()),
            EXPECTED_ALLOWLIST_OUTPUT_KEYS,
        )

    def test_classification_counts_are_exposed(self) -> None:
        entries = [
            _entry(
                repository_class="ReadOnlyRepository",
                method_name="load_task",
                read_write_classification="read_only",
            ),
            _entry(
                repository_class="DeclaredMutationRepository",
                method_name="record_declared_mutation",
                read_write_classification=(
                    "mutation_declared_but_not_authorized"
                ),
            ),
            _entry(
                repository_class="FutureWriteRepository",
                method_name="record_future_write",
                read_write_classification="future_write_candidate",
            ),
        ]
        result = validate_repository_uow_allowlist(
            _payload(allowlist=_allowlist(allowlist_entries=entries))
        )
        allowlist = result["allowlist"]
        self.assertTrue(result["allowlist_ready"])
        self.assertEqual(allowlist["allowlist_entry_count"], 3)
        self.assertEqual(allowlist["read_only_entry_count"], 1)
        self.assertEqual(
            allowlist[
                "mutation_declared_but_not_authorized_entry_count"
            ],
            1,
        )
        self.assertEqual(
            allowlist["future_write_candidate_entry_count"],
            1,
        )


class TopLevelInputTests(unittest.TestCase):
    def test_non_mapping_rejected(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], (), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = validate_repository_uow_allowlist(candidate)
                self.assertFalse(result["allowlist_ready"])
                self.assertEqual(result["reason_code"], "invalid_allowlist_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        _assert_rejected_with({}, "payload_shape_mismatch")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _payload()
        payload["unexpected"] = "x"
        _assert_rejected_with(payload, "payload_shape_mismatch")


class AllowlistStructureTests(unittest.TestCase):
    def test_allowlist_non_mapping_rejected(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], object()):
            with self.subTest(candidate=type(candidate).__name__):
                _assert_rejected_with(
                    {"repository_uow_allowlist": candidate},
                    "allowlist_not_mapping",
                )

    def test_allowlist_missing_key_rejected(self) -> None:
        allowlist = _allowlist()
        del allowlist["surface"]
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_shape_mismatch",
        )

    def test_allowlist_unknown_key_rejected(self) -> None:
        allowlist = _allowlist()
        allowlist["unexpected"] = "x"
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_shape_mismatch",
        )

    def test_wrong_surface_rejected(self) -> None:
        allowlist = _allowlist(surface="OtherSurface")
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_surface_invalid",
        )

    def test_wrong_version_rejected(self) -> None:
        allowlist = _allowlist(version=2)
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_version_invalid",
        )

    def test_bool_as_int_version_rejected(self) -> None:
        allowlist = _allowlist(version=True)
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_version_invalid",
        )


class SourceBindingTests(unittest.TestCase):
    def test_each_source_ref_mismatch_rejected(self) -> None:
        for field, failure in SOURCE_BINDING_FAILURES.items():
            with self.subTest(field=field):
                allowlist = _allowlist()
                allowlist[field] = "wrong-ref"
                result = _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    failure,
                )
                self.assertNotIn("allowlist_shape_mismatch", result["failures"])


class EntryStructureTests(unittest.TestCase):
    def test_entries_must_be_list(self) -> None:
        for bad in (None, "x", {}, 1, True):
            with self.subTest(bad=type(bad).__name__):
                allowlist = _allowlist(allowlist_entries=bad)
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "allowlist_entries_invalid",
                )

    def test_entry_must_be_mapping(self) -> None:
        allowlist = _allowlist(allowlist_entries=["not-mapping"])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_entry_not_mapping",
        )

    def test_entry_exact_key_set_required(self) -> None:
        entry = _entry()
        del entry["method_owner"]
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_entry_shape_mismatch",
        )

        entry = _entry(unexpected="x")
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_entry_shape_mismatch",
        )

    def test_required_entry_strings_rejected_when_invalid(self) -> None:
        for field, failure in ENTRY_STRING_FAILURES.items():
            for bad in (None, "", 1, True, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    entry = _entry(**{field: bad})
                    allowlist = _allowlist(allowlist_entries=[entry])
                    _assert_rejected_with(
                        _payload(allowlist=allowlist),
                        failure,
                    )

    def test_wildcard_and_private_methods_rejected(self) -> None:
        for overrides in (
            {"method_name": "*"},
            {"method_name": "_private_mutation"},
            {"repository_class": "Any*Repository"},
        ):
            with self.subTest(overrides=overrides):
                entry = _entry(**overrides)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "allowlist_entry_method_forbidden",
                )

    def test_read_write_classification_rejected_when_unknown(self) -> None:
        entry = _entry(read_write_classification="write_now")
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "read_write_classification_invalid",
        )

    def test_entry_authorization_flags_rejected_when_not_bool(self) -> None:
        for field in ENTRY_AUTHORIZATION_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    entry = _entry(**{field: bad})
                    allowlist = _allowlist(allowlist_entries=[entry])
                    _assert_rejected_with(
                        _payload(allowlist=allowlist),
                        "entry_authorization_flag_invalid",
                    )

    def test_entry_authorization_flags_rejected_when_true(self) -> None:
        for field in ENTRY_AUTHORIZATION_FLAGS:
            with self.subTest(field=field):
                entry = _entry(**{field: True})
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "entry_authorization_flag_true",
                )

    def test_required_idempotency_binding_rejected_when_not_bool(self) -> None:
        for bad in (None, "idempotency_key", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                entry = _entry(required_idempotency_binding=bad)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "required_idempotency_binding_invalid",
                )

    def test_required_idempotency_binding_rejected_when_false(self) -> None:
        entry = _entry(required_idempotency_binding=False)
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "required_idempotency_binding_false",
        )

    def test_json_safe_result_required_rejected_when_not_bool(self) -> None:
        for bad in (None, "true", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                entry = _entry(json_safe_result_required=bad)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "json_safe_result_required_invalid",
                )

    def test_json_safe_result_required_rejected_when_false(self) -> None:
        entry = _entry(json_safe_result_required=False)
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "json_safe_result_required_false",
        )

    def test_entry_required_true_flags_rejected_when_false(self) -> None:
        for field in ENTRY_REQUIRED_TRUE_FLAGS:
            if field == "json_safe_result_required":
                continue
            with self.subTest(field=field):
                entry = _entry(**{field: False})
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "entry_required_declaration_false",
                )

    def test_entry_required_true_flags_rejected_when_not_bool(self) -> None:
        for field in ENTRY_REQUIRED_TRUE_FLAGS:
            if field == "json_safe_result_required":
                continue
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    entry = _entry(**{field: bad})
                    allowlist = _allowlist(allowlist_entries=[entry])
                    _assert_rejected_with(
                        _payload(allowlist=allowlist),
                        "entry_required_declaration_invalid",
                    )

    def test_required_evidence_fields_rejected_when_invalid_shape(self) -> None:
        for bad in (None, "x", [""], [1], {}, True):
            with self.subTest(bad=type(bad).__name__):
                entry = _entry(required_evidence_output_fields=bad)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "required_evidence_output_fields_invalid",
                )

    def test_required_mutation_summary_fields_rejected_when_invalid_shape(
        self,
    ) -> None:
        for bad in (None, "x", [""], [1], {}, True):
            with self.subTest(bad=type(bad).__name__):
                entry = _entry(required_mutation_summary_fields=bad)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "required_mutation_summary_fields_invalid",
                )

    def test_allowed_failure_modes_rejected_when_invalid(self) -> None:
        bad_values = (
            None,
            "expected_rejection",
            [""],
            [1],
            {},
            True,
            ["expected_rejection"],
            ["expected_rejection", "unexpected_failure", "extra"],
            ["unexpected_failure", "expected_rejection", "expected_rejection"],
        )
        for bad in bad_values:
            with self.subTest(bad=bad):
                entry = _entry(allowed_failure_modes=bad)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "allowed_failure_modes_invalid",
                )

    def test_allowed_failure_modes_accepts_list_equivalent_order(self) -> None:
        entry = _entry(
            allowed_failure_modes=[
                "unexpected_failure",
                "expected_rejection",
            ],
        )
        result = validate_repository_uow_allowlist(
            _payload(allowlist=_allowlist(allowlist_entries=[entry]))
        )
        self.assertTrue(result["allowlist_ready"])

    def test_forbidden_side_effects_rejected_when_invalid(self) -> None:
        bad_values = (
            None,
            "filesystem",
            [""],
            [1],
            {},
            True,
            ["filesystem"],
            FORBIDDEN_SIDE_EFFECTS + ["extra"],
            FORBIDDEN_SIDE_EFFECTS[:-1],
            FORBIDDEN_SIDE_EFFECTS[:-1] + ["filesystem"],
        )
        for bad in bad_values:
            with self.subTest(bad=bad):
                entry = _entry(forbidden_side_effects=bad)
                allowlist = _allowlist(allowlist_entries=[entry])
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "forbidden_side_effects_invalid",
                )

    def test_forbidden_side_effects_accepts_list_equivalent_order(self) -> None:
        entry = _entry(
            forbidden_side_effects=list(reversed(FORBIDDEN_SIDE_EFFECTS)),
        )
        result = validate_repository_uow_allowlist(
            _payload(allowlist=_allowlist(allowlist_entries=[entry]))
        )
        self.assertTrue(result["allowlist_ready"])

    def test_legacy_generic_entry_list_failure_not_used(self) -> None:
        for field, failure in (
            (
                "required_evidence_output_fields",
                "required_evidence_output_fields_invalid",
            ),
            (
                "required_mutation_summary_fields",
                "required_mutation_summary_fields_invalid",
            ),
            ("allowed_failure_modes", "allowed_failure_modes_invalid"),
            ("forbidden_side_effects", "forbidden_side_effects_invalid"),
        ):
            for bad in (None, "x", [""], [1], {}, True):
                with self.subTest(field=field, bad=type(bad).__name__):
                    entry = _entry(**{field: bad})
                    allowlist = _allowlist(allowlist_entries=[entry])
                    result = _assert_rejected_with(
                        _payload(allowlist=allowlist),
                        failure,
                    )
                    self.assertNotIn(
                        "allowlist_entry_list_invalid",
                        result["failures"],
                    )

    def test_required_evidence_fields_must_match_spec(self) -> None:
        fields = list(REQUIRED_EVIDENCE_OUTPUT_FIELDS)
        fields.remove("journal_ref_requirement")
        entry = _entry(required_evidence_output_fields=fields)
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "required_evidence_output_fields_invalid",
        )

    def test_required_mutation_summary_fields_must_match_spec(self) -> None:
        fields = list(REQUIRED_MUTATION_SUMMARY_FIELDS)
        fields.remove("rollback_summary_requirement")
        entry = _entry(required_mutation_summary_fields=fields)
        allowlist = _allowlist(allowlist_entries=[entry])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "required_mutation_summary_fields_invalid",
        )

    def test_duplicate_repository_method_pair_rejected(self) -> None:
        allowlist = _allowlist(allowlist_entries=[_entry(), _entry()])
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "allowlist_entry_duplicate",
        )


class RequiredDeclarationTests(unittest.TestCase):
    def test_each_required_declaration_non_bool_rejected(self) -> None:
        for flag in REQUIRED_TRUE_FLAGS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(flag=flag, bad=type(bad).__name__):
                    allowlist = _allowlist(**{flag: bad})
                    _assert_rejected_with(
                        _payload(allowlist=allowlist),
                        "required_declaration_invalid",
                    )

    def test_each_required_declaration_false_rejected(self) -> None:
        for flag in REQUIRED_TRUE_FLAGS:
            with self.subTest(flag=flag):
                allowlist = _allowlist(**{flag: False})
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "required_declaration_false",
                )


class AuthorizationFlagTests(unittest.TestCase):
    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(flag=flag, bad=type(bad).__name__):
                    allowlist = _allowlist(**{flag: bad})
                    _assert_rejected_with(
                        _payload(allowlist=allowlist),
                        "authorization_flag_invalid",
                    )

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                allowlist = _allowlist(**{flag: True})
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "authorization_flag_true",
                )


class JsonSafeTests(unittest.TestCase):
    def test_json_safe_false_rejected(self) -> None:
        allowlist = _allowlist(json_safe=False)
        _assert_rejected_with(
            _payload(allowlist=allowlist),
            "json_safe_invalid",
        )

    def test_json_safe_non_bool_rejected(self) -> None:
        for bad in (None, "true", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                allowlist = _allowlist(json_safe=bad)
                _assert_rejected_with(
                    _payload(allowlist=allowlist),
                    "json_safe_invalid",
                )


class FailureOrderingTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        entry = _entry(
            method_name="*",
            read_write_classification="write_now",
            json_safe_result_required=False,
        )
        entry["required_evidence_output_fields"] = ["target_artifact_id"]
        allowlist = _allowlist(
            surface="OtherSurface",
            version=True,
            allowlist_entries=[entry, entry],
            fail_closed_declared=False,
            json_safe=False,
            executor_implementation_authorized=True,
        )
        allowlist["source_preflight_read_only_stack_tag"] = "wrong-tag"
        result = validate_repository_uow_allowlist(
            _payload(allowlist=allowlist)
        )
        self.assertFalse(result["allowlist_ready"])
        positions = [FAILURE_ORDER.index(item) for item in result["failures"]]
        self.assertEqual(positions, sorted(positions))


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = repository_uow_allowlist_validator_manifest()
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        first = repository_uow_allowlist_validator_manifest()
        first["mutated"] = "x"
        first["depends_on"]["mutated"] = "y"
        first["failure_values"].append("mutated")
        second = repository_uow_allowlist_validator_manifest()
        self.assertEqual(second, EXPECTED_MANIFEST)
        self.assertNotIn("mutated", second)
        self.assertNotIn("mutated", second["depends_on"])
        self.assertNotIn("mutated", second["failure_values"])


class JsonSafetyTests(unittest.TestCase):
    def test_output_json_safe(self) -> None:
        result = validate_repository_uow_allowlist(_payload())
        _assert_json_safe(result)

    def test_manifest_json_safe(self) -> None:
        manifest = repository_uow_allowlist_validator_manifest()
        _assert_json_safe(manifest)

    def test_no_runtime_repr_leakage(self) -> None:
        result = validate_repository_uow_allowlist(_payload())
        _assert_no_runtime_repr(result)


class InputImmutabilityTests(unittest.TestCase):
    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)
        validate_repository_uow_allowlist(payload)
        self.assertEqual(payload, snapshot)


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(validator_module.__all__),
            sorted(
                [
                    "repository_uow_allowlist_validator_manifest",
                    "validate_repository_uow_allowlist",
                ]
            ),
        )

    def test_signatures(self) -> None:
        manifest_sig = inspect.signature(
            repository_uow_allowlist_validator_manifest
        )
        self.assertEqual(list(manifest_sig.parameters.keys()), [])
        validate_sig = inspect.signature(validate_repository_uow_allowlist)
        self.assertEqual(list(validate_sig.parameters.keys()), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_only_allowed_production_imports(self) -> None:
        source = inspect.getsource(validator_module)
        import_lines = [
            line.strip()
            for line in source.splitlines()
            if line.startswith("from ") or line.startswith("import ")
        ]
        self.assertEqual(
            import_lines,
            [
                "from collections.abc import Mapping as _Mapping",
                "from copy import deepcopy as _deepcopy",
            ],
        )

    def test_source_boundary_forbids_external_runtime_coupling(self) -> None:
        source = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_hidden_wall_clock_dependency(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
            "datetime.now",
            "time.time",
            "time.monotonic",
            "perf_counter",
            "wall_clock",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_timestamp_parsing(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
            "fromisoformat",
            "strptime",
            "isoformat",
            "tzinfo",
            "utcoffset",
            "timezone",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_digest_computation(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
            "hashlib",
            "hmac",
            "secrets",
            "sha1",
            "sha256",
            "sha512",
            "blake2",
            "md5",
            "digest",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
