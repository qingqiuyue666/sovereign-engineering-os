"""Tracer-bullet tests for the executor precondition validator CI consumer."""

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

from kernel.lifecycle import executor_precondition_validator_ci as ci_module
from kernel.lifecycle.executor_precondition_validator_ci import (
    consume_executor_precondition_validator_ci,
    executor_precondition_validator_ci_manifest,
)


EXPECTED_MANIFEST = {
    "surface": "executor_precondition_validator_ci",
    "version": 1,
    "input_shape": "already_rendered_executor_precondition_validator_output",
    "depends_on": {
        "executor_precondition_validator": "executor-precondition-validator-v1",
        "executor_precondition_contract_spec_only": (
            "executor-precondition-contract-spec-only-v1"
        ),
        "execution_authorization_read_only_stack": (
            "execution-authorization-read-only-stack-v1"
        ),
        "execution_authorization_validator_ci": (
            "execution-authorization-validator-ci-v1"
        ),
        "execution_authorization_validator": (
            "execution-authorization-validator-v1"
        ),
        "execution_authorization_spec_only": (
            "execution-authorization-spec-only-v1"
        ),
        "preflight_read_only_stack": "preflight-read-only-stack-v1",
        "preflight_aggregate_summary": "preflight-aggregate-summary-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
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
    "durable_writes": False,
    "executes_plan": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        "invalid_ci_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "precondition_not_ready",
        "precondition_invalid",
        "precondition_surface_invalid",
        "precondition_version_invalid",
        "required_field_invalid",
        "required_declaration_invalid",
        "required_declaration_false",
        "no_go_declaration_invalid",
        "no_go_declaration_false",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "execution_flag_invalid",
        "execution_flag_true",
        "durable_writes_invalid",
        "durable_writes_true",
        "json_safe_invalid",
    ],
}


EXPECTED_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "executor_precondition_ready",
    "executor_precondition_reason_code",
    "executor_precondition_failures",
    "source_execution_authorization_read_only_stack_tag",
    "source_execution_authorization_read_only_stack_commit",
    "source_execution_authorization_validator_ci_ref",
    "source_preflight_read_only_stack_tag",
    "source_preflight_read_only_stack_commit",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "authorization_issuer",
    "authorization_reason",
    "executor_intent_ref",
    "executor_intent_created_at",
    "executor_intent_expires_at",
    "executor_mode",
    "evaluation_time",
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    "audit_append_required",
    "evidence_append_required",
    "expected_rejection_policy_required",
    "no_schema_migration_required",
    "no_daemon_server_queue_required",
    "no_cli_required",
    "no_db_repair_required",
    "irreversible_action_prohibited",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "fail_closed_declared",
    "json_safe",
    "executes_plan",
    "durable_writes",
]


PRECONDITION_KEYS = [
    "surface",
    "version",
    "source_execution_authorization_read_only_stack_tag",
    "source_execution_authorization_read_only_stack_commit",
    "source_execution_authorization_validator_ci_ref",
    "source_preflight_read_only_stack_tag",
    "source_preflight_read_only_stack_commit",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "authorization_issuer",
    "authorization_reason",
    "executor_intent_ref",
    "executor_intent_created_at",
    "executor_intent_expires_at",
    "executor_mode",
    "evaluation_time",
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    "audit_append_required",
    "evidence_append_required",
    "expected_rejection_policy_required",
    "no_schema_migration_required",
    "no_daemon_server_queue_required",
    "no_cli_required",
    "no_db_repair_required",
    "irreversible_action_prohibited",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "fail_closed_declared",
    "json_safe",
    "executes_plan",
    "durable_writes",
]


REQUIRED_STRING_FIELDS = (
    "source_execution_authorization_read_only_stack_tag",
    "source_execution_authorization_read_only_stack_commit",
    "source_execution_authorization_validator_ci_ref",
    "source_preflight_read_only_stack_tag",
    "source_preflight_read_only_stack_commit",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "authorization_issuer",
    "authorization_reason",
    "executor_intent_ref",
    "executor_intent_created_at",
    "executor_intent_expires_at",
    "executor_mode",
    "evaluation_time",
)


REQUIRED_DECLARATION_FLAGS = (
    "dry_run_required",
    "transaction_plan_required",
    "rollback_plan_required",
    "idempotency_reservation_required",
    "before_evidence_capture_required",
    "after_evidence_capture_required",
    "audit_append_required",
    "evidence_append_required",
    "expected_rejection_policy_required",
    "irreversible_action_prohibited",
    "fail_closed_declared",
)


NO_GO_DECLARATION_FLAGS = (
    "no_schema_migration_required",
    "no_daemon_server_queue_required",
    "no_cli_required",
    "no_db_repair_required",
)


