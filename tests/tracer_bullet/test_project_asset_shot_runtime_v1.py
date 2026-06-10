"""Behavior tests for project, asset, and shot runtime."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.production_runtime import ProductionRuntime


class ProjectAssetShotRuntimeV1Tests(unittest.TestCase):
    def test_project_create_and_asset_scan_write_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            asset_root = root / "assets"
            asset_root.mkdir()
            (asset_root / "plate.txt").write_text("plate", encoding="utf-8")
            runtime = ProductionRuntime(root / "runtime")
            project = runtime.create_project("demo")["project"]
            scan = runtime.scan_assets(asset_root, project_id=project["project_id"])
            registry = json.loads(Path(scan["registry_path"]).read_text(encoding="utf-8"))

        self.assertEqual(registry["asset_count"], 1)
        self.assertEqual(registry["project_id"], project["project_id"])
        self.assertEqual(registry["assets"][0]["relative_path"], "plate.txt")
        self.assertTrue(registry["assets"][0]["sha256"].startswith("sha256:"))

    def test_shot_create_references_latest_assets_and_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            asset_root = root / "assets"
            asset_root.mkdir()
            (asset_root / "plate.txt").write_text("plate", encoding="utf-8")
            workflow_path = _fake_workflow(root)
            runtime = ProductionRuntime(root / "runtime")
            project = runtime.create_project("demo")["project"]
            runtime.scan_assets(asset_root, project_id=project["project_id"])
            shot = runtime.create_shot(project["project_id"], "shot_001")["shot"]
            attached = runtime.attach_workflow(shot["shot_id"], workflow_path.as_posix())

        self.assertEqual(len(shot["asset_refs"]), 1)
        self.assertEqual(attached["workflow"]["workflow_id"], "fake_shot_workflow")

    def test_shot_run_executes_workflow_and_attaches_receipt_to_shot(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            workflow_path = _fake_workflow(root)
            runtime = ProductionRuntime(root / "runtime")
            project = runtime.create_project("demo")["project"]
            shot = runtime.create_shot(project["project_id"], "shot_001")["shot"]
            runtime.attach_workflow(shot["shot_id"], workflow_path.as_posix())
            run = runtime.run_shot(shot["shot_id"])
            receipt = json.loads(Path(run["run_path"]).read_text(encoding="utf-8"))
            shot_record = json.loads((root / "runtime" / "shots" / shot["shot_id"] / "shot.json").read_text(encoding="utf-8"))

        self.assertTrue(run["ok"])
        self.assertEqual(receipt["terminal_status"], "TERMINAL_SUCCEEDED")
        self.assertEqual(receipt["project_id"], project["project_id"])
        self.assertIn("text/plain", {ref["media_type"] for ref in receipt["artifact_refs"]})
        self.assertEqual(shot_record["runs"][0]["run_id"], receipt["run_id"])
        self.assertEqual(shot_record["versions"][0]["run_id"], receipt["run_id"])

    def test_missing_workflow_blocks_shot_run_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            runtime = ProductionRuntime(Path(tempdir) / "runtime")
            project = runtime.create_project("demo")["project"]
            shot = runtime.create_shot(project["project_id"], "shot_001")["shot"]
            with self.assertRaises(ValueError):
                runtime.run_shot(shot["shot_id"])


def _fake_workflow(root: Path) -> Path:
    path = root / "fake_workflow.json"
    write_json(
        path,
        {
            "schema_version": "seos.cross_software_workflow.v1",
            "workflow_id": "fake_shot_workflow",
            "nodes": [
                {
                    "node_id": "fake_output",
                    "adapter": "fake_dcc",
                    "action": "smoke_generate_file",
                    "payload": {"output_path": "shot_output.txt", "content": "shot output\n"},
                }
            ],
        },
    )
    return path


if __name__ == "__main__":
    unittest.main()
