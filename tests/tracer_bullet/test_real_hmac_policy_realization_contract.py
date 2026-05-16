import copy
import json
import unittest
from pathlib import Path

from kernel.evidence.real_hmac_policy_realization_contract import (
    RealHmacPolicyContractViolation,
    validate_hmac_key_policy,
    validate_hmac_policy_realization_report,
    validate_hmac_rotation_policy,
    validate_hmac_signature_receipt_contract,
    validate_hmac_signing_authority_policy,
    validate_hmac_verifier_policy,
    validate_real_hmac_policy,
)

POLICY_PATH = Path("governance/evidence/real_hmac_policy_realization_contract_v1.json")
FIXTURE_PATH = Path("governance/evidence/fixtures/real_hmac_policy_realization_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"

VALIDATORS = {
    "validate_real_hmac_policy": validate_real_hmac_policy,
    "validate_hmac_key_policy": validate_hmac_key_policy,
    "validate_hmac_signing_authority_policy": validate_hmac_signing_authority_policy,
    "validate_hmac_verifier_policy": validate_hmac_verifier_policy,
    "validate_hmac_signature_receipt_contract": validate_hmac_signature_receipt_contract,
    "validate_hmac_rotation_policy": validate_hmac_rotation_policy,
    "validate_hmac_policy_realization_report": validate_hmac_policy_realization_report,
}

FORBIDDEN_FLAGS = (
    "real_hmac_signature_created",
    "hmac_verification_performed",
    "key_material_read",
    "key_material_persisted",
    "key_generation_performed",
    "signing_runtime_enabled",
    "verification_runtime_enabled",
    "secret_value_read",
    "secret_value_persisted",
    "plaintext_secret_allowed",
    "runtime_execution_performed",
    "network_accessed",
    "sqlite_schema_changed",
    "audit_append_performed",
)

class RealHmacPolicyRealizationContractTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}
    def test_policy_map_is_accepted_contract_only(self):
        result = validate_real_hmac_policy(self.load_policy()); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.verdict, "accepted_contract_only"); self.assertEqual(result.contract_section, "policy")
    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"]); self.assertTrue(result.accepted, result.failures); self.assertTrue(item["expected_accepted"]); self.assertEqual(result.contract_section, item["expected_section"])
    def test_invalid_fixtures_are_rejected(self):
        valid_records = self.valid_by_validator()
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                base = copy.deepcopy(valid_records[item["validator"]]); base.update(item["record_patch"]); result = VALIDATORS[item["validator"]](base); self.assertFalse(result.accepted); self.assertFalse(item["expected_accepted"])
                for failure in item["expected_failures"]: self.assertIn(failure, result.failures)
    def test_all_forbidden_flags_fail_closed_for_policy(self):
        base = self.load_policy()
        for flag in FORBIDDEN_FLAGS:
            payload = copy.deepcopy(base); payload[flag] = True
            with self.subTest(flag=flag):
                result = validate_real_hmac_policy(payload); self.assertFalse(result.accepted); self.assertIn(f"{flag}_forbidden", result.failures)
    def test_allowed_digest_algorithms_are_strict(self):
        payload = self.load_policy(); payload["allowed_digest_algorithms"] = ["sha256", "sha384", "sha512", "md5"]; result = validate_real_hmac_policy(payload); self.assertFalse(result.accepted); self.assertIn("allowed_digest_algorithms_invalid", result.failures)
    def test_verifier_requires_constant_time_compare_before_real_verification(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_hmac_verifier_policy"]); payload["constant_time_compare_required"] = False; payload["verification_runtime_allowed"] = True; result = validate_hmac_verifier_policy(payload); self.assertFalse(result.accepted); self.assertIn("constant_time_compare_required_missing", result.failures); self.assertIn("verification_runtime_allowed_must_be_false", result.failures)
    def test_report_requires_all_sections_and_no_real_signature_ready(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_hmac_policy_realization_report"]); payload["validated_sections"] = ["policy"]; payload["real_signature_ready"] = True; result = validate_hmac_policy_realization_report(payload); self.assertFalse(result.accepted); self.assertIn("key_policy_section_missing", result.failures); self.assertIn("signing_authority_policy_section_missing", result.failures); self.assertIn("verifier_policy_section_missing", result.failures); self.assertIn("signature_receipt_contract_section_missing", result.failures); self.assertIn("rotation_policy_section_missing", result.failures); self.assertIn("real_signature_ready_must_be_false", result.failures)
    def test_non_mapping_payload_raises(self):
        with self.assertRaises(RealHmacPolicyContractViolation): validate_real_hmac_policy(["not", "mapping"])
    def test_makefile_declares_real_hmac_policy_realization_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8"); self.assertIn("test-real-hmac-policy-realization", text); self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_hmac_policy_realization_contract -v", text); self.assertIn(EXPECTED_HEALTH, text); self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement")); self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"), EXPECTED_HEALTH.index("test-schemas"))
    def test_source_does_not_introduce_hmac_key_or_runtime_surface(self):
        source = Path("kernel/evidence/real_hmac_policy_realization_contract.py").read_text(encoding="utf-8")
        for marker in ("import hmac", "hmac.", "compare_digest", "cryptography", "sqlite3", "requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text("):
            self.assertNotIn(marker, source)
    def test_runbook_exists_and_records_hmac_boundary(self):
        text = Path("docs/runbooks/real_hmac_policy_realization_contract_v1.md").read_text(encoding="utf-8")
        for marker in ("REAL_HMAC_POLICY_REALIZATION_CONTRACT_READY", "contract-only HMAC policy realization", "no real HMAC signature", "no key material read", "no key material persistence", "constant-time compare required before real verification", "protected storage contract required"):
            self.assertIn(marker, text)

if __name__ == "__main__": unittest.main()