AUTHORIZATION_FLAGS = (
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)


REPR_MARKERS = (
    "ExecutorPrecondition(",
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
    "validate_executor_precondition",
    "executor_precondition_validator_manifest",
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
    "executor_precondition_validator_ci",
    "executor_precondition_validator",
    "ExecutorPreconditionV1",
    "executor-precondition-validator-v1",
    "executor-precondition-contract-spec-only-v1",
    "execution-authorization-read-only-stack-v1",
    "execution-authorization-validator-ci-v1",
    "preflight-read-only-stack-v1",
    "source_execution_authorization_validator_ci_ref",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
    "no_daemon_server_queue_required",
    "audit_append_required",
    "evidence_append_required",
)


def _precondition(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "executor_precondition_validator",
        "version": 1,
        "source_execution_authorization_read_only_stack_tag": (
            "execution-authorization-read-only-stack-v1"
        ),
        "source_execution_authorization_read_only_stack_commit": (
            "d586aeb60620010c900df7be1a88621ab2cb8dc1"
        ),
        "source_execution_authorization_validator_ci_ref": "ci-ref-1",
        "source_preflight_read_only_stack_tag": "preflight-read-only-stack-v1",
        "source_preflight_read_only_stack_commit": (
            "662b6161253c35204b437e88809c5bab21908c6d"
        ),
        "approved_task_id": "T-1",
        "approved_operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "human_approval_ref": "AR-1",
        "operator_confirmation_ref": "CR-1",
        "authorization_issuer": "governance-board",
        "authorization_reason": "bounded executor eligibility review",
        "executor_intent_ref": "executor-intent/ref/1",
        "executor_intent_created_at": "2024-01-01T00:00:00Z",
        "executor_intent_expires_at": "2024-01-01T01:00:00Z",
        "executor_mode": "contract_only",
        "evaluation_time": "2024-01-01T00:30:00Z",
        "dry_run_required": True,
        "transaction_plan_required": True,
        "rollback_plan_required": True,
        "idempotency_reservation_required": True,
        "before_evidence_capture_required": True,
        "after_evidence_capture_required": True,
        "audit_append_required": True,
        "evidence_append_required": True,
        "expected_rejection_policy_required": True,
        "no_schema_migration_required": True,
        "no_daemon_server_queue_required": True,
        "no_cli_required": True,
        "no_db_repair_required": True,
        "irreversible_action_prohibited": True,
        "executor_implementation_authorized": False,
        "restore_execution_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "fail_closed_declared": True,
        "json_safe": True,
        "executes_plan": False,
        "durable_writes": False,
    }
    base.update(overrides)
    return base


def _payload(**overrides: object) -> dict[str, object]:
    precondition = overrides.pop("precondition", _precondition())
    base: dict[str, object] = {
        "executor_precondition_ready": True,
        "reason_code": "ready",
        "failures": [],
        "precondition": precondition,
    }
    base.update(overrides)
    return base


def _expected_happy_output() -> dict[str, object]:
    return {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "executor_precondition_validator",
        "version": 1,
        "executor_precondition_ready": True,
        "executor_precondition_reason_code": "ready",
        "executor_precondition_failures": [],
        "source_execution_authorization_read_only_stack_tag": (
            "execution-authorization-read-only-stack-v1"
        ),
        "source_execution_authorization_read_only_stack_commit": (
            "d586aeb60620010c900df7be1a88621ab2cb8dc1"
        ),
        "source_execution_authorization_validator_ci_ref": "ci-ref-1",
        "source_preflight_read_only_stack_tag": "preflight-read-only-stack-v1",
        "source_preflight_read_only_stack_commit": (
            "662b6161253c35204b437e88809c5bab21908c6d"
        ),
        "approved_task_id": "T-1",
        "approved_operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "human_approval_ref": "AR-1",
        "operator_confirmation_ref": "CR-1",
        "authorization_issuer": "governance-board",
        "authorization_reason": "bounded executor eligibility review",
        "executor_intent_ref": "executor-intent/ref/1",
        "executor_intent_created_at": "2024-01-01T00:00:00Z",
        "executor_intent_expires_at": "2024-01-01T01:00:00Z",
        "executor_mode": "contract_only",
        "evaluation_time": "2024-01-01T00:30:00Z",
        "dry_run_required": True,
        "transaction_plan_required": True,
        "rollback_plan_required": True,
        "idempotency_reservation_required": True,
        "before_evidence_capture_required": True,
        "after_evidence_capture_required": True,
        "audit_append_required": True,
        "evidence_append_required": True,
        "expected_rejection_policy_required": True,
        "no_schema_migration_required": True,
        "no_daemon_server_queue_required": True,
        "no_cli_required": True,
        "no_db_repair_required": True,
        "irreversible_action_prohibited": True,
        "executor_implementation_authorized": False,
        "restore_execution_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "fail_closed_declared": True,
        "json_safe": True,
        "executes_plan": False,
        "durable_writes": False,
    }


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


