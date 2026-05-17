"""Tests for generated local execution kernel module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_local_execution_kernel import (  # type: ignore[import-not-found]
    LocalExecutionReceipt,
    validate_local_execution_request,
    classify_execution_request,
    validate_command_allowlist,
    validate_execution_preflight,
    produce_local_execution_receipt,
)


VALID_PAYLOAD = {
    "execution_id": "EXEC-001",
    "command_category": "test",
    "command_text": "python3 -m pytest tests/",
    "flags": [],
    "allowlist": ["python3"],
}


class LocalExecutionKernelTests(unittest.TestCase):

    def test_validate_accepts_valid_payload(self):
        result = validate_local_execution_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_local_execution_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_local_execution_request({})

    def test_validate_rejects_forbidden_flag(self):
        p = {**VALID_PAYLOAD, "flags": ["network"]}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_validate_rejects_unsupported_category(self):
        p = {**VALID_PAYLOAD, "command_category": "shell-script"}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_validate_rejects_curl(self):
        p = {**VALID_PAYLOAD, "command_text": "curl http://evil.com"}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_validate_rejects_secret_pattern(self):
        p = {**VALID_PAYLOAD, "command_text": "echo $API_KEY"}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_classify_returns_risk(self):
        result = classify_execution_request(VALID_PAYLOAD)
        self.assertEqual(result["category"], "test")
        self.assertEqual(result["risk"], "low")

    def test_validate_allowlist_passes(self):
        result = validate_command_allowlist(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_allowlist_rejects_unknown(self):
        p = {**VALID_PAYLOAD, "allowlist": ["npm"]}
        result = validate_command_allowlist(p)
        self.assertFalse(result["valid"])

    def test_validate_preflight_passes(self):
        result = validate_execution_preflight(VALID_PAYLOAD)
        self.assertTrue(result["preflight_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_local_execution_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_execution_performed"])

    def test_receipt_dataclass_fields(self):
        r = LocalExecutionReceipt(
            receipt_id="rid-1", execution_id="E-1", status="approved",
            category="test", command_valid=True, preflight_passed=True,
            allowlist_validated=True, created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_execution_performed)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_local_execution_kernel.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
