from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.assets.local_asset_library import build_asset_library_scan, write_asset_library_outputs
from creative.reports.local_production_dashboard import build_local_production_dashboard

REPO = Path(__file__).resolve().parents[2]


class LocalProductionDashboardV1Tests(unittest.TestCase):
    def test_dashboard_summarizes_scan_risks_and_next_actions(self) -> None:
        scan = build_asset_library_scan(REPO / "tests/fixtures/creative/assets", mode="public", max_depth=12)
        dashboard = build_local_production_dashboard(scan)

        self.assertTrue(dashboard["ok"])
        self.assertTrue(dashboard["read_only"])
        self.assertGreaterEqual(dashboard["summary"]["total_assets"], 20)
        self.assertGreaterEqual(len(dashboard["largest_directories"]), 1)
        self.assertGreaterEqual(len(dashboard["duplicate_groups"]), 1)
        self.assertGreaterEqual(len(dashboard["archive_warnings"]), 1)
        self.assertGreaterEqual(len(dashboard["empty_directories"]), 1)
        self.assertTrue(dashboard["recommended_cleanup_actions"])
        readiness = {row["tool"]: row for row in dashboard["production_readiness_by_tool_category"]}
        self.assertEqual(readiness["houdini"]["status"], "ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED")
        self.assertEqual(readiness["comfyui"]["status"], "ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED")

    def test_cli_writes_markdown_and_html_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "outputs"
            output_dir.mkdir()
            scan = build_asset_library_scan(REPO / "tests/fixtures/creative/assets", mode="public", max_depth=12)
            registry_json = output_dir / "asset_library.json"
            output_md = output_dir / "dashboard.md"
            output_html = output_dir / "dashboard.html"
            write_asset_library_outputs(scan, root=REPO / "tests/fixtures/creative/assets", output_json=registry_json)

            result = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "production-dashboard",
                    "--registry-json",
                    registry_json.as_posix(),
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
            self.assertTrue(output_md.exists())
            self.assertTrue(output_html.exists())
            markdown = output_md.read_text(encoding="utf-8")
            html = output_html.read_text(encoding="utf-8")
            self.assertIn("SEOS Local Production Dashboard", markdown)
            self.assertIn("Production Readiness By Tool Category", markdown)
            self.assertIn("Archive Warnings", markdown)
            self.assertIn("Duplicate Groups", markdown)
            self.assertIn("<!doctype html>", html)
            self.assertNotIn(REPO.as_posix(), markdown)
            self.assertNotIn(REPO.as_posix(), html)


if __name__ == "__main__":
    unittest.main()
