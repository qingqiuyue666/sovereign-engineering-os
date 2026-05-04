"""Tracer-bullet tests for H1 Human Approval Readiness."""

from __future__ import annotations

import copy
import json
import pathlib
import unittest

from kernel.lifecycle import human_approval_readiness as module
from kernel.lifecycle.human_approval_readiness import (
    HumanApprovalReadiness,
    evaluate_human_approval_readiness,
    human_approval_readiness_manifest,
    render_human_approval_readiness,
)


_PRODUCTION_SOURCE_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "kernel"
    / "lifecycle"
    / "human_approval_readiness.py"
)


def _ready_aggregate_summary() -> dict[str, object]:
    return {
        "aggregate_ok": True,
        "reason_code": "ready",
        "failures": [],
        "summary": {
            "surface": "restore_dry_run_aggregate_summary",
            "version": 1,
            "readiness_ci_ok": True,
            "plan_ci_ok": True,
            "target_task_id": "T-1",
            "operation_kind": "op-recover",
            "idempotency_key": "idem-1",
            "projected_action": "projected.restore",
            "projected_evidence_ref": "ev/ref/1",
            "determinism_hash": "h1",
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
        },
    }


def _ready_declaration() -> dict[str, object]:
    return {
        "approval_present": True,
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


def _ready_payload() -> dict[str, object]:
    return {
        "aggregate_summary": _ready_aggregate_summary(),
        "human_approval_declaration": _ready_declaration(),
    }


class HappyPathTests(unittest.TestCase):
    def test_ready_payload_returns_ready(self) -> None:
        result = evaluate_human_approval_readiness(_ready_payload())
        self.assertIsInstance(result, HumanApprovalReadiness)
        self.assertTrue(result.human_approval_ready)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())
        self.assertTrue(result.human_approval["aggregate_summary_ready"])
        self.assertTrue(result.human_approval["approval_present"])
        for flag in (
            "restore_authorized",
            "write_side_recovery_authorized",
            "cli_execution_authorized",
            "schema_migration_authorized",
            "daemon_server_queue_authorized",
            "db_repair_authorized",
            "durable_writes",
            "executes_plan",
        ):
            self.assertFalse(result.human_approval[flag])
        self.assertTrue(result.human_approval["json_safe"])

    def test_render_is_json_safe(self) -> None:
        result = evaluate_human_approval_readiness(_ready_payload())
        rendered = render_human_approval_readiness(result)
        encoded = json.dumps(rendered)
        decoded = json.loads(encoded)
        self.assertEqual(decoded, rendered)
        self.assertEqual(rendered["human_approval_ready"], True)
        self.assertEqual(rendered["reason_code"], "ready")
        self.assertEqual(rendered["failures"], [])

    def test_freshness_with_only_expires_at(self) -> None:
        declaration = _ready_declaration()
        declaration["freshness_seconds"] = None
        payload = {
            "aggregate_summary": _ready_aggregate_summary(),
            "human_approval_declaration": declaration,
        }
        result = evaluate_human_approval_readiness(payload)
        self.assertTrue(result.human_approval_ready)

    def test_freshness_with_only_freshness_seconds(self) -> None:
        declaration = _ready_declaration()
        declaration["expires_at"] = None
        payload = {
            "aggregate_summary": _ready_aggregate_summary(),
            "human_approval_declaration": declaration,
        }
        result = evaluate_human_approval_readiness(payload)
        self.assertTrue(result.human_approval_ready)

    def test_freshness_with_both_allowed(self) -> None:
        result = evaluate_human_approval_readiness(_ready_payload())
        self.assertTrue(result.human_approval_ready)


class TopLevelShapeTests(unittest.TestCase):
    def test_payload_not_mapping(self) -> None:
        result = evaluate_human_approval_readiness("not-a-mapping")
        self.assertFalse(result.human_approval_ready)
        self.assertEqual(result.reason_code, "invalid_human_approval_payload")
        self.assertIn("payload_not_mapping", result.failures)

    def test_payload_missing_key(self) -> None:
        result = evaluate_human_approval_readiness(
            {"aggregate_summary": _ready_aggregate_summary()}
        )
        self.assertFalse(result.human_approval_ready)
        self.assertIn("payload_shape_mismatch", result.failures)
        self.assertEqual(result.reason_code, "invalid_human_approval_payload")

    def test_payload_unknown_key(self) -> None:
        payload = _ready_payload()
        payload["extra"] = "x"
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("payload_shape_mismatch", result.failures)
        self.assertEqual(result.reason_code, "invalid_human_approval_payload")


