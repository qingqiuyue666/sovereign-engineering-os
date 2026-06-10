from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.assets.local_asset_library import build_asset_library_scan
from creative.pressure.real_project import build_real_project_pressure_test

REPO = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO / "tests/fixtures/creative/assets"
TOOL_HEALTH = REPO / "tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json"
ADAPTER_CONTRACTS = REPO / "reports/creative/adapters/optional_adapter_contracts_v1.json"


class RealProjectPressureTestV1Tests(unittest.TestCase):
    def test_fixture_pressure_test_surfaces_real_repairs_without_execution(self) -> None:
        asset_report = build_asset_library_scan(ASSET_ROOT, mode="public", max_depth=12)
        tool_health = json.loads(TOOL_HEALTH.read_text(encoding="utf-8"))
        adapter_contracts = json.loads(ADAPTER_CONTRACTS.read_text(encoding="utf-8"))

        report = build_real_project_pressure_test(
            asset_report,
            template_name="energy-impact",
            shot_id="SHOT_PRESSURE_001",
            tool_health_report=tool_health,
            adapter_contracts_report=adapter_contracts,
        )

        self.assertTrue(report["ok"])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["ready_for_execution"])
        self.assertEqual(report["pressure_status"], "USABLE_WITH_MANUAL_REPAIR")
        self.assertTrue(report["ready_for_manual_shot_planning"])
        self.assertTrue(report["shot_plan_summary"]["complete"])
        finding_codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("ARCHIVE_PART_MISSING", finding_codes)
        self.assertIn("LOCAL_RUNNER_NOT_READY", finding_codes)
        self.assertIn("ADAPTERS_CONTRACT_ONLY", finding_codes)
        searches = {probe["query"]: probe for probe in report["search_probes"]}
        self.assertGreater(searches["houdini-fx-assets"]["result_count"], 0)
        self.assertGreater(searches["vdb-cache-assets"]["result_count"], 0)
        self.assertGreater(searches["incomplete-archives"]["result_count"], 0)
        as_text = json.dumps(report, sort_keys=True)
        self.assertNotIn(REPO.as_posix(), as_text)
        self.assertNotIn("/Users/", as_text)

    def test_empty_asset_root_becomes_blocked_not_fake_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_report = build_asset_library_scan(Path(temp_dir), mode="public", max_depth=12)

            report = build_real_project_pressure_test(
                asset_report,
                template_name="editorial-handoff",
                shot_id="SHOT_EMPTY_PRESSURE",
            )

        self.assertEqual(report["pressure_status"], "BLOCKED_NEEDS_ASSET_OR_TEMPLATE_REPAIR")
        self.assertFalse(report["ready_for_manual_shot_planning"])
        self.assertFalse(report["shot_plan_summary"]["complete"])
        finding_codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("ASSET_SCAN_EMPTY", finding_codes)
        self.assertIn("SHOT_REQUIRED_ASSETS_MISSING", finding_codes)
        checks = {check["id"]: check for check in report["regression_checks"]}
        self.assertFalse(checks["asset_scan_has_assets"]["passed"])
        self.assertFalse(checks["shot_plan_complete"]["passed"])

    def test_cli_writes_pressure_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            output_json = temp_dir / "pressure.json"
            output_md = temp_dir / "pressure.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "pressure-test",
                    "--root",
                    ASSET_ROOT.as_posix(),
                    "--template",
                    "portal-lightning",
                    "--shot-id",
                    "SHOT_PORTAL_PRESSURE",
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
            self.assertEqual(payload["kind"], "real_project_pressure_test_v1")
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SEOS Real Project Pressure Test", markdown)
            self.assertIn("Search Probes", markdown)
            self.assertIn("Regression Checks", markdown)


if __name__ == "__main__":
    unittest.main()
