import copy
import json
import unittest
from pathlib import Path

from kernel.evidence.protected_evidence_storage_contract import (
    ProtectedEvidenceStorageContractViolation,
    validate_access_policy,
    validate_deletion_policy,
    validate_protected_storage_policy,
    validate_recovery_policy,
    validate_storage_contract_report,
    validate_storage_manifest,
)

POLICY_PATH = Path("governance/evidence/protected_evidence_storage_contract_v1.json")
FIXTURE_PATH = Path("governance/evidence/fixtures/protected_evidence_storage_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {"validate_protected_storage_policy": validate_protected_storage_policy, "validate_storage_manifest": validate_storage_manifest, "validate_access_policy": validate_access_policy, "validate_recovery_policy": validate_recovery_policy, "validate_deletion_policy": validate_deletion_policy, "validate_storage_contract_report": validate_storage_contract_report}
FORBIDDEN_FLAGS = ("implementation_enabled", "encrypted_vault_implemented", "protected_storage_implemented", "key_material_read", "key_material_persisted", "plaintext_secret_allowed", "raw_prompt_allowed", "raw_provider_response_allowed", "runtime_execution_performed", "network_accessed", "sqlite_schema_changed", "audit_append_performed")

class ProtectedEvidenceStorageContractTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH)); return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH)); return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    def valid_by_validator(self): return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}
    def test_policy_map_is_accepted_contract_only(self):
        result = validate_protected_storage_policy(self.load_policy()); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.contract_section, "policy")
    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"]); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.contract_section, item["expected_section"])
    def test_invalid_fixtures_are_rejected(self):
        valid_records = self.valid_by_validator()
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                base = copy.deepcopy(valid_records[item["validator"]]); base.update(item["record_patch"]); result = VALIDATORS[item["validator"]](base); self.assertFalse(result.accepted)
                for failure in item["expected_failures"]: self.assertIn(failure, result.failures)
    def test_all_forbidden_flags_fail_closed_for_policy(self):
        base = self.load_policy()
        for flag in FORBIDDEN_FLAGS:
            payload = copy.deepcopy(base); payload[flag] = True
            with self.subTest(flag=flag): self.assertIn(f"{flag}_forbidden", validate_protected_storage_policy(payload).failures)
    def test_manifest_access_recovery_and_deletion_are_required(self):
        policy = self.load_policy()
        for flag in ("storage_manifest_required", "access_policy_required", "recovery_policy_required", "deletion_policy_required", "migration_receipt_required_before_implementation"):
            payload = copy.deepcopy(policy); payload[flag] = False
            with self.subTest(flag=flag): self.assertIn(f"{flag}_missing", validate_protected_storage_policy(payload).failures)
    def test_access_policy_rejects_plaintext_and_key_access(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_access_policy"]); payload["plaintext_access_allowed"] = True; payload["key_material_access_allowed"] = True; result = validate_access_policy(payload); self.assertIn("plaintext_access_must_be_false", result.failures); self.assertIn("key_material_access_must_be_false", result.failures)
    def test_report_requires_all_sections_and_no_implementation_ready(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_storage_contract_report"]); payload["validated_sections"] = ["policy"]; payload["implementation_ready"] = True; result = validate_storage_contract_report(payload); self.assertIn("storage_manifest_section_missing", result.failures); self.assertIn("implementation_ready_must_be_false", result.failures)
    def test_non_mapping_payload_raises(self):
        with self.assertRaises(ProtectedEvidenceStorageContractViolation): validate_protected_storage_policy(["not", "mapping"])
    def test_makefile_declares_protected_storage_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8"); self.assertIn("test-protected-evidence-storage", text); self.assertIn(EXPECTED_HEALTH, text); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation")); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"), EXPECTED_HEALTH.index("test-real-hmac-policy-realization")); self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement")); self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"), EXPECTED_HEALTH.index("test-schemas"))
    def test_source_does_not_introduce_crypto_storage_or_runtime_surface(self):
        source = Path("kernel/evidence/protected_evidence_storage_contract.py").read_text(encoding="utf-8")
        for marker in ("cryptography", "sqlite3", "requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text("):
            self.assertNotIn(marker, source)
    def test_runbook_exists_and_records_contract_boundary(self):
        text = Path("docs/runbooks/protected_evidence_storage_contract_v1.md").read_text(encoding="utf-8")
        for marker in ("PROTECTED_EVIDENCE_STORAGE_CONTRACT_READY", "contract-only storage boundary", "no encrypted vault", "no key material read", "no key material persistence", "no plaintext secret storage", "migration receipt required before implementation"):
            self.assertIn(marker, text)

if __name__ == "__main__": unittest.main()
