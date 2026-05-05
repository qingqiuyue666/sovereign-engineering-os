"""Tracer-bullet tests for the read-only Execution Preflight (H2)."""

from __future__ import annotations

import inspect
import json
import unittest
from copy import deepcopy

from kernel.lifecycle import execution_preflight as ep_module
from kernel.lifecycle.execution_preflight import (
    ExecutionPreflight,
    evaluate_execution_preflight,
    execution_preflight_manifest,
    render_execution_preflight,
)


PUBLIC_API = {
    "ExecutionPreflight",
    "execution_preflight_manifest",
    "evaluate_execution_preflight",
    "render_execution_preflight",
}


EXPECTED_PREFLIGHT_KEYS = [
    "surface",
    "version",
    "aggregate_summary_ok",
    "human_approval_ci_ok",
    "operator_confirmation_present",
    "execution_boundary_declared",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_ref",
    "actor_identity_approval",
    "actor_identity_confirmation",
    "actor_policy",
    "confirmation_digest",
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    "audit_evidence_envelope_declared",
    "before_after_evidence_declared",
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


AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
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
    "hashlib",
    "hmac",
    "secrets",
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
    "evaluate_human_approval_readiness",
    "render_human_approval_readiness",
    "consume_human_approval_readiness_ci",
    "human_approval_readiness_ci_manifest",
    "summarize_restore_dry_run_readiness",
    "restore_dry_run_aggregate_summary_manifest",
    "governance_readiness_aggregator",
)


ALLOWED_SOURCE_FIELD_STRINGS = (
    "execution_preflight",
    "human_approval_readiness_ci",
    "human-approval-readiness-ci-v1",
    "restore_dry_run_aggregate_summary",
    "restore-dry-run-read-only-stack-v1",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
    "daemon_server_queue_required",
    "confirmation_digest",
    "audit_evidence_envelope_declared",
    "audit_evidence_envelope_not_declared",
)


def _scrubbed_source() -> str:
    source = inspect.getsource(ep_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


def _aggregate_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "surface": "restore_dry_run_aggregate_summary",
        "version": 1,
        "readiness_ci_ok": True,
        "plan_ci_ok": True,
        "target_task_id": "T-1",
        "operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "determinism_hash": "det-hash-1",
        "transaction_required": True,
        "rollback_required": True,
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


def _h1_ci(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "human_approval_readiness",
        "version": 1,
        "human_approval_ready": True,
        "human_approval_reason_code": "ready",
        "approval_ref": "AR-1",
        "actor_identity": "alice@org",
        "approval_scope": "restore:T-1",
        "approval_reason": "recover from incident",
        "created_at": "2024-01-01T00:00:00Z",
        "expires_at": "2024-01-02T00:00:00Z",
        "freshness_seconds": 3600,
        "target_task_id": "T-1",
        "operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "aggregate_summary_ref": "agg-ref-1",
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


def _operator(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "confirmation_present": True,
        "confirmation_ref": "CR-1",
        "actor_identity": "alice@org",
        "actor_policy": "same_actor_required",
        "confirmation_scope": "restore:T-1",
        "confirmation_reason": "operator confirms restore",
        "confirmed_at": "2024-01-01T01:00:00Z",
        "target_task_id": "T-1",
        "operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "aggregate_summary_ref": "agg-ref-1",
        "human_approval_ref": "AR-1",
        "confirmation_digest": "digest-1",
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


def _boundary(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "transaction_declared": True,
        "rollback_declared": True,
        "expected_rejection_policy_declared": True,
        "idempotency_declared": True,
        "audit_evidence_envelope_declared": True,
        "before_after_evidence_declared": True,
        "target_task_id": "T-1",
        "operation_kind": "op-restore",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "aggregate_summary_ref": "agg-ref-1",
        "human_approval_ref": "AR-1",
        "confirmation_digest": "digest-1",
        "schema_migration_required": False,
        "db_repair_required": False,
        "cli_execution_required": False,
        "daemon_server_queue_required": False,
        "runtime_calls_required": False,
        "durable_writes_requested": False,
        "restore_requested": False,
        "write_side_recovery_requested": False,
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


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "restore_dry_run_aggregate_summary": _aggregate_summary(),
        "human_approval_readiness_ci": _h1_ci(),
        "operator_confirmation_declaration": _operator(),
        "execution_boundary_declaration": _boundary(),
    }
    base.update(overrides)
    return base


class HappyPathTests(unittest.TestCase):
    def test_same_actor_required_happy_path(self) -> None:
        result = evaluate_execution_preflight(_payload())
        self.assertIsInstance(result, ExecutionPreflight)
        self.assertIs(result.preflight_ok, True)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())

    def test_dual_control_allowed_happy_path(self) -> None:
        operator = _operator(
            actor_policy="dual_control_allowed",
            actor_identity="bob@org",
        )
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=operator)
        )
        self.assertIs(result.preflight_ok, True)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())
        self.assertEqual(
            result.preflight["actor_identity_approval"], "alice@org"
        )
        self.assertEqual(
            result.preflight["actor_identity_confirmation"], "bob@org"
        )
        self.assertEqual(result.preflight["actor_policy"], "dual_control_allowed")

    def test_preflight_ok_does_not_authorize_restore_or_write_side(
        self,
    ) -> None:
        result = evaluate_execution_preflight(_payload())
        self.assertIs(result.preflight_ok, True)
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(result.preflight[flag], False, flag)
        self.assertIs(result.preflight["executes_plan"], False)
        self.assertIs(result.preflight["json_safe"], True)

    def test_exact_output_shape(self) -> None:
        result = evaluate_execution_preflight(_payload())
        self.assertEqual(
            list(result.preflight.keys()), EXPECTED_PREFLIGHT_KEYS
        )
        rendered = render_execution_preflight(result)
        self.assertEqual(
            list(rendered.keys()),
            ["preflight_ok", "reason_code", "failures", "preflight"],
        )
        self.assertEqual(
            list(rendered["preflight"].keys()), EXPECTED_PREFLIGHT_KEYS
        )

    def test_render_output_is_json_safe(self) -> None:
        result = evaluate_execution_preflight(_payload())
        rendered = render_execution_preflight(result)
        encoded = json.dumps(rendered, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["preflight_ok"], True)
        self.assertEqual(decoded["reason_code"], "ready")
        self.assertEqual(decoded["failures"], [])
        self.assertEqual(decoded["preflight"]["surface"], "execution_preflight")
        self.assertEqual(decoded["preflight"]["version"], 1)


class TopLevelShapeTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        result = evaluate_execution_preflight("nope")
        self.assertIs(result.preflight_ok, False)
        self.assertEqual(result.reason_code, "invalid_preflight_payload")
        self.assertIn("payload_not_mapping", result.failures)

    def test_missing_top_level_key(self) -> None:
        payload = _payload()
        payload.pop("execution_boundary_declaration")
        result = evaluate_execution_preflight(payload)
        self.assertIn("payload_shape_mismatch", result.failures)
        self.assertEqual(result.reason_code, "invalid_preflight_payload")

    def test_unknown_top_level_key(self) -> None:
        payload = _payload(extra="nope")
        result = evaluate_execution_preflight(payload)
        self.assertIn("payload_shape_mismatch", result.failures)
        self.assertEqual(result.reason_code, "invalid_preflight_payload")

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = deepcopy(payload)
        evaluate_execution_preflight(payload)
        self.assertEqual(payload, snapshot)


class AggregateSummaryTests(unittest.TestCase):
    def test_aggregate_summary_invalid_when_not_mapping(self) -> None:
        result = evaluate_execution_preflight(
            _payload(restore_dry_run_aggregate_summary="oops")
        )
        self.assertIn("aggregate_summary_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_preflight_payload")

    def test_aggregate_summary_invalid_when_summary_shape_wrong(
        self,
    ) -> None:
        agg = _aggregate_summary()
        agg["summary"].pop("readiness_ci_ok")  # type: ignore[union-attr]
        result = evaluate_execution_preflight(
            _payload(restore_dry_run_aggregate_summary=agg)
        )
        self.assertIn("aggregate_summary_invalid", result.failures)

    def test_aggregate_summary_not_ready_when_aggregate_ok_false(self) -> None:
        agg = _aggregate_summary(aggregate_ok=False, reason_code="not_ready")
        result = evaluate_execution_preflight(
            _payload(restore_dry_run_aggregate_summary=agg)
        )
        self.assertIn("aggregate_summary_not_ready", result.failures)
        self.assertEqual(result.reason_code, "not_ready")

    def test_aggregate_summary_authorization_flag_true_rejected(self) -> None:
        agg = _aggregate_summary(summary__restore_authorized=True)
        result = evaluate_execution_preflight(
            _payload(restore_dry_run_aggregate_summary=agg)
        )
        self.assertIn("authorization_flag_true", result.failures)

    def test_aggregate_summary_executes_plan_true_rejected(self) -> None:
        agg = _aggregate_summary(summary__executes_plan=True)
        result = evaluate_execution_preflight(
            _payload(restore_dry_run_aggregate_summary=agg)
        )
        self.assertIn("execution_flag_true", result.failures)

    def test_aggregate_summary_json_safe_false_rejected(self) -> None:
        agg = _aggregate_summary(summary__json_safe=False)
        result = evaluate_execution_preflight(
            _payload(restore_dry_run_aggregate_summary=agg)
        )
        self.assertIn("json_safe_invalid", result.failures)


