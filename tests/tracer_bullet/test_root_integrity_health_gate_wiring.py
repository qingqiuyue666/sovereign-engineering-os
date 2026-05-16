import unittest
from pathlib import Path


EXPECTED_HEALTH = "health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-real-hmac-policy-realization test-schemas test-tracer-bullet test-acceptance diff-check"


class RootIntegrityHealthGateWiringTests(unittest.TestCase):
    def read_makefile(self) -> str:
        path = Path("Makefile")
        self.assertTrue(path.is_file(), "Makefile missing")
        return path.read_text(encoding="utf-8")

    def test_makefile_declares_root_integrity_target(self):
        text = self.read_makefile()
        self.assertIn("test-root-integrity", text)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_root_integrity_verifier -v", text)

    def test_health_runs_root_integrity_before_other_health_gates(self):
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
            ("test-runtime-sealed-receipt", "test-generic-payload-shadow"),
            ("test-generic-payload-shadow", "test-protected-evidence-storage"),
            ("test-protected-evidence-storage", "test-real-hmac-policy-realization"),
            ("test-real-hmac-policy-realization", "test-schemas"),
            ("test-schemas", "test-tracer-bullet"),
            ("test-tracer-bullet", "test-acceptance"),
            ("test-acceptance", "diff-check"),
        ):
            self.assertLess(health_line.index(earlier), health_line.index(later))

    def test_ci_still_depends_on_health_only(self):
        text = self.read_makefile()
        ci_line = next(line for line in text.splitlines() if line.startswith("ci:"))
        self.assertEqual(ci_line, "ci: health")

    def test_root_integrity_artifacts_exist_on_mainline_candidate(self):
        for path in ("governance/root/root_manifest_v1.json", "kernel/bootstrap/root_integrity_verifier.py", "tests/tracer_bullet/test_root_integrity_verifier.py", "docs/decisions/root_integrity_verifier_foundation_v1.md"):
            self.assertTrue(Path(path).is_file(), path)

    def test_root_integrity_health_gate_decision_exists(self):
        path = Path("docs/decisions/root_integrity_health_gate_wiring_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in ("ROOT_INTEGRITY_HEALTH_GATE_WIRING_READY_FOR_LOCAL_TESTS", "test-root-integrity", "health", "make ci", "no runtime execution", "no network access", "no secret read", "no automatic repair"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
