"""Behavior tests for patch repair job infrastructure."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.repair.classifier import classify_repairable_failure
from execution_plane.repair.local_model_bridge import invoke_local_patch_tool
from execution_plane.repair.patch_apply import apply_patch_for_job
from execution_plane.repair.repair_ledger import read_repair_ledger
from execution_plane.repair.writer import create_patch_repair_job


class PatchRepairJobsV1Tests(unittest.TestCase):
    def test_classifier_identifies_traceback_schema_failure_as_repairable(self) -> None:
        classification = classify_repairable_failure(_bundle())
        self.assertTrue(classification["repairable"])
        self.assertEqual(classification["failure_code"], "SCHEMA_INVALID")
        self.assertIn("execution_plane/adapters/comfyui_local.py", classification["target_files"])

    def test_writer_creates_patch_repair_job_and_ledger_event(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            bundle_path = root / "failure_bundle.json"
            write_json(bundle_path, _bundle())
            created = create_patch_repair_job(bundle_path, output_root=root / "repair_jobs")
            job = json.loads(Path(created["job_path"]).read_text(encoding="utf-8"))
            ledger = read_repair_ledger(root / "repair_jobs")

        self.assertTrue(created["ok"])
        self.assertEqual(job["schema_version"], "seos.patch_repair_job.v1")
        self.assertEqual(job["status"], "READY")
        self.assertEqual(ledger[0]["event"], "PATCH_REPAIR_JOB_CREATED")

    def test_local_tool_bridge_invokes_injected_command_and_writes_result(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            bundle_path = root / "failure_bundle.json"
            write_json(bundle_path, _bundle())
            created = create_patch_repair_job(bundle_path, output_root=root / "repair_jobs")
            invoked = invoke_local_patch_tool(
                created["job_path"],
                output_root=root / "repair_jobs",
                tool_command=[sys.executable, "-c", "print('patch candidate generated')"],
            )
            result = json.loads(Path(invoked["result_path"]).read_text(encoding="utf-8"))

        self.assertTrue(invoked["ok"])
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("patch candidate generated", result["stdout"])

    def test_unavailable_local_tool_writes_repair_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            bundle_path = root / "failure_bundle.json"
            write_json(bundle_path, {**_bundle(), "patch_repair_policy": {"allowed_tools": ["seos_missing_tool"], "auto_apply": False}})
            created = create_patch_repair_job(bundle_path, output_root=root / "repair_jobs")
            invoked = invoke_local_patch_tool(created["job_path"], output_root=root / "repair_jobs")
            failure = json.loads(Path(invoked["failure_bundle_path"]).read_text(encoding="utf-8"))

        self.assertFalse(invoked["ok"])
        self.assertEqual(failure["failure_code"], "LOCAL_TOOL_UNAVAILABLE")

    def test_apply_handler_is_policy_blocked_when_auto_apply_false(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            bundle_path = root / "failure_bundle.json"
            patch_path = root / "candidate.patch"
            patch_path.write_text("", encoding="utf-8")
            write_json(bundle_path, _bundle())
            created = create_patch_repair_job(bundle_path, output_root=root / "repair_jobs")
            applied = apply_patch_for_job(created["job_path"], patch_path, repo_root=root, output_root=root / "repair_jobs")
            receipt = json.loads(Path(applied["receipt_path"]).read_text(encoding="utf-8"))

        self.assertFalse(applied["ok"])
        self.assertEqual(receipt["failure_code"], "AUTO_APPLY_DISABLED")


def _bundle() -> dict[str, object]:
    return {
        "schema_version": "seos.failure_bundle.v1",
        "failure_code": "SCHEMA_INVALID",
        "failure_summary": "SCHEMA_INVALID: workflow_node_inputs_required:12",
        "log_excerpt": "Traceback (most recent call last):\n  File \"execution_plane/adapters/comfyui_local.py\", line 1",
        "schema_validation_stack": ["validate_comfyui_workflow", "workflow_node_inputs_required"],
        "adapter_module_path": "execution_plane/adapters/comfyui_local.py",
        "target_files": ["execution_plane/adapters/comfyui_local.py"],
        "reproduction_command": "python3 seos.py rpc invoke examples/rpc/comfyui_submit_workflow.json --json",
        "test_commands": ["python3 -m unittest tests.tracer_bullet.test_comfyui_real_execution_v1 -v"],
        "patch_repair_policy": {
            "allowed_tools": ["cline", "aider"],
            "mode": "generate_patch_then_test",
            "auto_apply": False,
            "max_iterations": 2,
        },
    }


if __name__ == "__main__":
    unittest.main()
