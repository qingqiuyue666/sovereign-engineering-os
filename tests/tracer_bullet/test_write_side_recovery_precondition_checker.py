"""Tracer-bullet tests for the read-only write-side precondition checker."""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle import write_side_recovery_precondition_checker as checker_module
from kernel.lifecycle.write_side_recovery_precondition_checker import (
    WriteSideRecoveryPreconditionCheck,
    check_write_side_recovery_preconditions,
    render_write_side_recovery_precondition_check,
    write_side_recovery_precondition_manifest,
)


BASELINE_TAG = "read-only-governance-layer-v1"
BASELINE_COMMIT = "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"

EXPECTED_MANIFEST = {
    "surface": "write_side_recovery_precondition_check",
    "version": 1,
    "input_shape": "mapping_of_already_rendered_precondition_payloads",
    "baseline_tag": BASELINE_TAG,
    "baseline_commit": BASELINE_COMMIT,
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "durable_writes": False,
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
        "source_truth_invalid",
        "baseline_tag_unresolved",
        "baseline_commit_mismatch",
        "working_tree_dirty",
        "governance_invalid",
        "governance_not_ready",
        "target_task_invalid",
        "target_task_not_ready",
        "evidence_replay_invalid",
        "evidence_replay_not_ready",
        "approval_review_invalid",
        "approval_review_not_ready",
        "human_approval_invalid",
        "human_approval_missing",
        "dry_run_invalid",
        "dry_run_missing",
        "dry_run_failed",
        "dry_run_target_mismatch",
        "idempotency_invalid",
        "idempotency_missing",
        "idempotency_replay_risk",
        "evidence_snapshot_invalid",
        "evidence_snapshot_missing",
        "transaction_invalid",
        "transaction_missing",
        "rollback_missing",
        "schema_runtime_invalid",
        "schema_migration_required",
        "db_repair_required",
        "runtime_boundary_violation",
        "operator_confirmation_invalid",
        "cli_confirmation_missing",
    ],
}

EXPECTED_RENDERED_TOP_KEYS = ["ready", "reason_code", "failures", "preconditions"]
EXPECTED_PRECONDITIONS_KEYS = [
    "surface",
    "version",
    "source_truth_ready",
    "governance_ready",
    "target_task_ready",
    "evidence_replay_ready",
    "approval_review_ready",
    "human_approval_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "transaction_ready",
    "rollback_ready",
    "schema_migration_safe",
    "runtime_boundary_safe",
    "operator_confirmation_ready",
    "operator_safe",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "json_safe",
]

AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
)

REPR_MARKERS = (
    "WriteSideRecoveryPreconditionCheck(",
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
)


