"""Tracer-bullet tests for the execution authorization validator."""

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

from kernel.lifecycle import execution_authorization_validator as validator_module
from kernel.lifecycle.execution_authorization_validator import (
    execution_authorization_validator_manifest,
    validate_execution_authorization,
)


EXPECTED_MANIFEST = {
    "surface": "execution_authorization_validator",
    "version": 1,
    "input_shape": (
        "already_rendered_preflight_summary_and_execution_authorization"
    ),
    "depends_on": {
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
        "invalid_authorization_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "preflight_summary_invalid",
        "preflight_summary_not_ready",
        "preflight_ref_invalid",
        "authorization_invalid",
        "authorization_shape_mismatch",
        "authorization_surface_invalid",
        "authorization_version_invalid",
        "source_preflight_stack_tag_mismatch",
        "source_preflight_stack_commit_mismatch",
        "source_preflight_aggregate_ref_mismatch",
        "task_id_mismatch",
        "operation_kind_mismatch",
        "idempotency_key_mismatch",
        "projected_action_mismatch",
        "projected_evidence_ref_mismatch",
        "human_approval_ref_mismatch",
        "operator_confirmation_ref_mismatch",
        "actor_policy_invalid",
        "actor_identity_mismatch",
        "issuer_invalid",
        "authorization_reason_invalid",
        "evaluation_time_invalid",
        "authorization_created_at_invalid",
        "authorization_expires_at_invalid",
        "authorization_expired",
        "freshness_seconds_invalid",
        "authorization_stale",
        "transaction_boundary_not_declared",
        "rollback_boundary_not_declared",
        "idempotency_boundary_not_declared",
        "before_evidence_ref_invalid",
        "after_evidence_not_required",
        "audit_append_not_required",
        "evidence_append_not_required",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "irreversible_action_not_prohibited",
        "fail_closed_not_declared",
        "execution_flag_invalid",
        "execution_flag_true",
        "json_safe_invalid",
    ],
}


EXPECTED_TOP_LEVEL_KEYS = [
    "authorization_ready",
    "reason_code",
    "failures",
    "authorization",
]


EXPECTED_AUTHORIZATION_KEYS = [
    "surface",
    "version",
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
    "irreversible_action_prohibited",
    "fail_closed_declared",
    "json_safe",
    "executes_plan",
    "durable_writes",
]


AUTHORIZATION_FLAGS = (
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "cli_execution_authorized",
    "restore_authorized",
    "write_side_recovery_authorized",
)


REPR_MARKERS = (
    "ExecutionAuthorization(",
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
    "execution_authorization_validator",
    "ExecutionAuthorizationV1",
    "execution-authorization-spec-only-v1",
    "preflight-read-only-stack-v1",
    "preflight_aggregate_summary",
    "preflight-aggregate-summary-v1",
    "source_preflight_aggregate_ref",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
    "audit_append_required",
    "evidence_append_required",
)


def _preflight_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "surface": "preflight_aggregate_summary",
        "version": 1,
        "human_approval_ci_ok": True,
        "execution_preflight_ci_ok": True,
        "target_task_id": "T-1",
        "operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "aggregate_summary_ref": "agg-ref-1",
        "human_approval_ref": "AR-1",
        "confirmation_ref": "CR-1",
        "actor_identity_approval": "alice@org",
        "actor_identity_confirmation": "alice@org",
        "actor_policy": "same_actor_required",
        "confirmation_digest": "digest-1",
        "transaction_declared": True,
        "rollback_declared": True,
        "expected_rejection_policy_declared": True,
        "idempotency_declared": True,
        "audit_evidence_envelope_declared": True,
        "before_after_evidence_declared": True,
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
    base: dict[str, object] = {
        "aggregate_ok": True,
        "reason_code": "ready",
        "failures": [],
        "summary": summary,
    }
    for key, value in overrides.items():
        if key.startswith("summary__"):
            summary[key[len("summary__"):]] = value
        else:
            base[key] = value
    return base


