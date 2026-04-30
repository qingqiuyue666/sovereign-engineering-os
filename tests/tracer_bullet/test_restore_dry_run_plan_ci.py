"""Tracer-bullet tests for the R2 restore dry-run plan CI consumer."""

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

from kernel.lifecycle import restore_dry_run_plan_ci as ci_module
from kernel.lifecycle.restore_dry_run_plan_ci import (
    consume_restore_dry_run_plan_ci,
    restore_dry_run_plan_ci_manifest,
)


EXPECTED_MANIFEST = {
    "surface": "restore_dry_run_plan_ci",
    "version": 1,
    "input_shape": "rendered_restore_dry_run_plan",
    "depends_on": {
        "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
        "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
        "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": "write-side-precondition-checker-v1",
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
    "reason_codes": ["invalid_ci_payload", "not_ready", "plan_ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "plan_invalid",
        "plan_shape_mismatch",
        "plan_surface_invalid",
        "plan_version_invalid",
        "plan_field_invalid",
        "plan_field_missing",
        "plan_not_ready",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "execution_flag_invalid",
        "execution_flag_true",
        "json_safe_invalid",
        "source_plan_not_ready",
    ],
}


EXPECTED_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "plan_ready",
    "plan_reason_code",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
    "transaction_required",
    "rollback_required",
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


PLAN_REQUIRED_STRINGS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "determinism_hash",
    "human_approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
)

PLAN_READINESS_BOOL_FIELDS = (
    "transaction_required",
    "rollback_required",
)

PLAN_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)


REPR_MARKERS = (
    "RestoreDryRunPlan(",
    " object at 0x",
    "<sqlite3.",
)


FORBIDDEN_SOURCE_MARKERS = (
    "sqlite",
    "open_connection",
    "Repository",
    "UnitOfWork",
    "KernelUnitOfWork",
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
    "audit",
    "evidence append",
    "render_restore_dry_run_plan",
    "render_restore_dry_run_plan_payload",
    "restore_dry_run_plan_renderer_manifest",
    "evaluate_restore_dry_run_readiness",
    "render_restore_dry_run_readiness",
    "consume_restore_dry_run_readiness_ci",
    "restore_dry_run_readiness_ci_manifest",
    "check_write_side_recovery_preconditions",
    "render_write_side_recovery_precondition_check",
    "write_side_recovery_precondition_ci",
    "governance_readiness_aggregator",
    "approval_review_readiness",
    "evidence_replay_readiness",
    "task_lifecycle_journal_snapshot",
)


ALLOWED_SOURCE_FIELD_STRINGS = (
    "restore_dry_run_plan",
    "restore-dry-run-plan-renderer-v1",
    "restore-dry-run-readiness-v1",
    "restore-dry-run-readiness-ci-v1",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
    "daemon_server_queue_authorized",
)


