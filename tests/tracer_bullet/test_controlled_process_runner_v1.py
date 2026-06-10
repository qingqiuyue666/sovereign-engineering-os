"""Tests for the controlled process runner V1."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from execution_plane.permits.builder import create_execution_permit
from execution_plane.runner.process_runner import run_controlled_process


class ControlledProcessRunnerV1Tests(unittest.TestCase):
    def test_successful_command_creates_output_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "out"
            permit = _permit(output_root)
            result = run_controlled_process(
                permit=permit,
                command=[
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('output.txt').write_text('ok\\n', encoding='utf-8'); print('done')",
                ],
                declared_output_paths=["output.txt"],
            )
            output = output_root / "output.txt"
            self.assertTrue(output.exists())
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertTrue(result["outputs"][0]["sha256"].startswith("sha256:"))
        self.assertTrue(result["stdout_digest"].startswith("sha256:"))

    def test_failed_command_returns_failed_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            result = run_controlled_process(
                permit=_permit(Path(tempdir) / "out"),
                command=[sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"],
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["exit_code"], 7)
        self.assertTrue(result["stderr_digest"].startswith("sha256:"))

    def test_timeout_kills_process(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = _permit(Path(tempdir) / "out", max_runtime_seconds=1)
            result = run_controlled_process(
                permit=permit,
                command=[sys.executable, "-c", "import time; time.sleep(5)"],
            )
        self.assertEqual(result["status"], "TIMED_OUT")
        self.assertEqual(result["failure_summary"], "process_timeout")

    def test_oversized_output_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = _permit(Path(tempdir) / "out", max_output_bytes=4)
            result = run_controlled_process(
                permit=permit,
                command=[
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('big.txt').write_text('too large', encoding='utf-8')",
                ],
                declared_output_paths=["big.txt"],
            )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("max_output_bytes_exceeded", result["policy_blocks"])

    def test_path_traversal_is_blocked_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "out"
            result = run_controlled_process(
                permit=_permit(output_root),
                command=[
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('should_not_exist.txt').write_text('no')",
                ],
                declared_output_paths=["../escape.txt"],
            )
            self.assertFalse((output_root / "should_not_exist.txt").exists())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("relative_output_path_escape", result["policy_blocks"])

    def test_public_result_does_not_leak_absolute_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "out"
            result = run_controlled_process(
                permit=_permit(output_root),
                command=[sys.executable, "-c", "print('no outputs')"],
            )
        self.assertEqual(result["output_root"], "<output-root:out>")
        self.assertNotIn(tempdir, str(result))


def _permit(
    output_root: Path,
    *,
    max_runtime_seconds: int = 5,
    max_output_bytes: int = 10_000,
) -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_RUNNER",
        operator_approval_id="RCPT_RUNNER",
        allowed_adapter="fake_dcc",
        allowed_action="smoke_generate_file",
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
        max_runtime_seconds=max_runtime_seconds,
        max_output_bytes=max_output_bytes,
    )


if __name__ == "__main__":
    unittest.main()

