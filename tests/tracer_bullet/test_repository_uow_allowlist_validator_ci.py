"""Tracer-bullet tests for the repository/UoW allowlist validator CI consumer."""

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

from kernel.lifecycle import repository_uow_allowlist_validator_ci as ci_module
from kernel.lifecycle.repository_uow_allowlist_validator_ci import (
    consume_repository_uow_allowlist_validator_ci,
    repository_uow_allowlist_validator_ci_manifest,
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
}


ENTRY_COUNT_FIELDS = (
    "allowlist_entry_count",
    "read_only_entry_count",
    "mutation_declared_but_not_authorized_entry_count",
    "future_write_candidate_entry_count",
)


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


RUNTIME_FLAGS = (
    "opens_db",
    "calls_repository",
    "calls_uow",
    "calls_services",
    "appends_evidence",
    "executes_plan",
)


VALIDATOR_FAILURE_TAXONOMY = (
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


FAILURE_ORDER = [
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
]


EXPECTED_MANIFEST = {
    "surface": "repository_uow_allowlist_validator_ci",
    "version": 1,
    "input_shape": (
        "already_rendered_repository_uow_allowlist_validator_output"
    ),
    "depends_on": {
        "repository_uow_allowlist_validator": (
            "repository-uow-allowlist-validator-v1"
        ),
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
        "write_side_recovery_spec_only": (
            "write-side-recovery-spec-only-v1"
        ),
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
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
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        "invalid_ci_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": list(FAILURE_ORDER),
}


EXPECTED_OUTPUT_KEYS = (
    [
        "ci_ok",
        "reason_code",
        "failures",
        "surface",
        "version",
    ]
    + list(SOURCE_BINDING_VALUES.keys())
    + [
        "allowlist_ready",
        "allowlist_reason_code",
        "allowlist_failures",
    ]
    + list(ENTRY_COUNT_FIELDS)
    + list(REQUIRED_TRUE_FLAGS)
    + list(AUTHORIZATION_FLAGS)
    + list(RUNTIME_FLAGS)
    + ["json_safe"]
)


REPR_MARKERS = (
    " object at 0x",
    "<sqlite3.",
)


FORBIDDEN_SOURCE_MARKERS = (
    "datetime.now",
    "time.time",
    "time.monotonic",
    "perf_counter",
    "wall_clock",
    "hashlib",
    "hmac",
    "secrets",
    "sha1",
    "sha256",
    "sha512",
    "blake2",
    "md5",
    "digest",
    "fromisoformat",
    "strptime",
    "isoformat",
    "tzinfo",
    "utcoffset",
    "timezone",
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
    "Repository",
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
    "repository_uow_allowlist_validator_manifest(",
    "validate_repository_uow_allowlist(",
)


ALLOWED_SOURCE_FIELD_STRINGS = (
    "repository_uow_allowlist_validator_ci_manifest",
    "consume_repository_uow_allowlist_validator_ci",
    "repository_uow_allowlist_validator_ci",
    "repository_uow_allowlist_validator",
    "repository-uow-allowlist-validator-v1",
    "repository-uow-allowlist-spec-only-v1",
    "write-path-read-only-stack-v1",
    "executor-precondition-read-only-stack-v1",
    "execution-authorization-read-only-stack-v1",
    "preflight-read-only-stack-v1",
    "restore-dry-run-read-only-stack-v1",
    "write-side-recovery-spec-only-v1",
    "write-side-precondition-ci-v1",
    "write-side-precondition-checker-v1",
    "read-only-governance-layer-v1",
    "required_evidence_output_fields_invalid",
    "required_mutation_summary_fields_invalid",
    "evidence_append_authorized",
    "audit_append_authorized",
    "evidence_audit_append_forbidden",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "evidence_service_authorized",
    "daemon_server_queue_authorized",
)


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "allowlist_ready": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "repository_uow_allowlist_validator",
        "version": 1,
    }
    payload.update(SOURCE_BINDING_VALUES)
    payload["allowlist_entry_count"] = 3
    payload["read_only_entry_count"] = 1
    payload["mutation_declared_but_not_authorized_entry_count"] = 1
    payload["future_write_candidate_entry_count"] = 1
    for flag in REQUIRED_TRUE_FLAGS:
        payload[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        payload[flag] = False
    for flag in RUNTIME_FLAGS:
        payload[flag] = False
    payload["json_safe"] = True
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    output: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "repository_uow_allowlist_validator_ci",
        "version": 1,
    }
    output.update(SOURCE_BINDING_VALUES)
    output["allowlist_ready"] = True
    output["allowlist_reason_code"] = "ready"
    output["allowlist_failures"] = []
    output["allowlist_entry_count"] = 3
    output["read_only_entry_count"] = 1
    output["mutation_declared_but_not_authorized_entry_count"] = 1
    output["future_write_candidate_entry_count"] = 1
    for flag in REQUIRED_TRUE_FLAGS:
        output[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        output[flag] = False
    for flag in RUNTIME_FLAGS:
        output[flag] = False
    output["json_safe"] = True
    return output


def _recursive_values(payload: object) -> list[object]:
    values = [payload]
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
    source = inspect.getsource(ci_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


def _assert_rejected_with(
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = consume_repository_uow_allowlist_validator_ci(payload)
    if result["ci_ok"] is not False:
        raise AssertionError("CI result unexpectedly ok")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(_payload())

        self.assertEqual(result, _expected_happy_output())

    def test_ci_ok_true_does_not_authorize_writes_executor_restore(
        self,
    ) -> None:
        result = consume_repository_uow_allowlist_validator_ci(_payload())

        self.assertIs(result["ci_ok"], True)
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result[flag], False)
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result[flag], False)

    def test_exact_output_shape(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)

    def test_output_surface_identifies_ci_consumer(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(_payload())

        self.assertEqual(
            result["surface"], "repository_uow_allowlist_validator_ci"
        )
        self.assertEqual(result["version"], 1)
        self.assertNotEqual(
            result["surface"], "repository_uow_allowlist_validator"
        )

    def test_output_surface_identifies_ci_consumer_on_rejection(
        self,
    ) -> None:
        result = consume_repository_uow_allowlist_validator_ci(None)

        self.assertEqual(
            result["surface"], "repository_uow_allowlist_validator_ci"
        )
        self.assertEqual(result["version"], 1)

    def test_input_validator_surface_still_required(self) -> None:
        payload = _payload()

        self.assertEqual(
            payload["surface"], "repository_uow_allowlist_validator"
        )

        result = consume_repository_uow_allowlist_validator_ci(payload)

        self.assertIs(result["ci_ok"], True)
        self.assertNotIn("validator_surface_invalid", result["failures"])

    def test_wrong_input_validator_surface_still_fails(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(surface="repository_uow_allowlist_validator_ci")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("validator_surface_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["surface"], "repository_uow_allowlist_validator_ci"
        )


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload_rejected(self) -> None:
        for candidate in (None, 1, "x", [1, 2], (1, 2), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = consume_repository_uow_allowlist_validator_ci(
                    candidate
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )
                self.assertEqual(
                    result["failures"], ["payload_not_mapping"]
                )

    def test_missing_key_rejected(self) -> None:
        payload = _payload()
        del payload["allowlist_entry_count"]

        result = _assert_rejected_with(payload, "payload_shape_mismatch")

        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_unknown_key_rejected(self) -> None:
        result = _assert_rejected_with(
            _payload(extra="unexpected"),
            "payload_shape_mismatch",
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_allowlist_ready_non_bool_rejected(self) -> None:
        for candidate in ("true", 1, 0, None, [], {}):
            with self.subTest(candidate=type(candidate).__name__):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(allowlist_ready=candidate)
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )
                self.assertIn("payload_shape_mismatch", result["failures"])


class ReadinessLogicTests(unittest.TestCase):
    def test_allowlist_not_ready_false_with_valid_failures(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(
                allowlist_ready=False,
                reason_code="not_ready",
                failures=["required_declaration_false"],
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["allowlist_not_ready"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIs(result["allowlist_ready"], False)
        self.assertEqual(result["allowlist_reason_code"], "not_ready")
        self.assertEqual(
            result["allowlist_failures"], ["required_declaration_false"]
        )

    def test_allowlist_ready_true_non_ready_reason_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("allowlist_reason_code_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_allowlist_ready_true_non_empty_failures_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(failures=["required_declaration_false"])
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("allowlist_failures_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_allowlist_ready_false_empty_failures_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(allowlist_ready=False, reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("allowlist_failures_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_invalid_reason_code_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(allowlist_ready=False, reason_code="weird_reason")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("allowlist_reason_code_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_failures_non_list_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(failures="oops")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("allowlist_failures_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_failures_value_outside_validator_taxonomy_rejected(
        self,
    ) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(
                allowlist_ready=False,
                reason_code="not_ready",
                failures=["totally_unknown_failure_value"],
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn(
            "allowlist_failure_value_invalid", result["failures"]
        )
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_validator_taxonomy_value_accepted_in_failures(
        self,
    ) -> None:
        for value in VALIDATOR_FAILURE_TAXONOMY:
            with self.subTest(value=value):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(
                        allowlist_ready=False,
                        reason_code="not_ready",
                        failures=[value],
                    )
                )

                self.assertNotIn(
                    "allowlist_failure_value_invalid",
                    result["failures"],
                )


class ValidatorIdentityTests(unittest.TestCase):
    def test_wrong_validator_surface_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(surface="other_surface")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("validator_surface_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_validator_version_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(version=2)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("validator_version_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_bool_as_int_validator_version_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(version=True)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("validator_version_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class SourceBindingTests(unittest.TestCase):
    def _assert_source_mismatch(self, field: str) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(**{field: "wrong"})
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn(SOURCE_BINDING_FAILURES[field], result["failures"])
        self.assertEqual(result[field], "wrong")
        self.assertEqual(result["reason_code"], "not_ready")

    def test_every_source_pair_mismatch(self) -> None:
        for field in SOURCE_BINDING_FAILURES:
            with self.subTest(field=field):
                self._assert_source_mismatch(field)


class EntryCountTests(unittest.TestCase):
    def test_entry_count_non_int_rejected(self) -> None:
        for field in ENTRY_COUNT_FIELDS:
            with self.subTest(field=field):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{field: "1"})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn("entry_count_invalid", result["failures"])
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_entry_count_bool_rejected(self) -> None:
        for field in ENTRY_COUNT_FIELDS:
            with self.subTest(field=field):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{field: True})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn("entry_count_invalid", result["failures"])
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_entry_count_negative_rejected(self) -> None:
        for field in ENTRY_COUNT_FIELDS:
            with self.subTest(field=field):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{field: -1})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn("entry_count_invalid", result["failures"])
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_ready_with_zero_entry_count_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(
                allowlist_entry_count=0,
                read_only_entry_count=0,
                mutation_declared_but_not_authorized_entry_count=0,
                future_write_candidate_entry_count=0,
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("entry_count_mismatch", result["failures"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_entry_count_sum_mismatch_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(
                allowlist_entry_count=4,
                read_only_entry_count=1,
                mutation_declared_but_not_authorized_entry_count=1,
                future_write_candidate_entry_count=1,
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("entry_count_mismatch", result["failures"])
        self.assertEqual(result["reason_code"], "not_ready")


class FlagValidationTests(unittest.TestCase):
    def test_each_required_declaration_non_bool_rejected(self) -> None:
        for flag in REQUIRED_TRUE_FLAGS:
            with self.subTest(flag=flag):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{flag: "true"})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn(
                    "required_declaration_invalid", result["failures"]
                )
                self.assertEqual(result[flag], None)
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_each_required_declaration_false_rejected(self) -> None:
        for flag in REQUIRED_TRUE_FLAGS:
            with self.subTest(flag=flag):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{flag: False})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn(
                    "required_declaration_false", result["failures"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{flag: "false"})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn(
                    "authorization_flag_invalid", result["failures"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{flag: True})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn(
                    "authorization_flag_true", result["failures"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_each_runtime_flag_non_bool_rejected(self) -> None:
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{flag: "false"})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn("runtime_flag_invalid", result["failures"])
                self.assertIs(result[flag], False)
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_each_runtime_flag_true_rejected(self) -> None:
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                result = consume_repository_uow_allowlist_validator_ci(
                    _payload(**{flag: True})
                )

                self.assertIs(result["ci_ok"], False)
                self.assertIn("runtime_flag_true", result["failures"])
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_json_safe_false_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(json_safe=False)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("json_safe_invalid", result["failures"])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(json_safe="true")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertIn("json_safe_invalid", result["failures"])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class DeterminismAndSafetyTests(unittest.TestCase):
    def test_allowlist_failures_deep_copied(self) -> None:
        original = ["required_declaration_false"]
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(
                allowlist_ready=False,
                reason_code="not_ready",
                failures=original,
            )
        )

        self.assertEqual(
            result["allowlist_failures"], ["required_declaration_false"]
        )
        result_failures = result["allowlist_failures"]
        assert isinstance(result_failures, list)
        result_failures.append("mutation")

        self.assertEqual(original, ["required_declaration_false"])

    def test_output_json_safe(self) -> None:
        _assert_json_safe(
            consume_repository_uow_allowlist_validator_ci(_payload())
        )

    def test_output_no_raw_declaration_or_entries_leakage(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(_payload())

        encoded = json.dumps(result, sort_keys=True)
        for marker in (
            "allowlist_entries",
            "method_owner",
            "rollback_behavior",
            "required_uow_context",
            "required_idempotency_binding",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, encoded)

    def test_no_runtime_repr_leakage(self) -> None:
        result = consume_repository_uow_allowlist_validator_ci(
            _payload(
                allowlist_ready=False,
                reason_code="not_ready",
                failures=[object()],
            )
        )

        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)

        consume_repository_uow_allowlist_validator_ci(payload)

        self.assertEqual(payload, snapshot)

    def test_no_hidden_wall_clock_dependency(self) -> None:
        payload = _payload()

        self.assertEqual(
            consume_repository_uow_allowlist_validator_ci(payload),
            consume_repository_uow_allowlist_validator_ci(payload),
        )

    def test_combined_failures_deterministic_order(self) -> None:
        payload = _payload(
            surface="other_surface",
            version=True,
            source_read_only_governance_layer_tag="wrong",
            source_preflight_read_only_stack_commit="wrong",
            allowlist_entry_count=99,
            ad_hoc_sql_forbidden=False,
            executor_implementation_authorized=True,
            opens_db=True,
            json_safe=False,
        )

        result = consume_repository_uow_allowlist_validator_ci(payload)

        positions = [
            FAILURE_ORDER.index(item) for item in result["failures"]
        ]
        self.assertEqual(positions, sorted(positions))


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            repository_uow_allowlist_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = repository_uow_allowlist_validator_ci_manifest()
        assert isinstance(manifest["runtime_dependencies"], list)
        assert isinstance(manifest["depends_on"], dict)
        manifest["runtime_dependencies"].append("unexpected")
        manifest["depends_on"]["unexpected"] = "unexpected"

        self.assertEqual(
            repository_uow_allowlist_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "repository_uow_allowlist_validator_ci_manifest",
                "consume_repository_uow_allowlist_validator_ci",
            ],
        )
        public = {
            name for name in dir(ci_module) if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {
                "repository_uow_allowlist_validator_ci_manifest",
                "consume_repository_uow_allowlist_validator_ci",
            },
        )

    def test_callable_signatures(self) -> None:
        manifest_sig = inspect.signature(
            repository_uow_allowlist_validator_ci_manifest
        )
        self.assertEqual(list(manifest_sig.parameters), [])

        consume_sig = inspect.signature(
            consume_repository_uow_allowlist_validator_ci
        )
        self.assertEqual(list(consume_sig.parameters), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary_required_forbidden(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_datetime_or_time_import(self) -> None:
        source = inspect.getsource(ci_module)

        for marker in (
            "import datetime",
            "from datetime",
            "import time",
            "from time",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_validator_import(self) -> None:
        source = inspect.getsource(ci_module)

        for marker in (
            "from kernel.lifecycle.repository_uow_allowlist_validator",
            "import repository_uow_allowlist_validator\n",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_repository_uow_service_db_cli_recovery_imports(
        self,
    ) -> None:
        source = inspect.getsource(ci_module)

        for marker in (
            "from kernel.repositories",
            "import repositories",
            "from kernel.unit_of_work",
            "import unit_of_work",
            "from kernel.services",
            "import services",
            "from kernel.lifecycle.recovery",
            "from kernel.lifecycle.signable_path",
            "from kernel.lifecycle.real_fix",
            "import sqlite3",
            "from sqlite3",
            "from kernel.lifecycle.recovery_cli",
            "from kernel.lifecycle.recovery_session_host",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_validator_or_ci_imports(self) -> None:
        source = inspect.getsource(ci_module)

        for marker in (
            "from kernel.lifecycle.write_path_contract_validator",
            "from kernel.lifecycle.executor_precondition_validator",
            "from kernel.lifecycle.execution_authorization_validator",
            "from kernel.lifecycle.execution_preflight",
            "from kernel.lifecycle.preflight_aggregate_summary",
            "from kernel.lifecycle.human_approval_readiness",
            "from kernel.lifecycle.restore_dry_run_readiness",
            "from kernel.lifecycle.restore_dry_run_aggregate_summary",
            "from kernel.lifecycle.governance_readiness_aggregator",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
