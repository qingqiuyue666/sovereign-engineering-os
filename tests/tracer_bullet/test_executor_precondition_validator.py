"""Tracer-bullet tests for the executor precondition validator."""

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

from kernel.lifecycle import executor_precondition_validator as validator_module
from kernel.lifecycle.executor_precondition_validator import (
    executor_precondition_validator_manifest,
    validate_executor_precondition,
)


EXPECTED_MANIFEST = {
    "surface": "executor_precondition_validator",
    "version": 1,
    "input_shape": "already_rendered_execution_authorization_ci_and_executor_precondition",
    "depends_on": {
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
        "h2_execution_preflight_ci": "h2-execution-preflight-ci-v1",
        "h2_execution_preflight": "h2-execution-preflight-v1",
        "human_approval_readiness_ci": "human-approval-readiness-ci-v1",
        "human_approval_readiness": "human-approval-readiness-v1",
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
    "durable_writes": False,
    "executes_plan": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        "invalid_precondition_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "authorization_ci_invalid",
        "authorization_ci_not_ready",
        "authorization_ci_ref_invalid",
        "precondition_invalid",
        "precondition_shape_mismatch",
        "precondition_surface_invalid",
        "precondition_version_invalid",
        "source_execution_authorization_stack_tag_mismatch",
        "source_execution_authorization_stack_commit_mismatch",
        "source_execution_authorization_validator_ci_ref_mismatch",
        "source_preflight_stack_tag_mismatch",
        "source_preflight_stack_commit_mismatch",
        "task_id_mismatch",
        "operation_kind_mismatch",
        "idempotency_key_mismatch",
        "projected_action_mismatch",
        "projected_evidence_ref_mismatch",
        "human_approval_ref_mismatch",
        "operator_confirmation_ref_mismatch",
        "authorization_issuer_mismatch",
        "authorization_reason_mismatch",
        "executor_intent_ref_invalid",
        "executor_intent_created_at_invalid",
        "executor_intent_expires_at_invalid",
        "executor_intent_expired",
        "evaluation_time_invalid",
        "executor_mode_invalid",
        "required_declaration_invalid",
        "required_declaration_false",
        "no_go_declaration_invalid",
        "no_go_declaration_false",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "irreversible_action_not_prohibited",
        "fail_closed_not_declared",
        "json_safe_invalid",
    ],
}


EXPECTED_TOP_LEVEL_KEYS = [
    "executor_precondition_ready",
    "reason_code",
    "failures",
    "precondition",
]


EXPECTED_PRECONDITION_KEYS = [
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
    "executor_precondition_validator",
    "ExecutorPreconditionV1",
    "executor-precondition-contract-spec-only-v1",
    "execution-authorization-read-only-stack-v1",
    "execution-authorization-validator-ci-v1",
    "execution-authorization-validator-v1",
    "execution-authorization-spec-only-v1",
    "preflight-read-only-stack-v1",
    "source_execution_authorization_validator_ci_ref",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
    "audit_append_required",
    "evidence_append_required",
)


