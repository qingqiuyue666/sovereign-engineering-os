"""Tracer-bullet tests for the restore dry-run readiness surface."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from kernel.lifecycle import restore_dry_run_readiness as module
from kernel.lifecycle.restore_dry_run_readiness import (
    RestoreDryRunReadiness,
    evaluate_restore_dry_run_readiness,
    render_restore_dry_run_readiness,
    restore_dry_run_readiness_manifest,
)


_GOVERNANCE_TAG = "read-only-governance-layer-v1"
_PRECONDITION_CHECKER_TAG = "write-side-precondition-checker-v1"
_PRECONDITION_CI_TAG = "write-side-precondition-ci-v1"
_RECOVERY_SPEC_ONLY_TAG = "write-side-recovery-spec-only-v1"

_GOVERNANCE_COMMIT = "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
_PRECONDITION_CHECKER_COMMIT = "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
_PRECONDITION_CI_COMMIT = "05c81541ad3d7deee20023843142f702937f6c3f"
_RECOVERY_SPEC_ONLY_COMMIT = "ad560cc2dab135f2c1d56d948410ae47586d118e"

_TARGET_TASK_ID = "task-001"
_IDEMPOTENCY_KEY = "idem-001"
_PROJECTED_EVIDENCE_REF = "evd://projected"
_PROJECTED_AFTER_SNAPSHOT_REF = "snap://after"
_PROJECTED_BEFORE_SNAPSHOT_REF = "snap://before"


def _valid_payload() -> dict[str, object]:
    return {
        "source_truth": {
            "current_head": "deadbeef",
            "working_tree_clean": True,
            "tags": {
                _GOVERNANCE_TAG: _GOVERNANCE_COMMIT,
                _PRECONDITION_CHECKER_TAG: _PRECONDITION_CHECKER_COMMIT,
                _PRECONDITION_CI_TAG: _PRECONDITION_CI_COMMIT,
                _RECOVERY_SPEC_ONLY_TAG: _RECOVERY_SPEC_ONLY_COMMIT,
            },
        },
        "governance_ci": {
            "ci_ok": True,
            "reason_code": "ready",
            "failures": [],
            "restore_authorized": False,
            "write_side_recovery_authorized": False,
            "cli_execution_authorized": False,
            "schema_migration_authorized": False,
            "daemon_server_queue_authorized": False,
            "durable_writes": False,
            "json_safe": True,
        },
        "precondition_ci": {
            "ci_ok": True,
            "reason_code": "ready",
            "failures": [],
            "restore_authorized": False,
            "write_side_recovery_authorized": False,
            "cli_execution_authorized": False,
            "schema_migration_authorized": False,
            "daemon_server_queue_authorized": False,
            "durable_writes": False,
            "json_safe": True,
        },
        "target_task": {
            "target_task_id": _TARGET_TASK_ID,
            "task_ready": True,
            "snapshot_ready": True,
            "lifecycle_ready": True,
        },
        "dry_run": {
            "dry_run_present": True,
            "dry_run_ok": True,
            "target_task_id": _TARGET_TASK_ID,
            "projected_action": "noop",
            "projected_evidence_ref": _PROJECTED_EVIDENCE_REF,
            "projected_before_snapshot_ref": _PROJECTED_BEFORE_SNAPSHOT_REF,
            "projected_after_snapshot_ref": _PROJECTED_AFTER_SNAPSHOT_REF,
            "determinism_hash": "hash-001",
            "mutates_state": False,
            "creates_files": False,
            "opens_write_transaction": False,
            "calls_restore": False,
        },
        "idempotency": {
            "idempotency_key": _IDEMPOTENCY_KEY,
            "target_task_id": _TARGET_TASK_ID,
            "operation_kind": "noop",
            "replay_status": "new",
        },
        "evidence_snapshot": {
            "before_snapshot_ref": _PROJECTED_BEFORE_SNAPSHOT_REF,
            "projected_after_snapshot_ref": _PROJECTED_AFTER_SNAPSHOT_REF,
            "projected_evidence_ref": _PROJECTED_EVIDENCE_REF,
            "immutable": True,
            "target_task_id": _TARGET_TASK_ID,
        },
        "human_approval": {
            "approval_present": True,
            "actor_identity": "actor",
            "scope": "scope",
            "reason": "reason",
            "created_at": "2026-01-01T00:00:00Z",
            "target_task_id": _TARGET_TASK_ID,
            "bound_idempotency_key": _IDEMPOTENCY_KEY,
        },
        "schema_runtime": {
            "schema_migration_required": False,
            "db_repair_required": False,
            "runtime_boundary_safe": True,
        },
    }


_READINESS_FLAGS = (
    "source_truth_ready",
    "governance_ci_ready",
    "precondition_ci_ready",
    "target_task_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "human_approval_ready",
    "schema_migration_safe",
    "db_repair_safe",
    "runtime_boundary_safe",
)

_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "source_truth_invalid",
    "baseline_tag_unresolved",
    "baseline_commit_mismatch",
    "working_tree_dirty",
    "governance_ci_invalid",
    "governance_ci_not_ready",
    "precondition_ci_invalid",
    "precondition_ci_not_ready",
    "target_task_invalid",
    "target_task_not_ready",
    "dry_run_invalid",
    "dry_run_missing",
    "dry_run_failed",
    "dry_run_target_mismatch",
    "dry_run_not_deterministic",
    "projected_action_missing",
    "projected_evidence_missing",
    "idempotency_invalid",
    "idempotency_missing",
    "idempotency_replay_risk",
    "evidence_snapshot_invalid",
    "evidence_snapshot_missing",
    "human_approval_invalid",
    "human_approval_missing",
    "schema_runtime_invalid",
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_violation",
)


class HappyPathTests(unittest.TestCase):
    def test_valid_payload_is_ready(self) -> None:
        payload = _valid_payload()
        result = evaluate_restore_dry_run_readiness(payload)
        self.assertIsInstance(result, RestoreDryRunReadiness)
        self.assertTrue(result.ready)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())

    def test_valid_payload_readiness_flags_all_true(self) -> None:
        result = evaluate_restore_dry_run_readiness(_valid_payload())
        for flag in _READINESS_FLAGS:
            self.assertIs(result.readiness[flag], True, msg=flag)

    def test_valid_payload_authorization_flags_false(self) -> None:
        result = evaluate_restore_dry_run_readiness(_valid_payload())
        for flag in _AUTHORIZATION_FLAGS:
            self.assertIs(result.readiness[flag], False, msg=flag)
        self.assertIs(result.readiness["durable_writes"], False)
        self.assertIs(result.readiness["json_safe"], True)

    def test_render_output_is_json_safe(self) -> None:
        rendered = render_restore_dry_run_readiness(
            evaluate_restore_dry_run_readiness(_valid_payload())
        )
        encoded = json.dumps(rendered)
        decoded = json.loads(encoded)
        self.assertEqual(decoded, rendered)


class TopLevelValidationTests(unittest.TestCase):
    def test_non_mapping_rejected(self) -> None:
        result = evaluate_restore_dry_run_readiness("not-a-mapping")
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")
        self.assertEqual(result.failures, ("payload_not_mapping",))

    def test_missing_top_level_section_rejected(self) -> None:
        payload = _valid_payload()
        del payload["dry_run"]
        result = evaluate_restore_dry_run_readiness(payload)
        self.assertFalse(result.ready)
        self.assertIn("payload_shape_mismatch", result.failures)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")

    def test_unknown_top_level_section_rejected(self) -> None:
        payload = _valid_payload()
        payload["unknown_section"] = {}
        result = evaluate_restore_dry_run_readiness(payload)
        self.assertFalse(result.ready)
        self.assertIn("payload_shape_mismatch", result.failures)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")

    def test_failure_ordering_deterministic(self) -> None:
        payload = _valid_payload()
        payload["source_truth"]["working_tree_clean"] = False
        payload["target_task"]["task_ready"] = False
        payload["schema_runtime"]["schema_migration_required"] = True
        payload["dry_run"]["dry_run_ok"] = False
        result = evaluate_restore_dry_run_readiness(payload)
        index_of = {fail: i for i, fail in enumerate(_FAILURE_ORDER)}
        positions = [index_of[fail] for fail in result.failures]
        self.assertEqual(positions, sorted(positions))


class SectionValidationTests(unittest.TestCase):
    def _evaluate(self, mutator) -> RestoreDryRunReadiness:
        payload = _valid_payload()
        mutator(payload)
        return evaluate_restore_dry_run_readiness(payload)

    def test_source_truth_missing_tag(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            del p["source_truth"]["tags"][_PRECONDITION_CI_TAG]

        result = self._evaluate(mutate)
        self.assertIn("baseline_tag_unresolved", result.failures)
        self.assertFalse(result.ready)

    def test_source_truth_wrong_tag_commit(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["source_truth"]["tags"][_GOVERNANCE_TAG] = "0" * 40

        result = self._evaluate(mutate)
        self.assertIn("baseline_commit_mismatch", result.failures)
        self.assertFalse(result.ready)

    def test_dirty_working_tree(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["source_truth"]["working_tree_clean"] = False

        result = self._evaluate(mutate)
        self.assertIn("working_tree_dirty", result.failures)
        self.assertFalse(result.ready)

    def test_governance_ci_not_ready(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["governance_ci"]["reason_code"] = "not_ready"
            p["governance_ci"]["failures"] = ["something"]
            p["governance_ci"]["ci_ok"] = False
            p["governance_ci"]["ready"] = False

        result = self._evaluate(mutate)
        self.assertIn("governance_ci_not_ready", result.failures)
        self.assertFalse(result.ready)

    def test_governance_ci_hazard_authorization_true(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["governance_ci"]["restore_authorized"] = True

        result = self._evaluate(mutate)
        self.assertIn("governance_ci_not_ready", result.failures)
        self.assertFalse(result.ready)

    def test_governance_ci_invalid(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["governance_ci"] = "not-a-mapping"

        result = self._evaluate(mutate)
        self.assertIn("governance_ci_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")

    def test_precondition_ci_not_ready(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["precondition_ci"]["reason_code"] = "not_ready"
            p["precondition_ci"]["ci_ok"] = False
            p["precondition_ci"]["ready"] = False

        result = self._evaluate(mutate)
        self.assertIn("precondition_ci_not_ready", result.failures)

    def test_precondition_ci_hazard_authorization_true(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["precondition_ci"]["write_side_recovery_authorized"] = True

        result = self._evaluate(mutate)
        self.assertIn("precondition_ci_not_ready", result.failures)

    def test_precondition_ci_invalid(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["precondition_ci"] = 5

        result = self._evaluate(mutate)
        self.assertIn("precondition_ci_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")

    def test_target_task_not_ready(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["target_task"]["task_ready"] = False

        result = self._evaluate(mutate)
        self.assertIn("target_task_not_ready", result.failures)

    def test_target_task_invalid(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["target_task"] = []

        result = self._evaluate(mutate)
        self.assertIn("target_task_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")

    def test_dry_run_missing(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["dry_run_present"] = False

        result = self._evaluate(mutate)
        self.assertIn("dry_run_missing", result.failures)

    def test_dry_run_failed(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["dry_run_ok"] = False

        result = self._evaluate(mutate)
        self.assertIn("dry_run_failed", result.failures)

    def test_dry_run_target_mismatch(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["target_task_id"] = "other-task"

        result = self._evaluate(mutate)
        self.assertIn("dry_run_target_mismatch", result.failures)

    def test_dry_run_not_deterministic(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["determinism_hash"] = ""

        result = self._evaluate(mutate)
        self.assertIn("dry_run_not_deterministic", result.failures)

    def test_dry_run_projected_action_missing(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["projected_action"] = ""

        result = self._evaluate(mutate)
        self.assertIn("projected_action_missing", result.failures)

    def test_dry_run_projected_evidence_missing(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["projected_evidence_ref"] = ""

        result = self._evaluate(mutate)
        self.assertIn("projected_evidence_missing", result.failures)

    def test_dry_run_side_effect_flag_true(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["dry_run"]["mutates_state"] = True

        result = self._evaluate(mutate)
        self.assertIn("dry_run_invalid", result.failures)
        self.assertEqual(result.reason_code, "invalid_readiness_payload")

    def test_idempotency_missing(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["idempotency"]["idempotency_key"] = ""

        result = self._evaluate(mutate)
        self.assertIn("idempotency_missing", result.failures)

    def test_idempotency_replay_risk(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["idempotency"]["replay_status"] = "unsafe"

        result = self._evaluate(mutate)
        self.assertIn("idempotency_replay_risk", result.failures)

    def test_evidence_snapshot_missing(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["evidence_snapshot"]["immutable"] = False

        result = self._evaluate(mutate)
        self.assertIn("evidence_snapshot_missing", result.failures)

    def test_evidence_snapshot_mismatch(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["evidence_snapshot"]["projected_after_snapshot_ref"] = "other"

        result = self._evaluate(mutate)
        self.assertIn("evidence_snapshot_missing", result.failures)

    def test_evidence_snapshot_invalid(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["evidence_snapshot"] = "bad"

        result = self._evaluate(mutate)
        self.assertIn("evidence_snapshot_invalid", result.failures)

    def test_human_approval_missing(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["human_approval"]["approval_present"] = False

        result = self._evaluate(mutate)
        self.assertIn("human_approval_missing", result.failures)

    def test_human_approval_invalid_mismatch(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["human_approval"]["bound_idempotency_key"] = "other-key"

        result = self._evaluate(mutate)
        self.assertIn("human_approval_invalid", result.failures)

    def test_human_approval_invalid_empty_field(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["human_approval"]["actor_identity"] = ""

        result = self._evaluate(mutate)
        self.assertIn("human_approval_invalid", result.failures)

    def test_schema_migration_required(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["schema_runtime"]["schema_migration_required"] = True

        result = self._evaluate(mutate)
        self.assertIn("schema_migration_required", result.failures)

    def test_db_repair_required(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["schema_runtime"]["db_repair_required"] = True

        result = self._evaluate(mutate)
        self.assertIn("db_repair_required", result.failures)

    def test_runtime_boundary_violation(self) -> None:
        def mutate(p: dict[str, object]) -> None:
            p["schema_runtime"]["runtime_boundary_safe"] = False

        result = self._evaluate(mutate)
        self.assertIn("runtime_boundary_violation", result.failures)


class OutputSafetyTests(unittest.TestCase):
    def test_renderer_exact_shape(self) -> None:
        result = evaluate_restore_dry_run_readiness(_valid_payload())
        rendered = render_restore_dry_run_readiness(result)
        self.assertEqual(
            set(rendered.keys()),
            {"ready", "reason_code", "failures", "readiness"},
        )
        self.assertIsInstance(rendered["failures"], list)
        readiness = rendered["readiness"]
        expected_keys = {
            "surface",
            "version",
            "source_truth_ready",
            "governance_ci_ready",
            "precondition_ci_ready",
            "target_task_ready",
            "dry_run_ready",
            "idempotency_ready",
            "evidence_snapshot_ready",
            "human_approval_ready",
            "schema_migration_safe",
            "db_repair_safe",
            "runtime_boundary_safe",
            "restore_authorized",
            "write_side_recovery_authorized",
            "cli_execution_authorized",
            "schema_migration_authorized",
            "daemon_server_queue_authorized",
            "db_repair_authorized",
            "durable_writes",
            "json_safe",
        }
        self.assertEqual(set(readiness.keys()), expected_keys)
        self.assertEqual(readiness["surface"], "restore_dry_run_readiness")
        self.assertEqual(readiness["version"], 1)

    def test_manifest_exact_shape(self) -> None:
        manifest = restore_dry_run_readiness_manifest()
        self.assertEqual(manifest["surface"], "restore_dry_run_readiness")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["input_shape"],
            "mapping_of_already_rendered_restore_dry_run_readiness_payloads",
        )
        self.assertEqual(
            manifest["baseline_tags"],
            {
                "read_only_governance_layer": _GOVERNANCE_TAG,
                "write_side_precondition_checker": _PRECONDITION_CHECKER_TAG,
                "write_side_precondition_ci": _PRECONDITION_CI_TAG,
                "write_side_recovery_spec_only": _RECOVERY_SPEC_ONLY_TAG,
            },
        )
        for flag in _AUTHORIZATION_FLAGS:
            self.assertIs(manifest[flag], False, msg=flag)
        self.assertIs(manifest["durable_writes"], False)
        self.assertIs(manifest["json_safe"], True)
        self.assertEqual(manifest["runtime_dependencies"], [])
        self.assertEqual(
            manifest["reason_codes"],
            ["invalid_readiness_payload", "not_ready", "ready"],
        )
        self.assertEqual(
            tuple(manifest["failure_values"]), _FAILURE_ORDER
        )

    def test_manifest_defensive_copy(self) -> None:
        first = restore_dry_run_readiness_manifest()
        first["restore_authorized"] = True
        first["failure_values"].append("malicious")
        first["baseline_tags"]["read_only_governance_layer"] = "tampered"
        second = restore_dry_run_readiness_manifest()
        self.assertIs(second["restore_authorized"], False)
        self.assertNotIn("malicious", second["failure_values"])
        self.assertEqual(
            second["baseline_tags"]["read_only_governance_layer"],
            _GOVERNANCE_TAG,
        )

    def test_renderer_defensive_copy(self) -> None:
        result = evaluate_restore_dry_run_readiness(_valid_payload())
        rendered_a = render_restore_dry_run_readiness(result)
        rendered_a["readiness"]["restore_authorized"] = True
        rendered_a["failures"].append("tampered")
        rendered_b = render_restore_dry_run_readiness(result)
        self.assertIs(rendered_b["readiness"]["restore_authorized"], False)
        self.assertNotIn("tampered", rendered_b["failures"])

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)
        evaluate_restore_dry_run_readiness(payload)
        self.assertEqual(payload, snapshot)

    def test_no_runtime_repr_leakage(self) -> None:
        result = evaluate_restore_dry_run_readiness(_valid_payload())
        rendered = render_restore_dry_run_readiness(result)
        encoded = json.dumps(rendered)
        self.assertNotIn("object at 0x", encoded)
        self.assertNotIn("<", encoded)
        self.assertNotIn(">", encoded)

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(module.__all__),
            sorted(
                [
                    "RestoreDryRunReadiness",
                    "restore_dry_run_readiness_manifest",
                    "evaluate_restore_dry_run_readiness",
                    "render_restore_dry_run_readiness",
                ]
            ),
        )


class SourceBoundaryTests(unittest.TestCase):
    _FORBIDDEN = (
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
        "check_write_side_recovery_preconditions",
        "render_write_side_recovery_precondition_check",
        "write_side_recovery_precondition_ci",
        "governance_readiness_aggregator",
        "approval_review_readiness",
        "evidence_replay_readiness",
        "task_lifecycle_journal_snapshot",
    )

    _ALLOWED_FIELD_STRINGS = (
        "projected_evidence_ref",
        "projected_evidence_missing",
        "evidence_snapshot_ready",
        "evidence_snapshot_invalid",
        "evidence_snapshot_missing",
        "daemon_server_queue_authorized",
    )

    def test_source_does_not_contain_forbidden_substrings(self) -> None:
        source_path = (
            Path(__file__).resolve().parents[2]
            / "kernel"
            / "lifecycle"
            / "restore_dry_run_readiness.py"
        )
        source = source_path.read_text(encoding="utf-8")
        sanitized = source
        for allowed in self._ALLOWED_FIELD_STRINGS:
            sanitized = sanitized.replace(allowed, "")
        for forbidden in self._FORBIDDEN:
            self.assertNotIn(
                forbidden,
                sanitized,
                msg=f"forbidden substring {forbidden!r} present in module",
            )


if __name__ == "__main__":
    unittest.main()
