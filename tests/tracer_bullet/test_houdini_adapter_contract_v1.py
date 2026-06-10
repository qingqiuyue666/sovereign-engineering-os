"""Tests for optional Houdini/hython adapter contract."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from execution_plane.adapters.houdini_hython import run_houdini_hython_smoke
from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.digest import attach_permit_digest
from execution_plane.permits.validator import ExecutionPermitValidationError


class HoudiniHythonAdapterContractV1Tests(unittest.TestCase):
    def test_missing_hython_returns_blocked_not_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = _permit(Path(tempdir) / "out")
            with mock.patch("execution_plane.adapters.houdini_hython.detect_hython", return_value=None):
                result = run_houdini_hython_smoke(permit)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("ENV_NOT_FOUND", result["policy_blocks"])
        self.assertEqual(result["output_root"], "<output-root:out>")
        self.assertNotIn(tempdir, str(result))

    def test_invalid_houdini_permit_fails_closed(self) -> None:
        permit = _permit(Path("work/houdini-invalid"))
        permit["allowed_adapter"] = "fake_dcc"
        permit = attach_permit_digest(permit)
        with self.assertRaises(ExecutionPermitValidationError):
            run_houdini_hython_smoke(permit)


def _permit(output_root: Path) -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_HOUDINI",
        operator_approval_id="RCPT_HOUDINI",
        allowed_adapter="houdini_hython",
        allowed_action="houdini_generate_geometry_cache",
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
    )


if __name__ == "__main__":
    unittest.main()