def _assert_rejected_with(payload: object, failure: str) -> dict[str, object]:
    result = consume_executor_precondition_validator_ci(payload)

    if result["ci_ok"] is not False:
        raise AssertionError("CI result unexpectedly ok")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = consume_executor_precondition_validator_ci(_payload())

        self.assertEqual(result, _expected_happy_output())

    def test_ci_ok_true_does_not_authorize_executor_restore_or_write_side(
        self,
    ) -> None:
        result = consume_executor_precondition_validator_ci(_payload())

        self.assertIs(result["ci_ok"], True)
        self.assertIs(result["executor_implementation_authorized"], False)
        self.assertIs(result["restore_execution_authorized"], False)
        self.assertIs(result["write_side_recovery_authorized"], False)
        self.assertIs(result["cli_execution_authorized"], False)
        self.assertIs(result["schema_migration_authorized"], False)
        self.assertIs(result["daemon_server_queue_authorized"], False)
        self.assertIs(result["db_repair_authorized"], False)
        self.assertIs(result["executes_plan"], False)
        self.assertIs(result["durable_writes"], False)

    def test_exact_output_shape(self) -> None:
        result = consume_executor_precondition_validator_ci(_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_top_level_rejected(self) -> None:
        for candidate in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(candidate=candidate):
                result = consume_executor_precondition_validator_ci(candidate)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _payload()
        del payload["precondition"]

        result = _assert_rejected_with(payload, "payload_shape_mismatch")

        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _payload(extra="unexpected")

        result = _assert_rejected_with(payload, "payload_shape_mismatch")

        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_executor_precondition_ready_false_rejected_as_not_ready(
        self,
    ) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(executor_precondition_ready=False)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["precondition_not_ready"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_wrong_reason_code_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["precondition_not_ready"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_non_empty_failures_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(failures=["precondition_expired"])
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["precondition_not_ready"])
        self.assertEqual(
            result["executor_precondition_failures"],
            ["precondition_expired"],
        )
        self.assertEqual(result["reason_code"], "not_ready")


class PreconditionShapeTests(unittest.TestCase):
    def test_precondition_non_mapping_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=object())
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["precondition_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_precondition_missing_key_rejected(self) -> None:
        precondition = _precondition()
        del precondition["approved_task_id"]

        result = consume_executor_precondition_validator_ci(
            _payload(precondition=precondition)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(
            result["failures"],
            ["precondition_invalid", "required_field_invalid"],
        )
        self.assertEqual(result["approved_task_id"], None)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_precondition_unknown_key_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(extra="unexpected"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["precondition_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_precondition_surface_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(surface="OtherSurface"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(
            result["failures"], ["precondition_surface_invalid"]
        )
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_version_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(version=2))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(
            result["failures"], ["precondition_version_invalid"]
        )
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_bool_as_int_version_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(version=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(
            result["failures"], ["precondition_version_invalid"]
        )
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class FieldValidationTests(unittest.TestCase):
    def test_each_required_string_field_invalid_rejected(self) -> None:
        for field in REQUIRED_STRING_FIELDS:
            for value in ("", 123):
                with self.subTest(field=field, value=value):
                    result = consume_executor_precondition_validator_ci(
                        _payload(
                            precondition=_precondition(**{field: value})
                        )
                    )

                    self.assertIs(result["ci_ok"], False)
                    self.assertEqual(
                        result["failures"], ["required_field_invalid"]
                    )
                    self.assertEqual(result[field], None)
                    self.assertEqual(
                        result["reason_code"], "invalid_ci_payload"
                    )

    def test_each_required_declaration_flag_non_bool_rejected(self) -> None:
        for flag in REQUIRED_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_executor_precondition_validator_ci(
                    _payload(precondition=_precondition(**{flag: "true"}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"], ["required_declaration_invalid"]
                )
                self.assertEqual(result[flag], None)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_required_declaration_flag_false_rejected(self) -> None:
        for flag in REQUIRED_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_executor_precondition_validator_ci(
                    _payload(precondition=_precondition(**{flag: False}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"], ["required_declaration_false"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_each_no_go_declaration_flag_non_bool_rejected(self) -> None:
        for flag in NO_GO_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_executor_precondition_validator_ci(
                    _payload(precondition=_precondition(**{flag: "true"}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"], ["no_go_declaration_invalid"]
                )
                self.assertEqual(result[flag], None)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_no_go_declaration_flag_false_rejected(self) -> None:
        for flag in NO_GO_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_executor_precondition_validator_ci(
                    _payload(precondition=_precondition(**{flag: False}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"], ["no_go_declaration_false"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_executor_precondition_validator_ci(
                    _payload(precondition=_precondition(**{flag: "false"}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"], ["authorization_flag_invalid"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_executor_precondition_validator_ci(
                    _payload(precondition=_precondition(**{flag: True}))
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["failures"], ["authorization_flag_true"]
                )
                self.assertIs(result[flag], False)
                self.assertEqual(result["reason_code"], "not_ready")

    def test_executes_plan_non_bool_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(executes_plan="false"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["execution_flag_invalid"])
        self.assertIs(result["executes_plan"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_executes_plan_true_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(executes_plan=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["execution_flag_true"])
        self.assertIs(result["executes_plan"], False)
        self.assertEqual(result["reason_code"], "not_ready")

    def test_durable_writes_non_bool_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(durable_writes="false"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["durable_writes_invalid"])
        self.assertIs(result["durable_writes"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_durable_writes_true_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(durable_writes=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["durable_writes_true"])
        self.assertIs(result["durable_writes"], False)
        self.assertEqual(result["reason_code"], "not_ready")

    def test_json_safe_false_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(json_safe=False))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(precondition=_precondition(json_safe="true"))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class DeterminismAndSafetyTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        payload = _payload(
            executor_precondition_ready=False,
            reason_code="not_ready",
            failures=["not_ready"],
            precondition=_precondition(
                surface="OtherSurface",
                version=True,
                source_execution_authorization_read_only_stack_tag="",
                dry_run_required="true",
                transaction_plan_required=False,
                no_cli_required="true",
                no_db_repair_required=False,
                executor_implementation_authorized="false",
                restore_execution_authorized=True,
                executes_plan="false",
                durable_writes=True,
                json_safe=False,
            ),
            extra="unexpected",
        )

        result = consume_executor_precondition_validator_ci(payload)

        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "precondition_not_ready",
                "precondition_surface_invalid",
                "precondition_version_invalid",
                "required_field_invalid",
                "required_declaration_invalid",
                "required_declaration_false",
                "no_go_declaration_invalid",
                "no_go_declaration_false",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "execution_flag_invalid",
                "durable_writes_true",
                "json_safe_invalid",
            ],
        )

    def test_output_json_safe(self) -> None:
        _assert_json_safe(consume_executor_precondition_validator_ci(_payload()))

    def test_no_runtime_repr_leakage(self) -> None:
        result = consume_executor_precondition_validator_ci(
            _payload(
                failures=[object()],
                precondition=_precondition(
                    approved_task_id=object(),
                    dry_run_required=object(),
                ),
            )
        )

        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)

        consume_executor_precondition_validator_ci(payload)

        self.assertEqual(payload, snapshot)

    def test_no_hidden_wall_clock_dependency(self) -> None:
        payload = _payload()

        self.assertEqual(
            consume_executor_precondition_validator_ci(payload),
            consume_executor_precondition_validator_ci(payload),
        )


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            executor_precondition_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = executor_precondition_validator_ci_manifest()
        assert isinstance(manifest["runtime_dependencies"], list)
        assert isinstance(manifest["depends_on"], dict)
        manifest["runtime_dependencies"].append("unexpected")
        manifest["depends_on"]["unexpected"] = "unexpected"

        self.assertEqual(
            executor_precondition_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "executor_precondition_validator_ci_manifest",
                "consume_executor_precondition_validator_ci",
            ],
        )
        public = {
            name for name in dir(ci_module) if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {
                "executor_precondition_validator_ci_manifest",
                "consume_executor_precondition_validator_ci",
            },
        )

    def test_callable_signatures(self) -> None:
        manifest_sig = inspect.signature(
            executor_precondition_validator_ci_manifest
        )
        self.assertEqual(list(manifest_sig.parameters), [])

        consume_sig = inspect.signature(
            consume_executor_precondition_validator_ci
        )
        self.assertEqual(list(consume_sig.parameters), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_datetime_import(self) -> None:
        source = inspect.getsource(ci_module)

        for marker in ("import datetime", "from datetime", "datetime"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_hidden_wall_clock_source_dependency(self) -> None:
        source = _scrubbed_source()

        for marker in (
            "datetime",
            "time",
            "datetime.now",
            "time.time",
            "time.monotonic",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_digest_computation(self) -> None:
        source = _scrubbed_source()

        for marker in ("hashlib", "hmac", "secrets", "sha256", "blake2"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_service_db_cli_or_recovery_imports(self) -> None:
        source = _scrubbed_source()

        for marker in (
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
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
            "recovery_session_host",
            "signable_path_orchestrator",
            "apply_migrations",
            "open(",
            "Path(",
            "validate_executor_precondition",
            "executor_precondition_validator_manifest",
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
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