def _authorization_ci(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "execution_authorization_validator",
        "version": 1,
        "authorization_ready": True,
        "authorization_reason_code": "ready",
        "authorization_failures": [],
        "source_preflight_stack_tag": "preflight-read-only-stack-v1",
        "source_preflight_stack_commit": (
            "662b6161253c35204b437e88809c5bab21908c6d"
        ),
        "source_preflight_aggregate_ref": "agg-ref-1",
        "approved_task_id": "T-1",
        "approved_operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "human_approval_ref": "AR-1",
        "operator_confirmation_ref": "CR-1",
        "actor_policy": "same_actor_required",
        "approval_actor_identity": "alice@org",
        "confirmation_actor_identity": "alice@org",
        "authorization_issuer": "governance-board",
        "authorization_reason": "bounded executor eligibility review",
        "authorization_created_at": "2024-01-01T00:00:00Z",
        "authorization_expires_at": "2024-01-01T02:00:00Z",
        "freshness_seconds": 3600,
        "evaluation_time": "2024-01-01T00:30:00Z",
        "transaction_boundary_declared": True,
        "rollback_boundary_declared": True,
        "idempotency_boundary_declared": True,
        "before_evidence_ref": "before/ref/1",
        "after_evidence_required": True,
        "audit_append_required": True,
        "evidence_append_required": True,
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "durable_writes": False,
        "executes_plan": False,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _precondition(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "ExecutorPreconditionV1",
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
    }
    base.update(overrides)
    return base


def _payload(
    *,
    authorization_ci: object | None = None,
    authorization_ci_ref: object = "ci-ref-1",
    precondition: object | None = None,
    evaluation_time: object = "2024-01-01T00:30:00Z",
) -> dict[str, object]:
    return {
        "execution_authorization_validator_ci": (
            _authorization_ci() if authorization_ci is None else authorization_ci
        ),
        "execution_authorization_validator_ci_ref": authorization_ci_ref,
        "executor_precondition": (
            _precondition() if precondition is None else precondition
        ),
        "evaluation_time": evaluation_time,
    }


def _expected_happy_output(mode: str = "contract_only") -> dict[str, object]:
    precondition = {
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
        "executor_mode": mode,
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
    return {
        "executor_precondition_ready": True,
        "reason_code": "ready",
        "failures": [],
        "precondition": precondition,
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


def _assert_rejected_with(payload: object, failure: str) -> dict[str, object]:
    result = validate_executor_precondition(payload)

    if result["executor_precondition_ready"] is not False:
        raise AssertionError("executor precondition unexpectedly ready")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path_contract_only(self) -> None:
        result = validate_executor_precondition(_payload())

        self.assertEqual(result, _expected_happy_output())

    def test_happy_path_future_executor_review(self) -> None:
        result = validate_executor_precondition(
            _payload(
                precondition=_precondition(
                    executor_mode="future_executor_review"
                )
            )
        )

        self.assertEqual(
            result,
            _expected_happy_output(mode="future_executor_review"),
        )

    def test_ready_true_does_not_authorize_executor_restore_or_write_side(
        self,
    ) -> None:
        result = validate_executor_precondition(_payload())
        precondition = result["precondition"]

        self.assertIs(result["executor_precondition_ready"], True)
        self.assertIs(precondition["executor_implementation_authorized"], False)
        self.assertIs(precondition["restore_execution_authorized"], False)
        self.assertIs(precondition["write_side_recovery_authorized"], False)
        self.assertIs(precondition["cli_execution_authorized"], False)
        self.assertIs(precondition["schema_migration_authorized"], False)
        self.assertIs(precondition["daemon_server_queue_authorized"], False)
        self.assertIs(precondition["db_repair_authorized"], False)
        self.assertIs(precondition["executes_plan"], False)
        self.assertIs(precondition["durable_writes"], False)


class OutputShapeTests(unittest.TestCase):
    def test_exact_output_shape(self) -> None:
        result = validate_executor_precondition(_payload())

        self.assertEqual(list(result.keys()), EXPECTED_TOP_LEVEL_KEYS)
        self.assertEqual(
            list(result["precondition"].keys()), EXPECTED_PRECONDITION_KEYS
        )

    def test_output_json_safe(self) -> None:
        _assert_json_safe(validate_executor_precondition(_payload()))

    def test_no_runtime_repr_leakage(self) -> None:
        result = validate_executor_precondition(
            _payload(
                authorization_ci=_authorization_ci(failures=[object()]),
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

        validate_executor_precondition(payload)

        self.assertEqual(payload, snapshot)


class TopLevelPayloadTests(unittest.TestCase):
    def test_non_mapping_top_level_rejected(self) -> None:
        for candidate in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(candidate=candidate):
                result = validate_executor_precondition(candidate)

                self.assertIs(result["executor_precondition_ready"], False)
                self.assertEqual(
                    result["reason_code"], "invalid_precondition_payload"
                )
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _payload()
        del payload["executor_precondition"]

        result = _assert_rejected_with(payload, "payload_shape_mismatch")

        self.assertEqual(result["reason_code"], "invalid_precondition_payload")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _payload()
        payload["extra"] = True

        result = _assert_rejected_with(payload, "payload_shape_mismatch")

        self.assertEqual(result["reason_code"], "invalid_precondition_payload")


class AuthorizationCiTests(unittest.TestCase):
    def test_malformed_authorization_ci_rejected(self) -> None:
        authorization_ci = _authorization_ci()
        del authorization_ci["approved_task_id"]

        _assert_rejected_with(
            _payload(authorization_ci=authorization_ci),
            "authorization_ci_invalid",
        )

    def test_authorization_ci_not_ready_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization_ci=_authorization_ci(
                    ci_ok=False,
                    reason_code="not_ready",
                    failures=["authorization_stale"],
                )
            ),
            "authorization_ci_not_ready",
        )

    def test_invalid_authorization_ci_ref_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization_ci_ref=""), "authorization_ci_ref_invalid"
        )


class PreconditionShapeTests(unittest.TestCase):
    def test_precondition_non_mapping_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition="not-a-mapping"), "precondition_invalid"
        )

    def test_precondition_missing_key_rejected(self) -> None:
        precondition = _precondition()
        del precondition["approved_task_id"]

        _assert_rejected_with(
            _payload(precondition=precondition), "precondition_shape_mismatch"
        )

    def test_precondition_unknown_key_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(extra=True)),
            "precondition_shape_mismatch",
        )

    def test_wrong_precondition_surface_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(surface="OtherSurface")),
            "precondition_surface_invalid",
        )

    def test_wrong_version_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(version=2)),
            "precondition_version_invalid",
        )

    def test_bool_as_int_version_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(version=True)),
            "precondition_version_invalid",
        )


