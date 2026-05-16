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
        self.assertEqual(audit["readiness_band"], "generic_payload_full_typed_shadow_ready")
        self.assertFalse(audit["claim_100_percent_complete"])
        self.assertFalse(audit["final_system_fully_finished"])
        self.assertLess(audit["estimated_completion_percent"], 100)
        self.assertGreaterEqual(audit["estimated_completion_percent"], 86)

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
                "test-gated-provider-transport",
                "test-runtime-sealed-receipt",
                "test-generic-payload-shadow",
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
            "evidence_proof_contract_foundation",
            "evidence_proof_fixtures",
            "final_runtime_completion_track_map",
            "final_runtime_contract_validators",
            "gated_provider_transport_map",
            "gated_provider_transport_contracts",
            "gated_provider_transport_fixtures",
            "runtime_sealed_receipt_map",
            "runtime_sealed_receipt_contracts",
            "runtime_sealed_receipt_fixtures",
            "generic_payload_shadow_policy",
            "generic_payload_shadow_contract",
            "generic_payload_shadow_fixtures",
            "generic_payload_shadow_runbook",
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
            "generic_payload_full_enforcement_without_migration_receipt",
        ):
            self.assertIn(surface_id, forbidden)

    def test_readiness_decision_allows_next_track_but_not_completion_claim(self):
        decision = self.load_audit()["readiness_decision"]
        self.assertFalse(decision["allow_claim_100_percent"])
        self.assertTrue(decision["allow_final_runtime_completion_track"])
        self.assertFalse(decision["allow_production_autonomy_claim"])
        self.assertTrue(decision["allow_manual_default_disabled_runtime_track"])
        self.assertFalse(decision["allow_generic_payload_full_enforcement"])
        self.assertEqual(decision["required_next_branch"], "protected-evidence-storage-contract-bundle-v1")

    def test_next_required_slices_are_not_empty(self):
        slices = self.load_audit()["next_required_slices_before_100_percent"]
        self.assertGreaterEqual(len(slices), 5)
        self.assertIn("protected-evidence-storage-contract-bundle-v1", slices)
        self.assertIn("generic-audit-payload-full-enforcement-bundle-v1", slices)
        self.assertIn("real-merkle-proof-realization-v1", slices)

    def test_decision_doc_exists_and_records_non_100_percent_posture(self):
        path = Path("docs/decisions/generic_payload_shadow_bundle_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "GENERIC_PAYLOAD_SHADOW_BUNDLE_READY_FOR_LOCAL_TESTS",
            "generic_payload_full_typed_shadow_ready",
            "not 100%",
            "test-generic-payload-shadow",
            "protected-evidence-storage-contract-bundle-v1",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