def _valid_plan(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "restore_dry_run_plan",
        "version": 1,
        "target_task_id": "task-001",
        "operation_kind": "restore",
        "idempotency_key": "idem-001",
        "projected_action": "restore_task",
        "projected_evidence_ref": "evidence-ref-001",
        "projected_before_snapshot_ref": "before-snap-001",
        "projected_after_snapshot_ref": "after-snap-001",
        "determinism_hash": "deadbeef",
        "human_approval_ref": "approval-001",
        "actor_identity": "actor-001",
        "approval_scope": "scope-001",
        "approval_reason": "reason-001",
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
    base.update(overrides)
    return base


def _valid_payload(**overrides: object) -> dict[str, object]:
    plan = overrides.pop("plan", _valid_plan())
    base: dict[str, object] = {
        "plan_ok": True,
        "reason_code": "plan_ready",
        "failures": [],
        "plan": plan,
    }
    base.update(overrides)
    return base


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
    def test_valid_rendered_plan_returns_ci_ok_true(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["surface"], "restore_dry_run_plan")
        self.assertEqual(result["version"], 1)
        self.assertIs(result["plan_ready"], True)
        self.assertEqual(result["plan_reason_code"], "plan_ready")

    def test_projected_plan_metadata_copied_deterministically(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload())

        self.assertEqual(result["target_task_id"], "task-001")
        self.assertEqual(result["operation_kind"], "restore")
        self.assertEqual(result["idempotency_key"], "idem-001")
        self.assertEqual(result["projected_action"], "restore_task")
        self.assertEqual(result["projected_evidence_ref"], "evidence-ref-001")
        self.assertEqual(
            result["projected_before_snapshot_ref"], "before-snap-001"
        )
        self.assertEqual(
            result["projected_after_snapshot_ref"], "after-snap-001"
        )
        self.assertEqual(result["determinism_hash"], "deadbeef")

    def test_happy_path_readiness_and_safety_flags(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload())

        self.assertIs(result["transaction_required"], True)
        self.assertIs(result["rollback_required"], True)
        for flag in PLAN_AUTHORIZATION_FLAGS:
            self.assertIs(result[flag], False, flag)
        self.assertIs(result["executes_plan"], False)
        self.assertIs(result["json_safe"], True)


class PayloadValidationTests(unittest.TestCase):
    def test_non_mapping_input_rejected(self) -> None:
        for payload in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(payload=payload):
                result = consume_restore_dry_run_plan_ci(payload)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])
                self.assertIsNone(result["surface"])
                self.assertIsNone(result["version"])

    def test_top_level_missing_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["plan_ok"]

        result = consume_restore_dry_run_plan_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_top_level_unknown_key_rejected(self) -> None:
        payload = _valid_payload()
        payload["extra"] = True

        result = consume_restore_dry_run_plan_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_plan_ok_not_bool_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload(plan_ok=1))

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertIs(result["plan_ready"], False)

    def test_reason_code_not_str_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(reason_code=1)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertEqual(result["plan_reason_code"], "invalid_ci_payload")

    def test_failures_not_list_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(failures=("x",))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_failures_invalid"])

    def test_failures_list_with_non_string_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(failures=["x", 1])
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_failures_invalid"])

    def test_plan_not_mapping_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload(plan=[]))

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_invalid"])
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])