class BindingTests(unittest.TestCase):
    def test_source_execution_authorization_stack_tag_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    source_execution_authorization_read_only_stack_tag="other"
                )
            ),
            "source_execution_authorization_stack_tag_mismatch",
        )

    def test_source_execution_authorization_stack_commit_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    source_execution_authorization_read_only_stack_commit="bad"
                )
            ),
            "source_execution_authorization_stack_commit_mismatch",
        )

    def test_source_authorization_ci_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    source_execution_authorization_validator_ci_ref="other"
                )
            ),
            "source_execution_authorization_validator_ci_ref_mismatch",
        )

    def test_source_preflight_stack_tag_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    source_preflight_read_only_stack_tag="other"
                )
            ),
            "source_preflight_stack_tag_mismatch",
        )

    def test_source_preflight_stack_commit_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    source_preflight_read_only_stack_commit="bad"
                )
            ),
            "source_preflight_stack_commit_mismatch",
        )

    def test_approved_task_id_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(approved_task_id="T-2")),
            "task_id_mismatch",
        )

    def test_approved_operation_kind_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(approved_operation_kind="other")
            ),
            "operation_kind_mismatch",
        )

    def test_idempotency_key_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(idempotency_key="idem-2")),
            "idempotency_key_mismatch",
        )

    def test_projected_action_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(projected_action="other")),
            "projected_action_mismatch",
        )

    def test_projected_evidence_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(projected_evidence_ref="other")),
            "projected_evidence_ref_mismatch",
        )

    def test_human_approval_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(human_approval_ref="AR-2")),
            "human_approval_ref_mismatch",
        )

    def test_operator_confirmation_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(operator_confirmation_ref="CR-2")
            ),
            "operator_confirmation_ref_mismatch",
        )

    def test_authorization_issuer_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(authorization_issuer="other")),
            "authorization_issuer_mismatch",
        )

    def test_authorization_reason_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(authorization_reason="other")),
            "authorization_reason_mismatch",
        )


class TimeAndModeTests(unittest.TestCase):
    def test_executor_intent_ref_invalid(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(executor_intent_ref="")),
            "executor_intent_ref_invalid",
        )

    def test_executor_intent_created_at_invalid(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    executor_intent_created_at="not-a-time"
                )
            ),
            "executor_intent_created_at_invalid",
        )

    def test_naive_executor_intent_created_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    executor_intent_created_at="2024-01-01T00:00:00"
                )
            ),
            "executor_intent_created_at_invalid",
        )

    def test_executor_intent_expires_at_invalid(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    executor_intent_expires_at="not-a-time"
                )
            ),
            "executor_intent_expires_at_invalid",
        )

    def test_naive_executor_intent_expires_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    executor_intent_expires_at="2024-01-01T01:00:00"
                )
            ),
            "executor_intent_expires_at_invalid",
        )

    def test_expires_at_before_created_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    executor_intent_expires_at="2023-12-31T23:59:59Z"
                )
            ),
            "executor_intent_expires_at_invalid",
        )

    def test_evaluation_time_invalid(self) -> None:
        _assert_rejected_with(
            _payload(evaluation_time="not-a-time"), "evaluation_time_invalid"
        )

    def test_naive_evaluation_time_rejected(self) -> None:
        _assert_rejected_with(
            _payload(evaluation_time="2024-01-01T00:30:00"),
            "evaluation_time_invalid",
        )

    def test_evaluation_time_before_created_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(evaluation_time="2023-12-31T23:59:59Z"),
            "evaluation_time_invalid",
        )

    def test_evaluation_time_at_or_after_expires_at_rejected(self) -> None:
        for evaluation_time in (
            "2024-01-01T01:00:00Z",
            "2024-01-01T01:00:01Z",
        ):
            with self.subTest(evaluation_time=evaluation_time):
                _assert_rejected_with(
                    _payload(evaluation_time=evaluation_time),
                    "executor_intent_expired",
                )

    def test_invalid_executor_mode(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(executor_mode="active")),
            "executor_mode_invalid",
        )


