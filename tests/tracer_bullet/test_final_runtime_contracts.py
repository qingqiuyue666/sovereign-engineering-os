import json
import unittest
from pathlib import Path

from kernel.runtime.final_runtime_contracts import (
    FinalRuntimeContractViolation,
    validate_failure_quarantine_link,
    validate_final_runtime_track_map,
    validate_post_run_health,
    validate_runtime_preflight,
    validate_runtime_receipt,
)

TRACK_MAP_PATH = Path("governance/runtime/final_runtime_completion_track_v1.json")
REQUIRED_GATES = ["test-root-integrity", "test-sealed-evidence-coverage", "test-evidence-proof-contract", "test-evidence-proof-fixtures", "test-final-runtime-contracts", "test-gated-provider-transport", "test-real-runtime-provider-transport-execution", "test-production-autonomy-final-gate", "test-runtime-sealed-receipt", "test-generic-payload-shadow", "test-protected-evidence-storage", "test-protected-evidence-storage-implementation", "test-real-hmac-policy-realization", "test-real-merkle-proof-realization", "test-generic-payload-full-enforcement", "test-schemas", "test-tracer-bullet", "test-acceptance", "diff-check"]
FORBIDDEN_FLAGS = ("provider_call_performed", "network_accessed", "secret_value_read", "secret_value_persisted", "sqlite_schema_changed", "audit_append_performed", "protected_storage_implemented", "real_hmac_performed", "real_merkle_tree_built", "zero_knowledge_proof_built", "production_autonomy_enabled", "raw_evidence_store_allowed")
EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"

class FinalRuntimeContractsTests(unittest.TestCase):
    def load_track_map(self):
        self.assertTrue(TRACK_MAP_PATH.is_file(), str(TRACK_MAP_PATH)); return json.loads(TRACK_MAP_PATH.read_text(encoding="utf-8"))
    def base_forbidden_false(self): return {flag: False for flag in FORBIDDEN_FLAGS}
    def valid_preflight(self):
        data = self.base_forbidden_false(); data.update({"preflight_id": "preflight-001", "task_id": "task-001", "runtime_track_id": "final-runtime-track-v1", "operator_approval_required": True, "operator_approval_present": True, "runtime_mode": "manual_dry_run", "provider_transport_status": "disabled", "evidence_policy_status": "passed", "proof_policy_status": "passed", "failure_quarantine_policy_status": "passed", "health_gate_status": "passed"}); return data
    def valid_receipt(self):
        data = self.base_forbidden_false(); data.update({"receipt_id": "receipt-001", "task_id": "task-001", "runtime_track_id": "final-runtime-track-v1", "preflight_id": "preflight-001", "preflight_result": "passed", "execution_attempted": False, "execution_mode": "manual_dry_run", "sealed_evidence_refs": ["sealed-evidence::task-001"], "proof_refs": ["proof::task-001"], "failure_quarantine_refs": [], "post_run_health_result": "not_run", "final_verdict": "manual_dry_run_receipt_only"}); return data
    def valid_post_run_health(self):
        data = self.base_forbidden_false(); data.update({"post_run_health_id": "post-run-health-001", "required_health_gates": REQUIRED_GATES, "gate_results": {gate: "passed" for gate in REQUIRED_GATES}, "worktree_clean": True}); return data
    def valid_failure_link(self):
        data = self.base_forbidden_false(); data.update({"link_id": "failure-link-001", "task_id": "task-001", "runtime_track_id": "final-runtime-track-v1", "failure_quarantine_policy_status": "linked_contract_only", "sealed_evidence_refs": ["sealed-evidence::task-001"], "proof_refs": ["proof::task-001"], "quarantine_refs": ["quarantine::task-001"]}); return data
    def test_track_map_is_accepted_contract_only(self):
        result = validate_final_runtime_track_map(self.load_track_map()); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.verdict, "accepted_contract_only")
    def test_preflight_accepts_disabled_manual_dry_run_contract(self): self.assertTrue(validate_runtime_preflight(self.valid_preflight()).accepted)
    def test_receipt_accepts_no_execution_receipt(self): self.assertTrue(validate_runtime_receipt(self.valid_receipt()).accepted)
    def test_post_run_health_accepts_all_required_gates(self): self.assertTrue(validate_post_run_health(self.valid_post_run_health()).accepted)
    def test_failure_quarantine_link_accepts_contract_only_link(self): self.assertTrue(validate_failure_quarantine_link(self.valid_failure_link()).accepted)
    def test_preflight_rejects_missing_operator_approval(self):
        data = self.valid_preflight(); data["operator_approval_present"] = False; self.assertIn("operator_approval_missing", validate_runtime_preflight(data).failures)
    def test_preflight_rejects_enabled_provider_transport(self):
        data = self.valid_preflight(); data["provider_transport_status"] = "enabled"; self.assertIn("provider_transport_must_be_disabled", validate_runtime_preflight(data).failures)
    def test_receipt_rejects_execution_attempt(self):
        data = self.valid_receipt(); data["execution_attempted"] = True; self.assertIn("execution_attempted_must_be_false", validate_runtime_receipt(data).failures)
    def test_post_run_health_rejects_missing_gate_result(self):
        data = self.valid_post_run_health(); data["gate_results"]["test-real-runtime-provider-transport-execution"] = "missing"; result = validate_post_run_health(data); self.assertFalse(result.accepted); self.assertIn("test-real-runtime-provider-transport-execution_not_passed", result.failures)
    def test_failure_link_rejects_wrong_policy_status(self):
        data = self.valid_failure_link(); data["failure_quarantine_policy_status"] = "unlinked"; self.assertIn("failure_quarantine_policy_status_invalid", validate_failure_quarantine_link(data).failures)
    def test_all_forbidden_true_flags_fail_closed_across_contracts(self):
        for validator, factory in ((validate_runtime_preflight, self.valid_preflight), (validate_runtime_receipt, self.valid_receipt), (validate_post_run_health, self.valid_post_run_health), (validate_failure_quarantine_link, self.valid_failure_link)):
            for flag in FORBIDDEN_FLAGS:
                payload = factory(); payload[flag] = True
                with self.subTest(validator=validator.__name__, flag=flag):
                    result = validator(payload); self.assertFalse(result.accepted); self.assertIn(f"{flag}_forbidden", result.failures)
    def test_non_mapping_payload_raises(self):
        with self.assertRaises(FinalRuntimeContractViolation): validate_runtime_preflight(["not", "mapping"])
    def test_makefile_declares_final_runtime_contract_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8"); self.assertIn("test-final-runtime-contracts", text); self.assertIn(EXPECTED_HEALTH, text)
    def test_source_does_not_introduce_runtime_execution_surface(self):
        source = Path("kernel/runtime/final_runtime_contracts.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "sqlite3", "openai.", "getenv", "environ", "write_text("):
            self.assertNotIn(marker, source)

if __name__ == "__main__": unittest.main()
