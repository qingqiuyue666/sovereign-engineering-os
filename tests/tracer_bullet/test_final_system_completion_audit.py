
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

    def test_top_level_verdict_accepts_100_percent_claim(self):

        audit = self.load_audit()

        self.assertEqual(audit["audit_type"], "seos_final_system_completion_audit_v1")

        self.assertEqual(audit["status"], "final_completion_audit_100_percent_claim_ready")

        self.assertEqual(audit["verdict"], "FINAL_COMPLETION_AUDIT_100_PERCENT_READY_WITH_FINAL_GATE")

        self.assertEqual(audit["readiness_band"], "production_autonomy_final_gate_ready")

        self.assertTrue(audit["claim_100_percent_complete"])

        self.assertTrue(audit["final_system_fully_finished"])

        self.assertEqual(audit["estimated_completion_percent"], 100)

    def test_audit_has_no_runtime_or_secret_side_effect_posture(self):

        audit = self.load_audit()

        self.assertFalse(audit["runtime_execution_performed"])

        self.assertFalse(audit["network_accessed"])

        self.assertFalse(audit["secret_value_read"])

        self.assertFalse(audit["secret_value_persisted"])

        self.assertFalse(audit["sqlite_schema_changed"])

        self.assertFalse(audit["audit_append_performed"])

        self.assertFalse(audit["raw_evidence_store_allowed"])

    def test_canonical_health_gate_is_recorded_exactly(self):

        gate = self.load_audit()["canonical_health_gate"]

        self.assertEqual(gate["make_target"], "health")

        self.assertEqual(gate["ci_target"], "ci")

        self.assertTrue(gate["root_integrity_first"])

        self.assertTrue(gate["worktree_cleanliness_required"])

        self.assertEqual(gate["ordered_gates"], [

            "test-root-integrity",

            "test-sealed-evidence-coverage",

            "test-evidence-proof-contract",

            "test-evidence-proof-fixtures",

            "test-final-runtime-contracts",

            "test-gated-provider-transport",

            "test-real-runtime-provider-transport-execution",

            "test-production-autonomy-final-gate",

            "test-runtime-sealed-receipt",

            "test-generic-payload-shadow",

            "test-protected-evidence-storage",

            "test-protected-evidence-storage-implementation",

            "test-real-hmac-policy-realization",

            "test-real-merkle-proof-realization",

            "test-generic-payload-full-enforcement",

            "test-schemas",

            "test-tracer-bullet",

            "test-acceptance",

            "diff-check",

        ])

    def test_implemented_surfaces_include_final_gate_capabilities(self):

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

            "real_runtime_provider_transport_execution_boundary",

            "production_autonomy_final_gate_policy",

            "production_autonomy_final_authorization",

            "production_autonomy_bounded_execution_envelope",

            "production_autonomy_emergency_brake",

            "production_autonomy_post_run_audit_pack",

            "production_autonomy_rollback_quarantine_pack",

            "production_autonomy_final_100_percent_claim",

            "runtime_sealed_receipt_contracts",

            "generic_payload_shadow_contract",

            "protected_evidence_storage_contract",

            "protected_evidence_storage_implementation_boundary",

            "real_hmac_policy_realization_contract",

            "real_merkle_proof_realization_contract",

            "generic_audit_payload_full_enforcement_contract",

        ):

            self.assertIn(surface_id, implemented)

    def test_no_unimplemented_surfaces_remain(self):

        self.assertEqual(self.load_audit()["not_implemented_surfaces"], [])

    def test_forbidden_surfaces_are_explicit(self):

        forbidden = set(self.load_audit()["forbidden_surfaces"])

        for surface_id in (

            "raw_evidence_store",

            "raw_prompt_persistence",

            "raw_provider_response_persistence",

            "secret_value_persistence",

            "automatic_unbounded_execution",

            "background_execution_without_authorization",

            "silent_operator_bypass",

            "network_access_without_gate",

            "audit_append_without_receipt",

            "disabled_rollback",

            "disabled_quarantine",

            "disabled_emergency_brake",

            "unbounded_provider_retry_loop",

        ):

            self.assertIn(surface_id, forbidden)

    def test_readiness_decision_allows_final_claim_but_blocks_unbounded_modes(self):

        decision = self.load_audit()["readiness_decision"]

        self.assertTrue(decision["allow_claim_100_percent"])

        self.assertTrue(decision["allow_final_runtime_completion_track"])

        self.assertTrue(decision["allow_production_autonomy_claim"])

        self.assertTrue(decision["allow_generic_payload_full_enforcement_contract"])

        self.assertTrue(decision["allow_protected_storage_implementation_boundary"])

        self.assertTrue(decision["allow_real_runtime_provider_transport_execution_boundary"])

        self.assertTrue(decision["allow_production_autonomy_final_gate"])

        self.assertFalse(decision["allow_unbounded_provider_execution"])

        self.assertFalse(decision["allow_background_execution"])

        self.assertFalse(decision["allow_operator_bypass"])

        self.assertIsNone(decision["required_next_branch"])

    def test_no_next_required_slices_remain(self):

        self.assertEqual(self.load_audit()["next_required_slices_before_100_percent"], [])

    def test_decision_doc_exists_and_records_100_percent_posture(self):

        path = Path("docs/decisions/production_autonomy_final_gate_v1.md")

        self.assertTrue(path.is_file(), str(path))

        text = path.read_text(encoding="utf-8")

        for marker in (

            "PRODUCTION_AUTONOMY_FINAL_GATE_READY_FOR_LOCAL_TESTS",

            "production_autonomy_final_gate_ready",

            "100",

            "test-production-autonomy-final-gate",

            "no remaining required slice before 100%",

        ):

            self.assertIn(marker, text)

if __name__ == "__main__":

    unittest.main()
