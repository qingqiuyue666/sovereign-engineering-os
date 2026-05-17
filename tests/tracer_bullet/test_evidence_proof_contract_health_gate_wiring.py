import unittest
from pathlib import Path


EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-operator-task-ledger test-operator-cli test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"


class EvidenceProofContractHealthGateWiringTests(unittest.TestCase):
    def read_makefile(self) -> str:
        path = Path("Makefile")
        self.assertTrue(path.is_file(), "Makefile missing")
        return path.read_text(encoding="utf-8")

    def test_makefile_declares_evidence_proof_contract_target(self):
        text = self.read_makefile()
        self.assertIn("test-evidence-proof-contract", text)
        self.assertIn("tests.tracer_bullet.test_evidence_proof_contract", text)

    def test_health_runs_proof_contract_after_coverage_before_schemas(self):
        health_line = next(line for line in self.read_makefile().splitlines() if line.startswith("health:"))
        self.assertEqual(health_line, EXPECTED_HEALTH)
        for earlier, later in (
            ("test-root-integrity", "test-sealed-evidence-coverage"),
            ("test-protected-evidence-storage", "test-protected-evidence-storage-implementation"),
            ("test-protected-evidence-storage-implementation", "test-real-hmac-policy-realization"),
            ("test-real-merkle-proof-realization", "test-generic-payload-full-enforcement"),
            ("test-generic-payload-full-enforcement", "test-schemas"),
            ("test-acceptance", "diff-check"),
        ):
            self.assertLess(health_line.index(earlier), health_line.index(later))

    def test_ci_still_depends_on_health_only(self):
        ci_line = next(line for line in self.read_makefile().splitlines() if line.startswith("ci:"))
        self.assertEqual(ci_line, "ci: health")

    def test_proof_contract_artifacts_exist(self):
        for path in ("kernel/evidence/evidence_proof_contract.py", "tests/tracer_bullet/test_evidence_proof_contract.py", "docs/decisions/evidence_proof_contract_foundation_v1.md"):
            self.assertTrue(Path(path).is_file(), path)

    def test_decision_doc_exists_and_records_no_crypto_runtime_posture(self):
        text = Path("docs/decisions/evidence_proof_contract_health_gate_v1.md").read_text(encoding="utf-8")
        for marker in ("EVIDENCE_PROOF_CONTRACT_HEALTH_GATE_READY_FOR_LOCAL_TESTS", "test-evidence-proof-contract", "make ci"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
