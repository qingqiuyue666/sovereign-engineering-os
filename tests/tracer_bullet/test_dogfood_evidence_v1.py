"""Tests for Wave 7 dogfooding evidence."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_JSON = REPO_ROOT / "reports" / "dogfood" / "dogfood_index_v1.json"

REQUIRED_CATEGORIES = {
    "repository_maturity_readme_docs_hardening",
    "failure_path_hardening",
    "installability_reproducibility_hardening",
    "ai_admission_safety_hardening",
    "security_supply_chain_threat_model_hardening",
}

REQUIRED_SECTIONS = (
    "## Task Contract",
    "## Approval Receipt",
    "## Dry-Run/Execution Receipt",
    "## Evidence Trace",
    "## Replay Explain",
    "## PR Or Commit Reference",
    "## Validation Result",
    "## Post-Merge Validation",
    "## Outcome",
    "## Residual Risk",
)


class DogfoodEvidenceV1Tests(unittest.TestCase):
    def test_dogfood_evidence_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/dogfood_evidence_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("dogfood_evidence_check_v1: PASS", completed.stdout)

    def test_index_covers_required_categories(self) -> None:
        payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "dogfood_index_v1")
        self.assertIs(payload["external_review_required"], True)
        self.assertIs(payload["global_recognition_claimed"], False)
        categories = {record["category"] for record in payload["records"]}
        self.assertTrue(REQUIRED_CATEGORIES.issubset(categories))
        self.assertGreaterEqual(len(payload["records"]), 5)

    def test_each_record_has_required_sections_and_real_pr_shape(self) -> None:
        payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        for entry in payload["records"]:
            record = json.loads((REPO_ROOT / entry["json_path"]).read_text(encoding="utf-8"))
            markdown = (REPO_ROOT / entry["markdown_path"]).read_text(encoding="utf-8")
            self.assertTrue(record["historical_evidence_available"])
            self.assertRegex(
                record["pr_link_or_commit_reference"]["pr_url"],
                r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/[0-9]+$",
            )
            self.assertRegex(
                record["pr_link_or_commit_reference"]["merge_commit"],
                r"^[0-9a-f]{40}$",
            )
            self.assertEqual(record["approval_receipt"]["approval_boundary"], "merge_after_required_checks")
            self.assertFalse(record["approval_receipt"]["separate_historical_approval_artifact_available"])
            self.assertEqual(record["validation_result"]["status"], "passed")
            self.assertEqual(record["post_merge_validation"]["status"], "passed")
            self.assertIn("not invented", record["fabrication_guard"])
            for section in REQUIRED_SECTIONS:
                self.assertIn(section, markdown)

    def test_evidence_refs_exist(self) -> None:
        payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        for entry in payload["records"]:
            record = json.loads((REPO_ROOT / entry["json_path"]).read_text(encoding="utf-8"))
            for ref in record["evidence_trace"]:
                if ref.startswith("http"):
                    continue
                self.assertTrue((REPO_ROOT / ref).exists(), ref)


if __name__ == "__main__":
    unittest.main()
