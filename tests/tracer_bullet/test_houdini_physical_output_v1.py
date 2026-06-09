"""Behavior tests for the Houdini physical output adapter."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from execution_plane.adapters.houdini_hython import run_houdini_hython_smoke
from execution_plane.permits.builder import create_execution_permit
from execution_plane.runner.result_envelope import sha256_file


class HoudiniPhysicalOutputV1Tests(unittest.TestCase):
    def test_missing_hython_writes_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "missing"
            with mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value=None):
                result = run_houdini_hython_smoke(_permit(output_root, "smoke_cache_test"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
            receipt_exists = (output_root / "execution_receipt.json").exists()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(bundle["failure_code"], "ENV_NOT_FOUND")
        self.assertTrue(receipt_exists)

    def test_timeout_writes_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "timeout"
            timeout = subprocess.TimeoutExpired(cmd=["hython"], timeout=1, output="partial", stderr="late")
            with (
                mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value="/mock/hython"),
                mock.patch("execution_plane.adapters.houdini_hython.subprocess.run", side_effect=timeout),
            ):
                result = run_houdini_hython_smoke(_permit(output_root, "smoke_cache_test"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "TIMED_OUT")
        self.assertIn("TIMEOUT", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "TIMEOUT")

    def test_nonzero_hython_exit_writes_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "nonzero"
            completed = subprocess.CompletedProcess(args=["hython"], returncode=42, stdout="out", stderr="boom")
            with (
                mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value="/mock/hython"),
                mock.patch("execution_plane.adapters.houdini_hython.subprocess.run", return_value=completed),
            ):
                result = run_houdini_hython_smoke(_permit(output_root, "smoke_cache_test"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("NONZERO_EXIT", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "NONZERO_EXIT")

    def test_mock_successful_output_files_generate_refs_receipt_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "success"

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                root = Path(command[command.index("--output-root") + 1])
                root.mkdir(parents=True, exist_ok=True)
                (root / "smoke_cache_metadata.json").write_text(
                    json.dumps(
                        {
                            "schema_version": "seos.houdini.smoke_cache_metadata.v1",
                            "cache_limitation": {"code": "HOUDINI_API_UNAVAILABLE"},
                        },
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (root / "smoke_cache_execution.log").write_text("ok\n", encoding="utf-8")
                (root / "smoke_cache.bgeo.sc").write_bytes(b"BGEO")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="done", stderr="")

            with (
                mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value="/mock/hython"),
                mock.patch("execution_plane.adapters.houdini_hython.subprocess.run", side_effect=fake_run),
            ):
                result = run_houdini_hython_smoke(_permit(output_root, "smoke_cache_test"))
            receipt = json.loads((output_root / "execution_receipt.json").read_text(encoding="utf-8"))
            metadata_hash = sha256_file(output_root / "smoke_cache_metadata.json")
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertTrue(result["artifact_refs"])
        self.assertEqual(receipt["status"], "SUCCEEDED")
        output_record = next(item for item in result["outputs"] if item["relative_path"] == "smoke_cache_metadata.json")
        self.assertEqual(output_record["sha256"], metadata_hash)

    def test_output_missing_is_classified_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "missing-output"
            completed = subprocess.CompletedProcess(args=["hython"], returncode=0, stdout="", stderr="")
            with (
                mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value="/mock/hython"),
                mock.patch("execution_plane.adapters.houdini_hython.subprocess.run", return_value=completed),
            ):
                result = run_houdini_hython_smoke(_permit(output_root, "smoke_cache_test"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("OUTPUT_MISSING", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "OUTPUT_MISSING")

    def test_version_probe_uses_repo_owned_script_command(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "version"
            captured: dict[str, list[str]] = {}

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                captured["command"] = command
                root = Path(command[command.index("--output-root") + 1])
                root.mkdir(parents=True, exist_ok=True)
                (root / "houdini_version_probe.json").write_text("{}\n", encoding="utf-8")
                (root / "smoke_cache_execution.log").write_text("version\n", encoding="utf-8")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with (
                mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value="/mock/hython"),
                mock.patch("execution_plane.adapters.houdini_hython.subprocess.run", side_effect=fake_run),
            ):
                result = run_houdini_hython_smoke(_permit(output_root, "version_probe"))
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertIn("execution_plane/adapters/houdini_scripts/smoke_cache_test.py", captured["command"][1])


def _permit(output_root: Path, action: str) -> dict[str, object]:
    return create_execution_permit(
        task_id=f"TASK_HOUDINI_{action.upper()}",
        operator_approval_id=f"RCPT_HOUDINI_{action.upper()}",
        allowed_adapter="houdini_hython",
        allowed_action=action,
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
        max_runtime_seconds=1,
    )


if __name__ == "__main__":
    unittest.main()
