import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.runtime_sealed_receipt_contracts import (
    RuntimeSealedReceiptContractViolation,
    validate_blocked_attempt_receipt,
    validate_postcheck_receipt,
    validate_receipt_chain,
    validate_runtime_sealed_receipt_policy,
    validate_transport_attempt_receipt,
)


POLICY_PATH = Path("governance/runtime/runtime_sealed_receipt_v1.json")
FIXTURE_PATH = Path("governance/runtime/fixtures/runtime_sealed_receipt_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-schemas test-tracer-bullet test-acceptance diff-check"

VALIDATORS = {
    "validate_runtime_sealed_receipt_policy": validate_runtime_sealed_receipt_policy,
    "validate_transport_attempt_receipt": validate_transport_attempt_receipt,
    "validate_blocked_attempt_receipt": validate_blocked_attempt_receipt,
    "validate_postcheck_receipt": validate_postcheck_receipt,
    "validate_receipt_chain": validate_receipt_chain,
}

FORBIDDEN_FLAGS = (
    "provider_live_call_performed",
    "transport_attempted",
    "network_accessed",
    "secret_value_read",
    "secret_value_persisted",
    "env_read_performed",
    "raw_prompt_persisted",
    "raw_response_persisted",
    "sqlite_schema_changed",
    "audit_append_performed",
    "protected_storage_implemented",
    "real_hmac_performed",
    "real_merkle_tree_built",
    "zero_knowledge_proof_built",
    "production_autonomy_enabled",
    "raw_evidence_store_allowed",
)


class RuntimeSealedReceiptContractsTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}

    def test_policy_map_is_accepted_contract_only(self):
        result = validate_runtime_sealed_receipt_policy(self.load_policy())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.verdict, "accepted_contract_only")

    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"])
                self.assertTrue(result.accepted, result.failures)
                self.assertTrue(item["expected_accepted"])

    def test_invalid_fixtures_are_rejected_with_expected_failures(self):
        valid_records = self.valid_by_validator()
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                base = copy.deepcopy(valid_records[item["validator"]])
                base.update(item["record_patch"])
                result = VALIDATORS[item["validator"]](base)
                self.assertFalse(result.accepted)
                self.assertFalse(item["expected_accepted"])
                for failure in item["expected_failures"]:
                    self.assertIn(failure, result.failures)

    def test_all_forbidden_flags_fail_closed_across_validators(self):
        valid_records = self.valid_by_validator()
        for validator_name, validator in VALIDATORS.items():
            if validator_name not in valid_records:
                continue
            for flag in FORBIDDEN_FLAGS:
                payload = copy.deepcopy(valid_records[validator_name])
                payload[flag] = True
                with self.subTest(validator=validator_name, flag=flag):
                    result = validator(payload)
                    self.assertFalse(result.accepted)
                    self.assertIn(f"{flag}_forbidden", result.failures)

    def test_receipt_chain_requires_all_links(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_receipt_chain"])
        payload["policy_receipt_ref"] = ""
        payload["chain_complete"] = False
        result = validate_receipt_chain(payload)
        self.assertFalse(result.accepted)
        self.assertIn("policy_receipt_ref_required", result.failures)
        self.assertIn("chain_complete_required", result.failures)

    def test_transport_receipt_requires_seal_postcheck_and_quarantine_link(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_transport_attempt_receipt"])
        payload["sealed"] = False
        payload["postcheck_required"] = False
        payload["failure_quarantine_link_required"] = False
        result = validate_transport_attempt_receipt(payload)
        self.assertFalse(result.accepted)
        self.assertIn("sealed_required", result.failures)
        self.assertIn("postcheck_required", result.failures)
        self.assertIn("failure_quarantine_link_required", result.failures)

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(RuntimeSealedReceiptContractViolation):
            validate_runtime_sealed_receipt_policy(["not", "mapping"])

    def test_makefile_declares_runtime_sealed_receipt_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("test-runtime-sealed-receipt", text)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_sealed_receipt_contracts -v", text)
        self.assertIn(EXPECTED_HEALTH, text)
        self.assertLess(EXPECTED_HEALTH.index("test-gated-provider-transport"), EXPECTED_HEALTH.index("test-runtime-sealed-receipt"))
        self.assertLess(EXPECTED_HEALTH.index("test-runtime-sealed-receipt"), EXPECTED_HEALTH.index("test-generic-payload-shadow"))
        self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-shadow"), EXPECTED_HEALTH.index("test-protected-evidence-storage"))
        self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-schemas"))

    def test_source_does_not_introduce_live_transport_surface(self):
        source = Path("kernel/runtime/runtime_sealed_receipt_contracts.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "sqlite3", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text("):
            self.assertNotIn(marker, source)

    def test_runbook_exists_and_records_receipt_boundary(self):
        path = Path("docs/runbooks/runtime_sealed_receipt_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in ("RUNTIME_SEALED_RECEIPT_CONTRACT_READY", "transport attempt receipt", "blocked attempt receipt", "postcheck receipt", "receipt chain", "no provider live call", "no network access", "no secret read"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
