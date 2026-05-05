"""Tracer-bullet tests for the write path contract validator CI consumer."""

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

from kernel.lifecycle import write_path_contract_validator_ci as ci_module
from kernel.lifecycle.write_path_contract_validator_ci import (
    consume_write_path_contract_validator_ci,
    write_path_contract_validator_ci_manifest,
)


SOURCE_BINDING_VALUES = {
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
}


SOURCE_BINDING_FAILURES = {
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
}


REQUIRED_FIELDS = (
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


REQUIRED_DECLARATION_FLAGS = (
    "after_evidence_required",
    "outer_transaction_required",
    "kernel_owned_transaction_required",
    "uncontrolled_nested_transactions_forbidden",
    "direct_executor_sqlite_forbidden",
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
    "direct_sqlite_forbidden",
    "ad_hoc_sql_forbidden",
    "filesystem_side_channel_forbidden",
    "repository_uow_allowlist_required",
    "one_uow_boundary_per_attempt_required",
    "service_side_effects_forbidden",
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
    "evidence_append_authorized",
    "audit_append_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
)


EXECUTION_WRITE_FAILURES = {
    "executes_plan": ("execution_flag_invalid", "execution_flag_true"),
    "opens_db": ("opens_db_invalid", "opens_db_true"),
    "appends_evidence": ("appends_evidence_invalid", "appends_evidence_true"),
}


FAILURE_ORDER = [
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
]


EXPECTED_MANIFEST = {
    "surface": "write_path_contract_validator_ci",
    "version": 1,
    "input_shape": "already_rendered_write_path_contract_validator_output",
    "depends_on": {
        "write_path_contract_validator": "write-path-contract-validator-v1",
        "write_path_transaction_evidence_idempotency_spec_only": (
            "write-path-transaction-evidence-idempotency-spec-only-v1"
        ),
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
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
    "executes_plan": False,
    "opens_db": False,
    "appends_evidence": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        "invalid_ci_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": FAILURE_ORDER,
}


EXPECTED_OUTPUT_KEYS = [
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
    "direct_executor_sqlite_forbidden",
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
    "direct_sqlite_forbidden",
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
]


REPR_MARKERS = (
    "WritePathContractValidatorCI(",
    " object at 0x",
    "<sqlite3.",
)


FORBIDDEN_SOURCE_MARKERS = (
    "datetime",
    "time",
    "sqlite",
    "open_connection",
    "Repository",
    "UnitOfWork",
    "KernelUnitOfWork",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "evidence_service",
    "append_audit",
    "append_evidence",
    "subprocess",
    "os.environ",
    "argparse",
    "click",
    "socket",
    "queue",
    "threading",
    "asyncio",
    "datetime.now",
    "time.time",
    "time.monotonic",
    "hashlib",
    "hmac",
    "secrets",
    "sha256",
    "blake2",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "signable_path_orchestrator",
    "apply_migrations",
    "open(",
    "Path(",
    "audit",
    "evidence append",
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
    "write_path_contract_validator_ci",
    "write_path_contract_validator",
    "write-path-contract-validator-v1",
    "write-path-transaction-evidence-idempotency-spec-only-v1",
    "executor-precondition-read-only-stack-v1",
    "execution-authorization-read-only-stack-v1",
    "preflight-read-only-stack-v1",
    "restore-dry-run-read-only-stack-v1",
    "write-side-recovery-spec-only-v1",
    "write_side_precondition_ci",
    "write_side_precondition_checker",
    "projected_evidence_ref",
    "before_evidence_ref",
    "mutation_intent_evidence_before_mutation_required",
    "deterministic_evidence_audit_order_required",
    "evidence_append_authorized",
    "audit_append_authorized",
    "daemon_server_queue_authorized",
)


def _contract(**overrides: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "surface": "write_path_contract_validator",
        "version": 1,
    }
    contract.update(SOURCE_BINDING_VALUES)
    for index, field in enumerate(REQUIRED_FIELDS):
        contract[field] = f"field-{index}-value"
    for flag in REQUIRED_DECLARATION_FLAGS:
        contract[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        contract[flag] = False
    contract["fail_closed_declared"] = True
    contract["json_safe"] = True
    contract["executes_plan"] = False
    contract["opens_db"] = False
    contract["appends_evidence"] = False
    contract.update(overrides)
    return contract


def _payload(**overrides: object) -> dict[str, object]:
    contract = overrides.pop("contract", _contract())
    payload: dict[str, object] = {
        "write_path_contract_ready": True,
        "reason_code": "ready",
        "failures": [],
        "contract": contract,
    }
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    output: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "write_path_contract_validator",
        "version": 1,
        "write_path_contract_ready": True,
        "write_path_contract_reason_code": "ready",
        "write_path_contract_failures": [],
    }
    output.update(SOURCE_BINDING_VALUES)
    for index, field in enumerate(REQUIRED_FIELDS):
        output[field] = f"field-{index}-value"
    for flag in REQUIRED_DECLARATION_FLAGS:
        output[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        output[flag] = False
    output["executes_plan"] = False
    output["opens_db"] = False
    output["appends_evidence"] = False
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
    result = consume_write_path_contract_validator_ci(payload)
    if result["ci_ok"] is not False:
        raise AssertionError("CI result unexpectedly ok")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = consume_write_path_contract_validator_ci(_payload())

        self.assertEqual(result, _expected_happy_output())

    def test_ci_ok_true_does_not_authorize_executor_restore_write_db_evidence(
        self,
    ) -> None:
        result = consume_write_path_contract_validator_ci(_payload())

        self.assertIs(result["ci_ok"], True)
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result[flag], False)
        self.assertIs(result["executes_plan"], False)
        self.assertIs(result["opens_db"], False)
        self.assertIs(result["appends_evidence"], False)

    def test_exact_output_shape(self) -> None:
        result = consume_write_path_contract_validator_ci(_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_top_level_rejected(self) -> None:
        for candidate in (None, 1, "x", [1, 2], (1, 2), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = consume_write_path_contract_validator_ci(candidate)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _payload()
        del payload["contract"]

        result = _assert_rejected_with(payload, "payload_shape_mismatch")

        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_unknown_top_level_key_rejected(self) -> None:
        result = _assert_rejected_with(
            _payload(extra="unexpected"),
            "payload_shape_mismatch",
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_contract_not_ready_when_ready_false(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(write_path_contract_ready=False)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_not_ready"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_contract_invalid_when_reason_code_not_ready(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_contract_invalid_when_failures_not_empty(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(failures=["required_field_invalid"])
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_invalid"])
        self.assertEqual(
            result["write_path_contract_failures"],
            ["required_field_invalid"],
        )
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class ContractShapeTests(unittest.TestCase):
    def test_contract_non_mapping_rejected(self) -> None:
        for candidate in (None, 1, "x", [1], object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=candidate)
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["failures"], ["contract_invalid"])
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_contract_missing_key_rejected(self) -> None:
        contract = _contract()
        del contract["approved_task_id"]

        result = consume_write_path_contract_validator_ci(
            _payload(contract=contract)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(
            result["failures"],
            ["contract_invalid", "required_field_invalid"],
        )
        self.assertEqual(result["approved_task_id"], None)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_contract_unknown_key_rejected(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(extra="unexpected"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_contract_surface_rejected(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(surface="other_surface"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_surface_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_version_rejected(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(version=2))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_version_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_bool_as_int_version_rejected(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(version=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["contract_version_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class SourceBindingTests(unittest.TestCase):
    def _assert_source_mismatch(self, field: str) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(**{field: "wrong"}))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(
            result["failures"],
            [SOURCE_BINDING_FAILURES[field]],
        )
        self.assertEqual(result[field], "wrong")
        self.assertEqual(result["reason_code"], "not_ready")

    def test_source_restore_stack_tag_mismatch(self) -> None:
        self._assert_source_mismatch(
            "source_restore_dry_run_read_only_stack_tag"
        )

    def test_source_restore_stack_commit_mismatch(self) -> None:
        self._assert_source_mismatch(
            "source_restore_dry_run_read_only_stack_commit"
        )

    def test_source_preflight_stack_tag_mismatch(self) -> None:
        self._assert_source_mismatch("source_preflight_read_only_stack_tag")

    def test_source_preflight_stack_commit_mismatch(self) -> None:
        self._assert_source_mismatch("source_preflight_read_only_stack_commit")

    def test_source_execution_authorization_stack_tag_mismatch(self) -> None:
        self._assert_source_mismatch(
            "source_execution_authorization_read_only_stack_tag"
        )

    def test_source_execution_authorization_stack_commit_mismatch(self) -> None:
        self._assert_source_mismatch(
            "source_execution_authorization_read_only_stack_commit"
        )

    def test_source_executor_precondition_stack_tag_mismatch(self) -> None:
        self._assert_source_mismatch(
            "source_executor_precondition_read_only_stack_tag"
        )

    def test_source_executor_precondition_stack_commit_mismatch(self) -> None:
        self._assert_source_mismatch(
            "source_executor_precondition_read_only_stack_commit"
        )


class FieldValidationTests(unittest.TestCase):
    def test_each_required_field_invalid_rejected(self) -> None:
        for field in REQUIRED_FIELDS:
            for value in ("", 123, [], {}, True):
                with self.subTest(field=field, value=type(value).__name__):
                    result = consume_write_path_contract_validator_ci(
                        _payload(contract=_contract(**{field: value}))
                    )

                    self.assertIs(result["ci_ok"], False)
                    self.assertEqual(
                        result["failures"],
                        ["required_field_invalid"],
                    )
                    self.assertEqual(result[field], None)
                    self.assertEqual(
                        result["reason_code"], "invalid_ci_payload"
                    )

    def test_each_required_declaration_flag_non_bool_rejected(self) -> None:
        for flag in REQUIRED_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=_contract(**{flag: "true"}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"],
                    ["required_declaration_invalid"],
                )
                self.assertEqual(result[flag], None)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_required_declaration_flag_false_rejected(self) -> None:
        for flag in REQUIRED_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=_contract(**{flag: False}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"],
                    ["required_declaration_false"],
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=_contract(**{flag: "false"}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"],
                    ["authorization_flag_invalid"],
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=_contract(**{flag: True}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"],
                    ["authorization_flag_true"],
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_each_execution_write_flag_non_bool_rejected(self) -> None:
        for flag, (failure, _true_failure) in EXECUTION_WRITE_FAILURES.items():
            with self.subTest(flag=flag):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=_contract(**{flag: "false"}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["failures"], [failure])
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_execution_write_flag_true_rejected(self) -> None:
        for flag, (_invalid_failure, failure) in (
            EXECUTION_WRITE_FAILURES.items()
        ):
            with self.subTest(flag=flag):
                result = consume_write_path_contract_validator_ci(
                    _payload(contract=_contract(**{flag: True}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["failures"], [failure])
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_json_safe_false_rejected(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(json_safe=False))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(contract=_contract(json_safe="true"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class DeterminismAndSafetyTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        contract = _contract(
            surface="other_surface",
            version=True,
            source_restore_dry_run_read_only_stack_tag="wrong",
            source_preflight_read_only_stack_commit="wrong",
            execution_authorization_validator_ci_ref="",
            after_evidence_required="true",
            outer_transaction_required=False,
            executor_implementation_authorized="false",
            restore_execution_authorized=True,
            executes_plan="false",
            opens_db=True,
            appends_evidence="false",
            json_safe=False,
            extra="unexpected",
        )
        result = consume_write_path_contract_validator_ci(
            _payload(
                write_path_contract_ready=False,
                reason_code="not_ready",
                failures=["contract_not_ready"],
                contract=contract,
                extra="unexpected",
            )
        )

        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "contract_not_ready",
                "contract_invalid",
                "contract_surface_invalid",
                "contract_version_invalid",
                "source_restore_dry_run_stack_tag_mismatch",
                "source_preflight_stack_commit_mismatch",
                "required_field_invalid",
                "required_declaration_invalid",
                "required_declaration_false",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "execution_flag_invalid",
                "opens_db_true",
                "appends_evidence_invalid",
                "json_safe_invalid",
            ],
        )
        positions = [FAILURE_ORDER.index(item) for item in result["failures"]]
        self.assertEqual(positions, sorted(positions))

    def test_output_json_safe(self) -> None:
        _assert_json_safe(
            consume_write_path_contract_validator_ci(_payload())
        )

    def test_no_runtime_repr_leakage(self) -> None:
        result = consume_write_path_contract_validator_ci(
            _payload(
                failures=[object()],
                contract=_contract(
                    approved_task_id=object(),
                    after_evidence_required=object(),
                ),
            )
        )

        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)

        consume_write_path_contract_validator_ci(payload)

        self.assertEqual(payload, snapshot)

    def test_no_hidden_wall_clock_dependency(self) -> None:
        payload = _payload()

        self.assertEqual(
            consume_write_path_contract_validator_ci(payload),
            consume_write_path_contract_validator_ci(payload),
        )


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            write_path_contract_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = write_path_contract_validator_ci_manifest()
        assert isinstance(manifest["runtime_dependencies"], list)
        assert isinstance(manifest["depends_on"], dict)
        manifest["runtime_dependencies"].append("unexpected")
        manifest["depends_on"]["unexpected"] = "unexpected"

        self.assertEqual(
            write_path_contract_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "write_path_contract_validator_ci_manifest",
                "consume_write_path_contract_validator_ci",
            ],
        )
        public = {
            name for name in dir(ci_module) if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {
                "write_path_contract_validator_ci_manifest",
                "consume_write_path_contract_validator_ci",
            },
        )

    def test_callable_signatures(self) -> None:
        manifest_sig = inspect.signature(
            write_path_contract_validator_ci_manifest
        )
        self.assertEqual(list(manifest_sig.parameters), [])

        consume_sig = inspect.signature(
            consume_write_path_contract_validator_ci
        )
        self.assertEqual(list(consume_sig.parameters), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary(self) -> None:
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

    def test_no_hidden_wall_clock_dependency(self) -> None:
        source = _scrubbed_source()

        for marker in (
            "datetime",
            "time",
            "datetime.now",
            "time.time",
            "time.monotonic",
            "perf_counter",
            "wall_clock",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_timestamp_parsing(self) -> None:
        source = inspect.getsource(ci_module)

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
        source = _scrubbed_source()

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

    def test_no_validator_upstream_service_db_cli_or_recovery_imports(
        self,
    ) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