class HumanApprovalCITests(unittest.TestCase):
    def test_h1_ci_invalid_when_not_mapping(self) -> None:
        result = evaluate_execution_preflight(
            _payload(human_approval_readiness_ci=42)
        )
        self.assertIn("human_approval_ci_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_preflight_payload")

    def test_h1_ci_invalid_when_keys_wrong(self) -> None:
        h1 = _h1_ci()
        h1.pop("approval_ref")
        result = evaluate_execution_preflight(
            _payload(human_approval_readiness_ci=h1)
        )
        self.assertIn("human_approval_ci_invalid", result.failures)

    def test_h1_ci_not_ready_when_ci_ok_false(self) -> None:
        h1 = _h1_ci(ci_ok=False, reason_code="not_ready")
        result = evaluate_execution_preflight(
            _payload(human_approval_readiness_ci=h1)
        )
        self.assertIn("human_approval_ci_not_ready", result.failures)
        self.assertEqual(result.reason_code, "not_ready")

    def test_h1_ci_authorization_flag_invalid_rejected(self) -> None:
        h1 = _h1_ci(restore_authorized="yes")
        result = evaluate_execution_preflight(
            _payload(human_approval_readiness_ci=h1)
        )
        self.assertIn("authorization_flag_invalid", result.failures)

    def test_h1_ci_executes_plan_invalid_rejected(self) -> None:
        h1 = _h1_ci(executes_plan="false")
        result = evaluate_execution_preflight(
            _payload(human_approval_readiness_ci=h1)
        )
        self.assertIn("execution_flag_invalid", result.failures)

    def test_h1_ci_json_safe_invalid_rejected(self) -> None:
        h1 = _h1_ci(json_safe="yes")
        result = evaluate_execution_preflight(
            _payload(human_approval_readiness_ci=h1)
        )
        self.assertIn("json_safe_invalid", result.failures)


class OperatorConfirmationTests(unittest.TestCase):
    def test_operator_invalid_when_not_mapping(self) -> None:
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=None)
        )
        self.assertIn("operator_confirmation_invalid", result.failures)

    def test_operator_invalid_when_keys_wrong(self) -> None:
        op = _operator()
        op.pop("confirmation_ref")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("operator_confirmation_invalid", result.failures)

    def test_operator_missing_when_confirmation_present_false(self) -> None:
        op = _operator(confirmation_present=False)
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("operator_confirmation_missing", result.failures)

    def test_operator_authorization_true_rejected(self) -> None:
        op = _operator(restore_authorized=True)
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("authorization_flag_true", result.failures)

    def test_operator_execution_flag_true_rejected(self) -> None:
        op = _operator(executes_plan=True)
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("execution_flag_true", result.failures)

    def test_operator_json_safe_false_rejected(self) -> None:
        op = _operator(json_safe=False)
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("json_safe_invalid", result.failures)


