import unittest
from pathlib import Path


EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-schemas test-tracer-bullet test-acceptance diff-check"


class SealedEvidenceCoverageHealthGateWiringTests(unittest.TestCase):
    def read_makefile(self) -> str:
        path = Path("Makefile")
        self.assertTrue(path.is_file(), "Makefile missing")
        return path.read_text(encoding="utf-8")

    def test_makefile_declares_sealed_evidence_coverage_target(self):
        text = self.read_makefile()
        self.assertIn("test-sealed-evidence-coverage", text)
        self.assertIn(
            "PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v",
            text,
        )

    def test_health_runs_root_integrity_then_sealed_coverage_before_other_gates(self):
        text = self.read_makefile()
        health_line = next(line for line in text.splitlines() if line.startswith("health:"))
        self.assertEqual(health_line, EXPECTED_HEALTH)
        for earlier, later in (
            ("test-root-integrity", "test-sealed-evidence-coverage"),
            ("test-sealed-evidence-coverage", "test-evidence-proof-contract"),
            ("test-evidence-proof-contract", "test-evidence-proof-fixtures"),
            ("test-evidence-proof-fixtures", "test-final-runtime-contracts"),
            ("test-final-runtime-contracts", "test-gated-provider-transport"),
            ("test-gated-provider-transport", "test-runtime-sealed-receipt"),
            ("test-runtime-sealed-receipt", "test-schemas"),
            ("test-schemas", "test-tracer-bullet"),
            ("test-tracer-bullet", "test-acceptance"),
            ("test-acceptance", "diff-check"),
        ):
            self.assertLess(health_line.index(earlier), health_line.index(later))

    def test_ci_still_depends_on_health_only(self):
        text = self.read_makefile()
        ci_line = next(line for line in text.splitlines() if line.startswith("ci:"))
        self.assertEqual(ci_line, "ci: health")

    def test_coverage_map_artifacts_exist(self):
        required_paths = (
            "governance/evidence/sealed_evidence_coverage_map_v1.json",
            "tests/tracer_bullet/test_sealed_evidence_coverage_map.py",
            "docs/decisions/sealed_evidence_coverage_map_v1.md",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_decision_doc_exists_and_records_no_runtime_posture(self):
        path = Path("docs/decisions/sealed_evidence_coverage_health_gate_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "SEALED_EVIDENCE_COVERAGE_HEALTH_GATE_READY_FOR_LOCAL_TESTS",
            "test-sealed-evidence-coverage",
            "health",
            "make ci",
            "no runtime execution",
            "no network access",
            "no secret read",
            "no SQLite schema change",
            "no encrypted vault",
            "no Merkle proof",
            "no HMAC proof",
            "no zero-knowledge-like proof",
            "no raw evidence store",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
