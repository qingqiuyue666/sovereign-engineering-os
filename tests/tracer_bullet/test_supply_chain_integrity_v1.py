"""Tests for Wave 5 supply-chain evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class SupplyChainIntegrityV1Tests(unittest.TestCase):
    def test_supply_chain_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/supply_chain_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("supply_chain_check_v1: PASS", completed.stdout)

    def test_ci_uses_minimal_permissions(self) -> None:
        text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("pull_request_target", text)


if __name__ == "__main__":
    unittest.main()
