"""Tracer-bullet tests for the H3 preflight aggregate summary."""

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

from kernel.lifecycle import preflight_aggregate_summary as aggregate_module
from kernel.lifecycle.preflight_aggregate_summary import (
    preflight_aggregate_summary_manifest,
    summarize_preflight_readiness,
)


EXPECTED_MANIFEST = {
    "surface": "preflight_aggregate_summary",
    "version": 1,
    "input_shape": "already_rendered_h1_ci_and_h2_ci",
    "depends_on": {
        "h2_execution_preflight_ci": "h2-execution-preflight-ci-v1",
        "h2_execution_preflight": "h2-execution-preflight-v1",
        "human_approval_readiness_ci": "human-approval-readiness-ci-v1",
        "human_approval_readiness": "human-approval-readiness-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "restore_dry_run_aggregate_summary": (
            "restore-dry-run-aggregate-summary-v1"
        ),
        "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
        "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
        "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
        "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
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
    "reason_codes": ["invalid_aggregate_payload", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "human_approval_ci_invalid",
        "human_approval_ci_not_ready",
        "execution_preflight_ci_invalid",
        "execution_preflight_ci_not_ready",
        "target_task_id_mismatch",
        "operation_kind_mismatch",
        "idempotency_key_mismatch",
        "projected_action_mismatch",
        "projected_evidence_ref_mismatch",
        "aggregate_summary_ref_mismatch",
        "human_approval_ref_mismatch",
        "actor_identity_mismatch",
        "actor_policy_invalid",
        "confirmation_ref_invalid",
        "confirmation_digest_invalid",
        "transaction_not_declared",
        "rollback_not_declared",
        "expected_rejection_policy_not_declared",
        "idempotency_not_declared",
        "audit_evidence_envelope_not_declared",
        "before_after_evidence_not_declared",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "execution_flag_invalid",
        "execution_flag_true",
        "json_safe_invalid",
    ],
}


EXPECTED_TOP_LEVEL_KEYS = ["aggregate_ok", "reason_code", "failures", "summary"]