def _authorization(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "ExecutionAuthorizationV1",
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
        "transaction_boundary_declared": True,
        "rollback_boundary_declared": True,
        "idempotency_boundary_declared": True,
        "before_evidence_ref": "before/ref/1",
        "after_evidence_required": True,
        "audit_append_required": True,
        "evidence_append_required": True,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "cli_execution_authorized": False,
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "irreversible_action_prohibited": True,
        "fail_closed_declared": True,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _payload(
    *,
    preflight: dict[str, object] | None = None,
    preflight_ref: object = "agg-ref-1",
    authorization: dict[str, object] | None = None,
    evaluation_time: object = "2024-01-01T00:30:00Z",
) -> dict[str, object]:
    return {
        "preflight_aggregate_summary": (
            preflight if preflight is not None else _preflight_summary()
        ),
        "preflight_aggregate_summary_ref": preflight_ref,
        "execution_authorization": (
            authorization if authorization is not None else _authorization()
        ),
        "evaluation_time": evaluation_time,
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
    result = validate_execution_authorization(payload)

    if result["authorization_ready"] is not False:
        raise AssertionError("authorization unexpectedly ready")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_same_actor_required_ready(self) -> None:
        result = validate_execution_authorization(_payload())

        self.assertIs(result["authorization_ready"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(list(result.keys()), EXPECTED_TOP_LEVEL_KEYS)
        self.assertEqual(
            result["authorization"]["source_preflight_aggregate_ref"],
            "agg-ref-1",
        )

    def test_dual_control_allowed_ready(self) -> None:
        preflight = _preflight_summary(
            summary__actor_identity_approval="alice@org",
            summary__actor_identity_confirmation="bob@org",
            summary__actor_policy="dual_control_allowed",
        )
        authorization = _authorization(
            actor_policy="dual_control_allowed",
            approval_actor_identity="alice@org",
            confirmation_actor_identity="bob@org",
        )

        result = validate_execution_authorization(
            _payload(preflight=preflight, authorization=authorization)
        )

        self.assertIs(result["authorization_ready"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["authorization"]["actor_policy"], "dual_control_allowed"
        )

    def test_authorization_ready_does_not_authorize_restore_or_write_side(
        self,
    ) -> None:
        result = validate_execution_authorization(_payload())
        authorization = result["authorization"]

        self.assertIs(result["authorization_ready"], True)
        self.assertIs(authorization["restore_authorized"], False)
        self.assertIs(authorization["write_side_recovery_authorized"], False)
        self.assertIs(authorization["cli_execution_authorized"], False)
        self.assertIs(authorization["schema_migration_authorized"], False)
        self.assertIs(authorization["daemon_server_queue_authorized"], False)
        self.assertIs(authorization["db_repair_authorized"], False)
        self.assertIs(authorization["executes_plan"], False)
        self.assertIs(authorization["durable_writes"], False)


class OutputShapeTests(unittest.TestCase):
    def test_exact_output_shape(self) -> None:
        result = validate_execution_authorization(_payload())

        self.assertEqual(list(result.keys()), EXPECTED_TOP_LEVEL_KEYS)
        self.assertEqual(
            list(result["authorization"].keys()), EXPECTED_AUTHORIZATION_KEYS
        )

    def test_output_json_safe(self) -> None:
        _assert_json_safe(validate_execution_authorization(_payload()))

    def test_no_runtime_repr_leakage(self) -> None:
        _assert_no_runtime_repr(validate_execution_authorization(_payload()))

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)

        validate_execution_authorization(payload)

        self.assertEqual(payload, snapshot)


class TopLevelPayloadTests(unittest.TestCase):
    def test_non_mapping_top_level_rejected(self) -> None:
        for candidate in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(candidate=candidate):
                result = validate_execution_authorization(candidate)

                self.assertIs(result["authorization_ready"], False)
                self.assertEqual(
                    result["reason_code"], "invalid_authorization_payload"
                )
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _payload()
        del payload["execution_authorization"]

        _assert_rejected_with(payload, "payload_shape_mismatch")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _payload()
        payload["extra"] = True

        _assert_rejected_with(payload, "payload_shape_mismatch")


class PreflightSummaryTests(unittest.TestCase):
    def test_malformed_preflight_summary_rejected(self) -> None:
        preflight = _preflight_summary()
        del preflight["summary"]["surface"]

        _assert_rejected_with(
            _payload(preflight=preflight), "preflight_summary_invalid"
        )

    def test_preflight_aggregate_not_ready_rejected(self) -> None:
        preflight = _preflight_summary(
            aggregate_ok=False,
            reason_code="not_ready",
            failures=["not_ready"],
        )

        _assert_rejected_with(
            _payload(preflight=preflight), "preflight_summary_not_ready"
        )

    def test_invalid_preflight_ref_rejected(self) -> None:
        _assert_rejected_with(_payload(preflight_ref=""), "preflight_ref_invalid")


class AuthorizationShapeTests(unittest.TestCase):
    def test_authorization_non_mapping_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization="not-a-mapping"), "authorization_invalid"
        )

    def test_authorization_missing_key_rejected(self) -> None:
        authorization = _authorization()
        del authorization["authorization_issuer"]

        _assert_rejected_with(
            _payload(authorization=authorization), "authorization_shape_mismatch"
        )

    def test_authorization_unknown_key_rejected(self) -> None:
        authorization = _authorization(extra=True)

        _assert_rejected_with(
            _payload(authorization=authorization), "authorization_shape_mismatch"
        )

    def test_wrong_authorization_surface_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(surface="OtherSurface")),
            "authorization_surface_invalid",
        )

    def test_wrong_version_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(version=2)),
            "authorization_version_invalid",
        )

    def test_bool_as_int_version_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(version=True)),
            "authorization_version_invalid",
        )


