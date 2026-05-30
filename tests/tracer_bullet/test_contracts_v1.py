"""Tests for Wave 3 contract documentation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_FILES = (
    Path("docs/contracts/task_contract_v1.md"),
    Path("docs/contracts/approval_receipt_v1.md"),
    Path("docs/contracts/rejection_receipt_v1.md"),
    Path("docs/contracts/execution_receipt_v1.md"),
    Path("docs/contracts/evidence_trace_v1.md"),
    Path("docs/contracts/replay_explain_v1.md"),
    Path("docs/contracts/failure_bundle_v1.md"),
    Path("docs/contracts/observation_log_v1.md"),
    Path("docs/contracts/ai_context_bundle_v1.md"),
    Path("docs/contracts/token_roi_v1.md"),
    Path("docs/contracts/provider_request_envelope_v1.md"),
    Path("docs/contracts/provider_response_receipt_v1.md"),
    Path("docs/contracts/release_check_v1.md"),
    Path("docs/contracts/audit_packet_v1.md"),
)

REQUIRED_SECTIONS = (
    "Purpose",
    "Required Fields",
    "Optional Fields",
    "Version",
    "Immutability Rule",
    "Unknown Field Policy",
    "Compatibility Rule",
    "Migration/Deprecation Rule",
    "Valid Example",
    "Invalid Example",
    "Failure Behavior",
)


def _read(relative_path: Path) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class ContractsV1Tests(unittest.TestCase):
    def test_required_contract_files_exist(self) -> None:
        for relative_path in CONTRACT_FILES:
            self.assertTrue(
                (REPO_ROOT / relative_path).exists(),
                f"missing {relative_path.as_posix()}",
            )

    def test_contract_check_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/contract_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("contract_check_v1: PASS", completed.stdout)

    def test_each_contract_has_required_sections_and_examples(self) -> None:
        pattern = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
        for relative_path in CONTRACT_FILES:
            text = _read(relative_path)
            for section in REQUIRED_SECTIONS:
                self.assertIn(f"## {section}", text, relative_path.as_posix())
            blocks = pattern.findall(text)
            self.assertGreaterEqual(len(blocks), 2, relative_path.as_posix())
            valid_example = json.loads(blocks[0])
            self.assertEqual(
                valid_example["contract_version"],
                relative_path.stem,
                relative_path.as_posix(),
            )

    def test_contracts_do_not_claim_external_certification(self) -> None:
        forbidden = (
            "GLOBAL_RECOGNITION_CONFIRMED",
            "externally certified",
            "world class confirmed",
        )
        for relative_path in CONTRACT_FILES:
            text = _read(relative_path).lower()
            for phrase in forbidden:
                self.assertNotIn(phrase.lower(), text, relative_path.as_posix())


if __name__ == "__main__":
    unittest.main()
