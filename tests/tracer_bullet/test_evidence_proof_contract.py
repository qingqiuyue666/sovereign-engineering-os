import hashlib
import unittest
from pathlib import Path

from kernel.evidence.evidence_proof_contract import (
    EvidenceProofContractViolation,
    validate_evidence_proof_record,
)


class EvidenceProofContractTests(unittest.TestCase):
    def digest(self, text="payload"):
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    def base_record(self, **overrides):
        record = {
            "proof_id": "proof-001",
            "proof_kind": "sha256_digest",
            "classification": "public",
            "subject_evidence_id": "ev-001",
            "digest": self.digest("ev-001"),
            "algorithm": "sha256",
            "payload": {"shape": "hash_only"},
            "encrypted_vault_implemented": False,
            "real_hmac_key_read": False,
            "real_merkle_tree_built": False,
            "zero_knowledge_proof_built": False,
            "secret_value_read": False,
            "runtime_execution_performed": False,
            "network_accessed": False,
        }
        record.update(overrides)
        return record

    def test_sha256_digest_record_is_accepted(self):
        result = validate_evidence_proof_record(self.base_record())

        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.proof_kind, "sha256_digest")
        self.assertEqual(result.classification, "public")
        self.assertFalse(result.placeholder_only)

    def test_redacted_digest_record_is_accepted(self):
        result = validate_evidence_proof_record(
            self.base_record(
                proof_kind="redacted_digest",
                classification="restricted",
                algorithm="redacted_sha256",
                digest=self.digest("redacted"),
                payload={"raw_prompt_persisted": False},
            )
        )

        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.proof_kind, "redacted_digest")
        self.assertEqual(result.classification, "restricted")
        self.assertFalse(result.placeholder_only)

    def test_hmac_placeholder_record_is_accepted_without_real_key(self):
        result = validate_evidence_proof_record(
            self.base_record(
                proof_kind="hmac_placeholder",
                classification="secret",
                digest="hmac_placeholder",
                algorithm="hmac_sha256_placeholder",
                key_id="placeholder",
            )
        )

        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(result.placeholder_only)

    def test_merkle_placeholder_record_is_accepted_without_real_tree(self):
        result = validate_evidence_proof_record(
            self.base_record(
                proof_kind="merkle_placeholder",
                classification="secret",
                digest="merkle_placeholder",
                algorithm="merkle_sha256_placeholder",
                merkle_root="placeholder",
            )
        )

        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(result.placeholder_only)

    def test_real_hmac_key_is_forbidden(self):
        result = validate_evidence_proof_record(
            self.base_record(
                proof_kind="hmac_placeholder",
                classification="secret",
                digest="hmac_placeholder",
                algorithm="hmac_sha256_placeholder",
                key_id="real-key-001",
            )
        )

        self.assertFalse(result.accepted)
        self.assertIn("real_hmac_key_forbidden", result.failures)

    def test_real_merkle_root_is_forbidden(self):
        result = validate_evidence_proof_record(
            self.base_record(
                proof_kind="merkle_placeholder",
                classification="secret",
                digest="merkle_placeholder",
                algorithm="merkle_sha256_placeholder",
                merkle_root=self.digest("real-root"),
            )
        )

        self.assertFalse(result.accepted)
        self.assertIn("real_merkle_root_forbidden", result.failures)

    def test_invalid_shape_is_rejected(self):
        result = validate_evidence_proof_record(
            self.base_record(proof_id="", proof_kind="unknown", digest="bad")
        )

        self.assertFalse(result.accepted)
        self.assertIn("proof_id_required", result.failures)
        self.assertIn("proof_kind_invalid", result.failures)

    def test_runtime_network_secret_and_vault_claims_are_rejected(self):
        result = validate_evidence_proof_record(
            self.base_record(
                encrypted_vault_implemented=True,
                real_hmac_key_read=True,
                real_merkle_tree_built=True,
                zero_knowledge_proof_built=True,
                secret_value_read=True,
                runtime_execution_performed=True,
                network_accessed=True,
            )
        )

        self.assertFalse(result.accepted)
        for failure in (
            "encrypted_vault_implementation_forbidden",
            "real_hmac_key_read_forbidden",
            "real_merkle_tree_build_forbidden",
            "zero_knowledge_proof_build_forbidden",
            "secret_value_read_forbidden",
            "runtime_execution_forbidden",
            "network_access_forbidden",
        ):
            self.assertIn(failure, result.failures)

    def test_raw_fields_and_plaintext_secret_markers_are_rejected(self):
        result = validate_evidence_proof_record(
            self.base_record(
                payload={
                    "raw_prompt": "copy this prompt",
                    "note": "OPENAI_API_KEY=sk-test-secret-value",
                }
            )
        )

        self.assertFalse(result.accepted)
        self.assertIn("forbidden_raw_field_present", result.failures)
        self.assertIn("plaintext_secret_marker_present", result.failures)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(EvidenceProofContractViolation):
            validate_evidence_proof_record(["not", "mapping"])

    def test_source_does_not_introduce_crypto_runtime_or_network_surface(self):
        source = Path("kernel/evidence/evidence_proof_contract.py").read_text(encoding="utf-8")
        forbidden_markers = (
            "hmac.new",
            "secrets.",
            "requests",
            "httpx",
            "urllib",
            "socket.",
            "subprocess",
            "os.system",
            "sqlite3",
            "openai.",
            "getenv",
            "environ",
            "write_text(",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