class BindingTests(unittest.TestCase):
    def test_source_stack_tag_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    source_preflight_stack_tag="other-tag"
                )
            ),
            "source_preflight_stack_tag_mismatch",
        )

    def test_source_stack_commit_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    source_preflight_stack_commit="bad-commit"
                )
            ),
            "source_preflight_stack_commit_mismatch",
        )

    def test_source_preflight_aggregate_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    source_preflight_aggregate_ref="agg-other"
                )
            ),
            "source_preflight_aggregate_ref_mismatch",
        )

    def test_task_id_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(approved_task_id="T-2")),
            "task_id_mismatch",
        )

    def test_operation_kind_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    approved_operation_kind="op-other"
                )
            ),
            "operation_kind_mismatch",
        )

    def test_idempotency_key_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(idempotency_key="idem-2")),
            "idempotency_key_mismatch",
        )

    def test_projected_action_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(projected_action="project.other")
            ),
            "projected_action_mismatch",
        )

    def test_projected_evidence_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(projected_evidence_ref="ev/other")
            ),
            "projected_evidence_ref_mismatch",
        )

    def test_human_approval_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(human_approval_ref="AR-2")),
            "human_approval_ref_mismatch",
        )

    def test_operator_confirmation_ref_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(operator_confirmation_ref="CR-2")
            ),
            "operator_confirmation_ref_mismatch",
        )


