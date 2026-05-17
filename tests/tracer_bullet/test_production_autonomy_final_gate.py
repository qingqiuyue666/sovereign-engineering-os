import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.production_autonomy_final_gate import (
    ProductionAutonomyFinalGateViolation,
    validate_bounded_execution_envelope,
    validate_emergency_brake,
    validate_final_100_percent_claim,
    validate_final_authorization,
    validate_final_gate_policy,
    validate_final_gate_report,
    validate_post_run_audit_pack,
    validate_rollback_quarantine_pack,
)

POLICY_PATH = Path("governance/runtime/production_autonomy_final_gate_v1.json")
FIXTURE_PATH = Path("governance/runtime/fixtures/production_autonomy_final_gate_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {
    "validate_final_gate_policy": validate_final_gate_policy,
    "validate_final_authorization": validate_final_authorization,
    "validate_bounded_execution_envelope": validate_bounded_execution_envelope,
    "validate_emergency_brake": validate_emergency_brake,
    "validate_post_run_audit_pack": validate_post_run_audit_pack,
    "validate_rollback_quarantine_pack": validate_rollback_quarantine_pack,
    "validate_final_100_percent_claim": validate_final_100_percent_claim,
    "validate_final_gate_report": validate_final_gate_report,
}


class ProductionAutonomyFinalGateTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}

    def test_policy_map_is_accepted_final_gate(self):
        result = validate_final_gate_policy(self.load_policy())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.verdict, "accepted_final_gate")
        self.assertEqual(result.contract_section, "final_gate_policy")

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

    def test_authorization_requires_operator_and_single_run_scope(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_final_authorization"])
        payload["operator_explicitly_approved"] = False
        payload["scope"] = "unbounded"
        payload["expires_after_single_run"] = False
        result = validate_final_authorization(payload)
        self.assertFalse(result.accepted)
        self.assertIn("operator_explicitly_approved_required", result.failures)
        self.assertIn("scope_invalid", result.failures)
        self.assertIn("expires_after_single_run_required", result.failures)

    def test_bounded_execution_blocks_unbounded_or_mutating_behavior(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_bounded_execution_envelope"])
        payload["max_provider_calls"] = 2
        payload["max_mutating_actions"] = 1
        payload["digest_only_payload"] = False
        result = validate_bounded_execution_envelope(payload)
        self.assertFalse(result.accepted)
        self.assertIn("max_provider_calls_must_be_one", result.failures)
        self.assertIn("max_mutating_actions_must_be_zero", result.failures)
        self.assertIn("digest_only_payload_required", result.failures)

    def test_final_claim_requires_all_gates_and_final_gate_passed(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_final_100_percent_claim"])
        payload["all_required_health_gates_passed"] = False
        payload["all_runtime_boundaries_authorized"] = False
        payload["production_autonomy_final_gate_passed"] = False
        result = validate_final_100_percent_claim(payload)
        self.assertFalse(result.accepted)
        self.assertIn("all_required_health_gates_passed_required", result.failures)
        self.assertIn("all_runtime_boundaries_authorized_required", result.failures)
        self.assertIn("production_autonomy_final_gate_passed_required", result.failures)

    def test_report_requires_all_sections_and_finished_flag(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_final_gate_report"])
        payload["validated_sections"] = ["final_gate_policy"]
        payload["final_system_fully_finished"] = False
        result = validate_final_gate_report(payload)
        self.assertFalse(result.accepted)
        self.assertIn("final_system_fully_finished_required", result.failures)
        self.assertIn("final_authorization_section_missing", result.failures)
        self.assertIn("bounded_execution_envelope_section_missing", result.failures)
        self.assertIn("emergency_brake_section_missing", result.failures)
        self.assertIn("post_run_audit_pack_section_missing", result.failures)
        self.assertIn("rollback_quarantine_pack_section_missing", result.failures)
        self.assertIn("final_100_percent_claim_section_missing", result.failures)

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(ProductionAutonomyFinalGateViolation):
            validate_final_gate_policy(["not", "mapping"])

    def test_makefile_declares_production_autonomy_final_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("test-production-autonomy-final-gate", text)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_production_autonomy_final_gate -v", text)
        self.assertIn(EXPECTED_HEALTH, text)
        self.assertLess(EXPECTED_HEALTH.index("test-real-runtime-provider-transport-execution"), EXPECTED_HEALTH.index("test-production-autonomy-final-gate"))
        self.assertLess(EXPECTED_HEALTH.index("test-production-autonomy-final-gate"), EXPECTED_HEALTH.index("test-runtime-sealed-receipt"))

    def test_source_does_not_execute_runtime_side_effects(self):
        source = Path("kernel/runtime/production_autonomy_final_gate.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "socket.", "subprocess", "sqlite3", "open(", "write_text(", "os.environ", "getenv"):
            self.assertNotIn(marker, source)

    def test_runbook_exists_and_records_final_gate(self):
        path = Path("docs/runbooks/production_autonomy_final_gate_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "PRODUCTION_AUTONOMY_FINAL_GATE_READY",
            "default deny",
            "explicit authorization required",
            "bounded execution",
            "emergency brake",
            "100% completion claim",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
