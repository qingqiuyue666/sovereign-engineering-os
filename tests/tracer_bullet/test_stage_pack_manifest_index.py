"""Tests for generated stage pack manifest index module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_stage_pack_manifest_index import (  # type: ignore[import-not-found]
    StagePackManifestReceipt,
    validate_stage_pack_manifest,
    validate_stage_pack_entry,
    validate_stage_pack_test_coverage,
    produce_stage_pack_manifest_receipt,
    STAGE_IDS,
)

VALID_STAGE = {
    "stage_id": "patch_application_pipeline",
    "artifacts": ["generated_module", "registry", "policy", "runbook", "test"],
    "test_coverage": True,
}

VALID_PAYLOAD = {
    "pack_version": "v1",
    "stages": [
        {"stage_id": sid, "artifacts": ["generated_module", "registry", "policy", "runbook", "test"], "test_coverage": True}
        for sid in STAGE_IDS
    ],
}


class StagePackManifestIndexTests(unittest.TestCase):

    def test_stage_ids_list(self):
        self.assertEqual(len(STAGE_IDS), 16)

    def test_validate_manifest_accepts_valid(self):
        result = validate_stage_pack_manifest(VALID_PAYLOAD)
        self.assertTrue(result["valid"])
        self.assertEqual(result["stage_count"], 16)

    def test_validate_manifest_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_stage_pack_manifest("not a dict")

    def test_validate_manifest_rejects_empty_stages(self):
        p = {"pack_version": "v1", "stages": []}
        with self.assertRaises(ValueError):
            validate_stage_pack_manifest(p)

    def test_validate_entry_accepts_valid(self):
        result = validate_stage_pack_entry(VALID_STAGE)
        self.assertEqual(result["stage_id"], "patch_application_pipeline")

    def test_validate_entry_rejects_unknown_stage(self):
        p = {"stage_id": "magic_unknown_stage", "artifacts": [], "test_coverage": False}
        with self.assertRaises(ValueError):
            validate_stage_pack_entry(p)

    def test_validate_test_coverage_all_covered(self):
        result = validate_stage_pack_test_coverage(VALID_PAYLOAD)
        self.assertTrue(result["test_coverage_valid"])
        self.assertEqual(result["covered"], 16)

    def test_validate_test_coverage_partial(self):
        stages = [
            {"stage_id": sid, "artifacts": [], "test_coverage": i % 2 == 0}
            for i, sid in enumerate(STAGE_IDS)
        ]
        result = validate_stage_pack_test_coverage({"pack_version": "v1", "stages": stages})
        self.assertFalse(result["test_coverage_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_stage_pack_manifest_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["total_stages"], 16)

    def test_receipt_dataclass(self):
        r = StagePackManifestReceipt(
            receipt_id="rid-1", pack_version="v1", total_stages=16,
            stages_indexed=STAGE_IDS[:2], test_coverage_valid=True,
            all_entries_valid=True, status="complete",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_stage_pack_manifest_index.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_stage_pack_manifest_receipt(VALID_PAYLOAD)
        result2 = produce_stage_pack_manifest_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_stage_pack_manifest_receipt(VALID_PAYLOAD)
        result2 = produce_stage_pack_manifest_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
