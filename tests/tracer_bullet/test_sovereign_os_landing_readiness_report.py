"""Tests for the landing readiness report generator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.generate_sovereign_os_landing_readiness_report import generate_report


class SovereignOsLandingReadinessReportTests(unittest.TestCase):
    def test_generator_runs_deterministically_with_stable_json_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = generate_report(repo_root=Path.cwd(), output_dir=Path(tmp) / "report")
            second = generate_report(repo_root=Path.cwd(), output_dir=Path(tmp) / "report")
            self.assertEqual(first, second)
            expected_keys = {
                "artifact_store_status",
                "built_in_worker_status",
                "current_git_commit",
                "desktop_smoke_status",
                "final_claim_allowed",
                "hfx_008_dry_run_landing_status",
                "hfx_pipeline_scaffolding_status",
                "human_review_gate_status",
                "local_runtime_status",
                "next_real_run_command_list",
                "os_core_v2_v3_status",
                "real_files_referenced",
                "remaining_blockers",
                "resource_warning_status",
                "sqlite_wal_status",
            }
            self.assertEqual(set(first), expected_keys)
            loaded = json.loads((Path(tmp) / "report" / "landing_readiness.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded, first)

    def test_report_preserves_final_claim_boundary_and_references_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = generate_report(repo_root=Path.cwd(), output_dir=Path(tmp) / "report")
            self.assertFalse(report["final_claim_allowed"])
            self.assertNotIn("final production completion", json.dumps(report).lower())
            for relative in report["real_files_referenced"]:
                self.assertTrue((Path.cwd() / relative).is_file())
            generated_files = list((Path(tmp) / "report").iterdir())
            self.assertEqual({item.name for item in generated_files}, {"README.md", "landing_readiness.json"})
            self.assertFalse(any(item.suffix.lower() in {".hip", ".exr", ".mov", ".mp4", ".vdb"} for item in generated_files))

    def test_generator_uses_no_external_network_surface(self) -> None:
        source = Path("tools/generate_sovereign_os_landing_readiness_report.py").read_text(encoding="utf-8")
        self.assertNotIn("requests.", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
