import unittest
from pathlib import Path


class RootIntegrityHealthGateWiringTests(unittest.TestCase):
    def read_makefile(self) -> str:
        path = Path("Makefile")
        self.assertTrue(path.is_file(), "Makefile missing")
        return path.read_text(encoding="utf-8")

    def test_makefile_declares_root_integrity_target(self):
        text = self.read_makefile()
        self.assertIn("test-root-integrity", text)
        self.assertIn(
            "PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_root_integrity_verifier -v",
            text,
        )

    def test_health_runs_root_integrity_before_other_health_gates(self):
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

    def test_root_integrity_artifacts_exist_on_mainline_candidate(self):
        required_paths = (
            "governance/root/root_manifest_v1.json",
            "kernel/bootstrap/root_integrity_verifier.py",
            "tests/tracer_bullet/test_root_integrity_verifier.py",
            "docs/decisions/root_integrity_verifier_foundation_v1.md",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_root_integrity_health_gate_decision_exists(self):
        path = Path("docs/decisions/root_integrity_health_gate_wiring_v1.md")
        self.assertTrue(path.is_file(), str(path))
        text = path.read_text(encoding="utf-8")
        for marker in (
            "ROOT_INTEGRITY_HEALTH_GATE_WIRING_READY_FOR_LOCAL_TESTS",
            "test-root-integrity",
            "health",
            "make ci",
            "no runtime execution",
            "no network access",
            "no secret read",
            "no automatic repair",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