class AggregateSummaryTests(unittest.TestCase):
    def test_aggregate_not_mapping(self) -> None:
        payload = _ready_payload()
        payload["aggregate_summary"] = "nope"
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("aggregate_summary_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_human_approval_payload")
        self.assertFalse(result.human_approval["aggregate_summary_ready"])

    def test_aggregate_missing_summary_field(self) -> None:
        payload = _ready_payload()
        agg = payload["aggregate_summary"]
        agg["summary"].pop("determinism_hash")  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("aggregate_summary_invalid", result.failures)

    def test_aggregate_not_ready(self) -> None:
        payload = _ready_payload()
        payload["aggregate_summary"]["aggregate_ok"] = False  # type: ignore[index]
        payload["aggregate_summary"]["reason_code"] = "not_ready"  # type: ignore[index]
        payload["aggregate_summary"]["failures"] = ["plan_ci_not_ready"]  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("aggregate_summary_not_ready", result.failures)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertFalse(result.human_approval_ready)

    def test_aggregate_authorization_hazard(self) -> None:
        payload = _ready_payload()
        payload["aggregate_summary"]["summary"]["restore_authorized"] = True  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("aggregate_summary_authorization_hazard", result.failures)
        self.assertEqual(result.reason_code, "not_ready")

    def test_aggregate_execution_hazard(self) -> None:
        payload = _ready_payload()
        payload["aggregate_summary"]["summary"]["executes_plan"] = True  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("aggregate_summary_execution_hazard", result.failures)


