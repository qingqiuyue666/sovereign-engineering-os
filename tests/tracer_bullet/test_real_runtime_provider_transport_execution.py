import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.real_runtime_provider_transport_execution import (
    RealRuntimeProviderTransportExecutionViolation,
    validate_execution_envelope,
    validate_execution_postcheck,
    validate_execution_preflight,
    validate_execution_quarantine_link,
    validate_execution_receipt,
    validate_execution_report,
    validate_operator_authorization,
    validate_transport_execution_policy,
)

POLICY_PATH = Path("governance/runtime/real_runtime_provider_transport_execution_v1.json")
FIXTURE_PATH = Path("governance/runtime/fixtures/real_runtime_provider_transport_execution_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-operator-task-ledger test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {
    "validate_transport_execution_policy": validate_transport_execution_policy,
    "validate_operator_authorization": validate_operator_authorization,
    "validate_execution_preflight": validate_execution_preflight,
    "validate_execution_envelope": validate_execution_envelope,
    "validate_execution_receipt": validate_execution_receipt,
    "validate_execution_postcheck": validate_execution_postcheck,
    "validate_execution_quarantine_link": validate_execution_quarantine_link,
    "validate_execution_report": validate_execution_report,
}
FORBIDDEN_FLAGS = (
    "automatic_execution_enabled",
    "background_execution_enabled",
    "unbounded_provider_calls_allowed",
    "network_access_without_authorization",
    "secret_value_read",
    "secret_value_persisted",
    "env_read_performed",
    "raw_prompt_persisted",
    "raw_response_persisted",
    "sqlite_schema_changed",
    "audit_append_performed",
    "production_autonomy_enabled",
    "provider_retry_loop_enabled",
    "provider_streaming_enabled",
)

class RealRuntimeProviderTransportExecutionTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}

    def test_policy_map_is_accepted_execution_boundary(self):
        result = validate_transport_execution_policy(self.load_policy())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.verdict, "accepted_execution_boundary")
        self.assertEqual(result.contract_section, "execution_policy")

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
                result = validate_transport_execution_policy(payload)
                self.assertFalse(result.accepted)
                self.assertIn(f"{flag}_forbidden", result.failures)

    def test_operator_authorization_requires_single_call_scope(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_operator_authorization"])
        payload["operator_explicitly_approved"] = False
        payload["authorization_scope"] = "unbounded"
        result = validate_operator_authorization(payload)
        self.assertFalse(result.accepted)
        self.assertIn("operator_explicitly_approved_required", result.failures)
        self.assertIn("authorization_scope_invalid", result.failures)

    def test_preflight_rejects_env_and_missing_policy_links(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_execution_preflight"])
        payload["env_value"] = "forbidden"
        payload["sealed_receipt_policy_verified"] = False
        result = validate_execution_preflight(payload)
        self.assertFalse(result.accepted)
        self.assertIn("high_risk_key_forbidden", result.failures)
        self.assertIn("sealed_receipt_policy_verified_missing", result.failures)

    def test_envelope_rejects_raw_prompt_and_multiple_calls(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_execution_envelope"])
        payload["raw_prompt"] = "forbidden"
        payload["single_call_limit"] = 2
        result = validate_execution_envelope(payload)
        self.assertFalse(result.accepted)
        self.assertIn("high_risk_key_forbidden", result.failures)
        self.assertIn("single_call_limit_must_be_one", result.failures)

    def test_receipt_rejects_count_mismatch_and_raw_response_persistence(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_execution_receipt"])
        payload["provider_call_count"] = 1
        payload["execution_result"] = "not_executed"
        payload["raw_response_persisted"] = True
        result = validate_execution_receipt(payload)
        self.assertFalse(result.accepted)
        self.assertIn("provider_call_count_result_mismatch", result.failures)
        self.assertIn("raw_response_persisted_must_be_false", result.failures)
        self.assertIn("raw_response_persisted_forbidden", result.failures)

    def test_report_requires_all_sections_and_no_production_autonomy(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_execution_report"])
        payload["validated_sections"] = ["execution_policy"]
        payload["production_autonomy_ready"] = True
        result = validate_execution_report(payload)
        self.assertFalse(result.accepted)
        self.assertIn("operator_authorization_section_missing", result.failures)
        self.assertIn("execution_preflight_section_missing", result.failures)
        self.assertIn("execution_envelope_section_missing", result.failures)
        self.assertIn("execution_receipt_section_missing", result.failures)
        self.assertIn("execution_postcheck_section_missing", result.failures)
        self.assertIn("execution_quarantine_link_section_missing", result.failures)
        self.assertIn("production_autonomy_ready_must_be_false", result.failures)

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(RealRuntimeProviderTransportExecutionViolation):
            validate_transport_execution_policy(["not", "mapping"])

    def test_makefile_declares_real_runtime_provider_transport_execution_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("test-real-runtime-provider-transport-execution", text)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_runtime_provider_transport_execution -v", text)
        self.assertIn(EXPECTED_HEALTH, text)
        self.assertLess(EXPECTED_HEALTH.index("test-gated-provider-transport"), EXPECTED_HEALTH.index("test-real-runtime-provider-transport-execution"))
        self.assertLess(EXPECTED_HEALTH.index("test-real-runtime-provider-transport-execution"), EXPECTED_HEALTH.index("test-runtime-sealed-receipt"))

    def test_source_does_not_introduce_live_transport_runtime_surface(self):
        source = Path("kernel/runtime/real_runtime_provider_transport_execution.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "sqlite3", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "open(", "write_text(", "audit_append(", "ledger_append("):
            self.assertNotIn(marker, source)

    def test_runbook_exists_and_records_execution_boundary(self):
        path = Path("docs/runbooks/real_runtime_provider_transport_execution_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "REAL_RUNTIME_PROVIDER_TRANSPORT_EXECUTION_BOUNDARY_READY",
            "default disabled",
            "manual preflight required",
            "operator authorization required",
            "single provider call",
            "sealed receipt required",
            "failure quarantine link required",
            "no production autonomy",
        ):
            self.assertIn(marker, text)

if __name__ == "__main__":
    unittest.main()
