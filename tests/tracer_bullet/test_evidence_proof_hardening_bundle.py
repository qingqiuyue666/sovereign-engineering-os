import json
import unittest
from pathlib import Path


GENERIC_PLAN = Path("governance/evidence/generic_audit_payload_typed_enforcement_plan_v1.json")
STORAGE_PLAN = Path("governance/evidence/protected_evidence_storage_policy_plan_v1.json")
PROOF_POLICY = Path("governance/evidence/proof_authority_policy_contracts_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"


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
        self.assertFalse(payload["full_generic_enforcement_enabled"])
        self.assert_no_execution_posture(payload)

    def test_protected_storage_policy_plan_is_not_implementation(self):
        payload = self.load_json(STORAGE_PLAN)
        self.assertEqual(payload["plan_type"], "seos_protected_evidence_storage_policy_plan_v1")
        self.assertEqual(payload["status"], "policy_plan_only_storage_not_implemented")
        self.assertFalse(payload["protected_storage_implemented"])
        self.assert_no_execution_posture(payload)

    def test_proof_authority_policy_contracts_are_placeholder_only(self):
        payload = self.load_json(PROOF_POLICY)
        self.assertEqual(payload["contract_type"], "seos_proof_authority_policy_contracts_v1")
        self.assertFalse(payload["real_hmac_implemented"])
        self.assertFalse(payload["real_merkle_implemented"])
        self.assertFalse(payload["zero_knowledge_proof_implemented"])
        self.assert_no_execution_posture(payload)

    def test_makefile_health_runs_fixtures_then_runtime_gates_before_schemas(self):
        health_line = next(line for line in Path("Makefile").read_text(encoding="utf-8").splitlines() if line.startswith("health:"))
        self.assertEqual(health_line, EXPECTED_HEALTH)
        for earlier, later in (
            ("test-evidence-proof-contract", "test-evidence-proof-fixtures"),
            ("test-protected-evidence-storage", "test-protected-evidence-storage-implementation"),
            ("test-protected-evidence-storage-implementation", "test-real-hmac-policy-realization"),
            ("test-real-merkle-proof-realization", "test-generic-payload-full-enforcement"),
            ("test-generic-payload-full-enforcement", "test-schemas"),
        ):
            self.assertLess(health_line.index(earlier), health_line.index(later))

    def test_decision_doc_exists_and_records_bundle_boundary(self):
        text = Path("docs/decisions/evidence_proof_hardening_bundle_v1.md").read_text(encoding="utf-8")
        for marker in ("EVIDENCE_PROOF_HARDENING_BUNDLE_READY_FOR_LOCAL_TESTS", "test-evidence-proof-fixtures", "generic_audit_payload_typed_enforcement_plan_v1", "protected_evidence_storage_policy_plan_v1", "proof_authority_policy_contracts_v1", "no runtime execution", "no network access", "no sensitive value read", "no SQLite schema change", "no real HMAC", "no real Merkle", "no protected storage implementation"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