class DeclarationShapeTests(unittest.TestCase):
    def test_declaration_not_mapping(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"] = 123
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("human_approval_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_human_approval_payload")

    def test_declaration_missing_key(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"].pop("approval_ref")  # type: ignore[union-attr]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("human_approval_invalid", result.failures)

    def test_declaration_unknown_key(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["extra"] = "x"  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("human_approval_invalid", result.failures)

    def test_declaration_missing_approval(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["approval_present"] = False  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("human_approval_missing", result.failures)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertFalse(result.human_approval["approval_present"])


class FieldValidationTests(unittest.TestCase):
    def _evaluate_with_field(self, field: str, value: object) -> HumanApprovalReadiness:
        payload = _ready_payload()
        payload["human_approval_declaration"][field] = value  # type: ignore[index]
        return evaluate_human_approval_readiness(payload)

    def test_invalid_approval_ref(self) -> None:
        result = self._evaluate_with_field("approval_ref", "")
        self.assertIn("approval_ref_invalid", result.failures)

    def test_invalid_actor_identity(self) -> None:
        result = self._evaluate_with_field("actor_identity", 1)
        self.assertIn("actor_identity_invalid", result.failures)

    def test_invalid_approval_scope(self) -> None:
        result = self._evaluate_with_field("approval_scope", "")
        self.assertIn("approval_scope_invalid", result.failures)

    def test_invalid_approval_reason(self) -> None:
        result = self._evaluate_with_field("approval_reason", None)
        self.assertIn("approval_reason_invalid", result.failures)

    def test_invalid_created_at_type(self) -> None:
        result = self._evaluate_with_field("created_at", 0)
        self.assertIn("created_at_invalid", result.failures)

    def test_invalid_created_at_unparseable(self) -> None:
        result = self._evaluate_with_field("created_at", "yesterday")
        self.assertIn("created_at_invalid", result.failures)

    def test_invalid_expires_at_unparseable(self) -> None:
        result = self._evaluate_with_field("expires_at", "soon")
        self.assertIn("expires_at_invalid", result.failures)

    def test_invalid_expires_at_type(self) -> None:
        result = self._evaluate_with_field("expires_at", 5)
        self.assertIn("expires_at_invalid", result.failures)

    def test_invalid_freshness_seconds_negative(self) -> None:
        result = self._evaluate_with_field("freshness_seconds", -1)
        self.assertIn("freshness_seconds_invalid", result.failures)

    def test_invalid_freshness_seconds_bool(self) -> None:
        result = self._evaluate_with_field("freshness_seconds", True)
        self.assertIn("freshness_seconds_invalid", result.failures)

    def test_invalid_freshness_seconds_zero(self) -> None:
        result = self._evaluate_with_field("freshness_seconds", 0)
        self.assertIn("freshness_seconds_invalid", result.failures)

    def test_freshness_window_invalid_when_neither_provided(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["expires_at"] = None  # type: ignore[index]
        payload["human_approval_declaration"]["freshness_seconds"] = None  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("freshness_window_invalid", result.failures)
        self.assertEqual(result.reason_code, "not_ready")

    def test_freshness_window_invalid_when_expires_not_after_created(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["expires_at"] = (  # type: ignore[index]
            "2023-12-31T00:00:00Z"
        )
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("freshness_window_invalid", result.failures)


class CrossFieldMismatchTests(unittest.TestCase):
    def _mismatch(self, field: str, replacement: str) -> HumanApprovalReadiness:
        payload = _ready_payload()
        payload["human_approval_declaration"][field] = replacement  # type: ignore[index]
        return evaluate_human_approval_readiness(payload)

    def test_target_mismatch(self) -> None:
        result = self._mismatch("target_task_id", "T-OTHER")
        self.assertIn("target_mismatch", result.failures)

    def test_operation_mismatch(self) -> None:
        result = self._mismatch("operation_kind", "op-other")
        self.assertIn("operation_mismatch", result.failures)

    def test_idempotency_mismatch(self) -> None:
        result = self._mismatch("idempotency_key", "idem-other")
        self.assertIn("idempotency_mismatch", result.failures)

    def test_projected_action_mismatch(self) -> None:
        result = self._mismatch("projected_action", "other.action")
        self.assertIn("projected_action_mismatch", result.failures)

    def test_projected_evidence_mismatch(self) -> None:
        result = self._mismatch("projected_evidence_ref", "other-ref")
        self.assertIn("projected_evidence_mismatch", result.failures)


class SummaryRefTests(unittest.TestCase):
    def test_aggregate_summary_ref_invalid(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["aggregate_summary_ref"] = ""  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("summary_ref_invalid", result.failures)

    def test_aggregate_summary_ref_wrong_type(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["aggregate_summary_ref"] = 7  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("summary_ref_invalid", result.failures)


class AuthorizationFlagTests(unittest.TestCase):
    def test_authorization_flag_invalid(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["restore_authorized"] = "no"  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("authorization_flag_invalid", result.failures)

    def test_authorization_flag_true(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["write_side_recovery_authorized"] = True  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("authorization_flag_true", result.failures)

    def test_execution_flag_invalid(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["executes_plan"] = "yes"  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("execution_flag_invalid", result.failures)

    def test_execution_flag_true(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["executes_plan"] = True  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("execution_flag_true", result.failures)

    def test_json_safe_invalid_type(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["json_safe"] = "yes"  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("json_safe_invalid", result.failures)

    def test_json_safe_false(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["json_safe"] = False  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        self.assertIn("json_safe_invalid", result.failures)


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = human_approval_readiness_manifest()
        self.assertEqual(manifest["surface"], "human_approval_readiness")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["input_shape"], "already_rendered_human_approval_pair")
        expected_depends_on = {
            "restore_dry_run_read_only_stack": "restore-dry-run-read-only-stack-v1",
            "restore_dry_run_aggregate_summary": "restore-dry-run-aggregate-summary-v1",
            "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
            "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
            "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
            "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
            "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
            "write_side_precondition_ci": "write-side-precondition-ci-v1",
            "write_side_precondition_checker": "write-side-precondition-checker-v1",
            "read_only_governance_layer": "read-only-governance-layer-v1",
        }
        self.assertEqual(manifest["depends_on"], expected_depends_on)
        for flag in (
            "restore_authorized",
            "write_side_recovery_authorized",
            "cli_execution_authorized",
            "schema_migration_authorized",
            "daemon_server_queue_authorized",
            "db_repair_authorized",
            "durable_writes",
            "executes_plan",
        ):
            self.assertIs(manifest[flag], False)
        self.assertIs(manifest["json_safe"], True)
        self.assertEqual(manifest["runtime_dependencies"], [])

    def test_manifest_is_defensive_copy(self) -> None:
        first = human_approval_readiness_manifest()
        first["surface"] = "tampered"
        first["depends_on"]["read_only_governance_layer"] = "tampered-tag"
        second = human_approval_readiness_manifest()
        self.assertEqual(second["surface"], "human_approval_readiness")
        self.assertEqual(
            second["depends_on"]["read_only_governance_layer"],
            "read-only-governance-layer-v1",
        )


class InputImmutabilityTests(unittest.TestCase):
    def test_input_payload_not_mutated(self) -> None:
        payload = _ready_payload()
        snapshot = copy.deepcopy(payload)
        evaluate_human_approval_readiness(payload)
        self.assertEqual(payload, snapshot)

    def test_render_output_independent_of_dataclass(self) -> None:
        result = evaluate_human_approval_readiness(_ready_payload())
        rendered = render_human_approval_readiness(result)
        rendered["human_approval"]["approval_ref"] = "TAMPERED"
        rendered_again = render_human_approval_readiness(result)
        self.assertEqual(rendered_again["human_approval"]["approval_ref"], "AR-1")


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            set(module.__all__),
            {
                "HumanApprovalReadiness",
                "human_approval_readiness_manifest",
                "evaluate_human_approval_readiness",
                "render_human_approval_readiness",
            },
        )

    def test_dataclass_is_frozen(self) -> None:
        result = evaluate_human_approval_readiness(_ready_payload())
        with self.assertRaises(Exception):
            result.human_approval_ready = False  # type: ignore[misc]


class SourceBoundaryTests(unittest.TestCase):
    _ALLOWED_TOKENS = (
        "human_approval_readiness",
        "restore_dry_run_aggregate_summary",
        "restore-dry-run-read-only-stack-v1",
        "restore-dry-run-aggregate-summary-v1",
        "projected_evidence_ref",
        "projected_action",
        "daemon_server_queue_authorized",
    )

    _FORBIDDEN_TOKENS = (
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
        "summarize_restore_dry_run_readiness",
        "restore_dry_run_aggregate_summary_manifest",
        "consume_restore_dry_run_plan_ci",
        "render_restore_dry_run_plan",
        "consume_restore_dry_run_readiness_ci",
        "evaluate_restore_dry_run_readiness",
        "governance_readiness_aggregator",
    )

    def setUp(self) -> None:
        self._source = _PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8")
        masked = self._source
        for allowed in self._ALLOWED_TOKENS:
            masked = masked.replace(allowed, "")
        self._masked = masked

    def test_no_forbidden_tokens(self) -> None:
        offenders: list[tuple[str, int]] = []
        for token in self._FORBIDDEN_TOKENS:
            count = self._masked.count(token)
            if count > 0:
                offenders.append((token, count))
        self.assertEqual(
            offenders,
            [],
            f"forbidden tokens found in production source: {offenders}",
        )

    def test_no_wall_clock_time(self) -> None:
        self.assertNotIn("datetime.now", self._source)
        self.assertNotIn("time.time", self._source)
        self.assertNotIn("import time", self._source)

    def test_no_filesystem_access(self) -> None:
        self.assertNotIn("open(", self._source)
        self.assertNotIn("Path(", self._source)

    def test_no_db_or_service_imports(self) -> None:
        self.assertNotIn("sqlite", self._source)
        self.assertNotIn("Repository", self._source)
        self.assertNotIn("UnitOfWork", self._source)
        self.assertNotIn("approval_service", self._source)
        self.assertNotIn("review_service", self._source)
        self.assertNotIn("revision_seal_service", self._source)
        self.assertNotIn("evidence_service", self._source)

    def test_no_async_or_runtime_primitives(self) -> None:
        self.assertNotIn("asyncio", self._source)
        self.assertNotIn("threading", self._source)
        self.assertNotIn("subprocess", self._source)

    def test_no_upstream_builders_or_consumers(self) -> None:
        self.assertNotIn("summarize_restore_dry_run_readiness", self._source)
        self.assertNotIn("restore_dry_run_aggregate_summary_manifest", self._source)
        self.assertNotIn("consume_restore_dry_run_plan_ci", self._source)
        self.assertNotIn("render_restore_dry_run_plan", self._source)
        self.assertNotIn("consume_restore_dry_run_readiness_ci", self._source)
        self.assertNotIn("evaluate_restore_dry_run_readiness", self._source)
        self.assertNotIn("governance_readiness_aggregator", self._source)


class FailureOrderingTests(unittest.TestCase):
    def test_multiple_failures_are_ordered(self) -> None:
        payload = _ready_payload()
        payload["human_approval_declaration"]["target_task_id"] = "T-OTHER"  # type: ignore[index]
        payload["human_approval_declaration"]["aggregate_summary_ref"] = ""  # type: ignore[index]
        payload["human_approval_declaration"]["executes_plan"] = True  # type: ignore[index]
        result = evaluate_human_approval_readiness(payload)
        seen = list(result.failures)
        # target_mismatch must come before summary_ref_invalid which must come
        # before execution_flag_true.
        self.assertLess(seen.index("target_mismatch"), seen.index("summary_ref_invalid"))
        self.assertLess(
            seen.index("summary_ref_invalid"), seen.index("execution_flag_true")
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
