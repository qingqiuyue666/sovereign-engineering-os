from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.hardening.production import build_production_hardening_plan

REPO = Path(__file__).resolve().parents[2]
PRESSURE_REPORT = REPO / "reports/creative/pressure/real_project_pressure_test_v1.json"


class ProductionHardeningV1Tests(unittest.TestCase):
    def test_hardening_plan_turns_pressure_findings_into_actions_and_package_manifest(self) -> None:
        pressure = json.loads(PRESSURE_REPORT.read_text(encoding="utf-8"))

        report = build_production_hardening_plan(pressure, root=REPO)

        self.assertTrue(report["ok"])
        self.assertTrue(report["read_only"])
        self.assertTrue(report["output_package_manifest_only"])
        self.assertFalse(report["execution_performed"])
        self.assertEqual(report["hardening_status"], "NEEDS_REPAIR_BEFORE_EXECUTION")
        self.assertEqual(report["package_summary"]["package_status"], "READY_FOR_HANDOFF")
        self.assertEqual(report["package_summary"]["missing_count"], 0)
        self.assertEqual(report["package_summary"]["local_path_leak_count"], 0)
        self.assertGreaterEqual(report["package_summary"]["artifact_count"], 10)
        action_codes = {action["source_finding_code"] for action in report["repair_actions"]}
        self.assertIn("ARCHIVE_PART_MISSING", action_codes)
        self.assertIn("LOCAL_RUNNER_NOT_READY", action_codes)
        priorities = {action["priority"] for action in report["repair_actions"]}
        self.assertIn("P1", priorities)
        self.assertTrue(all(artifact["exists"] for artifact in report["package_manifest"]))
        as_text = json.dumps(report, sort_keys=True)
        self.assertNotIn(REPO.as_posix(), as_text)
        self.assertNotIn("/Users/", as_text)

    def test_package_manifest_blocks_local_path_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            leak_file = temp_dir / "leaky.md"
            leak_file.write_text("bad local path /Users/example/private.mov\n", encoding="utf-8")
            pressure = {
                "kind": "real_project_pressure_test_v1",
                "findings": [],
                "outputs": {},
                "pressure_status": "READY_FOR_MANUAL_SHOT_PLANNING",
            }

            report = build_production_hardening_plan(
                pressure,
                package_paths=[leak_file.as_posix()],
                root=REPO,
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["hardening_status"], "BLOCKED_NEEDS_PACKAGE_REPAIR")
        self.assertEqual(report["package_summary"]["package_status"], "LOCAL_PATH_LEAK_BLOCKED")
        self.assertEqual(report["package_summary"]["local_path_leak_count"], 1)

    def test_cli_writes_hardening_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            output_json = temp_dir / "hardening.json"
            output_md = temp_dir / "hardening.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "hardening-plan",
                    "--pressure-json",
                    PRESSURE_REPORT.as_posix(),
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
            self.assertEqual(payload["kind"], "production_hardening_plan_v1")
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SEOS Production Hardening Plan", markdown)
            self.assertIn("Repair Actions", markdown)
            self.assertIn("Package Manifest", markdown)


if __name__ == "__main__":
    unittest.main()
