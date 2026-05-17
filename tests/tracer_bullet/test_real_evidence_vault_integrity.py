"""Tracer bullet tests for real evidence vault integrity.

Covers:
- corrupted payload detected
- corrupted index detected
- digest verification
- envelope integrity checks
- storage envelope verification
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

from evidence_vault import EvidenceIntegrity
from evidence_vault.evidence_integrity import EvidenceIntegrityError


class RealEvidenceVaultIntegrityTests(unittest.TestCase):
    """Integrity verification tests for the evidence vault."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmpdir.cleanup()

    # --- corrupted payload detected ---

    def test_corrupted_payload_detected(self):
        payload_path = os.path.join(self._tmpdir.name, "artifact.json")
        original_content = b"original content"
        expected_hash = hashlib.sha256(original_content).hexdigest()

        # Write original
        with open(payload_path, "wb") as f:
            f.write(original_content)

        # Verify original
        result = EvidenceIntegrity.verify_payload_integrity(payload_path, expected_hash)
        self.assertTrue(result["valid"])
        self.assertEqual(result["reason"], "hash_match")

        # Corrupt the file
        with open(payload_path, "wb") as f:
            f.write(b"corrupted content")

        # Verify corruption
        result = EvidenceIntegrity.verify_payload_integrity(payload_path, expected_hash)
        self.assertFalse(result["valid"])
        self.assertIn("corruption", result["reason"])

    # --- corrupted index detected ---

    def test_corrupted_index_detected(self):
        index_path = os.path.join(self._tmpdir.name, "index.jsonl")

        # Write valid entries
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"artifact_id": "A", "index_key": "k1", "content_hash": "h1"}) + "\n")
            f.write(json.dumps({"artifact_id": "B", "index_key": "k2", "content_hash": "h2"}) + "\n")

        result = EvidenceIntegrity.verify_index_integrity(index_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["total_entries"], 2)
        self.assertEqual(result["corrupt_entries"], 0)

        # Corrupt: add a line that is not valid JSON
        with open(index_path, "a", encoding="utf-8") as f:
            f.write("not valid json!!!\n")

        result = EvidenceIntegrity.verify_index_integrity(index_path)
        self.assertFalse(result["valid"])
        self.assertIn("corruption", result["reason"])
        self.assertEqual(result["total_entries"], 3)
        self.assertEqual(result["corrupt_entries"], 1)

    # --- corrupted index with missing fields ---

    def test_corrupted_index_missing_fields_detected(self):
        index_path = os.path.join(self._tmpdir.name, "index.jsonl")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"artifact_id": "A", "index_key": "k1", "content_hash": "h1"}) + "\n")
            f.write(json.dumps({"bad_field": "no_required_fields"}) + "\n")

        result = EvidenceIntegrity.verify_index_integrity(index_path)
        self.assertFalse(result["valid"])
        self.assertEqual(result["corrupt_entries"], 1)

    # --- empty index is valid ---

    def test_empty_index_is_valid(self):
        index_path = os.path.join(self._tmpdir.name, "nonexistent.jsonl")
        result = EvidenceIntegrity.verify_index_integrity(index_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["total_entries"], 0)
        self.assertEqual(result["reason"], "no_index_file_empty_state")

    # --- missing payload file detected ---

    def test_missing_payload_file_detected(self):
        result = EvidenceIntegrity.verify_payload_integrity(
            os.path.join(self._tmpdir.name, "nonexistent.json"),
            "a" * 64,
        )
        self.assertFalse(result["valid"])
        self.assertIn("payload_file_missing", result["reason"])

    # --- compute_digest ---

    def test_compute_digest_sha256(self):
        digest = EvidenceIntegrity.compute_digest(b"hello", "sha256")
        expected = hashlib.sha256(b"hello").hexdigest()
        self.assertEqual(digest, expected)

    def test_compute_digest_sha512(self):
        digest = EvidenceIntegrity.compute_digest(b"hello", "sha512")
        expected = hashlib.sha512(b"hello").hexdigest()
        self.assertEqual(digest, expected)

    def test_compute_digest_blake2b(self):
        digest = EvidenceIntegrity.compute_digest(b"hello", "blake2b")
        expected = hashlib.blake2b(b"hello", digest_size=64).hexdigest()
        self.assertEqual(digest, expected)

    def test_compute_digest_unsupported_algorithm(self):
        with self.assertRaises(EvidenceIntegrityError) as ctx:
            EvidenceIntegrity.compute_digest(b"hello", "md5")
        self.assertIn("unsupported_hash_algorithm", str(ctx.exception))

    # --- verify_storage_envelope ---

    def test_verify_storage_envelope_valid(self):
        # Build an envelope with a correctly computed envelope_hash so
        # the new hash-recomputation check (DEFECT-4) passes.
        payload = {
            "artifact_id": "ART-001",
            "artifact_type": "run_log",
            "content_hash": "a" * 64,
            "hash_algorithm": "sha256",
            "created_at": "2025-01-01T00:00:00Z",
            "producer": "test",
            "lineage": ["l1"],
            "immutable": True,
            "append_only": True,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        correct_hash = hashlib.sha256(canonical).hexdigest()
        envelope = {**payload, "envelope_hash": correct_hash}
        result = EvidenceIntegrity.verify_storage_envelope(envelope)
        self.assertTrue(result["valid"])

    def test_verify_storage_envelope_missing_fields(self):
        envelope = {
            "artifact_id": "ART-001",
            "content_hash": "a" * 64,
        }
        result = EvidenceIntegrity.verify_storage_envelope(envelope)
        self.assertFalse(result["valid"])
        self.assertIn("has_envelope_hash", result["checks"])
        self.assertFalse(result["checks"].get("has_envelope_hash", True))

    def test_verify_storage_envelope_immutable_false(self):
        envelope = {
            "artifact_id": "ART-001",
            "content_hash": "a" * 64,
            "envelope_hash": "b" * 64,
            "hash_algorithm": "sha256",
            "created_at": "2025-01-01T00:00:00Z",
            "producer": "test",
            "lineage": ["l1"],
            "immutable": False,
            "append_only": True,
        }
        result = EvidenceIntegrity.verify_storage_envelope(envelope)
        self.assertFalse(result["valid"])

    def test_verify_storage_envelope_append_only_false(self):
        envelope = {
            "artifact_id": "ART-001",
            "content_hash": "a" * 64,
            "envelope_hash": "b" * 64,
            "hash_algorithm": "sha256",
            "created_at": "2025-01-01T00:00:00Z",
            "producer": "test",
            "lineage": ["l1"],
            "immutable": True,
            "append_only": False,
        }
        result = EvidenceIntegrity.verify_storage_envelope(envelope)
        self.assertFalse(result["valid"])

    # --- non-mapping payload raises for all checks ---

    def test_non_mapping_verify_payload_integrity(self):
        with self.assertRaises(TypeError):
            EvidenceIntegrity.verify_storage_envelope("not a dict")

    # --- deterministic digest verification ---

    def test_digest_verification_is_deterministic(self):
        data = b"deterministic test data"
        d1 = EvidenceIntegrity.compute_digest(data, "sha256")
        d2 = EvidenceIntegrity.compute_digest(data, "sha256")
        self.assertEqual(d1, d2)

    # --- multiple corrupt entries ---

    def test_multiple_corrupt_entries_detected(self):
        index_path = os.path.join(self._tmpdir.name, "index.jsonl")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"artifact_id": "A", "index_key": "k1", "content_hash": "h1"}) + "\n")
            f.write("garbage line 1\n")
            f.write(json.dumps({"artifact_id": "B", "index_key": "k2", "content_hash": "h2"}) + "\n")
            f.write("garbage line 2\n")

        result = EvidenceIntegrity.verify_index_integrity(index_path)
        self.assertFalse(result["valid"])
        self.assertEqual(result["corrupt_entries"], 2)
        self.assertEqual(len(result["corrupt_line_numbers"]), 2)

    # --- payload with sha512 ---

    def test_verify_payload_integrity_sha512(self):
        payload_path = os.path.join(self._tmpdir.name, "artifact.json")
        content = b"sha512 content"
        expected_hash = hashlib.sha512(content).hexdigest()

        with open(payload_path, "wb") as f:
            f.write(content)

        result = EvidenceIntegrity.verify_payload_integrity(payload_path, expected_hash, "sha512")
        self.assertTrue(result["valid"])

    # --- payload with blake2b ---

    def test_verify_payload_integrity_blake2b(self):
        payload_path = os.path.join(self._tmpdir.name, "artifact.json")
        content = b"blake2b content"
        expected_hash = hashlib.blake2b(content, digest_size=64).hexdigest()

        with open(payload_path, "wb") as f:
            f.write(content)

        result = EvidenceIntegrity.verify_payload_integrity(payload_path, expected_hash, "blake2b")
        self.assertTrue(result["valid"])

    # --- empty file integrity ---

    def test_empty_file_integrity(self):
        payload_path = os.path.join(self._tmpdir.name, "empty.json")
        with open(payload_path, "wb") as f:
            f.write(b"")

        expected_hash = hashlib.sha256(b"").hexdigest()
        result = EvidenceIntegrity.verify_payload_integrity(payload_path, expected_hash)
        self.assertTrue(result["valid"])

    # --- index with empty lines is valid ---

    def test_index_with_empty_lines_is_valid(self):
        index_path = os.path.join(self._tmpdir.name, "index.jsonl")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"artifact_id": "A", "index_key": "k1", "content_hash": "h1"}) + "\n")
            f.write("\n")
            f.write(json.dumps({"artifact_id": "B", "index_key": "k2", "content_hash": "h2"}) + "\n")
            f.write("\n")

        result = EvidenceIntegrity.verify_index_integrity(index_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["total_entries"], 2)
        self.assertEqual(result["corrupt_entries"], 0)

    # --- unreadable file ---

    def test_unreadable_payload_handled_gracefully(self):
        result = EvidenceIntegrity.verify_payload_integrity(
            os.path.join(self._tmpdir.name, "nonexistent.json"),
            "a" * 64,
        )
        self.assertFalse(result["valid"])

    # ==================================================================
    # AUDIT-HARDENING TESTS
    # ==================================================================

    # --- DEFECT-4: verify_storage_envelope detects hash mismatch ---

    def test_verify_storage_envelope_hash_mismatch_returns_invalid(self):
        """DEFECT-4: verify_storage_envelope detects when envelope_hash is wrong."""
        envelope = {
            "artifact_id": "ART-001",
            "artifact_type": "run_log",
            "content_hash": "a" * 64,
            "hash_algorithm": "sha256",
            "created_at": "2025-01-01T00:00:00Z",
            "producer": "test",
            "lineage": ["l1"],
            "immutable": True,
            "append_only": True,
            "envelope_hash": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        }
        result = EvidenceIntegrity.verify_storage_envelope(envelope)
        self.assertFalse(result["valid"],
                         "verify_storage_envelope must detect hash mismatch")
        self.assertFalse(result["checks"]["envelope_hash_match"],
                         "envelope_hash_match must be False on mismatch")

    def test_verify_storage_envelope_valid_with_correct_hash(self):
        """DEFECT-4: verify_storage_envelope passes when hash matches."""
        # Build a known-good envelope with a correct envelope_hash
        payload = {
            "artifact_id": "ART-OK",
            "artifact_type": "run_log",
            "content_hash": "a" * 64,
            "hash_algorithm": "sha256",
            "created_at": "2025-06-01T00:00:00Z",
            "producer": "test",
            "lineage": ["l1"],
            "immutable": True,
            "append_only": True,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        correct_hash = hashlib.sha256(canonical).hexdigest()
        envelope = {**payload, "envelope_hash": correct_hash}
        result = EvidenceIntegrity.verify_storage_envelope(envelope)
        self.assertTrue(result["valid"],
                        f"verify_storage_envelope must pass with correct hash: {result}")
        self.assertTrue(result["checks"]["envelope_hash_match"])


if __name__ == "__main__":
    unittest.main()
