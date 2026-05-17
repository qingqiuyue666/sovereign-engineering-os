"""Status reporter V12 tests — no overclaim verification."""

import unittest

from kernel.status.status_reporter import v12_status_report


class StatusReporterV12Tests(unittest.TestCase):
    def test_report_is_machine_readable_and_deterministic(self):
        first = v12_status_report()
        second = v12_status_report()
        self.assertEqual(first, second)
        self.assertIn("security", first["implemented_modules"])

    def test_forbidden_surfaces_not_claimed_absent_without_gate_evidence(self):
        report = v12_status_report()
        surfaces = report["forbidden_surfaces"]
        self.assertIsInstance(surfaces, dict)
        for name, status in surfaces.items():
            self.assertIn(status, (
                "unknown_without_gate_evidence",
                "absent_by_gate_evidence",
                "gate_check_failed",
            ))

    def test_forbidden_surfaces_unknown_without_gate_results(self):
        report = v12_status_report()
        for name, status in report["forbidden_surfaces"].items():
            self.assertEqual(status, "unknown_without_gate_evidence",
                             f"Surface '{name}' should be unknown_without_gate_evidence when no gate results provided")

    def test_production_autonomy_not_enabled(self):
        report = v12_status_report()
        self.assertFalse(report["production_autonomy_enabled"])

    def test_report_includes_health_plan(self):
        report = v12_status_report()
        self.assertIn("health_plan", report)
        self.assertIsInstance(report["health_plan"], list)
