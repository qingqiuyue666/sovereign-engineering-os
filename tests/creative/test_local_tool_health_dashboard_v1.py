from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.reports.local_tool_health_dashboard import build_local_tool_health_dashboard

REPO = Path(__file__).resolve().parents[2]
DOCTOR_FIXTURE = REPO / "tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json"


class LocalToolHealthDashboardV1Tests(unittest.TestCase):
    def test_dashboard_reports_truthful_tool_status_and_next_actions(self) -> None:
        doctor_report = {
            "schema_version": "seos_creative_pipeline_v3",
            "destructive_actions_performed": False,
            "warnings": ["houdini", "comfyui", "after_effects", "davinci", "unreal"],
            "software": {
                "python": {"status": "FOUND_AND_SMOKE_PASSED", "version": "3.13.0", "path": "/opt/seos/bin/python"},
                "macos": {"status": "FOUND_AND_SMOKE_PASSED", "version": "Darwin-fixture"},
                "apple_silicon": {"status": "FOUND_AND_SMOKE_PASSED"},
                "git": {"status": "FOUND_BUT_UNTESTED", "path": "/opt/tools/git"},
                "ffmpeg": {"status": "NOT_FOUND", "path": ""},
                "houdini": {"status": "NOT_FOUND", "path": ""},
                "comfyui": {"status": "CONFIG_REQUIRED", "path": ""},
                "blender": {"status": "FOUND_BUT_UNTESTED", "path": "/opt/tools/blender"},
                "after_effects": {"status": "CONFIG_REQUIRED", "path": ""},
                "davinci": {"status": "CONFIG_REQUIRED", "path": ""},
                "unreal": {"status": "CONFIG_REQUIRED", "path": ""},
                "zbrush": {"status": "FOUND_BUT_REQUIRES_USER_LAUNCH", "path": ""},
            },
        }

        dashboard = build_local_tool_health_dashboard(
            doctor_report,
            mode="public",
            dependency_names=("json", "seos_missing_dependency_fixture"),
        )

        self.assertTrue(dashboard["ok"])
        self.assertTrue(dashboard["read_only"])
        self.assertFalse(dashboard["dcc_or_ai_tools_launched"])
        self.assertEqual(dashboard["proprietary_tools_required_for_default_ci"], [])
        rows = {row["tool"]: row for row in dashboard["tool_health"]}
        self.assertEqual(rows["python"]["configured_path"], "<local-path:python>")
        self.assertEqual(rows["python_dependencies"]["status"], "CONFIG_REQUIRED")
        self.assertEqual(rows["python_dependencies"]["smoke_capability"], "NOT_RUN_CONFIG_REQUIRED")
        self.assertEqual(rows["houdini"]["status"], "NOT_FOUND")
        self.assertEqual(rows["comfyui"]["next_fix_action"], "Configure ComfyUI path or service settings before running ComfyUI jobs.")
        self.assertEqual(rows["blender"]["configured_path"], "<local-path:blender>")
        self.assertEqual(rows["blender"]["smoke_capability"], "PATH_DETECTED_NO_SMOKE_RUN")
        self.assertGreaterEqual(dashboard["summary"]["config_required_count"], 4)
        self.assertGreaterEqual(dashboard["summary"]["missing_count"], 2)
        self.assertTrue(any("Houdini" in action for action in dashboard["next_actions"]))

    def test_cli_writes_public_tool_health_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "outputs"
            output_dir.mkdir()
            output_json = output_dir / "tool_health.json"
            output_md = output_dir / "tool_health.md"
            output_html = output_dir / "tool_health.html"

            result = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "tool-health-dashboard",
                    "--mode",
                    "public",
                    "--doctor-json",
                    DOCTOR_FIXTURE.as_posix(),
                    "--output-json",
                    output_json.as_posix(),
                    "--output-md",
                    output_md.as_posix(),
                    "--output-html",
                    output_html.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            self.assertTrue(output_html.exists())
            report_json = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")
            html = output_html.read_text(encoding="utf-8")
            self.assertEqual(report_json["kind"], "local_tool_health_dashboard_v1")
            self.assertEqual(report_json["summary"]["tool_count"], 13)
            self.assertIn("SEOS Local Tool Health Dashboard", markdown)
            self.assertIn("Houdini / hython", markdown)
            self.assertIn("<local-path:Blender.app>", markdown)
            self.assertIn("3.1-fixture", markdown)
            self.assertIn("Default CI does not require Houdini", markdown)
            self.assertIn("<!doctype html>", html)
            self.assertNotIn(REPO.as_posix(), output_json.read_text(encoding="utf-8"))
            self.assertNotIn(REPO.as_posix(), markdown)
            self.assertNotIn(REPO.as_posix(), html)

    def test_cli_can_report_live_local_doctor_without_report_files(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "seos.py",
                "creative",
                "tool-health-dashboard",
                "--mode",
                "public",
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["kind"], "local_tool_health_dashboard_v1")
        self.assertGreaterEqual(len(payload["tool_health"]), 10)


if __name__ == "__main__":
    unittest.main()
