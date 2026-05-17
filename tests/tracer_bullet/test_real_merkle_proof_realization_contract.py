import copy
import json
import unittest
from pathlib import Path

from kernel.evidence.real_merkle_proof_realization_contract import (
    RealMerkleProofContractViolation,
    validate_merkle_leaf_digest_policy,
    validate_merkle_node_digest_policy,
    validate_merkle_policy_realization_report,
    validate_merkle_proof_path_contract,
    validate_merkle_root_commitment_receipt_contract,
    validate_merkle_tree_manifest,
    validate_merkle_verifier_receipt_contract,
    validate_real_merkle_policy,
)

POLICY_PATH = Path("governance/evidence/real_merkle_proof_realization_contract_v1.json")
FIXTURE_PATH = Path("governance/evidence/fixtures/real_merkle_proof_realization_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"
VALIDATORS = {
    "validate_real_merkle_policy": validate_real_merkle_policy,
    "validate_merkle_tree_manifest": validate_merkle_tree_manifest,
    "validate_merkle_leaf_digest_policy": validate_merkle_leaf_digest_policy,
    "validate_merkle_node_digest_policy": validate_merkle_node_digest_policy,
    "validate_merkle_proof_path_contract": validate_merkle_proof_path_contract,
    "validate_merkle_verifier_receipt_contract": validate_merkle_verifier_receipt_contract,
    "validate_merkle_root_commitment_receipt_contract": validate_merkle_root_commitment_receipt_contract,
    "validate_merkle_policy_realization_report": validate_merkle_policy_realization_report,
}
FORBIDDEN_FLAGS = (
    "real_merkle_tree_built", "merkle_proof_verified", "root_commitment_published",
    "evidence_append_behavior_changed", "raw_evidence_store_allowed", "protected_storage_implemented",
    "secret_value_read", "secret_value_persisted", "runtime_execution_performed", "network_accessed",
    "sqlite_schema_changed", "audit_append_performed",
)

class RealMerkleProofRealizationContractTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH)); return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH)); return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}
    def test_policy_map_is_accepted_contract_only(self):
        result = validate_real_merkle_policy(self.load_policy()); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.verdict, "accepted_contract_only"); self.assertEqual(result.contract_section, "policy")
    def test_valid_fixtures_are_accepted(self):
        for item in self.load_fixtures()["valid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                result = VALIDATORS[item["validator"]](item["record"]); self.assertTrue(result.accepted, result.failures); self.assertEqual(result.contract_section, item["expected_section"])
    def test_invalid_fixtures_are_rejected(self):
        valid_records = self.valid_by_validator()
        for item in self.load_fixtures()["invalid_records"]:
            with self.subTest(fixture_id=item["fixture_id"]):
                base = copy.deepcopy(valid_records[item["validator"]]); base.update(item["record_patch"]); result = VALIDATORS[item["validator"]](base); self.assertFalse(result.accepted)
                for failure in item["expected_failures"]: self.assertIn(failure, result.failures)
    def test_all_forbidden_flags_fail_closed_for_policy(self):
        base = self.load_policy()
        for flag in FORBIDDEN_FLAGS:
            payload = copy.deepcopy(base); payload[flag] = True
            with self.subTest(flag=flag):
                result = validate_real_merkle_policy(payload); self.assertFalse(result.accepted); self.assertIn(f"{flag}_forbidden", result.failures)
    def test_allowed_digest_algorithms_are_strict(self):
        payload = self.load_policy(); payload["allowed_digest_algorithms"] = ["sha256", "sha512", "md5"]; result = validate_real_merkle_policy(payload); self.assertFalse(result.accepted); self.assertIn("allowed_digest_algorithms_invalid", result.failures)
    def test_leaf_and_proof_reject_raw_payloads(self):
        leaf = copy.deepcopy(self.valid_by_validator()["validate_merkle_leaf_digest_policy"]); leaf["raw_leaf_payload_allowed"] = True; leaf_result = validate_merkle_leaf_digest_policy(leaf); self.assertFalse(leaf_result.accepted); self.assertIn("raw_leaf_payload_allowed_must_be_false", leaf_result.failures)
        proof = copy.deepcopy(self.valid_by_validator()["validate_merkle_proof_path_contract"]); proof["raw_sibling_payload_allowed"] = True; proof_result = validate_merkle_proof_path_contract(proof); self.assertFalse(proof_result.accepted); self.assertIn("raw_sibling_payload_allowed_must_be_false", proof_result.failures)
    def test_report_requires_all_sections_and_no_real_tree_ready(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_merkle_policy_realization_report"]); payload["validated_sections"] = ["policy"]; payload["real_tree_ready"] = True; result = validate_merkle_policy_realization_report(payload); self.assertFalse(result.accepted); self.assertIn("tree_manifest_section_missing", result.failures); self.assertIn("leaf_digest_policy_section_missing", result.failures); self.assertIn("node_digest_policy_section_missing", result.failures); self.assertIn("proof_path_contract_section_missing", result.failures); self.assertIn("verifier_receipt_contract_section_missing", result.failures); self.assertIn("root_commitment_receipt_contract_section_missing", result.failures); self.assertIn("real_tree_ready_must_be_false", result.failures)
    def test_non_mapping_payload_raises(self):
        with self.assertRaises(RealMerkleProofContractViolation): validate_real_merkle_policy(["not", "mapping"])
    def test_makefile_declares_real_merkle_proof_realization_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8"); self.assertIn("test-real-merkle-proof-realization", text); self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_merkle_proof_realization_contract -v", text); self.assertIn(EXPECTED_HEALTH, text); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation")); self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"), EXPECTED_HEALTH.index("test-real-hmac-policy-realization")); self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement")); self.assertLess(EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"), EXPECTED_HEALTH.index("test-schemas"))
    def test_source_does_not_introduce_tree_storage_or_runtime_surface(self):
        source = Path("kernel/evidence/real_merkle_proof_realization_contract.py").read_text(encoding="utf-8")
        for marker in ("hashlib", "sqlite3", "requests", "httpx", "urllib", "socket.", "subprocess", "os.system", "openai.", "anthropic.", "google.generativeai", "getenv", "os.environ", ".environ", "write_text("):
            self.assertNotIn(marker, source)
    def test_runbook_exists_and_records_merkle_boundary(self):
        text = Path("docs/runbooks/real_merkle_proof_realization_contract_v1.md").read_text(encoding="utf-8")
        for marker in ("REAL_MERKLE_PROOF_REALIZATION_CONTRACT_READY", "contract-only Merkle proof realization", "no real Merkle tree build", "no Merkle proof verification runtime", "no root commitment publication", "no evidence append behavior mutation", "digest-only leaf payload policy"):
            self.assertIn(marker, text)

if __name__ == "__main__": unittest.main()
