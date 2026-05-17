import unittest
from pathlib import Path


EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"


class RootIntegrityHealthGateWiringTests(unittest.TestCase):
    def read_makefile(self) -> str:
        path = Path("Makefile")
        self.assertTrue(path.is_file(), "Makefile missing")
        return path.read_text(encoding="utf-8")

    def test_makefile_declares_root_integrity_target(self):
        text = self.read_makefile()
        self.assertIn("test-root-integrity", text)
        self.assertIn("tests.tracer_bullet.test_root_integrity_verifier", text)

    def test_health_runs_root_integrity_before_other_health_gates(self):
        health_line = next(line for line in self.read_makefile().splitlines() if line.startswith("health:"))
        self.assertEqual(health_line, EXPECTED_HEALTH)
        for earlier, later in (
            ("test-root-integrity", "test-sealed-evidence-coverage"),
            ("test-gated-provider-transport", "test-real-runtime-provider-transport-execution"),
            ("test-real-runtime-provider-transport-execution", "test-runtime-sealed-receipt"),
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

    def test_root_integrity_artifacts_exist_on_mainline_candidate(self):
        for path in ("governance/root/root_manifest_v1.json", "kernel/bootstrap/root_integrity_verifier.py", "tests/tracer_bullet/test_root_integrity_verifier.py"):
            self.assertTrue(Path(path).is_file(), path)

    def test_root_integrity_health_gate_decision_exists(self):
        text = Path("docs/decisions/root_integrity_health_gate_wiring_v1.md").read_text(encoding="utf-8")
        for marker in ("ROOT_INTEGRITY_HEALTH_GATE_WIRING_READY_FOR_LOCAL_TESTS", "test-root-integrity", "make ci"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