def _ready_subsystem(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ready": True,
        "reason_code": "ready",
        "failures": [],
        "restore_supported": False,
        "durable_writes": False,
        "cli_command_count": 0,
        "runtime_dependency_count": 0,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _ready_payload() -> dict[str, object]:
    return {
        "source_truth": {
            "baseline_tag": BASELINE_TAG,
            "baseline_commit": BASELINE_COMMIT,
            "current_head": "abc123def456",
            "working_tree_clean": True,
        },
        "governance": _ready_subsystem(),
        "target_task": _ready_subsystem(),
        "evidence_replay": _ready_subsystem(),
        "approval_review": _ready_subsystem(),
        "human_approval": {
            "approval_present": True,
            "actor_identity": "operator-1",
            "scope": "write_side_recovery",
            "reason": "approved-restore",
            "created_at": "2026-04-29T00:00:00Z",
        },
        "dry_run": {
            "dry_run_present": True,
            "dry_run_ok": True,
            "target_task_id": "task-42",
            "projected_action": "noop_action",
            "projected_evidence_ref": "ev-ref-1",
        },
        "idempotency": {
            "idempotency_key": "idem-1",
            "target_task_id": "task-42",
            "operation_kind": "write_side_recovery",
            "replay_status": "new",
        },
        "evidence_snapshot": {
            "before_snapshot_ref": "snap-before",
            "projected_after_snapshot_ref": "snap-after",
            "immutable": True,
        },
        "transaction": {
            "transaction_declared": True,
            "rollback_declared": True,
            "expected_rejection_policy": "rollback_on_violation",
        },
        "schema_runtime": {
            "schema_migration_required": False,
            "db_repair_required": False,
            "runtime_boundary_safe": True,
        },
        "operator_confirmation": {
            "cli_confirmation_present": True,
            "operator_safe": True,
        },
    }


class HappyPathTests(unittest.TestCase):
    def test_fully_valid_payload_returns_ready(self) -> None:
        check = check_write_side_recovery_preconditions(_ready_payload())
        self.assertIsInstance(check, WriteSideRecoveryPreconditionCheck)
        self.assertTrue(check.ready)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())

    def test_renderer_reports_ready_payload(self) -> None:
        check = check_write_side_recovery_preconditions(_ready_payload())
        rendered = render_write_side_recovery_precondition_check(check)
        self.assertEqual(rendered["ready"], True)
        self.assertEqual(rendered["reason_code"], "ready")
        self.assertEqual(rendered["failures"], [])

        preconditions = rendered["preconditions"]
        self.assertIsInstance(preconditions, dict)
        readiness_booleans = (
            "source_truth_ready",
            "governance_ready",
            "target_task_ready",
            "evidence_replay_ready",
            "approval_review_ready",
            "human_approval_ready",
            "dry_run_ready",
            "idempotency_ready",
            "evidence_snapshot_ready",
            "transaction_ready",
            "rollback_ready",
            "schema_migration_safe",
            "runtime_boundary_safe",
            "operator_confirmation_ready",
            "operator_safe",
        )
        for key in readiness_booleans:
            self.assertIs(preconditions[key], True, key)
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(preconditions[flag], False, flag)
        self.assertIs(preconditions["json_safe"], True)

    def test_output_is_json_safe(self) -> None:
        check = check_write_side_recovery_preconditions(_ready_payload())
        rendered = render_write_side_recovery_precondition_check(check)
        encoded = json.dumps(rendered)
        self.assertIn("\"ready\": true", encoded)


class TopLevelValidationTests(unittest.TestCase):
    def test_non_mapping_payload_rejected(self) -> None:
        for bad in (None, 1, "x", [1, 2], (1, 2)):
            check = check_write_side_recovery_preconditions(bad)
            self.assertFalse(check.ready)
            self.assertEqual(check.reason_code, "invalid_precondition_payload")
            self.assertEqual(check.failures, ("payload_not_mapping",))

    def test_missing_top_level_section_rejected(self) -> None:
        payload = _ready_payload()
        del payload["dry_run"]
        check = check_write_side_recovery_preconditions(payload)
        self.assertFalse(check.ready)
        self.assertEqual(check.reason_code, "invalid_precondition_payload")
        self.assertEqual(check.failures, ("payload_shape_mismatch",))

    def test_unknown_top_level_section_rejected(self) -> None:
        payload = _ready_payload()
        payload["bonus"] = {}
        check = check_write_side_recovery_preconditions(payload)
        self.assertFalse(check.ready)
        self.assertEqual(check.reason_code, "invalid_precondition_payload")
        self.assertEqual(check.failures, ("payload_shape_mismatch",))

    def test_failure_ordering_is_deterministic(self) -> None:
        payload = _ready_payload()
        payload["source_truth"]["baseline_tag"] = "wrong"
        payload["source_truth"]["baseline_commit"] = "deadbeef"
        payload["source_truth"]["working_tree_clean"] = False
        payload["schema_runtime"]["schema_migration_required"] = True
        payload["schema_runtime"]["db_repair_required"] = True
        payload["schema_runtime"]["runtime_boundary_safe"] = False
        payload["operator_confirmation"]["cli_confirmation_present"] = False
        payload["operator_confirmation"]["operator_safe"] = False

        check = check_write_side_recovery_preconditions(payload)
        expected_order = (
            "baseline_tag_unresolved",
            "baseline_commit_mismatch",
            "working_tree_dirty",
            "schema_migration_required",
            "db_repair_required",
            "runtime_boundary_violation",
            "cli_confirmation_missing",
        )
        self.assertEqual(check.failures, expected_order)
        self.assertFalse(check.ready)
        self.assertEqual(check.reason_code, "not_ready")


