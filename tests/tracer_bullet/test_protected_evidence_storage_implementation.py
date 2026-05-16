import copy
import json
import unittest
from pathlib import Path

from kernel.evidence.protected_evidence_storage_implementation import (
    ProtectedEvidenceStorageImplementationViolation,
    validate_access_decision,
    validate_deletion_tombstone,
    validate_digest_only_envelope,
    validate_implementation_manifest,
    validate_implementation_report,
    validate_migration_receipt,
    validate_recovery_plan,
    validate_rollback_plan,
    validate_storage_backend_boundary,
)

POLICY_PATH = Path("governance/evidence/protected_evidence_storage_implementation_v1.json")
FIXTURE_PATH = Path("governance/evidence/fixtures/protected_evidence_storage_implementation_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {
    "validate_storage_backend_boundary": validate_storage_backend_boundary,
    "validate_digest_only_envelope": validate_digest_only_envelope,
    "validate_implementation_manifest": validate_implementation_manifest,
    "validate_migration_receipt": validate_migration_receipt,
    "validate_access_decision": validate_access_decision,
    "validate_deletion_tombstone": validate_deletion_tombstone,
    "validate_recovery_plan": validate_recovery_plan,
    "validate_rollback_plan": validate_rollback_plan,
    "validate_implementation_report": validate_implementation_report,
}
FORBIDDEN_FLAGS = (
    "plaintext_secret_persisted",
    "raw_prompt_persisted",
    "raw_provider_response_persisted",
    "key_material_read",
    "key_material_persisted",
    "secret_value_read",
    "secret_value_persisted",
    "encrypted_vault_claimed",
    "encryption_performed",
    "decryption_performed",
    "sqlite_schema_changed",
    "audit_append_performed",
    "network_accessed",
    "provider_call_performed",
    "raw_evidence_store_allowed",
)

class ProtectedEvidenceStorageImplementationTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}

    def test_policy_map_is_accepted_implementation_boundary(self):
        result = validate_storage_backend_boundary(self.load_policy())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.verdict, "accepted_implementation_boundary")
        self.assertEqual(result.contract_section, "backend_boundary")

    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"])
                self.assertTrue(result.accepted, result.failures)
                self.assertEqual(result.contract_section, item["expected_section"])

    def test_invalid_fixtures_are_rejected(self):
        valid_records = self.valid_by_validator()
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                base = copy.deepcopy(valid_records[item["validator"]])
                base.update(item["record_patch"])
                result = VALIDATORS[item["validator"]](base)
                self.assertFalse(result.accepted)
                for failure in item["expected_failures"]:
                    self.assertIn(failure, result.failures)

    def test_all_forbidden_flags_fail_closed_for_policy(self):
        base = self.load_policy()
        for flag in FORBIDDEN_FLAGS:
            payload = copy.deepcopy(base)
            payload[flag] = True
            with self.subTest(flag=flag):
                result = validate_storage_backend_boundary(payload)
                self.assertFalse(result.accepted)
                self.assertIn(f"{flag}_forbidden", result.failures)

    def test_digest_only_envelope_rejects_payload_material(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_digest_only_envelope"])
        payload["payload_material_persisted"] = True
        payload["raw_provider_response"] = "forbidden"
        result = validate_digest_only_envelope(payload)
        self.assertFalse(result.accepted)
        self.assertIn("payload_material_persisted_must_be_false", result.failures)
        self.assertIn("high_risk_key_forbidden", result.failures)

    def test_migration_receipt_requires_generic_enforcement_and_rollback(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_migration_receipt"])
        payload["generic_payload_enforcement_verified"] = False
        payload["rollback_plan_verified"] = False
        result = validate_migration_receipt(payload)
        self.assertFalse(result.accepted)
        self.assertIn("generic_payload_enforcement_verified_missing", result.failures)
        self.assertIn("rollback_plan_verified_missing", result.failures)

    def test_access_decision_blocks_plaintext_and_key_material(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_access_decision"])
        payload["plaintext_access_allowed"] = True
        payload["key_material_access_allowed"] = True
        result = validate_access_decision(payload)
        self.assertFalse(result.accepted)
        self.assertIn("plaintext_access_allowed_must_be_false", result.failures)
        self.assertIn("key_material_access_allowed_must_be_false", result.failures)

    def test_report_requires_all_sections_and_no_encrypted_vault_claim(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_implementation_report"])
        payload["validated_sections"] = ["backend_boundary"]
        payload["encrypted_vault_ready"] = True
        result = validate_implementation_report(payload)
        self.assertFalse(result.accepted)
        self.assertIn("digest_only_envelope_section_missing", result.failures)
        self.assertIn("implementation_manifest_section_missing", result.failures)
        self.assertIn("migration_receipt_section_missing", result.failures)
        self.assertIn("access_decision_section_missing", result.failures)
        self.assertIn("deletion_tombstone_section_missing", result.failures)
        self.assertIn("recovery_plan_section_missing", result.failures)
        self.assertIn("rollback_plan_section_missing", result.failures)
        self.assertIn("encrypted_vault_ready_must_be_false", result.failures)

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(ProtectedEvidenceStorageImplementationViolation):
            validate_storage_backend_boundary(["not", "mapping"])

    def test_makefile_declares_protected_storage_implementation_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("test-protected-evidence-storage-implementation", text)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_protected_evidence_storage_implementation -v", text)
        self.assertIn(EXPECTED_HEALTH, text)
        self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"))
        self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"), EXPECTED_HEALTH.index("test-real-hmac-policy-realization"))

    def test_source_does_not_introduce_real_storage_or_key_surface(self):
        source = Path("kernel/evidence/protected_evidence_storage_implementation.py").read_text(encoding="utf-8")
        for marker in ("open(", "write_text(", "sqlite3", "cryptography", "Fernet", "AES", "requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "getenv", "os.environ", ".environ", "audit_append(", "ledger_append("):
            self.assertNotIn(marker, source)

    def test_runbook_exists_and_records_implementation_boundary(self):
        path = Path("docs/runbooks/protected_evidence_storage_implementation_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "PROTECTED_EVIDENCE_STORAGE_IMPLEMENTATION_BOUNDARY_READY",
            "digest-only envelope",
            "no encrypted vault claim",
            "no key material read",
            "no plaintext secret persistence",
            "rollback plan required",
        ):
            self.assertIn(marker, text)

if __name__ == "__main__":
    unittest.main()
