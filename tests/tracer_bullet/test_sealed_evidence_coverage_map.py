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

    def test_map_top_level_shape_and_no_runtime_posture(self):
        payload = self.load_map()
        self.assertEqual(payload["map_type"], "seos_sealed_evidence_coverage_map_v1")
        self.assertEqual(payload["version"], "v1")
        self.assertEqual(payload["status"], "coverage_map_only_no_runtime")
        self.assertFalse(payload["runtime_execution_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["secret_value_read"])
        self.assertFalse(payload["secret_value_persisted"])
        self.assertFalse(payload["sqlite_schema_changed"])
        self.assertFalse(payload["encrypted_vault_implemented"])
        self.assertFalse(payload["merkle_proof_implemented"])
        self.assertFalse(payload["hmac_proof_implemented"])
        self.assertFalse(payload["zero_knowledge_proof_implemented"])
        self.assertFalse(payload["raw_evidence_store_allowed"])
        self.assertIsInstance(payload["surfaces"], list)
        self.assertGreaterEqual(len(payload["surfaces"]), 9)

    def test_required_surfaces_are_declared(self):
        surfaces = self.surfaces_by_id()
        for surface_id in (
            "model_provider_manual_smoke_report",
            "failure_quarantine_manifest",
            "append_only_ledger_high_risk_payload_ingress",
            "generic_audit_payloads",
            "sealed_redacted_evidence_contract",
            "evidence_proof_contract_foundation",
            "encrypted_evidence_vault",
            "real_merkle_or_hmac_evidence_proofs",
            "zero_knowledge_like_evidence_proofs",
            "raw_evidence_store",
        ):
            self.assertIn(surface_id, surfaces)

    def test_model_provider_and_failure_quarantine_are_covered(self):
        surfaces = self.surfaces_by_id()
        for surface_id in (
            "model_provider_manual_smoke_report",
            "failure_quarantine_manifest",
        ):
            surface = surfaces[surface_id]
            self.assertEqual(surface["coverage_status"], "covered")
            self.assertEqual(surface["evidence_contract"], "sealed_redaction_v1")
            self.assertEqual(surface["coverage_mechanism"], "embedded_sealed_evidence_payload")
            self.assertEqual(surface["classification"], "secret")
            self.assertEqual(surface["representation"], "redacted_digest")
            self.assertFalse(surface["secret_value_allowed"])
            self.assertFalse(surface["runtime_authority_allowed"])
            self.assertTrue(surface["tests"])

    def test_evidence_proof_contract_foundation_is_contract_surface_only(self):
        surface = self.surfaces_by_id()["evidence_proof_contract_foundation"]
        self.assertEqual(surface["coverage_status"], "covered_contract_surface")
        self.assertEqual(surface["evidence_contract"], "evidence_proof_contract_v1")
        self.assertEqual(surface["coverage_mechanism"], "deterministic_proof_record_validation_contract")
        self.assertEqual(surface["representation"], "sha256_digest_redacted_digest_hmac_placeholder_merkle_placeholder")
        self.assertFalse(surface["real_hmac_key_allowed"])
        self.assertFalse(surface["real_merkle_tree_allowed"])
        self.assertFalse(surface["encrypted_vault_allowed"])
        self.assertFalse(surface["zero_knowledge_proof_allowed"])
        self.assertFalse(surface["runtime_execution_allowed"])
        self.assertFalse(surface["network_access_allowed"])
        self.assertFalse(surface["secret_value_allowed"])
        self.assertIn("tests.tracer_bullet.test_evidence_proof_contract", surface["tests"])

    def test_append_only_ledger_is_selected_high_risk_only(self):
        surface = self.surfaces_by_id()["append_only_ledger_high_risk_payload_ingress"]
        self.assertEqual(surface["coverage_status"], "selected_high_risk_only")
        self.assertEqual(surface["evidence_contract"], "sealed_redaction_v1")
        self.assertEqual(surface["coverage_mechanism"], "selected_high_risk_payload_ingress_guard")
        self.assertFalse(surface["ordinary_payload_behavior_changed"])
        self.assertFalse(surface["generic_classification_key_triggers_contract"])
        self.assertFalse(surface["raw_prompt_allowed"])
        self.assertFalse(surface["raw_provider_response_allowed"])
        self.assertFalse(surface["secret_value_allowed"])

    def test_generic_audit_payloads_are_not_claimed_as_fully_covered(self):
        surface = self.surfaces_by_id()["generic_audit_payloads"]
        self.assertEqual(surface["coverage_status"], "selected_high_risk_only")
        self.assertFalse(surface["ordinary_payload_behavior_changed"])
        self.assertIn("future_required_work", surface)

    def test_future_crypto_layers_are_explicitly_not_implemented(self):
        surfaces = self.surfaces_by_id()
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
        self.assertFalse(surface["raw_prompt_allowed"])
        self.assertFalse(surface["raw_provider_response_allowed"])
        self.assertFalse(surface["secret_value_allowed"])
        self.assertFalse(surface["raw_traceback_allowed"])
        self.assertFalse(surface["raw_exception_dump_allowed"])

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
        root_manifest = Path("governance/root/root_manifest_v1.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("sealed_evidence_coverage_map_v1.json", root_manifest)


if __name__ == "__main__":
    unittest.main()