class SourceTruthTests(unittest.TestCase):
    def test_source_truth_invalid_when_not_mapping(self) -> None:
        payload = _ready_payload()
        payload["source_truth"] = "not-a-mapping"
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("source_truth_invalid", check.failures)
        self.assertEqual(check.reason_code, "invalid_precondition_payload")
        self.assertFalse(check.preconditions["source_truth_ready"])

    def test_wrong_baseline_tag(self) -> None:
        payload = _ready_payload()
        payload["source_truth"]["baseline_tag"] = "wrong-tag"
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("baseline_tag_unresolved", check.failures)
        self.assertEqual(check.reason_code, "not_ready")

    def test_wrong_baseline_commit(self) -> None:
        payload = _ready_payload()
        payload["source_truth"]["baseline_commit"] = "0" * 40
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("baseline_commit_mismatch", check.failures)

    def test_dirty_working_tree(self) -> None:
        payload = _ready_payload()
        payload["source_truth"]["working_tree_clean"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("working_tree_dirty", check.failures)


class ReadinessSectionTests(unittest.TestCase):
    def test_governance_not_ready(self) -> None:
        payload = _ready_payload()
        payload["governance"] = _ready_subsystem(
            ready=False, reason_code="not_ready", failures=["x"]
        )
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_not_ready", check.failures)
        self.assertFalse(check.preconditions["governance_ready"])

    def test_governance_hazard_restore(self) -> None:
        payload = _ready_payload()
        payload["governance"] = _ready_subsystem(restore_supported=True)
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_not_ready", check.failures)

    def test_governance_hazard_durable(self) -> None:
        payload = _ready_payload()
        payload["governance"] = _ready_subsystem(durable_writes=True)
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_not_ready", check.failures)

    def test_governance_hazard_cli(self) -> None:
        payload = _ready_payload()
        payload["governance"] = _ready_subsystem(cli_command_count=1)
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_not_ready", check.failures)

    def test_governance_hazard_runtime(self) -> None:
        payload = _ready_payload()
        payload["governance"] = _ready_subsystem(runtime_dependency_count=2)
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_not_ready", check.failures)

    def test_governance_hazard_json(self) -> None:
        payload = _ready_payload()
        payload["governance"] = _ready_subsystem(json_safe=False)
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_not_ready", check.failures)

    def test_governance_invalid_shape(self) -> None:
        payload = _ready_payload()
        payload["governance"] = "not-a-mapping"
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("governance_invalid", check.failures)
        self.assertEqual(check.reason_code, "invalid_precondition_payload")

    def test_target_task_not_ready(self) -> None:
        payload = _ready_payload()
        payload["target_task"] = _ready_subsystem(ready=False, failures=["x"])
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("target_task_not_ready", check.failures)

    def test_evidence_replay_not_ready(self) -> None:
        payload = _ready_payload()
        payload["evidence_replay"] = _ready_subsystem(
            ready=False, reason_code="not_ready", failures=["x"]
        )
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("evidence_replay_not_ready", check.failures)

    def test_approval_review_not_ready(self) -> None:
        payload = _ready_payload()
        payload["approval_review"] = _ready_subsystem(
            ready=False, reason_code="not_ready", failures=["x"]
        )
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("approval_review_not_ready", check.failures)

    def test_ci_style_payload_accepted(self) -> None:
        payload = _ready_payload()
        payload["governance"] = {
            "ci_ok": True,
            "reason_code": "ready",
            "failures": [],
            "restore_supported": False,
            "durable_writes": False,
            "cli_command_count": 0,
            "runtime_dependency_count": 0,
            "json_safe": True,
        }
        check = check_write_side_recovery_preconditions(payload)
        self.assertTrue(check.ready, check.failures)


class HumanApprovalTests(unittest.TestCase):
    def test_human_approval_missing(self) -> None:
        payload = _ready_payload()
        payload["human_approval"]["approval_present"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("human_approval_missing", check.failures)

    def test_human_approval_invalid_empty_string(self) -> None:
        payload = _ready_payload()
        payload["human_approval"]["actor_identity"] = ""
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("human_approval_invalid", check.failures)
        self.assertEqual(check.reason_code, "invalid_precondition_payload")


class DryRunTests(unittest.TestCase):
    def test_dry_run_missing(self) -> None:
        payload = _ready_payload()
        payload["dry_run"]["dry_run_present"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("dry_run_missing", check.failures)

    def test_dry_run_failed(self) -> None:
        payload = _ready_payload()
        payload["dry_run"]["dry_run_ok"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("dry_run_failed", check.failures)

    def test_dry_run_target_mismatch(self) -> None:
        payload = _ready_payload()
        payload["dry_run"]["projected_evidence_ref"] = ""
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("dry_run_target_mismatch", check.failures)


class IdempotencyTests(unittest.TestCase):
    def test_idempotency_missing_when_key_empty(self) -> None:
        payload = _ready_payload()
        payload["idempotency"]["idempotency_key"] = ""
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("idempotency_missing", check.failures)

    def test_idempotency_replay_risk(self) -> None:
        payload = _ready_payload()
        payload["idempotency"]["replay_status"] = "duplicate_unsafe"
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("idempotency_replay_risk", check.failures)

    def test_idempotency_same_attempt_safe_accepted(self) -> None:
        payload = _ready_payload()
        payload["idempotency"]["replay_status"] = "same_attempt_safe"
        check = check_write_side_recovery_preconditions(payload)
        self.assertTrue(check.ready, check.failures)


class EvidenceSnapshotTests(unittest.TestCase):
    def test_evidence_snapshot_missing_when_immutable_false(self) -> None:
        payload = _ready_payload()
        payload["evidence_snapshot"]["immutable"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("evidence_snapshot_missing", check.failures)

    def test_evidence_snapshot_invalid_shape(self) -> None:
        payload = _ready_payload()
        payload["evidence_snapshot"] = []
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("evidence_snapshot_invalid", check.failures)


class TransactionTests(unittest.TestCase):
    def test_transaction_missing(self) -> None:
        payload = _ready_payload()
        payload["transaction"]["transaction_declared"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("transaction_missing", check.failures)

    def test_rollback_missing_when_not_declared(self) -> None:
        payload = _ready_payload()
        payload["transaction"]["rollback_declared"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("rollback_missing", check.failures)

    def test_rollback_missing_when_policy_empty(self) -> None:
        payload = _ready_payload()
        payload["transaction"]["expected_rejection_policy"] = ""
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("rollback_missing", check.failures)


class SchemaRuntimeTests(unittest.TestCase):
    def test_schema_migration_required(self) -> None:
        payload = _ready_payload()
        payload["schema_runtime"]["schema_migration_required"] = True
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("schema_migration_required", check.failures)
        self.assertFalse(check.preconditions["schema_migration_safe"])

    def test_db_repair_required(self) -> None:
        payload = _ready_payload()
        payload["schema_runtime"]["db_repair_required"] = True
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("db_repair_required", check.failures)

    def test_runtime_boundary_violation(self) -> None:
        payload = _ready_payload()
        payload["schema_runtime"]["runtime_boundary_safe"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("runtime_boundary_violation", check.failures)
        self.assertFalse(check.preconditions["runtime_boundary_safe"])


class OperatorConfirmationTests(unittest.TestCase):
    def test_cli_confirmation_missing(self) -> None:
        payload = _ready_payload()
        payload["operator_confirmation"]["cli_confirmation_present"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("cli_confirmation_missing", check.failures)
        self.assertFalse(check.preconditions["operator_confirmation_ready"])
        self.assertFalse(check.preconditions["operator_safe"])

    def test_operator_unsafe_triggers_failure(self) -> None:
        payload = _ready_payload()
        payload["operator_confirmation"]["operator_safe"] = False
        check = check_write_side_recovery_preconditions(payload)
        self.assertIn("cli_confirmation_missing", check.failures)


class OutputAndSafetyTests(unittest.TestCase):
    def test_renderer_exact_shape(self) -> None:
        check = check_write_side_recovery_preconditions(_ready_payload())
        rendered = render_write_side_recovery_precondition_check(check)
        self.assertEqual(list(rendered.keys()), EXPECTED_RENDERED_TOP_KEYS)
        preconditions = rendered["preconditions"]
        self.assertEqual(list(preconditions.keys()), EXPECTED_PRECONDITIONS_KEYS)

    def test_manifest_exact_shape(self) -> None:
        manifest = write_side_recovery_precondition_manifest()
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        manifest = write_side_recovery_precondition_manifest()
        manifest["surface"] = "tampered"
        manifest["failure_values"].append("hacked")
        again = write_side_recovery_precondition_manifest()
        self.assertEqual(again, EXPECTED_MANIFEST)

    def test_renderer_defensive_copy(self) -> None:
        check = check_write_side_recovery_preconditions(_ready_payload())
        rendered = render_write_side_recovery_precondition_check(check)
        rendered["preconditions"]["json_safe"] = False
        rendered["failures"].append("hacked")
        again = render_write_side_recovery_precondition_check(check)
        self.assertEqual(again["preconditions"]["json_safe"], True)
        self.assertEqual(again["failures"], [])

    def test_input_not_mutated(self) -> None:
        payload = _ready_payload()
        snapshot = copy.deepcopy(payload)
        check_write_side_recovery_preconditions(payload)
        self.assertEqual(payload, snapshot)

    def test_no_runtime_repr_leakage(self) -> None:
        check = check_write_side_recovery_preconditions(_ready_payload())
        rendered = render_write_side_recovery_precondition_check(check)
        encoded = json.dumps(rendered)
        for marker in REPR_MARKERS:
            self.assertNotIn(marker, encoded, marker)

    def test_authorization_flags_always_false(self) -> None:
        scenarios = [
            _ready_payload(),
            _ready_payload(),
            _ready_payload(),
        ]
        scenarios[1]["dry_run"]["dry_run_ok"] = False
        scenarios[2]["governance"] = "broken"
        for payload in scenarios:
            check = check_write_side_recovery_preconditions(payload)
            for flag in AUTHORIZATION_FLAGS:
                self.assertIs(check.preconditions[flag], False, flag)

    def test_public_api_exact(self) -> None:
        public = sorted(
            name
            for name in dir(checker_module)
            if not name.startswith("_")
        )
        # Only check exposed public names match the documented exports plus
        # standard library types pulled in via `from ... import` are private.
        self.assertIn("WriteSideRecoveryPreconditionCheck", public)
        self.assertIn("check_write_side_recovery_preconditions", public)
        self.assertIn("render_write_side_recovery_precondition_check", public)
        self.assertIn("write_side_recovery_precondition_manifest", public)
        self.assertEqual(
            sorted(checker_module.__all__),
            [
                "WriteSideRecoveryPreconditionCheck",
                "check_write_side_recovery_preconditions",
                "render_write_side_recovery_precondition_check",
                "write_side_recovery_precondition_manifest",
            ],
        )


class SourceBoundaryTests(unittest.TestCase):
    # Required manifest/precondition fields collide with forbidden substrings
    # ("evidence_snapshot" intentionally allowed; "daemon_server_queue_authorized"
    # intentionally allowed because it is a required authorization flag name).
    ALLOWED_FIELD_NAMES = (
        "evidence_snapshot",
        "daemon_server_queue_authorized",
    )

    def _scrubbed_source(self) -> str:
        with open(checker_module.__file__, "r", encoding="utf-8") as fh:
            source = fh.read()
        for allowed in self.ALLOWED_FIELD_NAMES:
            source = source.replace(allowed, "")
        return source

    def test_production_module_has_no_forbidden_symbols(self) -> None:
        source = self._scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            self.assertNotIn(marker, source, marker)

    def test_evidence_append_not_present(self) -> None:
        source = self._scrubbed_source()
        self.assertNotIn("evidence append", source)
        self.assertNotIn("evidence_append", source)


if __name__ == "__main__":
    unittest.main()
