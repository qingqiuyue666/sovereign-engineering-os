"""Tracer bullet tests for real evidence vault runtime v1.

Covers:
- valid artifact write succeeds
- duplicate artifact_id rejected
- content hash mismatch rejected
- unsupported hash algorithm rejected
- mutable record rejected
- append_only false rejected
- raw secret material rejected
- index lookup succeeds
- read path by artifact_id
- non-mapping payload raises
- policy active
- registry active
- runbook records runtime boundaries
- no network / subprocess / provider live surface
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

from evidence_vault import LocalEvidenceVault, EvidenceEnvelope, EvidenceIndex
from evidence_vault.local_evidence_vault import LocalEvidenceVaultError
from evidence_vault.evidence_envelope import EvidenceEnvelopeError

VALID_SHA256 = hashlib.sha256(b"test-content").hexdigest()

POLICY_PATH = ROOT / "governance" / "security" / "real_evidence_vault_runtime_policy_v1.json"
REGISTRY_PATH = ROOT / "governance" / "local_train" / "real_evidence_vault_runtime_registry_v1.json"
RUNBOOK_PATH = ROOT / "docs" / "runbooks" / "real_evidence_vault_runtime_v1.md"


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


class RealEvidenceVaultRuntimeTests(unittest.TestCase):
    """Core runtime tests for the real local evidence vault."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault = LocalEvidenceVault(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    # --- valid artifact write succeeds ---

    def test_valid_artifact_write_succeeds(self):
        result = self.vault.write_artifact(make_valid_payload())
        self.assertEqual(result["status"], "sealed")
        self.assertEqual(result["artifact_id"], "ART-001")
        self.assertTrue(result["envelope_hash"])

    # --- duplicate artifact_id rejected ---

    def test_duplicate_artifact_id_rejected(self):
        self.vault.write_artifact(make_valid_payload())
        with self.assertRaises(LocalEvidenceVaultError) as ctx:
            self.vault.write_artifact(make_valid_payload())
        self.assertIn("duplicate_artifact_id_rejected", str(ctx.exception))

    # --- content hash mismatch rejected ---

    def test_content_hash_mismatch_rejected(self):
        payload = make_valid_payload(content_hash=VALID_SHA256)
        envelope = EvidenceEnvelope.create_envelope(payload)
        result = EvidenceEnvelope.verify_hash(envelope, b"different-content")
        self.assertFalse(result["hash_match"])

    def test_content_hash_mismatch_raises_on_bad_format(self):
        p = make_valid_payload(content_hash="tooshort")
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.create_envelope(p)
        self.assertIn("content_hash_mismatch", str(ctx.exception))

    # --- unsupported hash algorithm rejected ---

    def test_unsupported_hash_algorithm_rejected(self):
        p = make_valid_payload(hash_algorithm="md5")
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.create_envelope(p)
        self.assertIn("unsupported_hash_algorithm", str(ctx.exception))

    # --- mutable record rejected ---

    def test_mutable_record_rejected(self):
        p = make_valid_payload(immutable=False)
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.create_envelope(p)
        self.assertIn("immutable_must_be_true", str(ctx.exception))

    # --- append_only false rejected ---

    def test_append_only_false_rejected(self):
        p = make_valid_payload(append_only=False)
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.create_envelope(p)
        self.assertIn("append_only_must_be_true", str(ctx.exception))

    # --- raw secret material rejected ---

    def test_raw_secret_material_rejected_by_type(self):
        for forbidden_type in ("raw_secret", "api_key", "private_key", "token", "password", "credential"):
            with self.subTest(forbidden_type=forbidden_type):
                p = make_valid_payload(artifact_type=forbidden_type)
                with self.assertRaises(EvidenceEnvelopeError) as ctx:
                    EvidenceEnvelope.create_envelope(p)
                self.assertIn("forbidden_artifact_type", str(ctx.exception))

    def test_raw_secret_content_marker_rejected(self):
        for marker in ("-----BEGIN", "API_KEY=", "SECRET=", "TOKEN=", "sk-"):
            with self.subTest(marker=marker):
                p = make_valid_payload(producer=f"test-{marker}-bad")
                with self.assertRaises(EvidenceEnvelopeError) as ctx:
                    EvidenceEnvelope.create_envelope(p)
                self.assertIn("forbidden_content_marker", str(ctx.exception))

    # --- index lookup succeeds ---

    def test_index_lookup_succeeds(self):
        self.vault.write_artifact(make_valid_payload())
        entry = EvidenceIndex.lookup(self.vault.index_path, "ART-001")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["artifact_id"], "ART-001")

    def test_index_lookup_missing_returns_none(self):
        entry = EvidenceIndex.lookup(self.vault.index_path, "NONEXISTENT")
        self.assertIsNone(entry)

    # --- read path by artifact_id ---

    def test_read_artifact_succeeds(self):
        self.vault.write_artifact(make_valid_payload())
        envelope = self.vault.read_artifact("ART-001")
        self.assertEqual(envelope["artifact_id"], "ART-001")
        self.assertEqual(envelope["artifact_type"], "run_log")
        self.assertTrue(envelope["immutable"])
        self.assertTrue(envelope["append_only"])

    def test_read_missing_artifact_raises(self):
        with self.assertRaises(LocalEvidenceVaultError) as ctx:
            self.vault.read_artifact("NONEXISTENT")
        self.assertIn("artifact_not_found", str(ctx.exception))

    # --- non-mapping payload raises ---

    def test_non_mapping_payload_raises_in_envelope(self):
        with self.assertRaises(TypeError):
            EvidenceEnvelope.create_envelope("not a dict")

    def test_non_mapping_payload_raises_in_write(self):
        with self.assertRaises(TypeError):
            self.vault.write_artifact("not a dict")

    # --- policy active ---

    def test_policy_file_exists_and_active(self):
        self.assertTrue(POLICY_PATH.is_file(), f"Missing: {POLICY_PATH}")
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "active")
        self.assertEqual(policy["policy_version"], "v1")
        self.assertTrue(policy["append_only_required"])
        self.assertTrue(policy["immutable_records_required"])
        self.assertTrue(policy["runtime_constraints"]["no_network"])
        self.assertTrue(policy["runtime_constraints"]["no_encryption"])
        self.assertTrue(policy["runtime_constraints"]["no_secret_storage"])

    # --- registry active ---

    def test_registry_file_exists_and_active(self):
        self.assertTrue(REGISTRY_PATH.is_file(), f"Missing: {REGISTRY_PATH}")
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(registry["status"], "active")
        self.assertEqual(registry["registry_version"], "v1")
        self.assertTrue(registry["append_only"])
        self.assertTrue(registry["no_network"])
        self.assertTrue(registry["no_encryption"])

    # --- runbook records runtime boundaries ---

    def test_runbook_exists_and_records_boundaries(self):
        self.assertTrue(RUNBOOK_PATH.is_file(), f"Missing: {RUNBOOK_PATH}")
        text = RUNBOOK_PATH.read_text(encoding="utf-8")
        for marker in (
            "REAL_EVIDENCE_VAULT_RUNTIME_READY",
            "local-only",
            "append-only",
            "no network",
            "no encryption",
            "no key management",
            "digest-only protected storage",
            "migration receipt required",
            "no destructive delete",
            "no overwrite",
        ):
            self.assertIn(marker, text)

    # --- no network / subprocess / provider live surface ---

    def test_no_network_subprocess_provider_in_implementation(self):
        source_paths = [
            ROOT / "tools" / "evidence_vault" / "local_evidence_vault.py",
            ROOT / "tools" / "evidence_vault" / "evidence_envelope.py",
            ROOT / "tools" / "evidence_vault" / "evidence_index.py",
            ROOT / "tools" / "evidence_vault" / "evidence_integrity.py",
            ROOT / "tools" / "evidence_vault" / "evidence_recovery.py",
        ]
        for sp in source_paths:
            with self.subTest(source=str(sp.relative_to(ROOT))):
                src = sp.read_text(encoding="utf-8")
                self.assertNotIn("import subprocess", src, f"{sp} has subprocess")
                self.assertNotIn("import socket", src, f"{sp} has socket")
                self.assertNotIn("import requests", src, f"{sp} has requests")
                self.assertNotIn("import httpx", src, f"{sp} has httpx")
                self.assertNotIn("import urllib", src, f"{sp} has urllib")
                self.assertNotIn("os.system", src, f"{sp} has os.system")
                self.assertNotIn("openai", src, f"{sp} has openai")
                self.assertNotIn("anthropic", src, f"{sp} has anthropic")

    # --- deterministic hashing ---

    def test_envelope_creation_is_deterministic(self):
        p1 = make_valid_payload()
        p2 = make_valid_payload()
        e1 = EvidenceEnvelope.create_envelope(p1)
        e2 = EvidenceEnvelope.create_envelope(p2)
        self.assertEqual(e1["envelope_hash"], e2["envelope_hash"])
        self.assertEqual(e1["content_hash"], e2["content_hash"])

    def test_index_entry_is_deterministic(self):
        p1 = make_valid_payload()
        p2 = make_valid_payload()
        e1 = EvidenceEnvelope.create_envelope(p1)
        e2 = EvidenceEnvelope.create_envelope(p2)
        i1 = EvidenceIndex.create_index_entry(e1)
        i2 = EvidenceIndex.create_index_entry(e2)
        self.assertEqual(i1["index_record_hash"], i2["index_record_hash"])

    # --- hash verification ---

    def test_hash_verification_succeeds_with_matching_content(self):
        content = b"actual content for hashing"
        content_hash = hashlib.sha256(content).hexdigest()
        envelope = EvidenceEnvelope.create_envelope(
            make_valid_payload(content_hash=content_hash)
        )
        result = EvidenceEnvelope.verify_hash(envelope, content)
        self.assertTrue(result["hash_match"])

    def test_hash_verification_fails_with_mismatched_content(self):
        content = b"actual content"
        wrong_content = b"different content"
        content_hash = hashlib.sha256(content).hexdigest()
        envelope = EvidenceEnvelope.create_envelope(
            make_valid_payload(content_hash=content_hash)
        )
        result = EvidenceEnvelope.verify_hash(envelope, wrong_content)
        self.assertFalse(result["hash_match"])

    # --- missing required fields ---

    def test_missing_required_fields_raises(self):
        p = make_valid_payload()
        del p["artifact_id"]
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.create_envelope(p)
        self.assertIn("missing_required_fields", str(ctx.exception))

    def test_missing_artifact_id_raises(self):
        p = make_valid_payload(artifact_id="")
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.create_envelope(p)
        self.assertIn("artifact_id", str(ctx.exception))

    # --- index list_all ---

    def test_index_list_all_returns_all_entries(self):
        for i in range(3):
            p = make_valid_payload(artifact_id=f"ART-{i:03d}")
            self.vault.write_artifact(p)
        entries = EvidenceIndex.list_all(self.vault.index_path)
        self.assertEqual(len(entries), 3)

    # --- vault with multiple artifacts ---

    def test_multiple_different_artifacts_works(self):
        for i in range(5):
            p = make_valid_payload(
                artifact_id=f"ART-{i:03d}",
                content_hash=hashlib.sha256(f"content-{i}".encode()).hexdigest(),
            )
            result = self.vault.write_artifact(p)
            self.assertEqual(result["status"], "sealed")

        for i in range(5):
            envelope = self.vault.read_artifact(f"ART-{i:03d}")
            self.assertEqual(envelope["artifact_id"], f"ART-{i:03d}")

    # --- blake2b hash algorithm ---

    def test_blake2b_hash_algorithm_accepted(self):
        import hashlib as hl
        content = b"blake2b-test-content"
        content_hash = hl.blake2b(content, digest_size=64).hexdigest()
        p = make_valid_payload(content_hash=content_hash, hash_algorithm="blake2b")
        envelope = EvidenceEnvelope.create_envelope(p)
        self.assertEqual(envelope["hash_algorithm"], "blake2b")

    # --- sha512 hash algorithm ---

    def test_sha512_hash_algorithm_accepted(self):
        content = b"sha512-test-content"
        content_hash = hashlib.sha512(content).hexdigest()
        p = make_valid_payload(content_hash=content_hash, hash_algorithm="sha512")
        envelope = EvidenceEnvelope.create_envelope(p)
        self.assertEqual(envelope["hash_algorithm"], "sha512")

    # --- recovery receipt ---

    def test_recovery_receipt_generated(self):
        self.vault.write_artifact(make_valid_payload())
        receipt = self.vault.get_recovery_receipt("ART-001")
        self.assertEqual(receipt["artifact_id"], "ART-001")
        self.assertEqual(receipt["status"], "recoverable")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["receipt_id"])

    # --- migration receipt ---

    def test_migration_receipt_generated(self):
        foundation_payload = {
            "receipt_id": "foundation-rid-1",
            "artifact_id": "ART-001",
            "content_hash": VALID_SHA256,
            "hash_algorithm": "sha256",
            "artifact_type": "run_log",
            "status": "sealed",
        }
        receipt = self.vault.get_migration_receipt(foundation_payload)
        self.assertEqual(receipt["receipt_type"], "migration")
        self.assertEqual(receipt["migration_status"], "migrated_from_foundation_contract")
        self.assertEqual(receipt["artifact_id"], "ART-001")

    # --- rollback plan ---

    def test_rollback_plan_generated(self):
        self.vault.write_artifact(make_valid_payload())
        plan = self.vault.get_rollback_plan("ART-001")
        self.assertEqual(plan["artifact_id"], "ART-001")
        self.assertEqual(plan["action"], "mark_for_review")
        self.assertIn("No destructive delete", plan["description"])
        self.assertEqual(plan["module_version"], "v1")

    # --- rollback plan for missing artifact ---

    def test_rollback_plan_missing_artifact(self):
        plan = self.vault.get_rollback_plan("NONEXISTENT")
        self.assertEqual(plan["artifact_id"], "NONEXISTENT")
        self.assertEqual(plan["action"], "mark_for_review")

    # --- verify artifact integrity ---

    def test_verify_artifact_integrity_passes_for_valid(self):
        self.vault.write_artifact(make_valid_payload())
        result = self.vault.verify_artifact_integrity("ART-001")
        self.assertTrue(result["valid"])

    def test_verify_artifact_integrity_fails_for_missing(self):
        result = self.vault.verify_artifact_integrity("NONEXISTENT")
        self.assertFalse(result["valid"])
        self.assertIn("artifact_not_in_index", result["reason"])

    # --- verify index integrity ---

    def test_verify_index_integrity_passes_empty(self):
        result = self.vault.verify_index_integrity()
        self.assertTrue(result["valid"])

    def test_verify_index_integrity_passes_with_data(self):
        self.vault.write_artifact(make_valid_payload())
        result = self.vault.verify_index_integrity()
        self.assertTrue(result["valid"])
        self.assertEqual(result["total_entries"], 1)
        self.assertEqual(result["corrupt_entries"], 0)

    # --- recovery receipt for missing artifact ---

    def test_recovery_receipt_missing_artifact_raises(self):
        with self.assertRaises(LocalEvidenceVaultError) as ctx:
            self.vault.get_recovery_receipt("NONEXISTENT")
        self.assertIn("artifact_not_found_for_recovery", str(ctx.exception))

    # --- verify hash unsupported algorithm ---

    def test_verify_hash_unsupported_algo_raises(self):
        envelope = {"hash_algorithm": "md5", "content_hash": "abc"}
        with self.assertRaises(EvidenceEnvelopeError) as ctx:
            EvidenceEnvelope.verify_hash(envelope, b"test")
        self.assertIn("unsupported_hash_algorithm", str(ctx.exception))

    # --- empty lineage rejected by runtime write path ---

    def test_empty_lineage_rejected_by_runtime(self):
        p = make_valid_payload(lineage=[])
        envelope = EvidenceEnvelope.create_envelope(p)
        self.assertEqual(envelope["lineage"], [])

    # --- non-list lineage raised ---

    def test_non_list_lineage_raises(self):
        p = make_valid_payload(lineage="not-a-list")
        with self.assertRaises(TypeError):
            EvidenceEnvelope.create_envelope(p)

    # --- immutable non-bool raises ---

    def test_immutable_non_bool_raises(self):
        p = make_valid_payload(immutable="yes")
        with self.assertRaises(TypeError):
            EvidenceEnvelope.create_envelope(p)

    # --- append_only non-bool raises ---

    def test_append_only_non_bool_raises(self):
        p = make_valid_payload(append_only="yes")
        with self.assertRaises(TypeError):
            EvidenceEnvelope.create_envelope(p)

    # --- deterministic created_at fallback ---

    def test_empty_created_at_gets_default(self):
        p = make_valid_payload(created_at="")
        envelope = EvidenceEnvelope.create_envelope(p)
        self.assertEqual(envelope["created_at"], "1970-01-01T00:00:00Z")

    # --- conflicting duplicate on disk rejected ---

    def test_existing_envelope_on_disk_rejected(self):
        p = make_valid_payload()
        # Manually create an envelope to simulate existing file
        envelope_path = self.vault._storage_envelope_path("ART-001")
        os.makedirs(os.path.dirname(envelope_path), exist_ok=True)
        with open(envelope_path, "w") as f:
            json.dump({"artifact_id": "ART-001"}, f)
        with self.assertRaises(LocalEvidenceVaultError) as ctx:
            self.vault.write_artifact(p)
        self.assertIn("duplicate_artifact_id_rejected", str(ctx.exception))

    # --- migration receipt non-mapping ---

    def test_migration_receipt_non_mapping_raises(self):
        with self.assertRaises(TypeError):
            self.vault.get_migration_receipt("not a dict")


if __name__ == "__main__":
    unittest.main()
