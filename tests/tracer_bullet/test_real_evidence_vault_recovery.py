"""Tracer bullet tests for real evidence vault recovery.

Covers:
- recovery receipt generated
- migration receipt generated from foundation contract
- rollback plan created
- deterministic recovery receipt
- recovery receipt requires artifact_id
- migration receipt format
- no network in recovery module
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from evidence_vault import LocalEvidenceVault, EvidenceRecovery
from evidence_vault.local_evidence_vault import LocalEvidenceVaultError

VALID_SHA256 = hashlib.sha256(b"test-content").hexdigest()


def make_valid_payload(**overrides):
    p = {
        "artifact_id": "ART-001",
        "artifact_type": "run_log",
        "content_hash": VALID_SHA256,
        "hash_algorithm": "sha256",
        "created_at": "2025-01-01T00:00:00Z",
        "producer": "test-runner",
        "lineage": ["run-001", "stage-002"],
        "immutable": True,
        "append_only": True,
    }
    p.update(overrides)
    return p


class RealEvidenceVaultRecoveryTests(unittest.TestCase):
    """Recovery tests for the evidence vault."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault = LocalEvidenceVault(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    # --- recovery receipt generated ---

    def test_recovery_receipt_generated(self):
        self.vault.write_artifact(make_valid_payload())
        receipt = self.vault.get_recovery_receipt("ART-001")
        self.assertEqual(receipt["artifact_id"], "ART-001")
        self.assertEqual(receipt["receipt_type"], "recovery")
        self.assertEqual(receipt["status"], "recoverable")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertIn("receipt_id", receipt)
        self.assertIn("storage_path", receipt)
        self.assertIn("content_hash", receipt)

    # --- recovery receipt is deterministic ---

    def test_recovery_receipt_is_deterministic(self):
        self.vault.write_artifact(make_valid_payload())
        r1 = self.vault.get_recovery_receipt("ART-001")
        r2 = self.vault.get_recovery_receipt("ART-001")

        self.assertEqual(r1["receipt_id"], r2["receipt_id"])
        self.assertEqual(r1["content_hash"], r2["content_hash"])
        self.assertEqual(r1["created_at"], r2["created_at"])

    # --- recovery receipt for missing artifact ---

    def test_recovery_receipt_missing_artifact_raises(self):
        with self.assertRaises(LocalEvidenceVaultError) as ctx:
            self.vault.get_recovery_receipt("NONEXISTENT")
        self.assertIn("artifact_not_found_for_recovery", str(ctx.exception))

    # --- migration receipt generated from foundation contract ---

    def test_migration_receipt_generated_from_foundation(self):
        foundation_payload = {
            "receipt_id": "foundation-rid-001",
            "artifact_id": "ART-001",
            "content_hash": VALID_SHA256,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
            "status": "sealed",
            "no_vault_write": True,
            "append_only_enforced": True,
        }
        receipt = self.vault.get_migration_receipt(foundation_payload)
        self.assertEqual(receipt["receipt_type"], "migration")
        self.assertEqual(receipt["migration_status"], "migrated_from_foundation_contract")
        self.assertEqual(receipt["artifact_id"], "ART-001")
        self.assertEqual(receipt["foundation_receipt_reference"], "foundation-rid-001")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertIn("migrated_at", receipt)
        self.assertTrue(receipt["receipt_id"])

    # --- migration receipt with empty artifact_id ---

    def test_migration_receipt_with_empty_id(self):
        foundation_payload = {
            "receipt_id": "",
            "artifact_id": "",
            "content_hash": "",
            "hash_algorithm": "",
            "artifact_type": "",
        }
        receipt = self.vault.get_migration_receipt(foundation_payload)
        self.assertEqual(receipt["receipt_type"], "migration")
        self.assertTrue(receipt["receipt_id"])

    # --- migration receipt is deterministic ---

    def test_migration_receipt_is_deterministic(self):
        foundation_payload = {
            "receipt_id": "foundation-rid-001",
            "artifact_id": "ART-001",
            "content_hash": VALID_SHA256,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
        }
        r1 = EvidenceRecovery.generate_migration_receipt(foundation_payload, migrated_at="2025-01-01T00:00:00Z")
        r2 = EvidenceRecovery.generate_migration_receipt(foundation_payload, migrated_at="2025-01-01T00:00:00Z")
        self.assertEqual(r1["receipt_id"], r2["receipt_id"])

    # --- migration receipt different artifacts have different ids ---

    def test_migration_receipt_different_artifacts_have_different_ids(self):
        p1 = {
            "receipt_id": "f-1",
            "artifact_id": "ART-A",
            "content_hash": VALID_SHA256,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
        }
        p2 = {
            "receipt_id": "f-2",
            "artifact_id": "ART-B",
            "content_hash": VALID_SHA256,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
        }
        r1 = EvidenceRecovery.generate_migration_receipt(p1, migrated_at="2025-01-01T00:00:00Z")
        r2 = EvidenceRecovery.generate_migration_receipt(p2, migrated_at="2025-01-01T00:00:00Z")
        self.assertNotEqual(r1["receipt_id"], r2["receipt_id"])

    # --- rollback plan created ---

    def test_rollback_plan_created_for_existing_artifact(self):
        self.vault.write_artifact(make_valid_payload())
        plan = self.vault.get_rollback_plan("ART-001")
        self.assertEqual(plan["artifact_id"], "ART-001")
        self.assertEqual(plan["action"], "mark_for_review")
        self.assertEqual(plan["module_version"], "v1")
        self.assertIn("No destructive delete", plan["description"])
        self.assertEqual(len(plan["steps"]), 5)
        self.assertIn("verify artifact integrity before rollback", plan["steps"])
        self.assertIn("no overwrite of artifact payload", plan["steps"])

    # --- rollback plan for non-existent artifact still returns plan ---

    def test_rollback_plan_for_nonexistent(self):
        plan = self.vault.get_rollback_plan("NONEXISTENT")
        self.assertEqual(plan["artifact_id"], "NONEXISTENT")
        self.assertEqual(plan["action"], "mark_for_review")

    # --- rollback plan is deterministic ---

    def test_rollback_plan_is_deterministic(self):
        self.vault.write_artifact(make_valid_payload())
        p1 = self.vault.get_rollback_plan("ART-001")
        p2 = self.vault.get_rollback_plan("ART-001")
        self.assertEqual(p1["plan_id"], p2["plan_id"])

    # --- recovery receipt has all required fields ---

    def test_recovery_receipt_has_all_required_fields(self):
        self.vault.write_artifact(make_valid_payload())
        receipt = self.vault.get_recovery_receipt("ART-001")
        required = [
            "receipt_id", "artifact_id", "receipt_type", "created_at",
            "storage_path", "content_hash", "envelope_hash", "hash_algorithm",
            "artifact_type", "producer", "lineage", "module_version", "status",
        ]
        for field in required:
            with self.subTest(field=field):
                self.assertIn(field, receipt)

    # --- recovery receipt producer and lineage correct ---

    def test_recovery_receipt_producer_and_lineage_correct(self):
        self.vault.write_artifact(make_valid_payload(producer="p1", lineage=["r1", "s2"]))
        receipt = self.vault.get_recovery_receipt("ART-001")
        self.assertEqual(receipt["producer"], "p1")
        self.assertEqual(receipt["lineage"], ["r1", "s2"])

    # --- no network/subprocess in recovery module source ---

    def test_no_network_in_recovery_source(self):
        sp = ROOT / "tools" / "evidence_vault" / "evidence_recovery.py"
        src = sp.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import httpx", src)
        self.assertNotIn("os.system", src)
        self.assertNotIn("openai", src)

    # --- multiple recoveries for multiple artifacts ---

    def test_multiple_artifact_recovery(self):
        for i in range(3):
            p = make_valid_payload(
                artifact_id=f"ART-{i:03d}",
                content_hash=hashlib.sha256(f"content-{i}".encode()).hexdigest(),
            )
            self.vault.write_artifact(p)

        for i in range(3):
            receipt = self.vault.get_recovery_receipt(f"ART-{i:03d}")
            self.assertEqual(receipt["artifact_id"], f"ART-{i:03d}")
            self.assertEqual(receipt["status"], "recoverable")

    # --- migration receipt non-mapping ---

    def test_migration_receipt_non_mapping_raises(self):
        with self.assertRaises(TypeError):
            self.vault.get_migration_receipt(["not", "mapping"])

    # --- recovery receipt via EvidenceRecovery directly ---

    def test_recovery_receipt_via_direct_call(self):
        storage_envelope = {
            "storage_path": "/tmp/test.json",
            "content_hash": VALID_SHA256,
            "envelope_hash": "b" * 64,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
            "producer": "test",
            "lineage": ["l1"],
        }
        receipt = EvidenceRecovery.generate_recovery_receipt("ART-001", storage_envelope)
        self.assertEqual(receipt["artifact_id"], "ART-001")
        self.assertEqual(receipt["receipt_type"], "recovery")
        self.assertEqual(receipt["status"], "recoverable")

    # --- migration receipt via EvidenceRecovery directly ---

    def test_migration_receipt_via_direct_call(self):
        foundation = {
            "receipt_id": "f-001",
            "artifact_id": "ART-001",
            "content_hash": VALID_SHA256,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
        }
        receipt = EvidenceRecovery.generate_migration_receipt(foundation, "2025-01-01T00:00:00Z")
        self.assertEqual(receipt["migrated_at"], "2025-01-01T00:00:00Z")

    # --- rollback plan via EvidenceRecovery directly ---

    def test_rollback_plan_via_direct_call(self):
        plan = EvidenceRecovery.create_rollback_plan("ART-001", "/tmp/ART-001.json")
        self.assertEqual(plan["artifact_id"], "ART-001")
        self.assertEqual(plan["action"], "mark_for_review")


if __name__ == "__main__":
    unittest.main()
