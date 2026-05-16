import json
import unittest
from pathlib import Path


AUDIT_PATH = Path("governance/completion/final_system_completion_audit_v1.json")


class FinalSystemCompletionAuditTests(unittest.TestCase):
    def load_audit(self):
        self.assertTrue(AUDIT_PATH.is_file(), str(AUDIT_PATH))
        return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    def ids(self, key):
        return {entry["surface_id"] for entry in self.load_audit()[key]}

    def test_top_level_verdict_refuses_100_percent_claim(self):
        audit = self.load_audit()
        self.assertEqual(audit["audit_type"], "seos_final_system_completion_audit_v1")
        self.assertEqual(audit["status"], "final_completion_audit_only_no_runtime")
        self.assertEqual(audit["verdict"], "FINAL_COMPLETION_AUDIT_READY_NOT_100_PERCENT")
        self.assertEqual(audit["readiness_band"], "final_runtime_track_contract_ready")
        self.assertFalse(audit["claim_100_percent_complete"])
        self.assertFalse(audit["final_system_fully_finished"])
        self.assertLess(audit["estimated_completion_percent"], 100)
        self.assertGreaterEqual(audit["estimated_completion_percent"], 70)

    def test_audit_has_no_runtime_or_secret_posture(self):
        audit = self.load_audit()
        self.assertFalse(audit["runtime_execution_performed"])
        self.assertFalse(audit["network_accessed"])
        self.assertFalse(audit["secret_value_read"])
        self.assertFalse(audit["secret_value_persisted"])
        self.assertFalse(audit["sqlite_schema_changed"])
        self.assertFalse(audit["audit_append_performed"])
        self.assertFalse(audit["raw_evidence_store_allowed"])

    def test_canonical_health_gate_is_recorded_exactly(self):
        audit = self.load_audit()
        gate = audit["canonical_health_gate"]
        self.assertEqual(gate["make_target"], "health")
        self.assertEqual(gate["ci_target"], "ci")
        self.assertTrue(gate["root_integrity_first"])
        self.assertTrue(gate["worktree_cleanliness_required"])
        self.assertEqual(
            gate["ordered_gates"],
            [
                "test-root-integrity",
                "test-sealed-evidence-coverage",
                "test-evidence-proof-contract",
                "test-evidence-proof-fixtures",
                "test-final-runtime-contracts",
                "test-schemas",
                "test-tracer-bullet",
                "test-acceptance",
                "diff-check",
            ],
        )

    def test_implemented_surfaces_include_current_health_and_evidence_capabilities(self):
        implemented = self.ids("implemented_surfaces")
        for surface_id in (
            "root_integrity_verifier",
            "schema_freeze_validation",
            "tracer_bullet_suite",
            "acceptance_suite",
            "sealed_evidence_coverage_map",
            "sealed_redacted_evidence_contract",
            "append_only_ledger_selected_high_risk_ingress",
            "model_provider_manual_smoke_sealed_payload",
            "failure_quarantine_sealed_payload",
            "evidence_proof_contract_foundation",
            "evidence_proof_fixtures",
            "generic_audit_payload_typed_enforcement_plan",
            "protected_evidence_storage_policy_plan",
            "proof_authority_policy_contracts",
            "final_runtime_completion_track_map",
            "final_runtime_contract_validators",
            "final_runtime_runbook",
        ):
            self.assertIn(surface_id, implemented)

    def test_not_implemented_surfaces_block_100_percent_claim(self):
        not_implemented = self.ids("not_implemented_surfaces")
        for surface_id in (
            "protected_evidence_storage_implementation",
            "real_hmac_key_management_and_signing",
            "real_merkle_tree_and_proof_verification",
            "full_generic_audit_payload_typed_enforcement",
            "real_runtime_provider_transport_execution",
            "production_autonomy",
        ):
            self.assertIn(surface_id, not_implemented)
        for entry in self.load_audit()["not_implemented_surfaces"]:
            if entry["surface_id"] != "zero_knowledge_like_evidence_proof":
                self.assertIn("required_before_100_percent", entry)

    def test_forbidden_surfaces_are_explicit(self):
        forbidden = set(self.load_audit()["forbidden_surfaces"])
        for surface_id in (
            "raw_evidence_store",
            "raw_prompt_persistence",
            "raw_provider_response_persistence",
            "raw_traceback_persistence",
            "raw_exception_dump_persistence",
            "secret_value_persistence",
            "ungated_runtime_authority",
            "network_access_without_explicit_transport_gate",
            "provider_live_call_without_transport_gate",
            "production_autonomy_without_final_authorization",
        ):
            self.assertIn(surface_id, forbidden)

    def test_readiness_decision_allows_next_track_but_not_completion_claim(self):
        decision = self.load_audit()["readiness_decision"]
        self.assertFalse(decision["allow_claim_100_percent"])
        self.assertTrue(decision["allow_final_runtime_completion_track"])
        self.assertFalse(decision["allow_production_autonomy_claim"])
        self.assertTrue(decision["allow_manual_default_disabled_runtime_track"])
        self.assertEqual(decision["required_next_branch"], "gated-provider-transport-contract-v1")

    def test_next_required_slices_are_not_empty(self):
        slices = self.load_audit()["next_required_slices_before_100_percent"]
        self.assertGreaterEqual(len(slices), 5)
        self.assertIn("gated-provider-transport-contract-v1", slices)
        self.assertIn("real-merkle-proof-realization-v1", slices)

    def test_decision_doc_exists_and_records_non_100_percent_posture(self):
        path = Path("docs/decisions/final_system_completion_audit_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "FINAL_SYSTEM_COMPLETION_AUDIT_READY_FOR_LOCAL_TESTS",
            "not 100%",
            "FINAL_COMPLETION_AUDIT_READY_NOT_100_PERCENT",
            "no runtime execution",
            "no network access",
            "no secret read",
            "encrypted_evidence_vault",
            "real_hmac_key_management_and_signing",
            "real_merkle_tree_and_proof_verification",
            "final-runtime-completion-track-v1",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
