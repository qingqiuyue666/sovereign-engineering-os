"""Tracer-bullet tests for the R2 restore dry-run plan renderer."""

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

from kernel.lifecycle import restore_dry_run_plan_renderer as plan_module
from kernel.lifecycle.restore_dry_run_plan_renderer import (
    RestoreDryRunPlan,
    render_restore_dry_run_plan,
    render_restore_dry_run_plan_payload,
    restore_dry_run_plan_renderer_manifest,
)


EXPECTED_MANIFEST = {
    "surface": "restore_dry_run_plan_renderer",
    "version": 1,
    "input_shape": "already_rendered_restore_dry_run_plan_inputs",
    "depends_on": {
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
    "reason_codes": ["invalid_plan_payload", "not_ready", "plan_ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "readiness_ci_invalid",
        "readiness_ci_not_ready",
        "readiness_ci_authorization_hazard",
        "dry_run_candidate_invalid",
        "dry_run_candidate_not_ready",
        "dry_run_candidate_target_mismatch",
        "dry_run_candidate_not_deterministic",
        "dry_run_candidate_side_effect_hazard",
        "projected_action_missing",
        "projected_evidence_missing",
        "idempotency_missing",
        "idempotency_replay_risk",
        "human_approval_missing",
        "human_approval_invalid",
        "schema_migration_required",
        "db_repair_required",
        "runtime_boundary_violation",
    ],
}


PLAN_KEYS = [
    "surface",
    "version",
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


PLAN_AUTH_FLAGS = (
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
    "restore_dry_run_plan_renderer",
    "restore_dry_run_plan",
    "restore_dry_run_readiness",
    "restore-dry-run-readiness-v1",
    "restore-dry-run-readiness-ci-v1",
    "projected_evidence_ref",
    "projected_before_snapshot_ref",
    "projected_after_snapshot_ref",
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


def _valid_dry_run_candidate(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "target_task_id": "task-001",
        "operation_kind": "restore",
        "idempotency_key": "idem-001",
        "replay_status": "new",
        "projected_action": "restore.no_op",
        "projected_evidence_ref": "evidence-001",
        "projected_before_snapshot_ref": "before-001",
        "projected_after_snapshot_ref": "after-001",
        "determinism_hash": "hash-001",
        "human_approval_ref": "approval-001",
        "actor_identity": "actor-001",
        "approval_scope": "scope-001",
        "approval_reason": "reason-001",
        "approval_present": True,
        "schema_migration_required": False,
        "db_repair_required": False,
        "runtime_boundary_safe": True,
        "mutates_state": False,
        "creates_files": False,
        "opens_write_transaction": False,
        "calls_restore": False,
    }
    base.update(overrides)
    return base


def _valid_payload(**overrides: object) -> dict[str, object]:
    readiness_ci = overrides.pop("readiness_ci", _valid_readiness_ci())
    dry_run_candidate = overrides.pop(
        "dry_run_candidate", _valid_dry_run_candidate()
    )
    base: dict[str, object] = {
        "readiness_ci": readiness_ci,
        "dry_run_candidate": dry_run_candidate,
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
    source = inspect.getsource(plan_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


class HappyPathTests(unittest.TestCase):
    def test_valid_payload_returns_plan_ok_true(self) -> None:
        payload = _valid_payload()
        result = render_restore_dry_run_plan(payload)

        self.assertIsInstance(result, RestoreDryRunPlan)
        self.assertIs(result.plan_ok, True)
        self.assertEqual(result.reason_code, "plan_ready")
        self.assertEqual(result.failures, ())

        rendered = render_restore_dry_run_plan_payload(result)
        self.assertEqual(
            list(rendered.keys()),
            ["plan_ok", "reason_code", "failures", "plan"],
        )
        self.assertIs(rendered["plan_ok"], True)
        self.assertEqual(rendered["reason_code"], "plan_ready")
        self.assertEqual(rendered["failures"], [])

        plan = rendered["plan"]
        self.assertIsInstance(plan, dict)
        self.assertEqual(list(plan.keys()), PLAN_KEYS)
        self.assertEqual(plan["surface"], "restore_dry_run_plan")
        self.assertEqual(plan["version"], 1)
        self.assertEqual(plan["target_task_id"], "task-001")
        self.assertEqual(plan["operation_kind"], "restore")
        self.assertEqual(plan["idempotency_key"], "idem-001")
        self.assertEqual(plan["projected_action"], "restore.no_op")
        self.assertEqual(plan["projected_evidence_ref"], "evidence-001")
        self.assertEqual(
            plan["projected_before_snapshot_ref"], "before-001"
        )
        self.assertEqual(
            plan["projected_after_snapshot_ref"], "after-001"
        )
        self.assertEqual(plan["determinism_hash"], "hash-001")
        self.assertEqual(plan["human_approval_ref"], "approval-001")
        self.assertEqual(plan["actor_identity"], "actor-001")
        self.assertEqual(plan["approval_scope"], "scope-001")
        self.assertEqual(plan["approval_reason"], "reason-001")
        self.assertIs(plan["transaction_required"], True)
        self.assertIs(plan["rollback_required"], True)
        for flag in PLAN_AUTH_FLAGS:
            self.assertIs(plan[flag], False, flag)
        self.assertIs(plan["executes_plan"], False)
        self.assertIs(plan["json_safe"], True)

        _assert_json_safe(rendered)
        _assert_no_runtime_repr(rendered)

    def test_happy_path_is_deterministic(self) -> None:
        a = render_restore_dry_run_plan_payload(
            render_restore_dry_run_plan(_valid_payload())
        )
        b = render_restore_dry_run_plan_payload(
            render_restore_dry_run_plan(_valid_payload())
        )
        self.assertEqual(a, b)


class TopLevelValidationTests(unittest.TestCase):
    def test_non_mapping_rejected(self) -> None:
        for payload in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(payload=payload):
                result = render_restore_dry_run_plan(payload)
                self.assertIs(result.plan_ok, False)
                self.assertEqual(result.reason_code, "invalid_plan_payload")
                self.assertEqual(result.failures, ("payload_not_mapping",))

    def test_missing_top_level_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["dry_run_candidate"]

        result = render_restore_dry_run_plan(payload)

        self.assertIs(result.plan_ok, False)
        self.assertEqual(result.reason_code, "invalid_plan_payload")
        self.assertEqual(result.failures, ("payload_shape_mismatch",))

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _valid_payload()
        payload["extra"] = True

        result = render_restore_dry_run_plan(payload)

        self.assertEqual(result.reason_code, "invalid_plan_payload")
        self.assertEqual(result.failures, ("payload_shape_mismatch",))

    def test_failure_ordering_deterministic(self) -> None:
        payload = _valid_payload(
            readiness_ci="not-a-mapping",
            dry_run_candidate="not-a-mapping",
        )
        result = render_restore_dry_run_plan(payload)

        index_readiness = result.failures.index("readiness_ci_invalid")
        index_dry = result.failures.index("dry_run_candidate_invalid")
        self.assertLess(index_readiness, index_dry)


class ReadinessCIValidationTests(unittest.TestCase):
    def test_readiness_ci_not_mapping(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=[])
        )
        self.assertIs(result.plan_ok, False)
        self.assertEqual(result.reason_code, "invalid_plan_payload")
        self.assertIn("readiness_ci_invalid", result.failures)

    def test_readiness_ci_ci_ok_false(self) -> None:
        readiness_ci = _valid_readiness_ci(ci_ok=False)
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIs(result.plan_ok, False)
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_reason_code_not_ready(self) -> None:
        readiness_ci = _valid_readiness_ci(reason_code="not_ready")
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_failures_non_empty(self) -> None:
        readiness_ci = _valid_readiness_ci(failures=["x"])
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_wrong_surface(self) -> None:
        readiness_ci = _valid_readiness_ci(surface="other")
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_wrong_version(self) -> None:
        readiness_ci = _valid_readiness_ci(version=2)
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_contract_ready_false(self) -> None:
        readiness_ci = _valid_readiness_ci(contract_ready=False)
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_contract_reason_code_not_ready(self) -> None:
        readiness_ci = _valid_readiness_ci(contract_reason_code="not_ready")
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)

    def test_readiness_ci_authorization_flag_true(self) -> None:
        readiness_ci = _valid_readiness_ci(restore_authorized=True)
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn(
            "readiness_ci_authorization_hazard", result.failures
        )

    def test_readiness_ci_durable_writes_true(self) -> None:
        readiness_ci = _valid_readiness_ci(durable_writes=True)
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn(
            "readiness_ci_authorization_hazard", result.failures
        )

    def test_readiness_ci_json_safe_false(self) -> None:
        readiness_ci = _valid_readiness_ci(json_safe=False)
        result = render_restore_dry_run_plan(
            _valid_payload(readiness_ci=readiness_ci)
        )
        self.assertIn("readiness_ci_not_ready", result.failures)


class DryRunCandidateValidationTests(unittest.TestCase):
    def test_missing_dry_run_key_rejected(self) -> None:
        candidate = _valid_dry_run_candidate()
        del candidate["target_task_id"]
        result = render_restore_dry_run_plan(
            _valid_payload(dry_run_candidate=candidate)
        )
        self.assertIs(result.plan_ok, False)
        self.assertIn("dry_run_candidate_invalid", result.failures)

    def test_unknown_dry_run_key_rejected(self) -> None:
        candidate = _valid_dry_run_candidate()
        candidate["unknown"] = True
        result = render_restore_dry_run_plan(
            _valid_payload(dry_run_candidate=candidate)
        )
        self.assertIn("dry_run_candidate_invalid", result.failures)

    def test_required_string_non_string_rejected(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    target_task_id=123
                )
            )
        )
        self.assertIn("dry_run_candidate_invalid", result.failures)

    def test_required_string_empty_rejected(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    target_task_id=""
                )
            )
        )
        self.assertIs(result.plan_ok, False)
        self.assertIn("dry_run_candidate_not_ready", result.failures)

    def test_projected_action_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    projected_action=""
                )
            )
        )
        self.assertIn("projected_action_missing", result.failures)

    def test_projected_evidence_ref_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    projected_evidence_ref=""
                )
            )
        )
        self.assertIn("projected_evidence_missing", result.failures)

    def test_projected_before_snapshot_ref_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    projected_before_snapshot_ref=""
                )
            )
        )
        self.assertIn("projected_evidence_missing", result.failures)

    def test_projected_after_snapshot_ref_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    projected_after_snapshot_ref=""
                )
            )
        )
        self.assertIn("projected_evidence_missing", result.failures)

    def test_determinism_hash_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    determinism_hash=""
                )
            )
        )
        self.assertIn("dry_run_candidate_not_deterministic", result.failures)

    def test_idempotency_key_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    idempotency_key=""
                )
            )
        )
        self.assertIn("idempotency_missing", result.failures)

    def test_replay_status_invalid(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    replay_status="other"
                )
            )
        )
        self.assertIn("idempotency_replay_risk", result.failures)

    def test_replay_status_same_attempt_safe_accepted(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    replay_status="same_attempt_safe"
                )
            )
        )
        self.assertIs(result.plan_ok, True)

    def test_approval_present_false(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    approval_present=False
                )
            )
        )
        self.assertIn("human_approval_missing", result.failures)

    def test_human_approval_ref_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    human_approval_ref=""
                )
            )
        )
        self.assertIn("human_approval_missing", result.failures)
        self.assertIn("human_approval_invalid", result.failures)

    def test_actor_identity_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(actor_identity="")
            )
        )
        self.assertIn("human_approval_invalid", result.failures)

    def test_approval_scope_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(approval_scope="")
            )
        )
        self.assertIn("human_approval_invalid", result.failures)

    def test_approval_reason_empty(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(approval_reason="")
            )
        )
        self.assertIn("human_approval_invalid", result.failures)

    def test_schema_migration_required_true(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    schema_migration_required=True
                )
            )
        )
        self.assertIn("schema_migration_required", result.failures)

    def test_db_repair_required_true(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    db_repair_required=True
                )
            )
        )
        self.assertIn("db_repair_required", result.failures)

    def test_runtime_boundary_safe_false(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    runtime_boundary_safe=False
                )
            )
        )
        self.assertIn("runtime_boundary_violation", result.failures)

    def test_mutates_state_true(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    mutates_state=True
                )
            )
        )
        self.assertIn("dry_run_candidate_side_effect_hazard", result.failures)

    def test_creates_files_true(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    creates_files=True
                )
            )
        )
        self.assertIn("dry_run_candidate_side_effect_hazard", result.failures)

    def test_opens_write_transaction_true(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    opens_write_transaction=True
                )
            )
        )
        self.assertIn("dry_run_candidate_side_effect_hazard", result.failures)

    def test_calls_restore_true(self) -> None:
        result = render_restore_dry_run_plan(
            _valid_payload(
                dry_run_candidate=_valid_dry_run_candidate(
                    calls_restore=True
                )
            )
        )
        self.assertIn("dry_run_candidate_side_effect_hazard", result.failures)


class ApiAndSafetyTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = restore_dry_run_plan_renderer_manifest()
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_returns_defensive_copy(self) -> None:
        a = restore_dry_run_plan_renderer_manifest()
        b = restore_dry_run_plan_renderer_manifest()
        self.assertIsNot(a, b)
        self.assertIsNot(a["depends_on"], b["depends_on"])
        self.assertIsNot(a["failure_values"], b["failure_values"])

        a["depends_on"]["restore_dry_run_readiness"] = "tampered"
        a["failure_values"].append("injected")

        c = restore_dry_run_plan_renderer_manifest()
        self.assertEqual(c, EXPECTED_MANIFEST)

    def test_renderer_returns_defensive_copy(self) -> None:
        plan = render_restore_dry_run_plan(_valid_payload())
        a = render_restore_dry_run_plan_payload(plan)
        b = render_restore_dry_run_plan_payload(plan)
        self.assertIsNot(a, b)
        self.assertIsNot(a["plan"], b["plan"])
        self.assertIsNot(a["failures"], b["failures"])

        a["plan"]["target_task_id"] = "tampered"
        a["failures"].append("injected")

        c = render_restore_dry_run_plan_payload(plan)
        self.assertEqual(c["plan"]["target_task_id"], "task-001")
        self.assertEqual(c["failures"], [])

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)
        render_restore_dry_run_plan(payload)
        self.assertEqual(payload, snapshot)

    def test_output_json_safe(self) -> None:
        plan = render_restore_dry_run_plan(_valid_payload())
        rendered = render_restore_dry_run_plan_payload(plan)
        _assert_json_safe(rendered)

    def test_no_runtime_repr_leakage(self) -> None:
        plan = render_restore_dry_run_plan(_valid_payload())
        rendered = render_restore_dry_run_plan_payload(plan)
        _assert_no_runtime_repr(rendered)

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(plan_module.__all__),
            sorted(
                [
                    "RestoreDryRunPlan",
                    "restore_dry_run_plan_renderer_manifest",
                    "render_restore_dry_run_plan",
                    "render_restore_dry_run_plan_payload",
                ]
            ),
        )

    def test_dataclass_is_frozen(self) -> None:
        plan = render_restore_dry_run_plan(_valid_payload())
        with self.assertRaises(Exception):
            plan.plan_ok = False  # type: ignore[misc]

    def test_plan_ok_does_not_authorize_restore(self) -> None:
        plan = render_restore_dry_run_plan(_valid_payload())
        rendered = render_restore_dry_run_plan_payload(plan)
        self.assertIs(plan.plan_ok, True)
        for flag in PLAN_AUTH_FLAGS:
            self.assertIs(rendered["plan"][flag], False, flag)
        self.assertIs(rendered["plan"]["executes_plan"], False)


class SourceBoundaryTests(unittest.TestCase):
    def test_production_source_has_no_forbidden_markers(self) -> None:
        scrubbed = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, scrubbed)

    def test_production_source_does_not_import_forbidden_modules(
        self,
    ) -> None:
        source = inspect.getsource(plan_module)
        for module_name in (
            "sqlite3",
            "subprocess",
            "argparse",
            "click",
            "socket",
            "asyncio",
            "threading",
            "queue",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(f"import {module_name}", source)
                self.assertNotIn(f"from {module_name}", source)


if __name__ == "__main__":
    unittest.main()
