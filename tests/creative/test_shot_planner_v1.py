from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.shots.shot_planner import build_shot_plan, list_shot_templates

REPO = Path(__file__).resolve().parents[2]
ASSET_REPORT = REPO / "reports/creative/assets/asset_library_report_v1.json"
TOOL_HEALTH = REPO / "tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json"
ADAPTER_CONTRACTS = REPO / "reports/creative/adapters/optional_adapter_contracts_v1.json"


class ShotPlannerV1Tests(unittest.TestCase):
    def test_templates_include_practical_vfx_and_editorial_plans(self) -> None:
        templates = list_shot_templates()
        names = [item["template"] for item in templates["templates"]]

        self.assertTrue(templates["ok"])
        self.assertIn("energy_impact", names)
        self.assertIn("smoke_dust", names)
        self.assertIn("portal_lightning", names)
        self.assertIn("editorial_handoff", names)

    def test_energy_impact_plan_binds_fixture_assets_and_runner_steps(self) -> None:
        asset_report = json.loads(ASSET_REPORT.read_text(encoding="utf-8"))
        tool_health = json.loads(TOOL_HEALTH.read_text(encoding="utf-8"))
        adapter_contracts = json.loads(ADAPTER_CONTRACTS.read_text(encoding="utf-8"))

        plan = build_shot_plan(
            asset_report,
            template_name="energy-impact",
            shot_id="SHOT_ENERGY_001",
            tool_health_report=tool_health,
            adapter_contracts_report=adapter_contracts,
        )

        self.assertTrue(plan["ok"])
        self.assertTrue(plan["complete"])
        self.assertEqual(plan["summary"]["missing_required_count"], 0)
        self.assertEqual(plan["summary"]["template"], "energy_impact")
        self.assertGreaterEqual(plan["summary"]["total_candidate_count"], 6)
        runner_ids = [step["runner_id"] for step in plan["execution_plan"]["optional_runner_steps"]]
        self.assertEqual(runner_ids, ["houdini_hython_smoke", "comfyui_workflow_smoke"])
        self.assertIn("Create the shot workspace", " ".join(plan["next_actions"]))

    def test_missing_assets_are_reported_without_success_claim(self) -> None:
        plan = build_shot_plan(
            {"kind": "empty_asset_report", "assets": []},
            template_name="editorial-handoff",
            shot_id="editorial demo",
        )

        self.assertFalse(plan["complete"])
        self.assertEqual(plan["summary"]["missing_required_count"], 4)
        self.assertTrue(all(item["status"] == "MISSING" for item in plan["required_assets"]))
        self.assertTrue(plan["shot_id"].startswith("SHOT_"))

    def test_cli_writes_json_and_markdown_shot_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            output_json = temp_dir / "shot_plan.json"
            output_md = temp_dir / "shot_plan.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "shot",
                    "plan",
                    "--template",
                    "portal-lightning",
                    "--shot-id",
                    "SHOT_PORTAL_001",
                    "--registry-json",
                    ASSET_REPORT.as_posix(),
                    "--tool-health-json",
                    TOOL_HEALTH.as_posix(),
                    "--adapter-contracts-json",
                    ADAPTER_CONTRACTS.as_posix(),
                    "--output-json",
                    output_json.as_posix(),
                    "--output-md",
                    output_md.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["kind"], "shot_plan_v1")
            self.assertTrue(payload["complete"])
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SEOS Shot Plan", markdown)
            self.assertIn("Optional Runner Steps", markdown)

    def test_cli_lists_templates(self) -> None:
        completed = subprocess.run(
            [sys.executable, "seos.py", "creative", "shot", "templates"],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["kind"], "shot_templates_v1")
        self.assertGreaterEqual(len(payload["templates"]), 4)


if __name__ == "__main__":
    unittest.main()
