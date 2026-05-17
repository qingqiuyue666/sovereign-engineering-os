"""Tests for generated patch application pipeline module."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_patch_application_pipeline import (  # type: ignore[import-not-found]
    PatchApplicationReceipt,
    validate_patch_application_request,
    classify_patch_risk,
    validate_patch_allowlist,
    validate_patch_preflight,
    produce_patch_application_receipt,
)


VALID_PAYLOAD = {
    "patch_id": "PATCH-001",
    "target_files": ["src/app/main.py", "src/lib/utils.py"],
    "diff_summary": "Fix typo in main.py, update util",
    "rollback_plan": "git revert PATCH-001",
    "tests": ["test_main.py", "test_utils.py"],
    "patch_mode": "dry-run",
    "flags": [],
    "allowlist": ["src/app/main.py", "src/lib/utils.py"],
}


class PatchApplicationPipelineTests(unittest.TestCase):

    def test_validate_accepts_valid_payload(self):
        result = validate_patch_application_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_patch_application_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_patch_application_request({})

    def test_validate_rejects_forbidden_flag(self):
        p = {**VALID_PAYLOAD, "flags": ["git_merge"]}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_validate_rejects_unsupported_patch_mode(self):
        p = {**VALID_PAYLOAD, "patch_mode": "unsafe-force-push"}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_validate_rejects_absolute_path(self):
        p = {**VALID_PAYLOAD, "target_files": ["/etc/passwd"]}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_validate_rejects_path_traversal(self):
        p = {**VALID_PAYLOAD, "target_files": ["../../../etc/passwd"]}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_classify_patch_risk_low_for_normal(self):
        result = classify_patch_risk(VALID_PAYLOAD)
        self.assertEqual(result["risk"], "low")

    def test_classify_patch_risk_high_for_security_paths(self):
        p = {**VALID_PAYLOAD, "target_files": ["src/security/auth.py"]}
        result = classify_patch_risk(p)
        self.assertEqual(result["risk"], "high")

    def test_classify_patch_risk_rejected_for_bad_mode(self):
        p = {**VALID_PAYLOAD, "patch_mode": "invalid"}
        result = classify_patch_risk(p)
        self.assertEqual(result["risk"], "rejected")

    def test_validate_allowlist_passes(self):
        result = validate_patch_allowlist(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_allowlist_rejects_unknown_file(self):
        p = {**VALID_PAYLOAD, "allowlist": ["src/app/main.py"]}
        result = validate_patch_allowlist(p)
        self.assertFalse(result["valid"])
        self.assertIn("src/lib/utils.py", result["violations"])

    def test_validate_preflight_passes(self):
        result = validate_patch_preflight(VALID_PAYLOAD)
        self.assertTrue(result["preflight_passed"])

    def test_validate_preflight_fails_missing_tests(self):
        p = {**VALID_PAYLOAD, "tests": []}
        result = validate_patch_preflight(p)
        self.assertFalse(result["preflight_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_patch_application_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_side_effects"])

    def test_produce_receipt_rejected_missing_fields(self):
        with self.assertRaises(ValueError):
            produce_patch_application_receipt({"patch_id": "only-id"})

    def test_receipt_dataclass_fields(self):
        r = PatchApplicationReceipt(
            receipt_id="rid-1", patch_id="P-1", status="approved",
            risk_classification="low", preflight_passed=True,
            allowlist_validated=True, diff_summary="x", rollback_plan_present=True,
            tests_present=True, created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_side_effects)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_patch_application_pipeline.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import http.client", src)
        self.assertNotIn("import urllib.request", src)

    def test_no_forbidden_strings_in_module(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_patch_application_pipeline.py") as f:
            src = f.read()
        for forbidden in ["cloud_ai", "API_KEY", ".env", "push main", "merge main", "branch delete"]:
            self.assertNotIn(forbidden, src.lower() if forbidden != ".env" else src)


if __name__ == "__main__":
    unittest.main()
