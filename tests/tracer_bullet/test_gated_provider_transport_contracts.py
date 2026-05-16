import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.gated_provider_transport_contracts import (
    GatedProviderTransportContractViolation,
    validate_provider_transport_blocked_attempt,
    validate_provider_transport_gate,
    validate_provider_transport_postcheck,
    validate_provider_transport_preflight,
    validate_provider_transport_receipt,
)

GATE_PATH = Path("governance/runtime/gated_provider_transport_v1.json")
FIXTURE_PATH = Path("governance/runtime/fixtures/gated_provider_transport_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {"validate_provider_transport_gate": validate_provider_transport_gate, "validate_provider_transport_preflight": validate_provider_transport_preflight, "validate_provider_transport_receipt": validate_provider_transport_receipt, "validate_provider_transport_blocked_attempt": validate_provider_transport_blocked_attempt, "validate_provider_transport_postcheck": validate_provider_transport_postcheck}
FORBIDDEN_FLAGS = ("provider_enabled", "provider_live_call_performed", "network_accessed", "secret_value_read", "secret_value_persisted", "env_read_performed", "raw_prompt_persisted", "raw_response_persisted", "sqlite_schema_changed", "audit_append_performed", "protected_storage_implemented", "real_hmac_performed", "real_merkle_tree_built", "zero_knowledge_proof_built", "production_autonomy_enabled", "raw_evidence_store_allowed")

class GatedProviderTransportContractsTests(unittest.TestCase):
    def load_gate(self): self.assertTrue(GATE_PATH.is_file(), str(GATE_PATH)); return json.loads(GATE_PATH.read_text(encoding="utf-8"))
    def load_fixtures(self): self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH)); return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    def valid_by_validator(self): return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}
    def test_gate_map_is_accepted_contract_only(self):
        result = validate_provider_transport_gate(self.load_gate()); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.verdict, "accepted_contract_only")
    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]): self.assertTrue(VALIDATORS[item["validator"]](item["record"]).accepted)
    def test_invalid_fixtures_are_rejected_with_expected_failures(self):
        valid_records = self.valid_by_validator()
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                base = copy.deepcopy(valid_records[item["validator"]]); base.update(item["record_patch"]); result = VALIDATORS[item["validator"]](base); self.assertFalse(result.accepted)
                for failure in item["expected_failures"]: self.assertIn(failure, result.failures)
    def test_all_forbidden_flags_fail_closed_across_validators(self):
        valid_records = self.valid_by_validator()
        for validator_name, validator in VALIDATORS.items():
            if validator_name not in valid_records: continue
            for flag in FORBIDDEN_FLAGS:
                payload = copy.deepcopy(valid_records[validator_name]); payload[flag] = True
                with self.subTest(validator=validator_name, flag=flag): self.assertIn(f"{flag}_forbidden", validator(payload).failures)
    def test_preflight_requires_manual_approval(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_provider_transport_preflight"]); payload["manual_approval_present"] = False; self.assertIn("manual_approval_missing", validate_provider_transport_preflight(payload).failures)
    def test_receipt_rejects_transport_attempt(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_provider_transport_receipt"]); payload["transport_attempted"] = True; self.assertIn("transport_attempted_must_be_false", validate_provider_transport_receipt(payload).failures)
    def test_postcheck_requires_all_links(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_provider_transport_postcheck"]); payload["post_run_health_present"] = False; self.assertIn("post_run_health_present_required", validate_provider_transport_postcheck(payload).failures)
    def test_non_mapping_payload_raises(self):
        with self.assertRaises(GatedProviderTransportContractViolation): validate_provider_transport_gate(["not", "mapping"])
    def test_makefile_declares_gated_provider_transport_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8"); self.assertIn("test-gated-provider-transport", text); self.assertIn(EXPECTED_HEALTH, text); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation")); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"), EXPECTED_HEALTH.index("test-real-hmac-policy-realization")); self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement")); self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"), EXPECTED_HEALTH.index("test-schemas"))
    def test_source_does_not_introduce_live_transport_surface(self):
        source = Path("kernel/runtime/gated_provider_transport_contracts.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "sqlite3", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text("):
            self.assertNotIn(marker, source)
    def test_runbook_exists_and_records_disabled_boundary(self):
        text = Path("docs/runbooks/gated_provider_transport_v1.md").read_text(encoding="utf-8")
        for marker in ("GATED_PROVIDER_TRANSPORT_CONTRACT_READY", "disabled by default", "manual dry run", "no provider live call", "no network access", "no secret read", "sealed receipt required", "failure quarantine linkage required", "postcheck required"):
            self.assertIn(marker, text)

if __name__ == "__main__": unittest.main()
