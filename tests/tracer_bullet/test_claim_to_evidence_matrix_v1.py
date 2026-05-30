"""Tests for Wave 3 claim-to-evidence matrix artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_JSON = Path("reports/audits/claim_to_evidence_matrix_v1.json")
MATRIX_MD = Path("docs/audits/claim_to_evidence_matrix_v1.md")


class ClaimToEvidenceMatrixV1Tests(unittest.TestCase):
    def test_claim_to_evidence_check_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/claim_to_evidence_check_v1.py"],
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
        self.assertIn("claim_to_evidence_check_v1: PASS", completed.stdout)

    def test_matrix_json_has_external_review_boundary(self) -> None:
        payload = json.loads((REPO_ROOT / MATRIX_JSON).read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "claim_to_evidence_matrix_v1")
        self.assertIs(payload["external_review_required"], True)
        self.assertIs(payload["global_recognition_claimed"], False)
        self.assertGreaterEqual(len(payload["claims"]), 6)

    def test_claim_evidence_refs_exist(self) -> None:
        payload = json.loads((REPO_ROOT / MATRIX_JSON).read_text(encoding="utf-8"))
        for claim in payload["claims"]:
            for evidence_ref in claim["evidence_refs"]:
                self.assertTrue(
                    (REPO_ROOT / evidence_ref).exists(),
                    f"{claim['claim_id']} missing {evidence_ref}",
                )

    def test_markdown_contains_all_claim_ids(self) -> None:
        payload = json.loads((REPO_ROOT / MATRIX_JSON).read_text(encoding="utf-8"))
        markdown = (REPO_ROOT / MATRIX_MD).read_text(encoding="utf-8")
        self.assertIn("No global recognition claim", markdown)
        for claim in payload["claims"]:
            self.assertIn(claim["claim_id"], markdown)


if __name__ == "__main__":
    unittest.main()
