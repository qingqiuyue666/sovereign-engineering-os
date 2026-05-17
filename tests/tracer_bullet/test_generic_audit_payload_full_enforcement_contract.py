import copy
import json
import unittest
from pathlib import Path

from kernel.evidence.generic_audit_payload_full_enforcement_contract import (
    GenericAuditPayloadFullEnforcementViolation,
    validate_compatibility_inventory,
    validate_enforcement_report,
    validate_full_enforcement_policy,
    validate_migration_receipt,
    validate_rollback_plan,
    validate_typed_enforcement_record,
)

POLICY_PATH = Path("governance/evidence/generic_audit_payload_full_enforcement_v1.json")
FIXTURE_PATH = Path("governance/evidence/fixtures/generic_audit_payload_full_enforcement_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-operator-task-ledger test-operator-cli test-runtime-runner-event-journal test-failurebundle-replay-foundation test-evidence-vault-boundary-foundation test-provider-execution-plane-boundary test-runtime-integration-hardening test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"

VALIDATORS = {
    "validate_full_enforcement_policy": validate_full_enforcement_policy,
    "validate_compatibility_inventory": validate_compatibility_inventory,
    "validate_migration_receipt": validate_migration_receipt,
    "validate_rollback_plan": validate_rollback_plan,
    "validate_typed_enforcement_record": validate_typed_enforcement_record,
    "validate_enforcement_report": validate_enforcement_report,
}

FORBIDDEN_FLAGS = (
    "ordinary_payload_behavior_changed",
    "audit_append_behavior_changed",
    "sqlite_schema_changed",
    "runtime_execution_performed",
    "network_accessed",
    "secret_value_read",
    "secret_value_persisted",
    "raw_material_persistence_allowed",
)


class GenericAuditPayloadFullEnforcementContractTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}

    def test_policy_map_is_accepted_contract_only(self):
        result = validate_full_enforcement_policy(self.load_policy())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.verdict, "accepted_contract_only")
        self.assertEqual(result.contract_section, "policy")

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
                result = validate_full_enforcement_policy(payload)
                self.assertFalse(result.accepted)
                self.assertIn(f"{flag}_forbidden", result.failures)

    def test_typed_record_rejects_unknown_payload_and_high_risk_keys(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_typed_enforcement_record"])
        payload["unknown_payload"] = True
        payload["raw_provider_response"] = "forbidden"
        result = validate_typed_enforcement_record(payload)
        self.assertFalse(result.accepted)
        self.assertIn("unknown_payload_fail_closed", result.failures)
        self.assertIn("high_risk_key_forbidden", result.failures)

    def test_migration_receipt_requires_inventory_and_rollback(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_migration_receipt"])
        payload["compatibility_inventory_verified"] = False
        payload["rollback_plan_verified"] = False
        result = validate_migration_receipt(payload)
        self.assertFalse(result.accepted)
        self.assertIn("compatibility_inventory_verified_missing", result.failures)
        self.assertIn("rollback_plan_verified_missing", result.failures)

    def test_report_requires_all_sections_and_no_runtime_ready(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_enforcement_report"])
        payload["validated_sections"] = ["policy"]
        payload["full_runtime_enforcement_ready"] = True
        result = validate_enforcement_report(payload)
        self.assertFalse(result.accepted)
        self.assertIn("compatibility_inventory_section_missing", result.failures)
        self.assertIn("migration_receipt_section_missing", result.failures)
        self.assertIn("rollback_plan_section_missing", result.failures)
        self.assertIn("typed_enforcement_record_section_missing", result.failures)
        self.assertIn("full_runtime_enforcement_ready_must_be_false", result.failures)

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(GenericAuditPayloadFullEnforcementViolation):
            validate_full_enforcement_policy(["not", "mapping"])

    def test_makefile_declares_generic_payload_full_enforcement_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("test-generic-payload-full-enforcement", text)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_generic_audit_payload_full_enforcement_contract -v", text)
        self.assertIn(EXPECTED_HEALTH, text)
        self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"))
        self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"), EXPECTED_HEALTH.index("test-real-hmac-policy-realization"))
        self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"))
        self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"), EXPECTED_HEALTH.index("test-schemas"))

    def test_source_does_not_introduce_runtime_or_append_mutation_surface(self):
        source = Path("kernel/evidence/generic_audit_payload_full_enforcement_contract.py").read_text(encoding="utf-8")
        for marker in ("sqlite3", "requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text(", "audit_append(", "ledger_append("):
            self.assertNotIn(marker, source)

    def test_runbook_exists_and_records_full_enforcement_boundary(self):
        path = Path("docs/runbooks/generic_audit_payload_full_enforcement_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "GENERIC_AUDIT_PAYLOAD_FULL_ENFORCEMENT_CONTRACT_READY",
            "contract-only full typed enforcement",
            "migration receipt required",
            "rollback plan required",
            "unknown payloads fail closed",
            "no audit append behavior mutation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
