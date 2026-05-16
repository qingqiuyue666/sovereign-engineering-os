import json
import unittest
from pathlib import Path

from kernel.evidence.evidence_proof_contract import validate_evidence_proof_record


FIXTURES_PATH = Path("governance/evidence/fixtures/evidence_proof_records_v1.json")


class EvidenceProofFixturesTests(unittest.TestCase):
    def load_fixtures(self):
        self.assertTrue(FIXTURES_PATH.is_file(), str(FIXTURES_PATH))
        return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))

    def test_fixture_top_level_shape_and_no_runtime_posture(self):
        payload = self.load_fixtures()
        self.assertEqual(payload["fixture_type"], "seos_evidence_proof_records_v1")
        self.assertEqual(payload["version"], "v1")
        self.assertEqual(payload["status"], "fixture_only_no_runtime")
        self.assertFalse(payload["runtime_execution_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["secret_value_read"])
        self.assertFalse(payload["secret_value_persisted"])
        self.assertFalse(payload["sqlite_schema_changed"])
        self.assertFalse(payload["encrypted_vault_implemented"])
        self.assertFalse(payload["real_hmac_implemented"])
        self.assertFalse(payload["real_merkle_implemented"])
        self.assertFalse(payload["zero_knowledge_proof_implemented"])
        self.assertFalse(payload["raw_evidence_store_allowed"])
        self.assertEqual(len(payload["valid_records"]), 4)
        self.assertGreaterEqual(len(payload["invalid_records"]), 9)

    def test_valid_records_are_accepted_by_contract(self):
        payload = self.load_fixtures()
        expected_ids = {
            "valid_sha256_digest_public",
            "valid_redacted_digest_restricted",
            "valid_hmac_placeholder_secret",
            "valid_merkle_placeholder_secret",
        }
        actual_ids = {fixture["fixture_id"] for fixture in payload["valid_records"]}
        self.assertEqual(actual_ids, expected_ids)
        for fixture in payload["valid_records"]:
            with self.subTest(fixture_id=fixture["fixture_id"]):
                result = validate_evidence_proof_record(fixture["record"])
                self.assertTrue(result.accepted, result.failures)
                self.assertTrue(fixture["expected_accepted"])

    def test_invalid_records_are_rejected_by_contract_with_expected_failures(self):
        payload = self.load_fixtures()
        expected_ids = {
            "invalid_real_hmac_key_present",
            "invalid_real_merkle_root_present",
            "invalid_encrypted_vault_claimed",
            "invalid_zero_knowledge_proof_claimed",
            "invalid_secret_value_read_claimed",
            "invalid_runtime_execution_claimed",
            "invalid_network_access_claimed",
            "invalid_raw_prompt_present",
            "invalid_plaintext_secret_marker_present",
        }
        actual_ids = {fixture["fixture_id"] for fixture in payload["invalid_records"]}
        self.assertEqual(actual_ids, expected_ids)
        for fixture in payload["invalid_records"]:
            with self.subTest(fixture_id=fixture["fixture_id"]):
                result = validate_evidence_proof_record(fixture["record"])
                self.assertFalse(result.accepted)
                self.assertFalse(fixture["expected_accepted"])
                for expected_failure in fixture["expected_failures"]:
                    self.assertIn(expected_failure, result.failures)

    def test_placeholder_valid_records_remain_placeholder_only(self):
        payload = self.load_fixtures()
        placeholder_ids = {
            "valid_hmac_placeholder_secret",
            "valid_merkle_placeholder_secret",
        }
        for fixture in payload["valid_records"]:
            if fixture["fixture_id"] not in placeholder_ids:
                continue
            result = validate_evidence_proof_record(fixture["record"])
            self.assertTrue(result.accepted, result.failures)
            self.assertTrue(result.placeholder_only)

    def test_fixtures_do_not_contain_raw_secret_or_runtime_surface(self):
        serialized = FIXTURES_PATH.read_text(encoding="utf-8").lower()
        forbidden_markers = (
            "openai_api_key",
            "bearer ",
            "password=",
            "private_key",
            "subprocess",
            "requests.",
            "httpx.",
            "socket.",
            "sqlite3",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, serialized)

    def test_decision_doc_exists_and_records_fixture_only_posture(self):
        path = Path("docs/decisions/evidence_proof_fixtures_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "EVIDENCE_PROOF_FIXTURES_READY_FOR_LOCAL_TESTS",
            "fixture_only_no_runtime",
            "sha256_digest",
            "redacted_digest",
            "hmac_placeholder",
            "merkle_placeholder",
            "real_hmac_key_present",
            "real_merkle_root_present",
            "encrypted_vault_claimed",
            "zero_knowledge_proof_claimed",
            "no runtime execution",
            "no network access",
            "no secret read",
            "no SQLite schema change",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
