"""Tests for Wave 5 release invariant evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"


class ReleaseInvariantV1Tests(unittest.TestCase):
    def test_release_invariant_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/release_invariant_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("release_invariant_check_v1: PASS", completed.stdout)

    def test_rc_tag_target_is_unchanged(self) -> None:
        completed = subprocess.run(
            ["git", "rev-parse", "v0.1.0-rc3^{}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), EXPECTED_TARGET)


if __name__ == "__main__":
    unittest.main()
