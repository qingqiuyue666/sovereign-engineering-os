from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.operation.real_works import build_real_works_operation_report

REPO = Path(__file__).resolve().parents[2]
ASSET_REPORT = REPO / "reports/creative/assets/asset_library_report_v1.json"
TOOL_HEALTH = REPO / "tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json"
ADAPTER_CONTRACTS = REPO / "reports/creative/adapters/optional_adapter_contracts_v1.json"
PRESSURE_REPORT = REPO / "reports/creative/pressure/real_project_pressure_test_v1.json"
HARDENING_PLAN = REPO / "reports/creative/hardening/production_hardening_plan_v1.json"


class RealWorksOperationV1Tests(unittest.TestCase):
    def test_operation_report_covers_repeated_workflows_and_real_needs(self) -> None:
        asset_report = json.loads(ASSET_REPORT.read_text(encoding="utf-8"))
        tool_health = json.loads(TOOL_HEALTH.read_text(encoding="utf-8"))
        adapter_contracts = json.loads(ADAPTER_CONTRACTS.read_text(encoding="utf-8"))
        pressure = json.loads(PRESSURE_REPORT.read_text(encoding="utf-8"))
        hardening = json.loads(HARDENING_PLAN.read_text(encoding="utf-8"))

        report = build_real_works_operation_report(
            asset_report,
            tool_health_report=tool_health,
            adapter_contracts_report=adapter_contracts,
            pressure_report=pressure,
            hardening_plan=hardening,
        )

        self.assertTrue(report["ok"])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["execution_performed"])
        self.assertEqual(report["operation_status"], "ACTIVE_REPAIR_LOOP")
        self.assertEqual(report["pressure_status"], "USABLE_WITH_MANUAL_REPAIR")
        self.assertEqual(report["hardening_status"], "NEEDS_REPAIR_BEFORE_EXECUTION")
        self.assertEqual(report["repeatability_summary"]["workflow_count"], 5)
        self.assertEqual(report["repeatability_summary"]["complete_workflow_count"], 5)
        self.assertEqual(report["repeatability_summary"]["blocked_workflow_count"], 0)
        self.assertGreaterEqual(report["repeatability_summary"]["nonready_optional_runner_count"], 2)
        workflow_ids = {workflow["id"] for workflow in report["workflows"]}
        self.assertEqual(workflow_ids, {"energy_impact", "smoke_dust", "portal_lightning", "asset_library", "editorial_handoff"})
        needs = {need["source"] for need in report["development_needs"]}
        self.assertIn("ARCHIVE_PART_MISSING", needs)
        self.assertIn("LOCAL_RUNNER_NOT_READY", needs)
        as_text = json.dumps(report, sort_keys=True)
        self.assertNotIn(REPO.as_posix(), as_text)
        self.assertNotIn("/Users/", as_text)

    def test_empty_assets_keep_operation_in_repair_loop(self) -> None:
        report = build_real_works_operation_report({"kind": "empty", "assets": [], "summary": {"total_assets": 0}})

        self.assertEqual(report["operation_status"], "ACTIVE_REPAIR_LOOP")
        self.assertEqual(report["repeatability_summary"]["blocked_workflow_count"], 5)
        self.assertTrue(all(workflow["status"] == "BLOCKED_MISSING_REQUIRED_ASSETS" for workflow in report["workflows"]))
        needs = {need["source"] for need in report["development_needs"]}
        self.assertIn("workflow_blocker", needs)

    def test_cli_writes_operation_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            output_json = temp_dir / "operation.json"
            output_md = temp_dir / "operation.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "works-operation",
                    "--registry-json",
                    ASSET_REPORT.as_posix(),
                    "--tool-health-json",
                    TOOL_HEALTH.as_posix(),
                    "--adapter-contracts-json",
                    ADAPTER_CONTRACTS.as_posix(),
                    "--pressure-json",
                    PRESSURE_REPORT.as_posix(),
                    "--hardening-json",
                    HARDENING_PLAN.as_posix(),
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
            self.assertEqual(payload["kind"], "real_works_operation_v1")
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SEOS Real Works Operation", markdown)
            self.assertIn("Development Needs", markdown)
            self.assertIn("Operation Loop", markdown)


if __name__ == "__main__":
    unittest.main()
