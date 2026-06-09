"""Behavior tests for production dogfood fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.production_dogfood import run_production_dogfood_fixture

REPO_ROOT = Path(__file__).resolve().parents[2]


class ProductionDogfoodFixturesV1Tests(unittest.TestCase):
    def test_cli_runs_fixture_through_project_shot_package_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "dogfood",
                    "run",
                    "examples/dogfood/production_shot_fixture_v1.json",
                    "--runtime-root",
                    (root / "runtime").as_posix(),
                    "--package-root",
                    (root / "packages").as_posix(),
                    "--output-root",
                    (root / "dogfood_runs").as_posix(),
                    "--review-root",
                    (root / "review").as_posix(),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            self.assertTrue(payload["ok"])
            receipt = json.loads(Path(payload["receipt_path"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
            artifact_manifest = json.loads(Path(receipt["artifact_manifest_path"]).read_text(encoding="utf-8"))
            run_package = json.loads(Path(manifest["run_package_manifest_path"]).read_text(encoding="utf-8"))
            shot_package = json.loads(Path(manifest["shot_package_manifest_path"]).read_text(encoding="utf-8"))
            ledger_lines = Path(receipt["state_ledger_path"]).read_text(encoding="utf-8").splitlines()
            ledger_steps = {json.loads(line)["step"] for line in ledger_lines}

            self.assertEqual(receipt["terminal_status"], "TERMINAL_SUCCEEDED")
            self.assertEqual(receipt["mocked_ci_path"]["adapter"], "fake_dcc")
            self.assertEqual(manifest["fixture_id"], "production_shot_dogfood_v1")
            self.assertEqual(run_package["copy_policy"], "artifact_refs_only")
            self.assertEqual(shot_package["package_kind"], "shot")
            self.assertTrue(Path(manifest["asset_registry_path"]).exists())
            self.assertTrue(Path(manifest["workflow_receipt_path"]).exists())
            self.assertTrue(Path(manifest["review_artifact_path"]).exists())
            self.assertGreaterEqual(len(artifact_manifest["receipt_refs"]), 4)
            self.assertIn("text/plain", {ref["media_type"] for ref in manifest["artifact_refs"]})
            self.assertIn("application/json", {ref["media_type"] for ref in manifest["artifact_refs"]})
            self.assertTrue(
                {
                    "fixture_loaded",
                    "asset_scan_created",
                    "shot_run_completed",
                    "run_packaged",
                    "shot_packaged",
                    "review_artifact_created",
                    "dogfood_manifest_written",
                }.issubset(ledger_steps)
            )

    def test_missing_workflow_writes_failure_bundle_and_failed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            asset_root = root / "assets"
            asset_root.mkdir()
            (asset_root / "plate.txt").write_text("plate\n", encoding="utf-8")
            fixture = root / "broken_fixture.json"
            write_json(
                fixture,
                {
                    "asset_root": asset_root.as_posix(),
                    "fixture_id": "broken_dogfood_fixture",
                    "project_name": "Broken Dogfood",
                    "schema_version": "seos.production_dogfood_fixture.v1",
                    "shot_name": "broken_shot",
                    "workflow_path": (root / "missing_workflow.json").as_posix(),
                },
            )
            payload = run_production_dogfood_fixture(
                fixture,
                runtime_root=root / "runtime",
                package_root=root / "packages",
                output_root=root / "dogfood_runs",
                review_root=root / "review",
            )
            receipt = json.loads(Path(payload["receipt_path"]).read_text(encoding="utf-8"))
            failure_bundle = json.loads(Path(payload["failure_bundle_path"]).read_text(encoding="utf-8"))
            ledger_exists = Path(receipt["state_ledger_path"]).exists()

            self.assertFalse(payload["ok"])
            self.assertEqual(receipt["terminal_status"], "TERMINAL_FAILED")
            self.assertEqual(failure_bundle["failure_code"], "FileNotFoundError")
            self.assertIn("workflow_missing", failure_bundle["failure_summary"])
            self.assertTrue(ledger_exists)


if __name__ == "__main__":
    unittest.main()
