"""Tests for Wave 5 secret/context safety evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class SecretContextSafetyV1Tests(unittest.TestCase):
    def test_secret_context_safety_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/secret_context_safety_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("secret_context_safety_check_v1: PASS", completed.stdout)

    def test_secret_policy_rejects_secret_values(self) -> None:
        text = (REPO_ROOT / "docs/security/secret_safety_policy_v1.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("must not include real secrets", text)
        self.assertIn("Use secret references", text)


if __name__ == "__main__":
    unittest.main()
