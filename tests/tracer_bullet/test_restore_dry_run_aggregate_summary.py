"""Tracer-bullet tests for restore dry-run aggregate summary."""

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

from kernel.lifecycle import restore_dry_run_aggregate_summary as summary_module
from kernel.lifecycle.restore_dry_run_aggregate_summary import (
    restore_dry_run_aggregate_summary_manifest,
    summarize_restore_dry_run_readiness,
)


EXPECTED_MANIFEST = {
    "surface": "restore_dry_run_aggregate_summary",
    "version": 1,
    "input_shape": "already_rendered_restore_dry_run_ci_pair",
    "depends_on": {
        "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
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
}

EXPECTED_OUTPUT_KEYS = [
    "aggregate_ok",
    "reason_code",
    "failures",
    "summary",
]

EXPECTED_SUMMARY_KEYS = [
    "surface",
    "version",
    "readiness_ci_ok",
    "plan_ci_ok",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
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

AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

CROSS_CHECK_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
)

REPR_MARKERS = (
    "RestoreDryRunAggregateSummary(",
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
    "consume_restore_dry_run_plan_ci",
    "restore_dry_run_plan_ci_manifest",
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
    "restore_dry_run_aggregate_summary",
    "restore_dry_run_plan",
    "restore-dry-run-plan-ci-v1",
    "restore-dry-run-plan-renderer-v1",
    "restore-dry-run-readiness-v1",
    "restore-dry-run-readiness-ci-v1",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
)


def _valid_readiness_ci(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "restore_dry_run_readiness",
        "version": 1,
        "contract_ready": True,
        "contract_reason_code": "ready",
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "durable_writes": False,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _valid_plan_ci(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "restore_dry_run_plan",
        "version": 1,
        "plan_ready": True,
        "plan_reason_code": "plan_ready",
        "target_task_id": "task-001",
        "operation_kind": "restore",
        "idempotency_key": "idem-001",
        "projected_action": "restore_task",
        "projected_evidence_ref": "evidence-ref-001",
        "projected_before_snapshot_ref": "before-snap-001",
        "projected_after_snapshot_ref": "after-snap-001",
        "determinism_hash": "deadbeef",
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
    base: dict[str, object] = {
        "readiness_ci": _valid_readiness_ci(),
        "plan_ci": _valid_plan_ci(),
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
    source = inspect.getsource(summary_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


class HappyPathTests(unittest.TestCase):
    def test_valid_rendered_ci_pair_returns_aggregate_ok_true(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertIs(result["aggregate_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])

        summary = result["summary"]
        self.assertEqual(list(summary.keys()), EXPECTED_SUMMARY_KEYS)
        self.assertEqual(summary["surface"], "restore_dry_run_aggregate_summary")
        self.assertEqual(summary["version"], 1)
        self.assertIs(summary["readiness_ci_ok"], True)
        self.assertIs(summary["plan_ci_ok"], True)
        self.assertEqual(summary["target_task_id"], "task-001")
        self.assertEqual(summary["operation_kind"], "restore")
        self.assertEqual(summary["idempotency_key"], "idem-001")
        self.assertEqual(summary["projected_action"], "restore_task")
        self.assertEqual(summary["projected_evidence_ref"], "evidence-ref-001")
        self.assertEqual(summary["determinism_hash"], "deadbeef")
        self.assertIs(summary["transaction_required"], True)
        self.assertIs(summary["rollback_required"], True)

    def test_aggregate_ok_does_not_authorize_restore_or_recovery(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload())
        summary = result["summary"]

        self.assertIs(result["aggregate_ok"], True)
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(summary[flag], False, flag)
        self.assertIs(summary["executes_plan"], False)
        self.assertIs(summary["json_safe"], True)


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_input_rejected(self) -> None:
        for payload in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(payload=payload):
                result = summarize_restore_dry_run_readiness(payload)

                self.assertIs(result["aggregate_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_summary_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["readiness_ci"]

        result = summarize_restore_dry_run_readiness(payload)

        self.assertEqual(result["reason_code"], "invalid_summary_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertIs(result["summary"]["readiness_ci_ok"], False)
        self.assertIs(result["summary"]["plan_ci_ok"], True)

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _valid_payload(extra=True)

        result = summarize_restore_dry_run_readiness(payload)

        self.assertEqual(result["reason_code"], "invalid_summary_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertIs(result["summary"]["readiness_ci_ok"], True)
        self.assertIs(result["summary"]["plan_ci_ok"], True)


class ReadinessCiValidationTests(unittest.TestCase):
    def test_readiness_ci_not_mapping_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(readiness_ci=[])
        )

        self.assertEqual(result["reason_code"], "invalid_summary_payload")
        self.assertEqual(result["failures"], ["readiness_ci_invalid"])
        self.assertIs(result["summary"]["readiness_ci_ok"], False)

    def test_readiness_ci_malformed_rejected(self) -> None:
        readiness_ci = _valid_readiness_ci()
        del readiness_ci["surface"]

        result = summarize_restore_dry_run_readiness(
            _valid_payload(readiness_ci=readiness_ci)
        )

        self.assertEqual(result["reason_code"], "invalid_summary_payload")
        self.assertEqual(result["failures"], ["readiness_ci_invalid"])

    def test_readiness_ci_not_ready_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(
                readiness_ci=_valid_readiness_ci(
                    ci_ok=False,
                    reason_code="not_ready",
                    failures=["source_detail"],
                    contract_ready=False,
                )
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["readiness_ci_not_ready"])
        self.assertIs(result["summary"]["readiness_ci_ok"], False)

    def test_readiness_ci_authorization_hazard_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(
                readiness_ci=_valid_readiness_ci(restore_authorized=True)
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"], ["readiness_ci_authorization_hazard"]
        )
        self.assertIs(result["summary"]["restore_authorized"], False)


class PlanCiValidationTests(unittest.TestCase):
    def test_plan_ci_not_mapping_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload(plan_ci=[]))

        self.assertEqual(result["reason_code"], "invalid_summary_payload")
        self.assertEqual(result["failures"], ["plan_ci_invalid"])
        self.assertIs(result["summary"]["plan_ci_ok"], False)

    def test_plan_ci_malformed_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(plan_ci=_valid_plan_ci(target_task_id=42))
        )

        self.assertEqual(result["reason_code"], "invalid_summary_payload")
        self.assertEqual(result["failures"], ["plan_ci_invalid"])
        self.assertIsNone(result["summary"]["target_task_id"])

    def test_plan_ci_not_ready_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(
                plan_ci=_valid_plan_ci(
                    ci_ok=False,
                    reason_code="not_ready",
                    failures=["source_detail"],
                    plan_ready=False,
                    target_task_id="",
                    transaction_required=False,
                )
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["plan_ci_not_ready"])
        self.assertIs(result["summary"]["plan_ci_ok"], False)

    def test_plan_ci_authorization_hazard_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(plan_ci=_valid_plan_ci(durable_writes=True))
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["plan_ci_authorization_hazard"])
        self.assertIs(result["summary"]["durable_writes"], False)

    def test_plan_ci_execution_hazard_rejected(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(plan_ci=_valid_plan_ci(executes_plan=True))
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["plan_ci_execution_hazard"])
        self.assertIs(result["summary"]["executes_plan"], False)


class CrossCheckTests(unittest.TestCase):
    def test_cross_check_mismatches_are_ordered(self) -> None:
        readiness_ci = _valid_readiness_ci(
            target_task_id="other-task",
            operation_kind="other-operation",
            idempotency_key="other-idem",
            projected_action="other-action",
            projected_evidence_ref="other-evidence",
        )

        result = summarize_restore_dry_run_readiness(
            _valid_payload(readiness_ci=readiness_ci)
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"],
            [
                "target_mismatch",
                "operation_mismatch",
                "idempotency_mismatch",
                "projected_action_mismatch",
                "projected_evidence_mismatch",
            ],
        )
        self.assertEqual(result["summary"]["target_task_id"], "task-001")
        self.assertEqual(result["summary"]["operation_kind"], "restore")

    def test_no_mismatch_when_readiness_ci_lacks_projection_fields(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload())

        self.assertIs(result["aggregate_ok"], True)
        self.assertEqual(result["failures"], [])

    def test_no_mismatch_when_readiness_optional_field_is_empty(self) -> None:
        result = summarize_restore_dry_run_readiness(
            _valid_payload(
                readiness_ci=_valid_readiness_ci(target_task_id="")
            )
        )

        self.assertIs(result["aggregate_ok"], True)
        self.assertEqual(result["failures"], [])


class SafetyAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = restore_dry_run_aggregate_summary_manifest()

        self.assertEqual(list(manifest.keys()), list(EXPECTED_MANIFEST.keys()))
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        manifest = restore_dry_run_aggregate_summary_manifest()
        manifest["surface"] = "tampered"
        manifest["runtime_dependencies"].append("injected")  # type: ignore[union-attr]
        manifest["depends_on"]["restore_dry_run_plan_ci"] = "broken"  # type: ignore[index]

        self.assertEqual(
            restore_dry_run_aggregate_summary_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_result_defensive_copy(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload())
        result["failures"].append("tampered")  # type: ignore[union-attr]
        result["summary"]["surface"] = "tampered"  # type: ignore[index]

        fresh = summarize_restore_dry_run_readiness(_valid_payload())

        self.assertEqual(fresh["failures"], [])
        self.assertEqual(
            fresh["summary"]["surface"], "restore_dry_run_aggregate_summary"
        )

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)

        summarize_restore_dry_run_readiness(payload)

        self.assertEqual(payload, snapshot)

    def test_output_json_safe(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload())

        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        result = summarize_restore_dry_run_readiness(_valid_payload())

        _assert_no_runtime_repr(result)

    def test_public_api_exact(self) -> None:
        public = sorted(
            name for name in dir(summary_module) if not name.startswith("_")
        )

        self.assertEqual(
            public,
            [
                "restore_dry_run_aggregate_summary_manifest",
                "summarize_restore_dry_run_readiness",
            ],
        )
        self.assertEqual(
            sorted(summary_module.__all__),
            [
                "restore_dry_run_aggregate_summary_manifest",
                "summarize_restore_dry_run_readiness",
            ],
        )

    def test_source_boundary_has_no_forbidden_symbols(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            self.assertNotIn(marker, source, marker)


if __name__ == "__main__":
    unittest.main()