class DeclarationFlagTests(unittest.TestCase):
    def test_each_required_declaration_flag_non_bool_rejected(self) -> None:
        for flag in REQUIRED_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(precondition=_precondition(**{flag: "true"})),
                    "required_declaration_invalid",
                )
                self.assertIsNone(result["precondition"][flag])

    def test_each_required_declaration_flag_false_rejected(self) -> None:
        for flag in REQUIRED_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(precondition=_precondition(**{flag: False})),
                    "required_declaration_false",
                )
                self.assertIs(result["precondition"][flag], False)

    def test_each_no_go_declaration_flag_non_bool_rejected(self) -> None:
        for flag in NO_GO_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(precondition=_precondition(**{flag: "true"})),
                    "no_go_declaration_invalid",
                )
                self.assertIsNone(result["precondition"][flag])

    def test_each_no_go_declaration_flag_false_rejected(self) -> None:
        for flag in NO_GO_DECLARATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(precondition=_precondition(**{flag: False})),
                    "no_go_declaration_false",
                )
                self.assertIs(result["precondition"][flag], False)

    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(precondition=_precondition(**{flag: "false"})),
                    "authorization_flag_invalid",
                )
                self.assertIsNone(result["precondition"][flag])

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(precondition=_precondition(**{flag: True})),
                    "authorization_flag_true",
                )
                self.assertIs(result["precondition"][flag], False)

    def test_irreversible_action_prohibited_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                precondition=_precondition(
                    irreversible_action_prohibited=False
                )
            ),
            "irreversible_action_not_prohibited",
        )

    def test_fail_closed_declared_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(fail_closed_declared=False)),
            "fail_closed_not_declared",
        )

    def test_json_safe_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(precondition=_precondition(json_safe=False)),
            "json_safe_invalid",
        )

    def test_json_safe_non_bool_rejected(self) -> None:
        result = _assert_rejected_with(
            _payload(precondition=_precondition(json_safe="true")),
            "json_safe_invalid",
        )

        self.assertIsNone(result["precondition"]["json_safe"])


class DeterminismAndSafetyTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        payload = _payload(
            authorization_ci=_authorization_ci(
                ci_ok=False,
                reason_code="not_ready",
                failures=["not_ready"],
            ),
            authorization_ci_ref="",
            precondition=_precondition(
                surface="OtherSurface",
                version=True,
                source_execution_authorization_read_only_stack_tag="other",
                source_preflight_read_only_stack_commit="bad",
                approved_task_id="T-2",
                executor_intent_ref="",
                executor_intent_created_at="not-a-time",
                executor_mode="active",
                dry_run_required="true",
                transaction_plan_required=False,
                no_cli_required="true",
                no_db_repair_required=False,
                executor_implementation_authorized="false",
                restore_execution_authorized=True,
                irreversible_action_prohibited=False,
                fail_closed_declared=False,
                json_safe=False,
            ),
            evaluation_time="not-a-time",
        )
        payload["extra"] = True

        result = validate_executor_precondition(payload)

        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "authorization_ci_not_ready",
                "authorization_ci_ref_invalid",
                "precondition_surface_invalid",
                "precondition_version_invalid",
                "source_execution_authorization_stack_tag_mismatch",
                "source_preflight_stack_commit_mismatch",
                "task_id_mismatch",
                "executor_intent_ref_invalid",
                "executor_intent_created_at_invalid",
                "evaluation_time_invalid",
                "executor_mode_invalid",
                "required_declaration_invalid",
                "required_declaration_false",
                "no_go_declaration_invalid",
                "no_go_declaration_false",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "irreversible_action_not_prohibited",
                "fail_closed_not_declared",
                "json_safe_invalid",
            ],
        )

    def test_hidden_wall_clock_not_used(self) -> None:
        payload = _payload()

        self.assertEqual(
            validate_executor_precondition(payload),
            validate_executor_precondition(payload),
        )

    def test_no_digest_computation(self) -> None:
        source = inspect.getsource(validator_module)

        for marker in ("hashlib", "hmac", "secrets", "sha256", "blake2"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            executor_precondition_validator_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = executor_precondition_validator_manifest()
        assert isinstance(manifest["runtime_dependencies"], list)
        assert isinstance(manifest["depends_on"], dict)
        manifest["runtime_dependencies"].append("unexpected")
        manifest["depends_on"]["unexpected"] = "unexpected"

        self.assertEqual(
            executor_precondition_validator_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            validator_module.__all__,
            [
                "executor_precondition_validator_manifest",
                "validate_executor_precondition",
            ],
        )
        public = {
            name for name in dir(validator_module) if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {
                "executor_precondition_validator_manifest",
                "validate_executor_precondition",
            },
        )

    def test_callable_signatures(self) -> None:
        manifest_sig = inspect.signature(
            executor_precondition_validator_manifest
        )
        self.assertEqual(list(manifest_sig.parameters), [])

        validate_sig = inspect.signature(validate_executor_precondition)
        self.assertEqual(list(validate_sig.parameters), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary(self) -> None:
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
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_service_db_cli_or_recovery_imports(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
