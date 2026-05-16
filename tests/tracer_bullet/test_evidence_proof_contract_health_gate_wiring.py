import unittest
from pathlib import Path


class EvidenceProofContractHealthGateWiringTests(unittest.TestCase):
    def read_makefile(self) -> str:
        path = Path("Makefile")
        self.assertTrue(path.is_file(), "Makefile missing")
        return path.read_text(encoding="utf-8")

    def test_makefile_declares_evidence_proof_contract_target(self):
        text = self.read_makefile()
        self.assertIn("test-evidence-proof-contract", text)
        self.assertIn(
            "PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_proof_contract -v",
            text,
        )

    def test_health_runs_proof_contract_after_coverage_before_schemas(self):
        text = self.read_makefile()
        health_line = next(
            line for line in text.splitlines() if line.startswith("health:")
        )
        expected = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-schemas test-tracer-bullet test-acceptance diff-check"
        self.assertEqual(health_line, expected)
        self.assertLess(health_line.index("test-root-integrity"), health_line.index("test-sealed-evidence-coverage"))
        self.assertLess(health_line.index("test-sealed-evidence-coverage"), health_line.index("test-evidence-proof-contract"))
        self.assertLess(health_line.index("test-evidence-proof-contract"), health_line.index("test-evidence-proof-fixtures"))
        self.assertLess(health_line.index("test-evidence-proof-fixtures"), health_line.index("test-schemas"))
        self.assertLess(health_line.index("test-schemas"), health_line.index("test-tracer-bullet"))
        self.assertLess(health_line.index("test-tracer-bullet"), health_line.index("test-acceptance"))
        self.assertLess(health_line.index("test-acceptance"), health_line.index("diff-check"))

    def test_ci_still_depends_on_health_only(self):
        text = self.read_makefile()
        ci_line = next(line for line in text.splitlines() if line.startswith("ci:"))
        self.assertEqual(ci_line, "ci: health")

    def test_proof_contract_artifacts_exist(self):
        required_paths = (
            "kernel/evidence/evidence_proof_contract.py",
            "tests/tracer_bullet/test_evidence_proof_contract.py",
            "docs/decisions/evidence_proof_contract_foundation_v1.md",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_decision_doc_exists_and_records_no_crypto_runtime_posture(self):
        path = Path("docs/decisions/evidence_proof_contract_health_gate_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "EVIDENCE_PROOF_CONTRACT_HEALTH_GATE_READY_FOR_LOCAL_TESTS",
            "test-evidence-proof-contract",
            "health",
            "make ci",
            "no runtime execution",
            "no network access",
            "no secret read",
            "no SQLite schema change",
            "no encrypted vault",
            "no real HMAC",
            "no real Merkle tree",
            "no zero-knowledge-like proof",
            "no raw evidence store",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
