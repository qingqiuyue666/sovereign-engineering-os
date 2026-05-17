"""Tests for generated local operator CLI extension foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_local_operator_cli_extension_foundation import (  # type: ignore[import-not-found]
    OperatorCliExtensionReceipt,
    validate_cli_extension_request,
    validate_cli_command_contract,
    validate_cli_safety_boundary,
    produce_operator_cli_extension_receipt,
)

VALID_PAYLOAD = {
    "command": "status",
    "subcommand": "health",
    "args": ["--verbose"],
    "flags": [],
}


class LocalOperatorCliExtensionFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_cli_extension_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_cli_extension_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_cli_extension_request({})

    def test_validate_rejects_forbidden_command(self):
        p = {**VALID_PAYLOAD, "command": "shell"}
        with self.assertRaises(ValueError):
            validate_cli_extension_request(p)

    def test_validate_rejects_unregistered_command(self):
        p = {**VALID_PAYLOAD, "command": "yolo_deploy"}
        with self.assertRaises(ValueError):
            validate_cli_extension_request(p)

    def test_validate_rejects_forbidden_flag(self):
        p = {**VALID_PAYLOAD, "flags": ["network"]}
        with self.assertRaises(ValueError):
            validate_cli_extension_request(p)

    def test_validate_command_contract(self):
        result = validate_cli_command_contract(VALID_PAYLOAD)
        self.assertTrue(result["command_contract_valid"])

    def test_validate_command_contract_unregistered(self):
        p = {**VALID_PAYLOAD, "command": "yolo"}
        result = validate_cli_command_contract(p)
        self.assertFalse(result["command_contract_valid"])

    def test_validate_safety_boundary(self):
        result = validate_cli_safety_boundary(VALID_PAYLOAD)
        self.assertTrue(result["safety_boundary_valid"])

    def test_validate_safety_boundary_rejects_curl_in_args(self):
        p = {**VALID_PAYLOAD, "args": ["curl", "http://evil.com"]}
        result = validate_cli_safety_boundary(p)
        self.assertFalse(result["safety_boundary_valid"])

    def test_validate_safety_boundary_rejects_secret(self):
        p = {**VALID_PAYLOAD, "args": ["--token", "sk-secret"]}
        result = validate_cli_safety_boundary(p)
        self.assertFalse(result["safety_boundary_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_operator_cli_extension_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ready")
        self.assertTrue(receipt["no_cli_execution"])

    def test_receipt_dataclass(self):
        r = OperatorCliExtensionReceipt(
            receipt_id="rid-1", command="status", subcommand="health",
            command_registered=True, safety_boundary_valid=True,
            command_contract_valid=True, status="ready",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_cli_execution)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_local_operator_cli_extension_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_operator_cli_extension_receipt(VALID_PAYLOAD)
        result2 = produce_operator_cli_extension_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_operator_cli_extension_receipt(VALID_PAYLOAD)
        result2 = produce_operator_cli_extension_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