class ActorPolicyTests(unittest.TestCase):
    def test_invalid_actor_policy(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(actor_policy="anything")),
            "actor_policy_invalid",
        )

    def test_same_actor_required_actor_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    actor_policy="same_actor_required",
                    confirmation_actor_identity="bob@org",
                )
            ),
            "actor_identity_mismatch",
        )

    def test_dual_control_allowed_actor_difference_accepted(self) -> None:
        preflight = _preflight_summary(
            summary__actor_identity_approval="alice@org",
            summary__actor_identity_confirmation="bob@org",
            summary__actor_policy="dual_control_allowed",
        )
        authorization = _authorization(
            actor_policy="dual_control_allowed",
            approval_actor_identity="alice@org",
            confirmation_actor_identity="bob@org",
        )

        result = validate_execution_authorization(
            _payload(preflight=preflight, authorization=authorization)
        )

        self.assertIs(result["authorization_ready"], True)
        self.assertNotIn("actor_identity_mismatch", result["failures"])


class IssuerReasonTests(unittest.TestCase):
    def test_issuer_invalid(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(authorization_issuer="")),
            "issuer_invalid",
        )

    def test_reason_invalid(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(authorization_reason=42)),
            "authorization_reason_invalid",
        )


class TimeValidationTests(unittest.TestCase):
    def test_evaluation_time_invalid(self) -> None:
        _assert_rejected_with(
            _payload(evaluation_time="not-a-time"), "evaluation_time_invalid"
        )

    def test_naive_evaluation_time_rejected(self) -> None:
        _assert_rejected_with(
            _payload(evaluation_time="2024-01-01T00:30:00"),
            "evaluation_time_invalid",
        )

    def test_authorization_created_at_invalid(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    authorization_created_at="not-a-time"
                )
            ),
            "authorization_created_at_invalid",
        )

    def test_naive_authorization_created_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    authorization_created_at="2024-01-01T00:00:00"
                )
            ),
            "authorization_created_at_invalid",
        )

    def test_authorization_expires_at_invalid(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    authorization_expires_at="not-a-time"
                )
            ),
            "authorization_expires_at_invalid",
        )

    def test_expires_at_before_created_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    authorization_expires_at="2023-12-31T23:00:00Z"
                )
            ),
            "authorization_expires_at_invalid",
        )

    def test_evaluation_time_before_created_at_rejected(self) -> None:
        _assert_rejected_with(
            _payload(evaluation_time="2023-12-31T23:59:59Z"),
            "evaluation_time_invalid",
        )

    def test_evaluation_time_at_or_after_expires_at_rejected(self) -> None:
        for evaluation_time in (
            "2024-01-01T02:00:00Z",
            "2024-01-01T02:00:01Z",
        ):
            with self.subTest(evaluation_time=evaluation_time):
                _assert_rejected_with(
                    _payload(evaluation_time=evaluation_time),
                    "authorization_expired",
                )

    def test_freshness_seconds_non_int_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(freshness_seconds="3600")),
            "freshness_seconds_invalid",
        )

    def test_freshness_seconds_bool_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(freshness_seconds=True)),
            "freshness_seconds_invalid",
        )

    def test_freshness_seconds_less_than_or_equal_zero_rejected(self) -> None:
        for freshness_seconds in (0, -1):
            with self.subTest(freshness_seconds=freshness_seconds):
                _assert_rejected_with(
                    _payload(
                        authorization=_authorization(
                            freshness_seconds=freshness_seconds
                        )
                    ),
                    "freshness_seconds_invalid",
                )

    def test_authorization_stale_by_freshness_seconds_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(freshness_seconds=10),
                evaluation_time="2024-01-01T00:00:11Z",
            ),
            "authorization_stale",
        )


class BoundaryFlagTests(unittest.TestCase):
    def test_transaction_boundary_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    transaction_boundary_declared=False
                )
            ),
            "transaction_boundary_not_declared",
        )

    def test_rollback_boundary_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(rollback_boundary_declared=False)
            ),
            "rollback_boundary_not_declared",
        )

    def test_idempotency_boundary_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    idempotency_boundary_declared=False
                )
            ),
            "idempotency_boundary_not_declared",
        )

    def test_before_evidence_ref_invalid(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(before_evidence_ref="")),
            "before_evidence_ref_invalid",
        )

    def test_after_evidence_required_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(after_evidence_required=False)),
            "after_evidence_not_required",
        )

    def test_audit_append_required_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(audit_append_required=False)),
            "audit_append_not_required",
        )

    def test_evidence_append_required_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(evidence_append_required=False)
            ),
            "evidence_append_not_required",
        )


