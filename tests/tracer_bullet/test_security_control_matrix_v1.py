"""Tests for Wave 5 security control evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_CONTROLS = (
    "AI approval bypass",
    "fake PASS",
    "receipt forgery",
    "missing evidence",
    "replay false success",
    "secret leakage",
    "context leakage",
    "provider response poisoning",
    "malicious PR/patch",
    "CI bypass",
    "dependency risk",
    "GitHub Actions risk",
    "operator misapproval",
    "tag mutation",
    "local path leakage",
)


class SecurityControlMatrixV1Tests(unittest.TestCase):
    def test_security_control_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/security_control_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("security_control_check_v1: PASS", completed.stdout)

    def test_control_matrix_covers_required_controls(self) -> None:
        text = (REPO_ROOT / "docs/security/security_control_matrix_v1.md").read_text(
            encoding="utf-8"
        )
        for control in REQUIRED_CONTROLS:
            self.assertIn(control, text)


if __name__ == "__main__":
    unittest.main()
