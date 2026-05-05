"""Tracer-bullet tests for the execution authorization validator CI consumer."""

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

from kernel.lifecycle import execution_authorization_validator_ci as ci_module
from kernel.lifecycle.execution_authorization_validator_ci import (
    consume_execution_authorization_validator_ci,
    execution_authorization_validator_ci_manifest,
)


EXPECTED_MANIFEST = {
    "surface": "execution_authorization_validator_ci",
    "version": 1,
    "input_shape": "already_rendered_execution_authorization_validator_output",
    "depends_on": {
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
    "restore_authorized": False,
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
        "authorization_not_ready",
        "authorization_invalid",
        "authorization_surface_invalid",
        "authorization_version_invalid",
        "required_field_invalid",
        "freshness_seconds_invalid",
        "boundary_flag_invalid",
        "boundary_flag_false",
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
    "authorization_ready",
    "authorization_reason_code",
    "authorization_failures",
    "source_preflight_stack_tag",
    "source_preflight_stack_commit",
    "source_preflight_aggregate_ref",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "actor_policy",
    "approval_actor_identity",
    "confirmation_actor_identity",
    "authorization_issuer",
    "authorization_reason",
    "authorization_created_at",
    "authorization_expires_at",
    "freshness_seconds",
    "evaluation_time",
    "transaction_boundary_declared",
    "rollback_boundary_declared",
    "idempotency_boundary_declared",
    "before_evidence_ref",
    "after_evidence_required",
    "audit_append_required",
    "evidence_append_required",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
]


REQUIRED_STRING_FIELDS = (
    "source_preflight_stack_tag",
    "source_preflight_stack_commit",
    "source_preflight_aggregate_ref",
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "actor_policy",
    "approval_actor_identity",
    "confirmation_actor_identity",
    "authorization_issuer",
    "authorization_reason",
    "authorization_created_at",
    "authorization_expires_at",
    "evaluation_time",
    "before_evidence_ref",
)


BOUNDARY_FLAGS = (
    "transaction_boundary_declared",
    "rollback_boundary_declared",
    "idempotency_boundary_declared",
    "after_evidence_required",
    "audit_append_required",
    "evidence_append_required",
    "irreversible_action_prohibited",
    "fail_closed_declared",
)


AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)


REPR_MARKERS = (
    "ExecutionAuthorization(",
    " object at 0x",
    "<sqlite3.",
)


FORBIDDEN_SOURCE_MARKERS = (
    "datetime",
    "time.",
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
    "execution_authorization_validator_ci",
    "execution_authorization_validator",
    "execution-authorization-validator-v1",
    "execution-authorization-spec-only-v1",
    "preflight-read-only-stack-v1",
    "preflight_aggregate_summary",
    "source_preflight_aggregate_ref",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
    "audit_append_required",
    "evidence_append_required",
)


def _valid_authorization(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "execution_authorization_validator",
        "version": 1,
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
        "authorization_reason": "bounded restore eligibility review",
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
        "irreversible_action_prohibited": True,
        "fail_closed_declared": True,
        "json_safe": True,
        "executes_plan": False,
        "durable_writes": False,
    }
    base.update(overrides)
    return base


def _valid_payload(**overrides: object) -> dict[str, object]:
    authorization = overrides.pop("authorization", _valid_authorization())
    base: dict[str, object] = {
        "authorization_ready": True,
        "reason_code": "ready",
        "failures": [],
        "authorization": authorization,
    }
    base.update(overrides)
    return base


