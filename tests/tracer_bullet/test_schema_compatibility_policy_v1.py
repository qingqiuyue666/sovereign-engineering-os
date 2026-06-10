"""Tests for Wave 8 schema compatibility policy."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "docs" / "compatibility" / "schema_versioning_policy_v1.md"


class SchemaCompatibilityPolicyV1Tests(unittest.TestCase):
    def test_schema_compatibility_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/schema_compatibility_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("schema_compatibility_check_v1: PASS", completed.stdout)

    def test_policy_contains_required_compatibility_terms(self) -> None:
        text = POLICY_PATH.read_text(encoding="utf-8").lower()
        for term in (
            "schema_version",
            "contract_version",
            "backward-compatible",
            "forward-compatible",
            "breaking change",
            "migration mapping",
            "fail closed",
            "no silent downgrade",
            "deterministic replay",
        ):
            self.assertIn(term, text)

    def test_frozen_schema_pack_uses_current_freeze_tag(self) -> None:
        schema_root = REPO_ROOT / "kernel" / "schemas"
        for schema_path in schema_root.glob("*.schema.json"):
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "v11-slice1", schema_path.name)

    def test_contract_docs_keep_migration_and_compatibility_sections(self) -> None:
        contract_root = REPO_ROOT / "docs" / "contracts"
        for contract_path in contract_root.glob("*_v1.md"):
            if contract_path.name == "narrow_adapter_contract_v1.md":
                continue
            text = contract_path.read_text(encoding="utf-8").lower()
            self.assertIn("## compatibility rule", text)
            self.assertIn("## migration/deprecation rule", text)
            self.assertIn("migration requires", text)
            self.assertIn("fail closed", text)


if __name__ == "__main__":
    unittest.main()