class AuthorizationFlagTests(unittest.TestCase):
    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(authorization=_authorization(**{flag: "no"})),
                    "authorization_flag_invalid",
                )
                self.assertIsNone(result["authorization"][flag])

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                result = _assert_rejected_with(
                    _payload(authorization=_authorization(**{flag: True})),
                    "authorization_flag_true",
                )
                self.assertIs(result["authorization"][flag], False)

    def test_irreversible_action_prohibited_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(
                authorization=_authorization(
                    irreversible_action_prohibited=False
                )
            ),
            "irreversible_action_not_prohibited",
        )

    def test_fail_closed_declared_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(fail_closed_declared=False)),
            "fail_closed_not_declared",
        )

    def test_json_safe_false_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(json_safe=False)),
            "json_safe_invalid",
        )

    def test_json_safe_non_bool_rejected(self) -> None:
        _assert_rejected_with(
            _payload(authorization=_authorization(json_safe="yes")),
            "json_safe_invalid",
        )


class CombinedFailureOrderingTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        payload = _payload(
            preflight=_preflight_summary(aggregate_ok=False),
            authorization=_authorization(
                source_preflight_stack_commit="bad-commit",
                approved_task_id="T-2",
                transaction_boundary_declared=False,
                audit_append_required=False,
                restore_authorized=True,
                json_safe=False,
            ),
        )
        payload["extra"] = True

        result = validate_execution_authorization(payload)

        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "preflight_summary_not_ready",
                "source_preflight_stack_commit_mismatch",
                "task_id_mismatch",
                "transaction_boundary_not_declared",
                "audit_append_not_required",
                "authorization_flag_true",
                "json_safe_invalid",
            ],
        )


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            execution_authorization_validator_manifest(), EXPECTED_MANIFEST
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest_a = execution_authorization_validator_manifest()
        manifest_a["failure_values"].append("tampered")
        manifest_a["depends_on"]["extra"] = "x"

        self.assertEqual(
            execution_authorization_validator_manifest(), EXPECTED_MANIFEST
        )


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(validator_module.__all__),
            sorted(
                [
                    "execution_authorization_validator_manifest",
                    "validate_execution_authorization",
                ]
            ),
        )
        public_names = {
            name for name in dir(validator_module) if not name.startswith("_")
        }
        self.assertEqual(
            public_names,
            {
                "execution_authorization_validator_manifest",
                "validate_execution_authorization",
            },
        )

    def test_callable_signatures(self) -> None:
        manifest_sig = inspect.signature(
            execution_authorization_validator_manifest
        )
        self.assertEqual(list(manifest_sig.parameters), [])

        validate_sig = inspect.signature(validate_execution_authorization)
        self.assertEqual(list(validate_sig.parameters), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_does_not_contain_forbidden_markers(self) -> None:
        scrubbed = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, scrubbed)

    def test_no_hidden_wall_clock_dependency(self) -> None:
        source = inspect.getsource(validator_module)
        self.assertNotIn("datetime.now", source)
        self.assertNotIn("time.time", source)
        self.assertNotIn("time.monotonic", source)

        payload = _payload()
        self.assertEqual(
            validate_execution_authorization(payload),
            validate_execution_authorization(payload),
        )

    def test_no_digest_computation(self) -> None:
        source = inspect.getsource(validator_module)
        self.assertNotIn("hashlib", source)
        self.assertNotIn("hmac", source)
        self.assertNotIn("secrets", source)
        self.assertNotIn("sha256", source)
        self.assertNotIn("blake2", source)


if __name__ == "__main__":
    unittest.main()
