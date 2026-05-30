"""Adversarial input regression tests for Wave 4."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class AdversarialInputsV1Tests(unittest.TestCase):
    def test_adversarial_smoke_passes_all_cases(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/adversarial_smoke_v1.py", "--json"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertIs(payload["global_recognition_claimed"], False)
        failed = [case for case in payload["cases"] if not case["passed"]]
        self.assertEqual(failed, [])

    def test_prompt_injection_case_does_not_claim_authority(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/adversarial_smoke_v1.py", "--json"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        by_id = {case["case_id"]: case for case in payload["cases"]}
        case = by_id["prompt_injection_no_authority"]
        self.assertTrue(case["passed"])
        self.assertIn("does not become authority", case["expected"])


if __name__ == "__main__":
    unittest.main()