class ExecutionBoundaryTests(unittest.TestCase):
    def test_boundary_invalid_when_not_mapping(self) -> None:
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=42)
        )
        self.assertIn("execution_boundary_invalid", result.failures)

    def test_boundary_invalid_when_keys_wrong(self) -> None:
        bd = _boundary()
        bd.pop("rollback_declared")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("execution_boundary_invalid", result.failures)

    def test_each_declaration_false_emits_specific_failure(self) -> None:
        cases = [
            ("transaction_declared", "transaction_not_declared"),
            ("rollback_declared", "rollback_not_declared"),
            (
                "expected_rejection_policy_declared",
                "expected_rejection_policy_not_declared",
            ),
            ("idempotency_declared", "idempotency_not_declared"),
            (
                "audit_evidence_envelope_declared",
                "audit_evidence_envelope_not_declared",
            ),
            (
                "before_after_evidence_declared",
                "before_after_evidence_not_declared",
            ),
        ]
        for flag, code in cases:
            with self.subTest(flag=flag):
                bd = _boundary(**{flag: False})
                result = evaluate_execution_preflight(
                    _payload(execution_boundary_declaration=bd)
                )
                self.assertIn(code, result.failures)

    def test_each_request_true_emits_specific_failure(self) -> None:
        request_flags = [
            "schema_migration_required",
            "db_repair_required",
            "cli_execution_required",
            "daemon_server_queue_required",
            "runtime_calls_required",
            "durable_writes_requested",
            "restore_requested",
            "write_side_recovery_requested",
        ]
        for flag in request_flags:
            with self.subTest(flag=flag):
                bd = _boundary(**{flag: True})
                result = evaluate_execution_preflight(
                    _payload(execution_boundary_declaration=bd)
                )
                self.assertIn(flag, result.failures)

    def test_boundary_authorization_flag_true_rejected(self) -> None:
        bd = _boundary(restore_authorized=True)
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("authorization_flag_true", result.failures)

    def test_boundary_authorization_flag_invalid_rejected(self) -> None:
        bd = _boundary(durable_writes="yes")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("authorization_flag_invalid", result.failures)

    def test_boundary_execution_flag_true_rejected(self) -> None:
        bd = _boundary(executes_plan=True)
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("execution_flag_true", result.failures)

    def test_boundary_execution_flag_invalid_rejected(self) -> None:
        bd = _boundary(executes_plan="no")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("execution_flag_invalid", result.failures)

    def test_boundary_json_safe_false_rejected(self) -> None:
        bd = _boundary(json_safe=False)
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("json_safe_invalid", result.failures)


class CrossCheckTests(unittest.TestCase):
    def test_target_task_id_mismatch(self) -> None:
        bd = _boundary(target_task_id="T-2")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("target_task_id_mismatch", result.failures)

    def test_operation_kind_mismatch(self) -> None:
        op = _operator(operation_kind="op-other")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("operation_kind_mismatch", result.failures)

    def test_idempotency_key_mismatch(self) -> None:
        op = _operator(idempotency_key="idem-2")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("idempotency_key_mismatch", result.failures)

    def test_projected_action_mismatch(self) -> None:
        bd = _boundary(projected_action="projected.other")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("projected_action_mismatch", result.failures)

    def test_projected_evidence_ref_mismatch(self) -> None:
        bd = _boundary(projected_evidence_ref="ev/ref/2")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("projected_evidence_ref_mismatch", result.failures)

    def test_aggregate_summary_ref_mismatch(self) -> None:
        op = _operator(aggregate_summary_ref="agg-ref-2")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("aggregate_summary_ref_mismatch", result.failures)

    def test_human_approval_ref_mismatch(self) -> None:
        op = _operator(human_approval_ref="AR-2")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("human_approval_ref_mismatch", result.failures)


class ActorPolicyTests(unittest.TestCase):
    def test_actor_policy_invalid(self) -> None:
        op = _operator(actor_policy="anything_goes")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("actor_policy_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_preflight_payload")

    def test_actor_identity_mismatch_under_same_actor_required(self) -> None:
        op = _operator(actor_identity="mallory@org")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("actor_identity_mismatch", result.failures)

    def test_actor_identity_allowed_to_differ_under_dual_control(self) -> None:
        op = _operator(
            actor_policy="dual_control_allowed",
            actor_identity="carol@org",
        )
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertNotIn("actor_identity_mismatch", result.failures)
        self.assertNotIn("actor_identity_missing", result.failures)
        self.assertIs(result.preflight_ok, True)

    def test_actor_identity_missing_under_same_actor(self) -> None:
        op = _operator(actor_identity="")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("actor_identity_missing", result.failures)

    def test_actor_identity_missing_under_dual_control(self) -> None:
        op = _operator(
            actor_policy="dual_control_allowed", actor_identity=""
        )
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("actor_identity_missing", result.failures)


