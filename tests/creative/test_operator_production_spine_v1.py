from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from creative.production.inspect import build_operator_production_spine_inspection

REPO = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO / "tests/fixtures/creative/assets"
DOCTOR_FIXTURE = REPO / "tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json"


class OperatorProductionSpineV1Tests(unittest.TestCase):
    def test_inspection_spine_writes_reports_graph_actions_and_obsidian_vault(self) -> None:
        output_relative = Path("work/test_operator_production_spine_v1_unit")
        output_dir = REPO / output_relative
        shutil.rmtree(output_dir, ignore_errors=True)
        doctor = json.loads(DOCTOR_FIXTURE.read_text(encoding="utf-8"))

        try:
            report = build_operator_production_spine_inspection(
                asset_root=ASSET_ROOT,
                output_dir=output_relative,
                doctor_report=doctor,
            )

            self.assertTrue(report["ok"])
            self.assertEqual(report["kind"], "operator_production_spine_inspection_v1")
            self.assertEqual(report["spine_id"], "operator-production-spine-v1")
            self.assertEqual(report["inspection_status"], "ACTIVE_REPAIR_LOOP")
            self.assertFalse(report["ready_for_execution"])
            self.assertTrue(report["read_only"])
            for value in report["safety"].values():
                self.assertFalse(value)

            expected_stages = {
                "asset_scan",
                "production_dashboard",
                "tool_health",
                "adapter_contracts",
                "shot_plan",
                "pressure_test",
                "hardening_plan",
                "works_operation",
                "action_list",
                "knowledge_graph",
                "obsidian_vault",
            }
            self.assertEqual({stage["id"] for stage in report["stage_outputs"]}, expected_stages)

            action_list = json.loads((output_dir / "action_list.json").read_text(encoding="utf-8"))
            self.assertFalse(action_list["execution_authority_granted"])
            self.assertFalse(action_list["approval_or_permit_created"])
            self.assertGreater(action_list["summary"]["total_actions"], 0)
            self.assertEqual(action_list["summary"]["blocked_command_count"], 0)
            action_commands = "\n".join(action["command"] for action in action_list["actions"])
            self.assertNotIn("--approve-local-execution", action_commands)
            self.assertNotIn("houdini-smoke", action_commands)
            self.assertNotIn("comfyui-smoke", action_commands)

            graph = json.loads((output_dir / "knowledge_graph.json").read_text(encoding="utf-8"))
            self.assertEqual(graph["authority"], "derived_index_only")
            self.assertFalse(graph["execution_authority_granted"])
            self.assertFalse(graph["approval_or_permit_created"])
            self.assertGreaterEqual(graph["summary"]["node_count"], len(expected_stages))

            vault_index = output_dir / "obsidian_vault/00_Index.md"
            self.assertTrue(vault_index.exists())
            vault_text = vault_index.read_text(encoding="utf-8")
            self.assertIn('authority: "mirror"', vault_text)
            self.assertIn("schema: \"seos_knowledge_object_v1\"", vault_text)
            self.assertIn("execution_authority_granted: false", vault_text)
            self.assertIn("approval_or_permit_created: false", vault_text)
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertTrue((output_dir / "manifest.md").exists())
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_cli_production_inspect_runs_complete_safe_spine(self) -> None:
        output_relative = Path("work/test_operator_production_spine_v1_cli")
        output_dir = REPO / output_relative
        shutil.rmtree(output_dir, ignore_errors=True)

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "production",
                    "inspect",
                    "--root",
                    ASSET_ROOT.as_posix(),
                    "--doctor-json",
                    DOCTOR_FIXTURE.as_posix(),
                    "--output-dir",
                    output_relative.as_posix(),
                    "--json",
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["kind"], "operator_production_spine_inspection_v1")
            self.assertEqual(payload["outputs"]["manifest_json"], (output_relative / "manifest.json").as_posix())
            self.assertEqual(payload["outputs"]["obsidian_vault"], (output_relative / "obsidian_vault").as_posix())
            self.assertFalse(payload["safety"]["dcc_execution_performed"])
            self.assertFalse(payload["safety"]["cloud_call_performed"])
            self.assertFalse(payload["safety"]["asset_move_performed"])
            self.assertFalse(payload["safety"]["approval_or_permit_created"])
            self.assertFalse(payload["safety"]["execution_authority_granted"])
            self.assertTrue((output_dir / "asset_scan.json").exists())
            self.assertTrue((output_dir / "tool_health.json").exists())
            self.assertTrue((output_dir / "pressure_test.json").exists())
            self.assertTrue((output_dir / "hardening_plan.json").exists())
            self.assertTrue((output_dir / "works_operation.json").exists())
            self.assertTrue((output_dir / "knowledge_graph.json").exists())
            self.assertTrue((output_dir / "obsidian_vault/02_Actions/action_list.md").exists())
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
