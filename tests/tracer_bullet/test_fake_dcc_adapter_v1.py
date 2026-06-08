"""Tests for the fake DCC execution-plane adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from execution_plane.adapters.fake_dcc import run_fake_dcc
from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.digest import attach_permit_digest
from execution_plane.permits.validator import ExecutionPermitValidationError


class FakeDccAdapterV1Tests(unittest.TestCase):
    def test_fake_dcc_produces_real_files_manifest_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "out"
            result = run_fake_dcc(
                _permit(output_root),
                job={"output_path": "output.txt", "content": "materialized\n"},
            )
            output = output_root / "output.txt"
            manifest = output_root / "manifest.json"
            self.assertTrue(output.exists())
            self.assertTrue(manifest.exists())
        self.assertEqual(result["status"], "SUCCEEDED")
        paths = {item["relative_path"] for item in result["outputs"]}
        self.assertEqual(paths, {"manifest.json", "output.txt"})
        self.assertTrue(all(item["sha256"].startswith("sha256:") for item in result["outputs"]))

    def test_invalid_permit_fails_closed(self) -> None:
        permit = _permit(Path("work/fake-dcc-invalid"))
        permit["operator_approval_id"] = ""
        permit = attach_permit_digest(permit)
        with self.assertRaises(ExecutionPermitValidationError):
            run_fake_dcc(permit)

    def test_fake_dcc_cannot_write_outside_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "out"
            result = run_fake_dcc(
                _permit(output_root),
                job={"output_path": "../escape.txt", "content": "escape"},
            )
            self.assertFalse((Path(tempdir) / "escape.txt").exists())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("relative_output_path_escape", result["policy_blocks"])

    def test_output_hash_is_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "out"
            result = run_fake_dcc(
                _permit(output_root),
                job={"output_path": "output.txt", "content": "stable\n"},
            )
            output_record = next(item for item in result["outputs"] if item["relative_path"] == "output.txt")
            from execution_plane.runner.result_envelope import sha256_file

            self.assertEqual(output_record["sha256"], sha256_file(output_root / "output.txt"))


def _permit(output_root: Path) -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_FAKE_DCC",
        operator_approval_id="RCPT_FAKE_DCC",
        allowed_adapter="fake_dcc",
        allowed_action="smoke_generate_file",
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
    )


if __name__ == "__main__":
    unittest.main()