class PlanValidationTests(unittest.TestCase):
    def test_missing_plan_key_rejected(self) -> None:
        plan = _valid_plan()
        del plan["json_safe"]

        result = consume_restore_dry_run_plan_ci(_valid_payload(plan=plan))

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_shape_mismatch"])

    def test_unknown_plan_key_rejected(self) -> None:
        plan = _valid_plan(extra=True)

        result = consume_restore_dry_run_plan_ci(_valid_payload(plan=plan))

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_shape_mismatch"])

    def test_wrong_surface_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(surface="wrong"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_surface_invalid"])
        self.assertEqual(result["surface"], "wrong")

    def test_wrong_version_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(version=2))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_version_invalid"])
        self.assertEqual(result["version"], 2)

    def test_bool_as_int_version_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(version=True))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_version_invalid"])
        self.assertIsNone(result["version"])

    def test_required_string_field_non_string_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(target_task_id=42))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_field_invalid"])
        self.assertIsNone(result["target_task_id"])

    def test_required_string_field_empty_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(determinism_hash=""))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["plan_field_missing"])
        self.assertIsNone(result["determinism_hash"])

    def test_transaction_required_non_bool_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(transaction_required="yes"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_field_invalid"])
        self.assertIsNone(result["transaction_required"])

    def test_transaction_required_false_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(transaction_required=False))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["plan_not_ready"])
        self.assertIs(result["transaction_required"], False)

    def test_rollback_required_non_bool_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(rollback_required="yes"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["plan_field_invalid"])
        self.assertIsNone(result["rollback_required"])

    def test_rollback_required_false_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(rollback_required=False))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["plan_not_ready"])
        self.assertIs(result["rollback_required"], False)

    def test_authorization_flag_non_bool_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(restore_authorized="no"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["authorization_flag_invalid"])
        self.assertIsNone(result["restore_authorized"])

    def test_authorization_flag_true_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(restore_authorized=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertIs(result["restore_authorized"], True)

    def test_durable_writes_true_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(durable_writes=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertIs(result["durable_writes"], True)

    def test_executes_plan_non_bool_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(executes_plan="no"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["execution_flag_invalid"])
        self.assertIsNone(result["executes_plan"])

    def test_executes_plan_true_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(executes_plan=True))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["execution_flag_true"])
        self.assertIs(result["executes_plan"], True)

    def test_json_safe_false_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(json_safe=False))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], False)

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(plan=_valid_plan(json_safe="yes"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIsNone(result["json_safe"])


class SourcePlanSemanticsTests(unittest.TestCase):
    def test_plan_ok_false_returns_not_ready_with_source_failure(
        self,
    ) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload(plan_ok=False))

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_plan_not_ready"])
        self.assertIs(result["plan_ready"], False)

    def test_reason_code_not_plan_ready_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_plan_not_ready"])
        self.assertEqual(result["plan_reason_code"], "not_ready")

    def test_failures_non_empty_returns_not_ready(self) -> None:
        result = consume_restore_dry_run_plan_ci(
            _valid_payload(failures=["upstream_detail"])
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_plan_not_ready"])

    def test_combined_failures_use_deterministic_order(self) -> None:
        plan = _valid_plan(
            surface="wrong",
            version=True,
            target_task_id=42,
            determinism_hash="",
            transaction_required=False,
            restore_authorized="bad",
            write_side_recovery_authorized=True,
            executes_plan="bad",
            json_safe=False,
        )
        payload = _valid_payload(
            plan_ok=False,
            reason_code="not_ready",
            failures=["upstream_detail"],
            plan=plan,
        )
        payload["extra"] = True

        result = consume_restore_dry_run_plan_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "plan_surface_invalid",
                "plan_version_invalid",
                "plan_field_invalid",
                "plan_field_missing",
                "plan_not_ready",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "execution_flag_invalid",
                "json_safe_invalid",
                "source_plan_not_ready",
            ],
        )


class SafetyAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = restore_dry_run_plan_ci_manifest()

        self.assertEqual(list(manifest.keys()), list(EXPECTED_MANIFEST.keys()))
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        manifest = restore_dry_run_plan_ci_manifest()
        manifest["surface"] = "tampered"
        manifest["failure_values"].append("injected")  # type: ignore[union-attr]
        manifest["depends_on"]["restore_dry_run_plan_renderer"] = "broken"  # type: ignore[index]

        self.assertEqual(restore_dry_run_plan_ci_manifest(), EXPECTED_MANIFEST)

    def test_manifest_authorization_flags_false(self) -> None:
        manifest = restore_dry_run_plan_ci_manifest()

        for flag in PLAN_AUTHORIZATION_FLAGS:
            self.assertIs(manifest[flag], False, flag)
        self.assertIs(manifest["executes_plan"], False)

    def test_output_json_safe(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload())

        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload())

        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)

        consume_restore_dry_run_plan_ci(payload)

        self.assertEqual(payload, snapshot)

    def test_ci_ok_does_not_authorize_writes(self) -> None:
        result = consume_restore_dry_run_plan_ci(_valid_payload())

        self.assertIs(result["ci_ok"], True)
        for flag in PLAN_AUTHORIZATION_FLAGS:
            self.assertIs(result[flag], False, flag)
        self.assertIs(result["executes_plan"], False)

    def test_public_api_exact(self) -> None:
        public = sorted(
            name for name in dir(ci_module) if not name.startswith("_")
        )

        self.assertEqual(
            public,
            [
                "consume_restore_dry_run_plan_ci",
                "restore_dry_run_plan_ci_manifest",
            ],
        )
        self.assertEqual(
            sorted(ci_module.__all__),
            [
                "consume_restore_dry_run_plan_ci",
                "restore_dry_run_plan_ci_manifest",
            ],
        )

    def test_source_boundary_has_no_forbidden_symbols(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            self.assertNotIn(marker, source, marker)


if __name__ == "__main__":
    unittest.main()