class ConfirmationDigestTests(unittest.TestCase):
    def test_confirmation_digest_invalid_when_operator_empty(self) -> None:
        op = _operator(confirmation_digest="")
        result = evaluate_execution_preflight(
            _payload(operator_confirmation_declaration=op)
        )
        self.assertIn("confirmation_digest_invalid", result.failures)

    def test_confirmation_digest_invalid_when_boundary_non_string(
        self,
    ) -> None:
        bd = _boundary(confirmation_digest=123)
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("confirmation_digest_invalid", result.failures)

    def test_confirmation_digest_mismatch(self) -> None:
        bd = _boundary(confirmation_digest="digest-2")
        result = evaluate_execution_preflight(
            _payload(execution_boundary_declaration=bd)
        )
        self.assertIn("confirmation_digest_mismatch", result.failures)


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = execution_preflight_manifest()
        self.assertEqual(manifest["surface"], "execution_preflight")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["input_shape"],
            "already_rendered_execution_preflight_payloads",
        )
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(manifest[flag], False, flag)
        self.assertIs(manifest["executes_plan"], False)
        self.assertEqual(manifest["runtime_dependencies"], [])
        self.assertIs(manifest["json_safe"], True)
        depends = manifest["depends_on"]
        self.assertEqual(
            depends["human_approval_readiness_ci"],
            "human-approval-readiness-ci-v1",
        )
        self.assertEqual(
            depends["human_approval_readiness"],
            "human-approval-readiness-v1",
        )
        self.assertEqual(
            depends["restore_dry_run_read_only_stack"],
            "restore-dry-run-read-only-stack-v1",
        )
        self.assertEqual(
            depends["restore_dry_run_aggregate_summary"],
            "restore-dry-run-aggregate-summary-v1",
        )
        self.assertEqual(
            depends["restore_dry_run_plan_ci"], "restore-dry-run-plan-ci-v1"
        )
        self.assertEqual(
            depends["restore_dry_run_plan_renderer"],
            "restore-dry-run-plan-renderer-v1",
        )
        self.assertEqual(
            depends["restore_dry_run_readiness_ci"],
            "restore-dry-run-readiness-ci-v1",
        )
        self.assertEqual(
            depends["restore_dry_run_readiness"],
            "restore-dry-run-readiness-v1",
        )
        self.assertEqual(
            depends["write_side_recovery_spec_only"],
            "write-side-recovery-spec-only-v1",
        )
        self.assertEqual(
            depends["write_side_precondition_ci"],
            "write-side-precondition-ci-v1",
        )
        self.assertEqual(
            depends["write_side_precondition_checker"],
            "write-side-precondition-checker-v1",
        )
        self.assertEqual(
            depends["read_only_governance_layer"],
            "read-only-governance-layer-v1",
        )

    def test_manifest_returns_defensive_copy(self) -> None:
        first = execution_preflight_manifest()
        first["surface"] = "tampered"
        first["depends_on"]["read_only_governance_layer"] = "tampered"
        second = execution_preflight_manifest()
        self.assertEqual(second["surface"], "execution_preflight")
        self.assertEqual(
            second["depends_on"]["read_only_governance_layer"],
            "read-only-governance-layer-v1",
        )


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(set(ep_module.__all__), PUBLIC_API)

    def test_render_returns_independent_copy(self) -> None:
        result = evaluate_execution_preflight(_payload())
        rendered_a = render_execution_preflight(result)
        rendered_a["preflight"]["surface"] = "tampered"
        rendered_b = render_execution_preflight(result)
        self.assertEqual(
            rendered_b["preflight"]["surface"], "execution_preflight"
        )


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary_has_no_forbidden_symbols(self) -> None:
        source = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            self.assertNotIn(marker, source, marker)

    def test_no_wall_clock_dependency(self) -> None:
        source = inspect.getsource(ep_module)
        self.assertNotIn("datetime", source)
        self.assertNotIn("time.time", source)
        self.assertNotIn("time.monotonic", source)

    def test_no_digest_computation(self) -> None:
        source = inspect.getsource(ep_module)
        self.assertNotIn("hashlib", source)
        self.assertNotIn("hmac", source)
        self.assertNotIn("sha256", source)
        self.assertNotIn("blake2", source)


if __name__ == "__main__":
    unittest.main()
