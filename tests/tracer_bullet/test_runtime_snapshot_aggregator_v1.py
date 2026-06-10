"""Tracer-bullet tests for runtime snapshot aggregator v1."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import json
import unittest

from kernel.runtime.event_journal import JournalEvent
from kernel.runtime.operator_console_state_model import (
    build_operator_console_state,
)
from kernel.runtime.runtime_snapshot_aggregator import (
    ALLOWED_NEXT_ACTIONS,
    FORBIDDEN_NEXT_ACTIONS,
    RuntimeSnapshot,
    aggregate_runtime_snapshot,
)
from kernel.runtime.task_to_workflow_router_skeleton import route_task_intent
from kernel.runtime.tool_approval_requirement_binding import generate_approval_requirement
from kernel.runtime.tool_manifest_normalizer import normalize_tool_manifest_candidate
from kernel.runtime.tool_manifest_risk_binding import bind_tool_manifest_risk

POLICY_PATH = Path("governance/operator/runtime_snapshot_aggregator_v1.json")
SOURCE_PATH = Path("kernel/runtime/runtime_snapshot_aggregator.py")


def _candidate(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "source_type": "CLI_TOOL",
        "tool_name": "Read Only Tool",
        "declared_capabilities": ["read_only"],
        "declared_inputs": {"schema": "metadata"},
        "declared_outputs": {"schema": "metadata"},
        "filesystem_scope": "none",
        "network_scope": "none",
        "process_scope": "none",
        "credential_scope": "none",
        "provider_scope": "none",
        "dcc_scope": "none",
        "model_scope": "none",
        "browser_scope": "none",
        "plugin_scope": "none",
    }
    fields.update(overrides)
    return fields


def _manifest(**overrides: object):
    return normalize_tool_manifest_candidate(_candidate(**overrides))


def _journal_event() -> JournalEvent:
    return JournalEvent(
        event_id="event-001",
        run_id="run-001",
        task_id="task-001",
        stage="review",
        event_type="risk_summary_recorded",
        logical_sequence=1,
        payload_digest="sha256:" + "1" * 64,
    )


def _asset_summary() -> dict[str, object]:
    return {
        "asset_id": "asset-001",
        "root_id": "root-001",
        "relative_path": "shots/shot001/readme.md",
        "media_class": "TEXT",
        "sha256": "sha256:" + "2" * 64,
        "content_hash": "sha256:" + "3" * 64,
    }


def _workflow():
    return route_task_intent(
        {
            "task_id": "task-001",
            "domain": "ASSET_INGESTION",
            "objective": "inventory bounded local assets",
            "inputs": {"assets": ["asset-001"]},
            "constraints": {"dry_run": True},
            "risk_tolerance": "low",
            "desired_outputs": ["inventory_summary"],
        }
    )


class RuntimeSnapshotAggregatorTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "runtime_snapshot_aggregator_v1")
        self.assertTrue(policy["aggregation_only"])
        self.assertTrue(policy["read_only"])
        self.assertFalse(policy["ui_implementation_allowed"])
        self.assertFalse(policy["journal_mutation_allowed"])
        self.assertFalse(policy["raw_payload_persistence_allowed"])
        self.assertFalse(policy["credential_material_allowed"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])
        self.assertEqual(set(policy["allowed_next_actions"]), ALLOWED_NEXT_ACTIONS)
        self.assertEqual(set(policy["forbidden_next_actions"]), FORBIDDEN_NEXT_ACTIONS)

    def test_aggregate_minimal_snapshot(self):
        snapshot = aggregate_runtime_snapshot(
            system_state={"state": "dry_run", "mode": "metadata_only"},
            generated_at="2026-05-25T00:00:00+00:00",
        )
        self.assertIsInstance(snapshot, RuntimeSnapshot)
        self.assertTrue(snapshot.snapshot_id.startswith("runtime_snapshot_"))
        self.assertEqual(snapshot.journal_summary["event_count"], 0)
        self.assertEqual(snapshot.asset_summary["asset_count"], 0)
        self.assertEqual(snapshot.workflow_summary["workflow_count"], 0)
        self.assertEqual(snapshot.tool_summary["tool_count"], 0)
        self.assertEqual(snapshot.risk_summary["risk_count"], 0)
        self.assertEqual(snapshot.approval_summary["requirement_count"], 0)
        self.assertEqual(snapshot.next_actions, ())

    def test_aggregate_snapshot_with_journal_risk_approval_and_asset_summaries(self):
        manifest = _manifest(source_type="API_ADAPTER", provider_scope="metadata_only")
        risk = bind_tool_manifest_risk(manifest)
        requirement = generate_approval_requirement(risk)
        snapshot = aggregate_runtime_snapshot(
            system_state={"state": "dry_run", "train": "tool_ingestion_v1"},
            journal_event_summaries=[_journal_event()],
            asset_inventory_summaries=[_asset_summary()],
            workflow_graph_descriptors=[_workflow()],
            tool_manifest_summaries=[manifest],
            risk_assessments=[risk],
            approval_requirements=[requirement],
            approval_token_summaries=[
                {
                    "approval_id": "approval-001",
                    "revoked": False,
                    "content_hash": "sha256:" + "4" * 64,
                }
            ],
            operator_console_state_model_ref=build_operator_console_state(),
        )
        self.assertEqual(snapshot.journal_summary["event_count"], 1)
        self.assertEqual(snapshot.asset_summary["asset_count"], 1)
        self.assertEqual(snapshot.workflow_summary["workflow_count"], 1)
        self.assertEqual(snapshot.tool_summary["tool_count"], 1)
        self.assertEqual(snapshot.risk_summary["approval_required_count"], 1)
        self.assertEqual(snapshot.approval_summary["requirement_count"], 1)
        self.assertEqual(snapshot.approval_summary["token_count"], 1)
        self.assertIn("review_risk_assessment", snapshot.next_actions)
        self.assertIn("issue_scoped_approval", snapshot.next_actions)
        self.assertIn("inspect_asset_inventory", snapshot.next_actions)

    def test_snapshot_hash_deterministic(self):
        first = aggregate_runtime_snapshot(
            system_state={"state": "dry_run"},
            next_actions=["run_dry_run_plan"],
            generated_at="2026-05-25T00:00:00+00:00",
        )
        second = aggregate_runtime_snapshot(
            system_state={"state": "dry_run"},
            next_actions=["run_dry_run_plan"],
            generated_at="2026-05-25T00:00:00+00:00",
        )
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertEqual(first.snapshot_id, second.snapshot_id)

    def test_generated_at_excluded_from_deterministic_hash(self):
        first = aggregate_runtime_snapshot(
            system_state={"state": "dry_run"},
            generated_at="2026-05-25T00:00:00+00:00",
        )
        second = aggregate_runtime_snapshot(
            system_state={"state": "dry_run"},
            generated_at="2030-01-01T00:00:00+00:00",
        )
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertNotEqual(first.generated_at, second.generated_at)

    def test_next_actions_advisory_only(self):
        snapshot = aggregate_runtime_snapshot(
            system_state={"state": "dry_run"},
            next_actions=["inspect_quarantine", "run_dry_run_plan"],
        )
        self.assertEqual(
            snapshot.next_actions,
            ("inspect_quarantine", "run_dry_run_plan"),
        )
        self.assertTrue(set(snapshot.next_actions).issubset(ALLOWED_NEXT_ACTIONS))

    def test_forbidden_next_actions_rejected(self):
        for action in ("execute_raw_command", "open_browser", "call_provider"):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    aggregate_runtime_snapshot(
                        system_state={"state": "dry_run"},
                        next_actions=[action],
                    )

    def test_no_raw_payload_stored(self):
        with self.assertRaises(ValueError) as context:
            aggregate_runtime_snapshot(
                system_state={"state": "dry_run"},
                journal_event_summaries=[
                    {
                        "event_id": "event-001",
                        "raw_payload": {"prompt": "do not store"},
                    }
                ],
            )
        self.assertIn("raw_payload", str(context.exception))

    def test_no_credential_material_stored(self):
        with self.assertRaises(ValueError) as context:
            aggregate_runtime_snapshot(
                system_state={"state": "dry_run", "credential": "secret-material"},
            )
        self.assertIn("credential", str(context.exception))

    def test_no_mutation_api(self):
        snapshot = aggregate_runtime_snapshot(system_state={"state": "dry_run"})
        with self.assertRaises(FrozenInstanceError):
            snapshot.snapshot_id = "changed"
        self.assertFalse(hasattr(snapshot, "append"))
        self.assertFalse(hasattr(snapshot, "mutate"))
        self.assertFalse(hasattr(snapshot, "persist"))

    def test_no_subprocess_network_browser_provider_dcc_or_comfyui_launch(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "bpy",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("shell=True", source)

    def test_operator_console_can_consume_snapshot_shape(self):
        snapshot = aggregate_runtime_snapshot(
            system_state={"state": "dry_run"},
            operator_console_state_model_ref=build_operator_console_state(),
            next_actions=["review_risk_assessment"],
        )
        data = snapshot.as_dict()
        self.assertEqual(
            set(data),
            {
                "snapshot_id",
                "generated_at",
                "system_state",
                "journal_summary",
                "asset_summary",
                "workflow_summary",
                "tool_summary",
                "risk_summary",
                "approval_summary",
                "queue_summary",
                "next_actions",
                "blockers",
                "warnings",
                "snapshot_hash",
            },
        )
        self.assertIn("operator_console_state_model_ref", data["system_state"])
        self.assertFalse(
            data["system_state"]["operator_console_state_model_ref"][
                "ui_runtime_present"
            ]
        )
        self.assertTrue(set(data["next_actions"]).issubset(ALLOWED_NEXT_ACTIONS))


if __name__ == "__main__":
    unittest.main()
