import json
import unittest
from pathlib import Path


GENERIC_PLAN = Path("governance/evidence/generic_audit_payload_typed_enforcement_plan_v1.json")
STORAGE_PLAN = Path("governance/evidence/protected_evidence_storage_policy_plan_v1.json")
PROOF_POLICY = Path("governance/evidence/proof_authority_policy_contracts_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-schemas test-tracer-bullet test-acceptance diff-check"


class EvidenceProofHardeningBundleTests(unittest.TestCase):
    def load_json(self, path: Path):
        self.assertTrue(path.is_file(), str(path))
        return json.loads(path.read_text(encoding="utf-8"))

    def assert_no_execution_posture(self, payload):
        self.assertFalse(payload["runtime_execution_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["sensitive_value_read"])
        self.assertFalse(payload["sensitive_value_persisted"])
        self.assertFalse(payload["sqlite_schema_changed"])
        self.assertFalse(payload["audit_append_performed"])

    def test_generic_audit_typed_enforcement_plan_is_plan_only(self):
        payload = self.load_json(GENERIC_PLAN)
        self.assertEqual(payload["plan_type"], "seos_generic_audit_payload_typed_enforcement_plan_v1")
        self.assertEqual(payload["status"], "contract_plan_only_not_enforced")
        self.assertEqual(payload["current_state"], "selected_high_risk_only")
        self.assertEqual(payload["target_state"], "full_typed_payload_enforcement_after_compatibility_plan")
        self.assertFalse(payload["full_generic_enforcement_enabled"])
        self.assert_no_execution_posture(payload)
        self.assertIn("phase_0_inventory", payload["allowed_phases"])
        self.assertIn("phase_4_full_enforcement", payload["allowed_phases"])
        self.assertIn("migration_compatibility_receipt_missing", payload["promotion_blockers_before_full_enforcement"])

    def test_protected_storage_policy_plan_is_not_implementation(self):
        payload = self.load_json(STORAGE_PLAN)
        self.assertEqual(payload["plan_type"], "seos_protected_evidence_storage_policy_plan_v1")
        self.assertEqual(payload["status"], "policy_plan_only_storage_not_implemented")
        self.assertFalse(payload["protected_storage_implemented"])
        self.assert_no_execution_posture(payload)
        self.assertIn("storage_boundary", payload["policy_sections"])
        self.assertIn("access_boundary", payload["policy_sections"])
        self.assertIn("recovery_boundary", payload["policy_sections"])
        self.assertIn("do_not_store_protected_payloads_in_this_slice", payload["non_goals"])

    def test_proof_authority_policy_contracts_are_placeholder_only(self):
        payload = self.load_json(PROOF_POLICY)
        self.assertEqual(payload["contract_type"], "seos_proof_authority_policy_contracts_v1")
        self.assertEqual(payload["status"], "policy_contract_only_no_real_crypto")
        self.assertFalse(payload["real_hmac_implemented"])
        self.assertFalse(payload["real_merkle_implemented"])
        self.assertFalse(payload["zero_knowledge_proof_implemented"])
        self.assert_no_execution_posture(payload)
        contract_ids = {contract["contract_id"] for contract in payload["contracts"]}
        self.assertIn("digest_authority_policy", contract_ids)
        self.assertIn("hmac_authority_policy_placeholder", contract_ids)
        self.assertIn("merkle_authority_policy_placeholder", contract_ids)
        forbidden = set(payload["forbidden_claims_in_this_slice"])
        self.assertIn("real_hmac_signature_created", forbidden)
        self.assertIn("real_merkle_tree_created", forbidden)
        self.assertIn("protected_storage_implemented", forbidden)
        self.assertIn("runtime_transport_enabled", forbidden)

    def test_makefile_health_runs_fixtures_then_runtime_gates_before_schemas(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        health_line = next(line for line in text.splitlines() if line.startswith("health:"))
        self.assertEqual(health_line, EXPECTED_HEALTH)
        self.assertLess(health_line.index("test-evidence-proof-contract"), health_line.index("test-evidence-proof-fixtures"))
        self.assertLess(health_line.index("test-evidence-proof-fixtures"), health_line.index("test-final-runtime-contracts"))
        self.assertLess(health_line.index("test-final-runtime-contracts"), health_line.index("test-gated-provider-transport"))
        self.assertLess(health_line.index("test-gated-provider-transport"), health_line.index("test-runtime-sealed-receipt"))
        self.assertLess(health_line.index("test-runtime-sealed-receipt"), health_line.index("test-generic-payload-shadow"))
        self.assertLess(health_line.index("test-generic-payload-shadow"), health_line.index("test-protected-evidence-storage"))
        self.assertLess(health_line.index("test-protected-evidence-storage"), health_line.index("test-schemas"))

    def test_decision_doc_exists_and_records_bundle_boundary(self):
        path = Path("docs/decisions/evidence_proof_hardening_bundle_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "EVIDENCE_PROOF_HARDENING_BUNDLE_READY_FOR_LOCAL_TESTS",
            "test-evidence-proof-fixtures",
            "generic_audit_payload_typed_enforcement_plan_v1",
            "protected_evidence_storage_policy_plan_v1",
            "proof_authority_policy_contracts_v1",
            "no runtime execution",
            "no network access",
            "no sensitive value read",
            "no SQLite schema change",
            "no real HMAC",
            "no real Merkle",
            "no protected storage implementation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
