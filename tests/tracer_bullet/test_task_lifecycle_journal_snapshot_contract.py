"""Read-only contract over the task lifecycle journal snapshot boundary.

Pins the structural contract enforced by
`kernel.lifecycle.task_lifecycle_journal_snapshot_contract` over the
existing `TaskLifecycleSnapshot` shape produced by the journal reader.

Read-only: no rows are written, no orchestrator runtime is touched, no
restore/CLI is exercised, no schema/migration is added. Only the
existing in-memory snapshot dataclass is consumed.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_lifecycle_journal_snapshot_contract import (
    TaskLifecycleJournalSnapshotContractCheck,
    check_task_lifecycle_journal_snapshot_contract,
    render_task_lifecycle_journal_snapshot_contract_check,
    task_lifecycle_journal_snapshot_contract_manifest,
)
from kernel.lifecycle.task_recovery import TaskLifecycleSnapshot


def _valid_snapshot(**overrides: object) -> TaskLifecycleSnapshot:
    base: dict[str, object] = {
        "task_id": "task-001",
        "intent_id": "intent-001",
        "current_stage": Stage.CONTEXT,
        "artifact_ids": {Stage.CONTEXT: "ctx-1"},
        "terminal_state": None,
        "last_event_sequence": 1,
        "lifecycle_record_count": 1,
        "malformed_event_count": 0,
        "intent_anchor_count": 1,
        "intent_created_at": "2025-01-01T00:00:00Z",
    }
    base.update(overrides)
    return TaskLifecycleSnapshot(**base)  # type: ignore[arg-type]


class TestSnapshotContractAcceptance(unittest.TestCase):
    """Valid snapshots are accepted with stable ready/contract output."""

    def test_valid_minimal_snapshot_is_ready(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot()
        )
        self.assertIsInstance(
            check, TaskLifecycleJournalSnapshotContractCheck
        )
        self.assertTrue(check.ready)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())

    def test_valid_sealed_snapshot_is_ready(self) -> None:
        snapshot = _valid_snapshot(
            current_stage=Stage.SEALED,
            terminal_state=Stage.SEALED,
            artifact_ids={
                Stage.CONTEXT: "ctx-1",
                Stage.EVIDENCE: "ev-1",
            },
            last_event_sequence=10,
            lifecycle_record_count=10,
        )
        check = check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertTrue(check.ready)
        self.assertEqual(check.failures, ())

    def test_valid_abandoned_snapshot_is_ready(self) -> None:
        snapshot = _valid_snapshot(
            current_stage=Stage.ABANDONED,
            terminal_state=Stage.ABANDONED,
        )
        check = check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertTrue(check.ready)

    def test_valid_empty_artifact_ids_is_ready(self) -> None:
        snapshot = _valid_snapshot(
            current_stage=None,
            artifact_ids={},
            last_event_sequence=None,
            lifecycle_record_count=0,
        )
        check = check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertTrue(check.ready)


class TestSnapshotContractRejection(unittest.TestCase):
    """Malformed inputs are rejected with deterministic stable codes."""

    def test_non_snapshot_input_short_circuits(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract({"task_id": "x"})
        self.assertFalse(check.ready)
        self.assertEqual(check.reason_code, "not_ready")
        self.assertEqual(check.failures, ("input_not_snapshot",))

    def test_none_input_short_circuits(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(None)
        self.assertFalse(check.ready)
        self.assertEqual(check.failures, ("input_not_snapshot",))

    def test_empty_task_id_rejected(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot(task_id="")
        )
        self.assertFalse(check.ready)
        self.assertIn("task_id_invalid", check.failures)

    def test_empty_intent_id_rejected(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot(intent_id="")
        )
        self.assertFalse(check.ready)
        self.assertIn("intent_id_invalid", check.failures)

    def test_artifact_ids_value_invalid(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot(artifact_ids={Stage.CONTEXT: ""})
        )
        self.assertFalse(check.ready)
        self.assertIn("artifact_ids_value_invalid", check.failures)

    def test_artifact_ids_terminal_stage_rejected(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot(
                artifact_ids={Stage.SEALED: "should-not-be-here"},
            )
        )
        self.assertFalse(check.ready)
        self.assertIn(
            "artifact_ids_stage_not_artifact_bearing", check.failures
        )

    def test_negative_counter_rejected(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot(lifecycle_record_count=-1)
        )
        self.assertFalse(check.ready)
        self.assertIn("lifecycle_record_count_invalid", check.failures)

    def test_terminal_state_inconsistent(self) -> None:
        snapshot = _valid_snapshot(
            current_stage=Stage.CONTEXT,
            terminal_state=Stage.SEALED,
        )
        check = check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertFalse(check.ready)
        self.assertIn("terminal_state_inconsistent", check.failures)


class TestSnapshotContractDeterminism(unittest.TestCase):
    """Failure ordering and contract manifest shape are deterministic."""

    def test_failure_ordering_is_field_declaration_order(self) -> None:
        snapshot = _valid_snapshot(
            task_id="",
            intent_id="",
            artifact_ids={Stage.CONTEXT: ""},
            lifecycle_record_count=-1,
            malformed_event_count=-1,
        )
        check = check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertEqual(
            check.failures,
            (
                "task_id_invalid",
                "intent_id_invalid",
                "artifact_ids_value_invalid",
                "lifecycle_record_count_invalid",
                "malformed_event_count_invalid",
            ),
        )

    def test_repeat_calls_produce_identical_failures(self) -> None:
        snapshot = _valid_snapshot(task_id="", intent_id="")
        first = check_task_lifecycle_journal_snapshot_contract(snapshot)
        second = check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertEqual(first.failures, second.failures)
        self.assertEqual(first.reason_code, second.reason_code)

    def test_manifest_shape_is_deterministic(self) -> None:
        m1 = task_lifecycle_journal_snapshot_contract_manifest()
        m2 = task_lifecycle_journal_snapshot_contract_manifest()
        self.assertEqual(m1, m2)
        self.assertEqual(m1["surface"], "task_lifecycle_journal_snapshot")
        self.assertEqual(m1["version"], 1)
        self.assertEqual(m1["input_shape"], "TaskLifecycleSnapshot")
        self.assertEqual(m1["restore_supported"], False)
        self.assertEqual(m1["durable_writes"], False)
        self.assertEqual(m1["cli_commands"], [])
        self.assertEqual(m1["runtime_dependencies"], [])
        self.assertEqual(m1["json_safe"], True)
        self.assertEqual(
            m1["reason_codes"], ["not_ready", "ready"]
        )


class TestSnapshotContractRendererDefensiveCopy(unittest.TestCase):
    """Renderer must deep-copy contract and not leak runtime objects."""

    def test_manifest_caller_mutation_does_not_affect_next_call(self) -> None:
        m1 = task_lifecycle_journal_snapshot_contract_manifest()
        m1["failure_values"].append("INJECTED")
        m1["surface"] = "tampered"
        m2 = task_lifecycle_journal_snapshot_contract_manifest()
        self.assertNotIn("INJECTED", m2["failure_values"])
        self.assertEqual(m2["surface"], "task_lifecycle_journal_snapshot")

    def test_render_produces_independent_contract(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot()
        )
        rendered_a = render_task_lifecycle_journal_snapshot_contract_check(
            check
        )
        rendered_a["contract"]["surface"] = "tampered"
        rendered_a["contract"]["failure_values"].append("INJECTED")
        rendered_b = render_task_lifecycle_journal_snapshot_contract_check(
            check
        )
        self.assertEqual(
            rendered_b["contract"]["surface"],
            "task_lifecycle_journal_snapshot",
        )
        self.assertNotIn(
            "INJECTED", rendered_b["contract"]["failure_values"]
        )

    def test_rendered_output_has_exact_keys(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot()
        )
        rendered = render_task_lifecycle_journal_snapshot_contract_check(
            check
        )
        self.assertEqual(
            set(rendered.keys()), {"ready", "reason_code", "failures", "contract"}
        )

    def test_rendered_output_is_json_safe(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot(
                current_stage=Stage.SEALED, terminal_state=Stage.SEALED
            )
        )
        rendered = render_task_lifecycle_journal_snapshot_contract_check(
            check
        )
        # json.dumps will fail if any non-JSON-native object leaked through
        # (e.g. a Stage enum, dataclass, frozenset, or repr placeholder).
        encoded = json.dumps(rendered, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["ready"], True)
        self.assertEqual(decoded["reason_code"], "ready")
        self.assertEqual(decoded["failures"], [])

    def test_rendered_failures_output_is_json_safe(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract({})
        rendered = render_task_lifecycle_journal_snapshot_contract_check(
            check
        )
        encoded = json.dumps(rendered, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["ready"], False)
        self.assertEqual(decoded["failures"], ["input_not_snapshot"])

    def test_rendered_contract_contains_no_runtime_repr(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot()
        )
        rendered = render_task_lifecycle_journal_snapshot_contract_check(
            check
        )
        text = json.dumps(rendered)
        # No object reprs, no dataclass leaks, no enum reprs.
        self.assertNotIn("TaskLifecycleSnapshot(", text)
        self.assertNotIn("<Stage.", text)
        self.assertNotIn(" object at 0x", text)


class TestSnapshotContractNoMutation(unittest.TestCase):
    """Contract check does not mutate input or leak references."""

    def test_input_snapshot_artifact_ids_not_mutated(self) -> None:
        artifact_ids = {Stage.CONTEXT: "ctx-1"}
        snapshot = _valid_snapshot(artifact_ids=artifact_ids)
        check_task_lifecycle_journal_snapshot_contract(snapshot)
        self.assertEqual(artifact_ids, {Stage.CONTEXT: "ctx-1"})
        self.assertEqual(snapshot.artifact_ids, {Stage.CONTEXT: "ctx-1"})

    def test_returned_check_contract_distinct_from_module_constant(
        self,
    ) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot()
        )
        manifest = task_lifecycle_journal_snapshot_contract_manifest()
        self.assertEqual(check.contract, manifest)
        check.contract["surface"] = "tampered"
        manifest_again = task_lifecycle_journal_snapshot_contract_manifest()
        self.assertEqual(
            manifest_again["surface"], "task_lifecycle_journal_snapshot"
        )


class TestSnapshotContractPublicAPI(unittest.TestCase):
    """Public API surface is exact and stable."""

    def test_public_api_exact(self) -> None:
        import kernel.lifecycle.task_lifecycle_journal_snapshot_contract as mod

        self.assertEqual(
            sorted(mod.__all__),
            sorted(
                [
                    "TaskLifecycleJournalSnapshotContractCheck",
                    "check_task_lifecycle_journal_snapshot_contract",
                    "render_task_lifecycle_journal_snapshot_contract_check",
                    "task_lifecycle_journal_snapshot_contract_manifest",
                ]
            ),
        )

    def test_check_dataclass_is_frozen(self) -> None:
        check = check_task_lifecycle_journal_snapshot_contract(
            _valid_snapshot()
        )
        with self.assertRaises(Exception):
            check.ready = False  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
