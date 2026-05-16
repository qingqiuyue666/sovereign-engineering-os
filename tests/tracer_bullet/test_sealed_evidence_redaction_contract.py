import unittest

from kernel.evidence.sealed_redaction_contract import (
    EvidenceContractViolation,
    classify_evidence_payload,
    redacted_digest,
    validate_sealed_evidence_record,
)


class SealedEvidenceRedactionContractTests(unittest.TestCase):
    def digest(self, text="payload"):
        import hashlib

        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_public_evidence_hash_only_record_is_accepted(self):
        result = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-public-001",
                "classification": "public",
                "digest": self.digest("public"),
                "payload": {"test_result": "ok", "commit": "abc123"},
            }
        )

        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.classification, "public")
        self.assertFalse(result.sealed_required)
        self.assertFalse(result.redaction_required)

    def test_restricted_evidence_redacted_record_is_accepted(self):
        result = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-restricted-001",
                "classification": "restricted",
                "digest": self.digest("restricted"),
                "payload": {
                    "classification": "restricted",
                    "prompt_sha256": self.digest("prompt"),
                    "raw_prompt_persisted": False,
                },
            }
        )

        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.classification, "restricted")
        self.assertFalse(result.sealed_required)
        self.assertTrue(result.redaction_required)

    def test_secret_evidence_hash_only_record_is_accepted(self):
        result = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-secret-001",
                "classification": "secret",
                "digest": self.digest("secret"),
                "representation": "sha256",
                "payload": {
                    "contains_sensitive_material": True,
                    "stored_as": "hash_only",
                },
            }
        )

        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(result.sealed_required)
        self.assertTrue(result.redaction_required)

    def test_secret_evidence_sealed_blob_requires_reference(self):
        missing = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-secret-002",
                "classification": "secret",
                "digest": self.digest("secret"),
                "representation": "sealed_blob_ref",
                "payload": {"contains_sensitive_material": True},
            }
        )
        self.assertFalse(missing.accepted)
        self.assertIn("sealed_ref_required", missing.failures)

        present = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-secret-003",
                "classification": "secret",
                "digest": self.digest("secret"),
                "representation": "sealed_blob_ref",
                "sealed_ref": "sealed://vault/ev-secret-003",
                "payload": {"contains_sensitive_material": True},
            }
        )
        self.assertTrue(present.accepted, present.failures)

    def test_raw_prompt_and_raw_provider_response_are_rejected(self):
        for forbidden_field in ("raw_prompt", "raw_provider_response"):
            result = validate_sealed_evidence_record(
                {
                    "evidence_id": "ev-forbidden-" + forbidden_field,
                    "classification": "restricted",
                    "digest": self.digest(forbidden_field),
                    "payload": {forbidden_field: "plain text must not persist"},
                }
            )
            self.assertFalse(result.accepted)
            self.assertIn("forbidden_raw_secret_field_present", result.failures)

    def test_secret_markers_and_plaintext_tokens_are_rejected(self):
        result = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-secret-leak",
                "classification": "secret",
                "digest": self.digest("leak"),
                "representation": "sha256",
                "payload": {"note": "OPENAI_API_KEY=sk-test-secret-value"},
            }
        )

        self.assertFalse(result.accepted)
        self.assertIn("plaintext_secret_marker_present", result.failures)

    def test_public_evidence_cannot_carry_sensitive_material(self):
        result = validate_sealed_evidence_record(
            {
                "evidence_id": "ev-public-secret",
                "classification": "public",
                "digest": self.digest("public-secret"),
                "payload": {"contains_sensitive_material": True},
            }
        )

        self.assertFalse(result.accepted)
        self.assertIn("public_evidence_contains_sensitive_material", result.failures)

    def test_classification_detects_secret_payload_without_copying_value(self):
        self.assertEqual(
            classify_evidence_payload({"contains_sensitive_material": True}),
            "secret",
        )
        self.assertEqual(
            classify_evidence_payload({"classification": "restricted"}),
            "restricted",
        )
        self.assertEqual(
            classify_evidence_payload({"test_result": "ok"}),
            "public",
        )

    def test_redacted_digest_is_stable_and_does_not_require_secret_read(self):
        payload_a = {"api_key": "sk-one", "shape": {"field": "value"}}
        payload_b = {"api_key": "sk-two", "shape": {"field": "value"}}

        self.assertEqual(redacted_digest(payload_a), redacted_digest(payload_b))
        self.assertTrue(redacted_digest(payload_a).startswith("sha256:"))

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(EvidenceContractViolation):
            classify_evidence_payload(["not", "mapping"])

    def test_contract_source_contains_no_runtime_or_network_surface(self):
        from pathlib import Path

        source = Path("kernel/evidence/sealed_redaction_contract.py").read_text(
            encoding="utf-8"
        )
        forbidden_markers = (
            "requests",
            "httpx",
            "urllib",
            "socket.",
            "subprocess",
            "os.system",
            "openai.",
            "write_text(",
            "append(",
            "sqlite3",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
