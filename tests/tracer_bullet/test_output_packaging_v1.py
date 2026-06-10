"""Behavior tests for run and shot packaging."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.packaging import package_run, package_shot
from execution_plane.production_runtime import ProductionRuntime


class OutputPackagingV1Tests(unittest.TestCase):
    def test_package_run_writes_manifest_receipts_and_artifact_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, shot_id, run_id = _runtime_with_run(root)
            packaged = package_run(run_id, runtime_root=runtime.root, package_root=root / "packages")
            manifest = json.loads(Path(packaged["package_path"]).read_text(encoding="utf-8"))
            package_dir = Path(packaged["package_path"]).parent
            shot_receipt_exists = (package_dir / "shot_run_receipt.json").exists()
            workflow_receipt_exists = (package_dir / "workflow_receipt.json").exists()
            artifact_refs_exists = (package_dir / "artifact_refs.json").exists()

        self.assertTrue(shot_receipt_exists)
        self.assertTrue(workflow_receipt_exists)
        self.assertTrue(artifact_refs_exists)
        self.assertEqual(manifest["copy_policy"], "artifact_refs_only")
        self.assertEqual(manifest["shot_id"], shot_id)
        self.assertIn("text/plain", {ref["media_type"] for ref in manifest["artifact_refs"]})

    def test_package_shot_aggregates_run_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, shot_id, run_id = _runtime_with_run(root)
            packaged = package_shot(shot_id, runtime_root=runtime.root, package_root=root / "packages")
            manifest = json.loads(Path(packaged["package_path"]).read_text(encoding="utf-8"))

        self.assertEqual(manifest["run_count"], 1)
        self.assertEqual(manifest["runs"][0]["run_id"], run_id)
        self.assertEqual(manifest["package_kind"], "shot")
        self.assertGreaterEqual(len(manifest["artifact_refs"]), 1)


def _runtime_with_run(root: Path) -> tuple[ProductionRuntime, str, str]:
    workflow_path = root / "fake_workflow.json"
    write_json(
        workflow_path,
        {
            "schema_version": "seos.cross_software_workflow.v1",
            "workflow_id": "fake_package_workflow",
            "nodes": [
                {
                    "node_id": "fake_output",
                    "adapter": "fake_dcc",
                    "action": "smoke_generate_file",
                    "payload": {"output_path": "package_output.txt", "content": "package output\n"},
                }
            ],
        },
    )
    runtime = ProductionRuntime(root / "runtime")
    project = runtime.create_project("demo")["project"]
    shot = runtime.create_shot(project["project_id"], "shot_001")["shot"]
    runtime.attach_workflow(shot["shot_id"], workflow_path.as_posix())
    run = runtime.run_shot(shot["shot_id"])["run"]
    return runtime, shot["shot_id"], run["run_id"]


if __name__ == "__main__":
    unittest.main()