def _expected_happy_output() -> dict[str, object]:
    return {
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
        "authorization_reason": "bounded restore eligibility review",
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


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = consume_execution_authorization_validator_ci(_valid_payload())

        self.assertEqual(result, _expected_happy_output())

    def test_ci_ok_true_does_not_authorize_restore_or_write_side(self) -> None:
        result = consume_execution_authorization_validator_ci(_valid_payload())

        self.assertTrue(result["ci_ok"])
        self.assertFalse(result["restore_authorized"])
        self.assertFalse(result["write_side_recovery_authorized"])
        self.assertFalse(result["cli_execution_authorized"])
        self.assertFalse(result["schema_migration_authorized"])
        self.assertFalse(result["daemon_server_queue_authorized"])
        self.assertFalse(result["db_repair_authorized"])
        self.assertFalse(result["executes_plan"])
        self.assertFalse(result["durable_writes"])

    def test_exact_output_shape(self) -> None:
        result = consume_execution_authorization_validator_ci(_valid_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_input_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(object())

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["authorization"]

        result = consume_execution_authorization_validator_ci(payload)

        self.assertFalse(result["ci_ok"])
        self.assertIn("payload_shape_mismatch", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _valid_payload(extra="unexpected")

        result = consume_execution_authorization_validator_ci(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_authorization_ready_false_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization_ready=False)
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_not_ready"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_reason_code_not_ready_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(reason_code="not_ready")
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_not_ready"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_failures_non_empty_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(failures=["authorization_stale"])
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_not_ready"])
        self.assertEqual(result["authorization_failures"], ["authorization_stale"])
        self.assertEqual(result["reason_code"], "not_ready")


class AuthorizationShapeTests(unittest.TestCase):
    def test_authorization_non_mapping_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=object())
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_authorization_missing_key_rejected(self) -> None:
        authorization = _valid_authorization()
        del authorization["approved_task_id"]

        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=authorization)
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(
            result["failures"],
            ["authorization_invalid", "required_field_invalid"],
        )
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_authorization_unknown_key_rejected(self) -> None:
        authorization = _valid_authorization(extra="unexpected")

        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=authorization)
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_authorization_surface_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(
                authorization=_valid_authorization(surface="wrong_surface")
            )
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_surface_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_authorization_version_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=_valid_authorization(version=2))
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_version_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_bool_as_int_version_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=_valid_authorization(version=True))
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["authorization_version_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")


class AuthorizationFieldTests(unittest.TestCase):
    def test_each_required_scalar_field_missing_rejected(self) -> None:
        for field in REQUIRED_STRING_FIELDS:
            with self.subTest(field=field):
                authorization = _valid_authorization()
                del authorization[field]

                result = consume_execution_authorization_validator_ci(
                    _valid_payload(authorization=authorization)
                )

                self.assertFalse(result["ci_ok"])
                self.assertIn("authorization_invalid", result["failures"])
                self.assertIn("required_field_invalid", result["failures"])
                self.assertEqual(result[field], None)

    def test_each_required_scalar_field_non_string_rejected(self) -> None:
        for field in REQUIRED_STRING_FIELDS:
            with self.subTest(field=field):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(**{field: 123})
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["failures"], ["required_field_invalid"])
                self.assertEqual(result[field], None)

    def test_each_required_scalar_field_empty_rejected(self) -> None:
        for field in REQUIRED_STRING_FIELDS:
            with self.subTest(field=field):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(**{field: ""})
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["failures"], ["required_field_invalid"])
                self.assertEqual(result[field], None)

    def test_freshness_seconds_non_int_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(
                authorization=_valid_authorization(freshness_seconds="3600")
            )
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["freshness_seconds_invalid"])
        self.assertEqual(result["freshness_seconds"], None)

    def test_freshness_seconds_bool_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(
                authorization=_valid_authorization(freshness_seconds=True)
            )
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["freshness_seconds_invalid"])
        self.assertEqual(result["freshness_seconds"], None)

    def test_freshness_seconds_less_than_or_equal_to_zero_rejected(self) -> None:
        for value in (0, -1):
            with self.subTest(value=value):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(
                            freshness_seconds=value
                        )
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(
                    result["failures"], ["freshness_seconds_invalid"]
                )
                self.assertEqual(result["freshness_seconds"], None)

    def test_each_boundary_flag_non_bool_rejected(self) -> None:
        for flag in BOUNDARY_FLAGS:
            with self.subTest(flag=flag):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(**{flag: "true"})
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["failures"], ["boundary_flag_invalid"])
                if flag in result:
                    self.assertEqual(result[flag], None)

    def test_each_boundary_flag_false_rejected(self) -> None:
        for flag in BOUNDARY_FLAGS:
            with self.subTest(flag=flag):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(**{flag: False})
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["failures"], ["boundary_flag_false"])
                self.assertEqual(result["reason_code"], "not_ready")
                if flag in result:
                    self.assertEqual(result[flag], False)

    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(**{flag: "false"})
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(
                    result["failures"], ["authorization_flag_invalid"]
                )
                self.assertFalse(result[flag])

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = consume_execution_authorization_validator_ci(
                    _valid_payload(
                        authorization=_valid_authorization(**{flag: True})
                    )
                )

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["failures"], ["authorization_flag_true"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertFalse(result[flag])

    def test_executes_plan_non_bool_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(
                authorization=_valid_authorization(executes_plan="false")
            )
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["execution_flag_invalid"])
        self.assertFalse(result["executes_plan"])

    def test_executes_plan_true_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=_valid_authorization(executes_plan=True))
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["execution_flag_true"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertFalse(result["executes_plan"])

    def test_durable_writes_non_bool_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(
                authorization=_valid_authorization(durable_writes="false")
            )
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["durable_writes_invalid"])
        self.assertFalse(result["durable_writes"])

    def test_durable_writes_true_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=_valid_authorization(durable_writes=True))
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["durable_writes_true"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertFalse(result["durable_writes"])

    def test_json_safe_false_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=_valid_authorization(json_safe=False))
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertTrue(result["json_safe"])

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_execution_authorization_validator_ci(
            _valid_payload(authorization=_valid_authorization(json_safe="true"))
        )

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertTrue(result["json_safe"])


class DeterminismAndSafetyTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        authorization = _valid_authorization(
            surface="wrong_surface",
            version=True,
            source_preflight_stack_tag="",
            freshness_seconds=False,
            transaction_boundary_declared="true",
            rollback_boundary_declared=False,
            restore_authorized="false",
            write_side_recovery_authorized=True,
            executes_plan=True,
            durable_writes="false",
            json_safe=False,
        )
        result = consume_execution_authorization_validator_ci(
            _valid_payload(
                authorization_ready=False,
                reason_code="not_ready",
                failures=["authorization_stale"],
                authorization=authorization,
            )
        )

        self.assertEqual(
            result["failures"],
            [
                "authorization_not_ready",
                "authorization_surface_invalid",
                "authorization_version_invalid",
                "required_field_invalid",
                "freshness_seconds_invalid",
                "boundary_flag_invalid",
                "boundary_flag_false",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "execution_flag_true",
                "durable_writes_invalid",
                "json_safe_invalid",
            ],
        )

    def test_output_json_safe(self) -> None:
        result = consume_execution_authorization_validator_ci(_valid_payload())

        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        authorization = _valid_authorization(
            approved_task_id=object(),
            transaction_boundary_declared=object(),
        )

        result = consume_execution_authorization_validator_ci(
            _valid_payload(failures=[object()], authorization=authorization)
        )

        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        original = copy.deepcopy(payload)

        consume_execution_authorization_validator_ci(payload)

        self.assertEqual(payload, original)


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            execution_authorization_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = execution_authorization_validator_ci_manifest()
        assert isinstance(manifest["runtime_dependencies"], list)
        assert isinstance(manifest["depends_on"], dict)
        manifest["runtime_dependencies"].append("unexpected")
        manifest["depends_on"]["unexpected"] = "unexpected"

        self.assertEqual(
            execution_authorization_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "execution_authorization_validator_ci_manifest",
                "consume_execution_authorization_validator_ci",
            ],
        )
        public = {
            name for name in dir(ci_module) if not name.startswith("_")
        }
        self.assertEqual(
            public,
            {
                "execution_authorization_validator_ci_manifest",
                "consume_execution_authorization_validator_ci",
            },
        )


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_wall_clock_dependency(self) -> None:
        source = _scrubbed_source()

        for marker in (
            "datetime",
            "time.",
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

    def test_no_validator_upstream_service_db_cli_or_recovery_imports(self) -> None:
        source = _scrubbed_source()

        for marker in (
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
            "sqlite",
            "Repository",
            "UnitOfWork",
            "approval_service",
            "review_service",
            "revision_seal_service",
            "evidence_service",
            "argparse",
            "click",
            "restore_task",
            "recovery_session_host",
            "signable_path_orchestrator",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