EXPECTED_SUMMARY_KEYS = [
    "surface",
    "version",
    "human_approval_ci_ok",
    "execution_preflight_ci_ok",
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


DECLARATION_FLAGS = (
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    "audit_evidence_envelope_declared",
    "before_after_evidence_declared",
)


DECLARATION_FAILURE = {
    "transaction_declared": "transaction_not_declared",
    "rollback_declared": "rollback_not_declared",
    "expected_rejection_policy_declared": "expected_rejection_policy_not_declared",
    "idempotency_declared": "idempotency_not_declared",
    "audit_evidence_envelope_declared": "audit_evidence_envelope_not_declared",
    "before_after_evidence_declared": "before_after_evidence_not_declared",
}


REPR_MARKERS = (
    "PreflightAggregate(",
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
    "evaluate_execution_preflight",
    "render_execution_preflight",
    "execution_preflight_manifest",
    "consume_execution_preflight_ci",
    "execution_preflight_ci_manifest",
    "evaluate_human_approval_readiness",
    "render_human_approval_readiness",
    "consume_human_approval_readiness_ci",
    "human_approval_readiness_ci_manifest",
    "summarize_restore_dry_run_readiness",
    "restore_dry_run_aggregate_summary_manifest",
    "governance_readiness_aggregator",
)


ALLOWED_SOURCE_FIELD_STRINGS = (
    "preflight_aggregate_summary",
    "execution_preflight_ci",
    "execution_preflight",
    "h2-execution-preflight-ci-v1",
    "h2-execution-preflight-v1",
    "human_approval_readiness_ci",
    "human-approval-readiness-ci-v1",
    "restore_dry_run_aggregate_summary",
    "restore-dry-run-read-only-stack-v1",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
    "confirmation_digest",
)


def _valid_h1_ci(**overrides: object) -> dict[str, object]:
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
        "operation_kind": "op-recover",
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


def _valid_h2_ci(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "execution_preflight",
        "version": 1,
        "preflight_ok": True,
        "preflight_reason_code": "ready",
        "target_task_id": "T-1",
        "operation_kind": "op-recover",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "aggregate_summary_ref": "agg-ref-1",
        "human_approval_ref": "AR-1",
        "confirmation_ref": "CR-1",
        "actor_identity_approval": "alice@org",
        "actor_identity_confirmation": "alice@org",
        "actor_policy": "same_actor_required",
        "confirmation_digest": "d1",
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
    base.update(overrides)
    return base


def _valid_payload(
    *,
    h1: dict[str, object] | None = None,
    h2: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "human_approval_readiness_ci": h1 if h1 is not None else _valid_h1_ci(),
        "execution_preflight_ci": h2 if h2 is not None else _valid_h2_ci(),
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
    source = inspect.getsource(aggregate_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


class HappyPathTests(unittest.TestCase):
    def test_same_actor_required_ready(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())

        self.assertIs(result["aggregate_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(list(result.keys()), EXPECTED_TOP_LEVEL_KEYS)

    def test_dual_control_allowed_ready(self) -> None:
        h2 = _valid_h2_ci(
            actor_policy="dual_control_allowed",
            actor_identity_approval="alice@org",
            actor_identity_confirmation="bob@org",
        )

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["summary"]["actor_policy"], "dual_control_allowed"
        )
        self.assertEqual(
            result["summary"]["actor_identity_approval"], "alice@org"
        )
        self.assertEqual(
            result["summary"]["actor_identity_confirmation"], "bob@org"
        )

    def test_aggregate_ok_does_not_authorize_restore_or_write_side(
        self,
    ) -> None:
        result = summarize_preflight_readiness(_valid_payload())
        summary = result["summary"]

        self.assertIs(result["aggregate_ok"], True)
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(summary[flag], False, flag)
        self.assertIs(summary["executes_plan"], False)
        self.assertIs(summary["json_safe"], True)

    def test_summary_fields_populated_from_inputs(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())
        summary = result["summary"]

        self.assertEqual(summary["surface"], "preflight_aggregate_summary")
        self.assertEqual(summary["version"], 1)
        self.assertIs(summary["human_approval_ci_ok"], True)
        self.assertIs(summary["execution_preflight_ci_ok"], True)
        self.assertEqual(summary["target_task_id"], "T-1")
        self.assertEqual(summary["operation_kind"], "op-recover")
        self.assertEqual(summary["idempotency_key"], "idem-1")
        self.assertEqual(summary["projected_action"], "projected.restore")
        self.assertEqual(summary["projected_evidence_ref"], "ev/ref/1")
        self.assertEqual(summary["aggregate_summary_ref"], "agg-ref-1")
        self.assertEqual(summary["human_approval_ref"], "AR-1")
        self.assertEqual(summary["confirmation_ref"], "CR-1")
        self.assertEqual(summary["actor_identity_approval"], "alice@org")
        self.assertEqual(summary["actor_identity_confirmation"], "alice@org")
        self.assertEqual(summary["actor_policy"], "same_actor_required")
        self.assertEqual(summary["confirmation_digest"], "d1")
        for flag in DECLARATION_FLAGS:
            self.assertIs(summary[flag], True, flag)


class OutputShapeTests(unittest.TestCase):
    def test_exact_top_level_keys(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())

        self.assertEqual(list(result.keys()), EXPECTED_TOP_LEVEL_KEYS)

    def test_exact_summary_keys(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())

        self.assertEqual(list(result["summary"].keys()), EXPECTED_SUMMARY_KEYS)

    def test_output_json_safe(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())

        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())

        _assert_no_runtime_repr(result)

    def test_output_failures_is_fresh_list(self) -> None:
        result_a = summarize_preflight_readiness(_valid_payload())
        result_b = summarize_preflight_readiness(_valid_payload())

        result_a["failures"].append("tampered")
        self.assertEqual(result_b["failures"], [])

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)

        summarize_preflight_readiness(payload)

        self.assertEqual(payload, snapshot)


class TopLevelPayloadTests(unittest.TestCase):
    def test_non_mapping_payload_rejected(self) -> None:
        for candidate in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(candidate=candidate):
                result = summarize_preflight_readiness(candidate)

                self.assertIs(result["aggregate_ok"], False)
                self.assertEqual(
                    result["reason_code"], "invalid_aggregate_payload"
                )
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["execution_preflight_ci"]

        result = summarize_preflight_readiness(payload)

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("payload_shape_mismatch", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _valid_payload()
        payload["extra"] = True

        result = summarize_preflight_readiness(payload)

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("payload_shape_mismatch", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")


class HumanApprovalCITests(unittest.TestCase):
    def test_h1_non_mapping_rejected(self) -> None:
        result = summarize_preflight_readiness(
            {
                "human_approval_readiness_ci": "not-a-mapping",
                "execution_preflight_ci": _valid_h2_ci(),
            }
        )

        self.assertIs(result["aggregate_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")
        self.assertIn("human_approval_ci_invalid", result["failures"])

    def test_h1_malformed_shape_rejected(self) -> None:
        h1 = _valid_h1_ci()
        del h1["surface"]

        result = summarize_preflight_readiness(_valid_payload(h1=h1))

        self.assertIs(result["aggregate_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")
        self.assertIn("human_approval_ci_invalid", result["failures"])

    def test_h1_not_ready_rejected(self) -> None:
        h1 = _valid_h1_ci(ci_ok=False, reason_code="not_ready")

        result = summarize_preflight_readiness(_valid_payload(h1=h1))

        self.assertIs(result["aggregate_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIn("human_approval_ci_not_ready", result["failures"])
        self.assertNotIn("human_approval_ci_invalid", result["failures"])

    def test_h1_authorization_true_rejected(self) -> None:
        h1 = _valid_h1_ci(restore_authorized=True)

        result = summarize_preflight_readiness(_valid_payload(h1=h1))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("authorization_flag_true", result["failures"])

    def test_h1_authorization_non_bool_rejected(self) -> None:
        h1 = _valid_h1_ci(restore_authorized=1)

        result = summarize_preflight_readiness(_valid_payload(h1=h1))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("authorization_flag_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")


class ExecutionPreflightCITests(unittest.TestCase):
    def test_h2_non_mapping_rejected(self) -> None:
        result = summarize_preflight_readiness(
            {
                "human_approval_readiness_ci": _valid_h1_ci(),
                "execution_preflight_ci": [1, 2, 3],
            }
        )

        self.assertIs(result["aggregate_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")
        self.assertIn("execution_preflight_ci_invalid", result["failures"])

    def test_h2_malformed_shape_rejected(self) -> None:
        h2 = _valid_h2_ci()
        h2["unexpected"] = True

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")
        self.assertIn("execution_preflight_ci_invalid", result["failures"])

    def test_h2_not_ready_rejected(self) -> None:
        h2 = _valid_h2_ci(ci_ok=False, reason_code="not_ready")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIn("execution_preflight_ci_not_ready", result["failures"])
        self.assertNotIn(
            "execution_preflight_ci_invalid", result["failures"]
        )

    def test_h2_preflight_ok_false_rejected(self) -> None:
        h2 = _valid_h2_ci(preflight_ok=False)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("execution_preflight_ci_not_ready", result["failures"])

    def test_h2_authorization_true_rejected(self) -> None:
        h2 = _valid_h2_ci(durable_writes=True)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("authorization_flag_true", result["failures"])

    def test_h2_authorization_non_bool_rejected(self) -> None:
        h2 = _valid_h2_ci(restore_authorized="yes")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("authorization_flag_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")

    def test_h2_executes_plan_true_rejected(self) -> None:
        h2 = _valid_h2_ci(executes_plan=True)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("execution_flag_true", result["failures"])

    def test_h2_executes_plan_non_bool_rejected(self) -> None:
        h2 = _valid_h2_ci(executes_plan=1)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("execution_flag_invalid", result["failures"])

    def test_h2_json_safe_false_rejected(self) -> None:
        h2 = _valid_h2_ci(json_safe=False)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("json_safe_invalid", result["failures"])

    def test_h2_json_safe_non_bool_rejected(self) -> None:
        h2 = _valid_h2_ci(json_safe=1)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("json_safe_invalid", result["failures"])


class CrossCheckTests(unittest.TestCase):
    def test_target_task_id_mismatch(self) -> None:
        h2 = _valid_h2_ci(target_task_id="T-2")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("target_task_id_mismatch", result["failures"])

    def test_operation_kind_mismatch(self) -> None:
        h2 = _valid_h2_ci(operation_kind="op-other")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("operation_kind_mismatch", result["failures"])

    def test_idempotency_key_mismatch(self) -> None:
        h2 = _valid_h2_ci(idempotency_key="idem-other")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("idempotency_key_mismatch", result["failures"])

    def test_projected_action_mismatch(self) -> None:
        h2 = _valid_h2_ci(projected_action="other.action")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("projected_action_mismatch", result["failures"])

    def test_projected_evidence_ref_mismatch(self) -> None:
        h2 = _valid_h2_ci(projected_evidence_ref="ev/ref/other")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn(
            "projected_evidence_ref_mismatch", result["failures"]
        )

    def test_aggregate_summary_ref_mismatch(self) -> None:
        h2 = _valid_h2_ci(aggregate_summary_ref="agg-other")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("aggregate_summary_ref_mismatch", result["failures"])

    def test_human_approval_ref_mismatch(self) -> None:
        h2 = _valid_h2_ci(human_approval_ref="AR-other")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("human_approval_ref_mismatch", result["failures"])


class ActorIdentityTests(unittest.TestCase):
    def test_h1_actor_mismatches_h2_approval_actor(self) -> None:
        h1 = _valid_h1_ci(actor_identity="bob@org")

        result = summarize_preflight_readiness(_valid_payload(h1=h1))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("actor_identity_mismatch", result["failures"])

    def test_same_actor_required_confirmation_actor_mismatch(self) -> None:
        h2 = _valid_h2_ci(
            actor_policy="same_actor_required",
            actor_identity_approval="alice@org",
            actor_identity_confirmation="bob@org",
        )

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("actor_identity_mismatch", result["failures"])

    def test_dual_control_allows_actor_difference(self) -> None:
        h2 = _valid_h2_ci(
            actor_policy="dual_control_allowed",
            actor_identity_approval="alice@org",
            actor_identity_confirmation="bob@org",
        )

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], True)
        self.assertNotIn("actor_identity_mismatch", result["failures"])

    def test_invalid_actor_policy_rejected(self) -> None:
        h2 = _valid_h2_ci(actor_policy="anyone_goes")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("actor_policy_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")


class ConfirmationTests(unittest.TestCase):
    def test_missing_confirmation_ref_rejected(self) -> None:
        h2 = _valid_h2_ci(confirmation_ref="")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("confirmation_ref_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")

    def test_invalid_confirmation_ref_type_rejected(self) -> None:
        h2 = _valid_h2_ci(confirmation_ref=42)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("confirmation_ref_invalid", result["failures"])

    def test_missing_confirmation_digest_rejected(self) -> None:
        h2 = _valid_h2_ci(confirmation_digest="")

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("confirmation_digest_invalid", result["failures"])
        self.assertEqual(result["reason_code"], "invalid_aggregate_payload")

    def test_invalid_confirmation_digest_type_rejected(self) -> None:
        h2 = _valid_h2_ci(confirmation_digest=None)

        result = summarize_preflight_readiness(_valid_payload(h2=h2))

        self.assertIs(result["aggregate_ok"], False)
        self.assertIn("confirmation_digest_invalid", result["failures"])


class DeclarationFlagTests(unittest.TestCase):
    def test_each_declaration_flag_false_emits_failure(self) -> None:
        for flag, failure_code in DECLARATION_FAILURE.items():
            with self.subTest(flag=flag):
                h2 = _valid_h2_ci(**{flag: False})
                result = summarize_preflight_readiness(_valid_payload(h2=h2))

                self.assertIs(result["aggregate_ok"], False)
                self.assertIn(failure_code, result["failures"])
                self.assertEqual(result["reason_code"], "not_ready")


class CombinedFailureOrderingTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        h2 = _valid_h2_ci(
            target_task_id="T-x",
            transaction_declared=False,
            durable_writes=True,
            executes_plan=True,
            json_safe=False,
        )

        result = summarize_preflight_readiness(_valid_payload(h2=h2))
        failures = result["failures"]

        order = [
            "target_task_id_mismatch",
            "transaction_not_declared",
            "authorization_flag_true",
            "execution_flag_true",
            "json_safe_invalid",
        ]
        positions = [failures.index(name) for name in order]
        self.assertEqual(positions, sorted(positions))


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = preflight_aggregate_summary_manifest()

        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        manifest_a = preflight_aggregate_summary_manifest()
        manifest_a["failure_values"].append("tampered")
        manifest_a["depends_on"]["extra"] = "x"

        manifest_b = preflight_aggregate_summary_manifest()

        self.assertEqual(manifest_b, EXPECTED_MANIFEST)

    def test_manifest_authorization_flags_false(self) -> None:
        manifest = preflight_aggregate_summary_manifest()

        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(manifest[flag], False, flag)
        self.assertIs(manifest["executes_plan"], False)
        self.assertIs(manifest["json_safe"], True)


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(aggregate_module.__all__),
            sorted(
                [
                    "preflight_aggregate_summary_manifest",
                    "summarize_preflight_readiness",
                ]
            ),
        )

    def test_callable_signatures(self) -> None:
        manifest_sig = inspect.signature(preflight_aggregate_summary_manifest)
        self.assertEqual(list(manifest_sig.parameters), [])

        summarize_sig = inspect.signature(summarize_preflight_readiness)
        self.assertEqual(list(summarize_sig.parameters), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_does_not_contain_forbidden_markers(self) -> None:
        scrubbed = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, scrubbed)

    def test_source_does_not_import_wall_clock(self) -> None:
        source = inspect.getsource(aggregate_module)
        self.assertNotIn("import time", source)
        self.assertNotIn("import datetime", source)
        self.assertNotIn("from time", source)
        self.assertNotIn("from datetime", source)

    def test_source_does_not_import_digest(self) -> None:
        source = inspect.getsource(aggregate_module)
        self.assertNotIn("import hashlib", source)
        self.assertNotIn("import hmac", source)
        self.assertNotIn("import secrets", source)
        self.assertNotIn("from hashlib", source)
        self.assertNotIn("from hmac", source)
        self.assertNotIn("from secrets", source)


class AggregateOkAuthorizationTests(unittest.TestCase):
    def test_aggregate_ok_does_not_authorize_restore(self) -> None:
        result = summarize_preflight_readiness(_valid_payload())

        self.assertIs(result["aggregate_ok"], True)
        self.assertIs(result["summary"]["restore_authorized"], False)
        self.assertIs(
            result["summary"]["write_side_recovery_authorized"], False
        )
        self.assertIs(result["summary"]["cli_execution_authorized"], False)
        self.assertIs(
            result["summary"]["schema_migration_authorized"], False
        )
        self.assertIs(
            result["summary"]["daemon_server_queue_authorized"], False
        )
        self.assertIs(result["summary"]["db_repair_authorized"], False)
        self.assertIs(result["summary"]["durable_writes"], False)
        self.assertIs(result["summary"]["executes_plan"], False)


if __name__ == "__main__":
    unittest.main()
