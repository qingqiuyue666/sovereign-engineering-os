"""Behavior tests for the local operator dashboard."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.operator_dashboard.build import build_dashboard
from creative.common import write_json


class LocalOperatorDashboardV1Tests(unittest.TestCase):
    def test_dashboard_builds_html_and_state_from_runtime_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime_root = root / "runtime"
            package_root = root / "packages"
            repair_root = root / "repair"
            write_json(
                runtime_root / "production_state.json",
                {
                    "projects": {"PROJ": {}},
                    "shots": {"SHOT": {"runs": [{"run_id": "RUN", "terminal_status": "TERMINAL_FAILED"}]}},
                    "asset_scans": {"SCAN": {}},
                },
            )
            write_json(package_root / "runs" / "RUN" / "manifest.json", {"package_kind": "run", "run_id": "RUN"})
            repair_root.mkdir()
            (repair_root / "repair_ledger.jsonl").write_text('{"event":"PATCH_REPAIR_JOB_CREATED"}\n', encoding="utf-8")
            built = build_dashboard(runtime_root=runtime_root, package_root=package_root, repair_root=repair_root, output_root=root / "dashboard")
            state = json.loads(Path(built["state_path"]).read_text(encoding="utf-8"))
            html = Path(built["dashboard_path"]).read_text(encoding="utf-8")

        self.assertEqual(state["project_count"], 1)
        self.assertEqual(state["package_count"], 1)
        self.assertIn("TERMINAL_FAILED", html)
        self.assertIn("SEOS Operator Dashboard", html)


if __name__ == "__main__":
    unittest.main()
