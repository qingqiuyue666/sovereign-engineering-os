import copy
import json
import unittest
from pathlib import Path

from kernel.evidence.generic_payload_shadow_contract import (
    GenericPayloadShadowContractViolation,
    classify_generic_payload,
    validate_generic_payload_compatibility_gap,
    validate_generic_payload_shadow_policy,
    validate_generic_payload_shadow_record,
    validate_generic_payload_shadow_report,
)

POLICY_PATH = Path("governance/evidence/generic_payload_shadow_v1.json")
FIXTURE_PATH = Path("governance/evidence/fixtures/generic_payload_shadow_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-operator-task-ledger test-operator-cli test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {"validate_generic_payload_shadow_policy": validate_generic_payload_shadow_policy, "validate_generic_payload_shadow_record": validate_generic_payload_shadow_record, "validate_generic_payload_compatibility_gap": validate_generic_payload_compatibility_gap, "validate_generic_payload_shadow_report": validate_generic_payload_shadow_report}
FORBIDDEN_FLAGS = ("enforcement_enabled", "ordinary_payload_behavior_changed", "audit_append_behavior_changed", "sqlite_schema_changed", "runtime_execution_performed", "network_accessed", "secret_value_read", "secret_value_persisted", "raw_material_persistence_allowed")

class GenericPayloadShadowContractTests(unittest.TestCase):
    def load_policy(self): self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH)); return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    def load_fixtures(self): self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH)); return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    def test_policy_map_is_accepted_shadow_only(self):
        result = validate_generic_payload_shadow_policy(self.load_policy()); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.category, "policy")
    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"]); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.category, item["expected_category"])
    def test_invalid_fixtures_are_rejected(self):
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"]); self.assertFalse(result.accepted)
                for failure in item["expected_failures"]: self.assertIn(failure, result.failures)
    def test_unknown_payload_becomes_compatibility_gap_not_enforcement_failure(self):
        payload = {"shadow_mode": True, "gap_recorded": True, "enforcement_blocked": True, "unknown_future_shape": "x", "enforcement_enabled": False, "ordinary_payload_behavior_changed": False}
        self.assertEqual(classify_generic_payload(payload), "compatibility_gap"); self.assertTrue(validate_generic_payload_compatibility_gap(payload).accepted)
    def test_all_forbidden_flags_fail_closed_for_policy(self):
        base = self.load_policy()
        for flag in FORBIDDEN_FLAGS:
            payload = copy.deepcopy(base); payload[flag] = True
            with self.subTest(flag=flag): self.assertIn(f"{flag}_forbidden", validate_generic_payload_shadow_policy(payload).failures)
    def test_high_risk_raw_keys_fail_closed(self):
        for key in ("raw_prompt", "raw_provider_response", "secret_value", "raw_traceback", "raw_exception_dump"):
            with self.subTest(key=key): self.assertIn("high_risk_payload_forbidden", validate_generic_payload_shadow_record({"shadow_mode": True, key: "forbidden"}).failures)
    def test_non_mapping_payload_raises(self):
        with self.assertRaises(GenericPayloadShadowContractViolation): validate_generic_payload_shadow_record(["not", "mapping"])
    def test_makefile_declares_generic_payload_shadow_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8"); self.assertIn("test-generic-payload-shadow", text); self.assertIn(EXPECTED_HEALTH, text); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation")); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"), EXPECTED_HEALTH.index("test-real-hmac-policy-realization")); self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement")); self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"), EXPECTED_HEALTH.index("test-schemas"))
    def test_source_does_not_introduce_execution_or_persistence_surface(self):
        source = Path("kernel/evidence/generic_payload_shadow_contract.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "sqlite3", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text("):
            self.assertNotIn(marker, source)
    def test_runbook_exists_and_records_shadow_boundary(self):
        text = Path("docs/runbooks/generic_payload_shadow_v1.md").read_text(encoding="utf-8")
        for marker in ("GENERIC_PAYLOAD_SHADOW_READY", "shadow validation only", "enforcement remains disabled", "ordinary payload behavior is unchanged", "compatibility gap", "no SQLite schema migration"):
            self.assertIn(marker, text)

if __name__ == "__main__": unittest.main()
