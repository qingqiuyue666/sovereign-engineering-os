import json
import unittest
from pathlib import Path


COVERAGE_MAP_PATH = Path("governance/evidence/sealed_evidence_coverage_map_v1.json")


class SealedEvidenceCoverageMapTests(unittest.TestCase):
    def load_map(self):
        self.assertTrue(COVERAGE_MAP_PATH.is_file(), str(COVERAGE_MAP_PATH))
        return json.loads(COVERAGE_MAP_PATH.read_text(encoding="utf-8"))

    def surfaces_by_id(self):
        payload = self.load_map()
        return {surface["surface_id"]: surface for surface in payload["surfaces"]}

    def test_map_top_level_shape_and_no_execution_posture(self):
        payload = self.load_map()
        self.assertEqual(payload["map_type"], "seos_sealed_evidence_coverage_map_v1")
        self.assertEqual(payload["version"], "v1")
        self.assertEqual(payload["status"], "coverage_map_only_no_runtime")
        self.assertFalse(payload["runtime_execution_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["sqlite_schema_changed"])
        self.assertFalse(payload["raw_evidence_store_allowed"])
        self.assertIsInstance(payload["surfaces"], list)
        self.assertGreaterEqual(len(payload["surfaces"]), 16)

    def test_required_surfaces_are_declared(self):
        surfaces = self.surfaces_by_id()
        for surface_id in (
            "model_provider_manual_smoke_report",
            "failure_quarantine_manifest",
            "append_only_ledger_high_risk_payload_ingress",
            "generic_audit_payloads",
            "sealed_redacted_evidence_contract",
            "evidence_proof_contract_foundation",
            "evidence_proof_fixtures",
            "generic_audit_payload_typed_enforcement_plan",
            "protected_evidence_storage_policy_plan",
            "proof_authority_policy_contracts",
            "final_runtime_completion_track_map",
            "final_runtime_contract_validators",
            "final_runtime_runbook",
            "encrypted_evidence_vault",
            "real_merkle_or_hmac_evidence_proofs",
            "zero_knowledge_like_evidence_proofs",
            "raw_evidence_store",
        ):
            self.assertIn(surface_id, surfaces)

    def test_contract_surfaces_are_not_runtime_surfaces(self):
        surfaces = self.surfaces_by_id()
        for surface_id in (
            "evidence_proof_contract_foundation",
            "evidence_proof_fixtures",
            "generic_audit_payload_typed_enforcement_plan",
            "protected_evidence_storage_policy_plan",
            "proof_authority_policy_contracts",
            "final_runtime_completion_track_map",
            "final_runtime_contract_validators",
            "final_runtime_runbook",
        ):
            surface = surfaces[surface_id]
            self.assertEqual(surface["coverage_status"], "covered_contract_surface")
            self.assertFalse(surface["runtime_execution_allowed"])
            self.assertFalse(surface["network_access_allowed"])

    def test_runtime_contract_surfaces_have_runtime_tests(self):
        surfaces = self.surfaces_by_id()
        for surface_id in (
            "final_runtime_completion_track_map",
            "final_runtime_contract_validators",
            "final_runtime_runbook",
        ):
            self.assertIn("tests.tracer_bullet.test_final_runtime_contracts", surfaces[surface_id]["tests"])

    def test_selected_high_risk_and_future_layers_are_not_overclaimed(self):
        surfaces = self.surfaces_by_id()
        self.assertEqual(surfaces["append_only_ledger_high_risk_payload_ingress"]["coverage_status"], "selected_high_risk_only")
        self.assertEqual(surfaces["generic_audit_payloads"]["coverage_status"], "selected_high_risk_only")
        for surface_id in (
            "encrypted_evidence_vault",
            "real_merkle_or_hmac_evidence_proofs",
            "zero_knowledge_like_evidence_proofs",
        ):
            surface = surfaces[surface_id]
            self.assertEqual(surface["coverage_status"], "not_implemented")
            self.assertIsNone(surface["evidence_contract"])
            self.assertEqual(surface["coverage_mechanism"], "not_implemented")
            self.assertIn("future_required_work", surface)

    def test_raw_evidence_store_is_forbidden(self):
        surface = self.surfaces_by_id()["raw_evidence_store"]
        self.assertEqual(surface["coverage_status"], "forbidden")
        self.assertEqual(surface["coverage_mechanism"], "explicitly_disallowed")

    def test_every_surface_uses_allowed_status(self):
        payload = self.load_map()
        allowed = set(payload["required_status_values"])
        for surface in payload["surfaces"]:
            self.assertIn(surface["coverage_status"], allowed)
            self.assertIsInstance(surface["surface_id"], str)
            self.assertTrue(surface["surface_id"])

    def test_referenced_paths_exist_when_non_null(self):
        for surface in self.load_map()["surfaces"]:
            path = surface.get("path")
            if path is not None:
                self.assertTrue(Path(path).exists(), path)

    def test_coverage_map_does_not_modify_root_manifest(self):
        root_manifest = Path("governance/root/root_manifest_v1.json").read_text(encoding="utf-8")
        self.assertNotIn("sealed_evidence_coverage_map_v1.json", root_manifest)


if __name__ == "__main__":
    unittest.main()
