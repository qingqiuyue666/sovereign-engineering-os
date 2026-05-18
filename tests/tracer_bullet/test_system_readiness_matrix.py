"""Tracer-bullet tests for the full system readiness matrix."""

import unittest
from pathlib import Path

from kernel.runtime.system_readiness_matrix import build_system_readiness_matrix

REQUIRED_SECTIONS = {
    "governance_integrity",
    "local_runtime",
    "review_gate",
    "operator_review_host",
    "decision_ledger",
    "durable_decision_store",
    "durable_review_store",
    "recovery",
    "audit_export",
    "read_only_status",
    "work_queue",
    "runbook_shell",
    "provider_worker_preflight",
    "real_provider_execution_blocked",
    "production_autonomy_blocked",
}


class SystemReadinessMatrixTests(unittest.TestCase):
    def test_readiness_matrix_includes_all_required_sections(self):
        matrix = build_system_readiness_matrix()
        self.assertEqual({section.section_name for section in matrix.sections}, REQUIRED_SECTIONS)

    def test_completed_implemented_sections_are_marked_available(self):
        matrix = build_system_readiness_matrix()
        sections = {section.section_name: section for section in matrix.sections}
        for section_name in (
            "durable_decision_store",
            "durable_review_store",
            "recovery",
            "audit_export",
            "read_only_status",
            "work_queue",
            "runbook_shell",
            "provider_worker_preflight",
        ):
            self.assertTrue(sections[section_name].available)
            self.assertEqual(sections[section_name].status, "available")

    def test_real_provider_execution_is_blocked(self):
        matrix = build_system_readiness_matrix()
        section = {item.section_name: item for item in matrix.sections}["real_provider_execution_blocked"]
        self.assertFalse(section.available)
        self.assertEqual(section.status, "blocked")

    def test_production_autonomy_is_blocked(self):
        matrix = build_system_readiness_matrix()
        section = {item.section_name: item for item in matrix.sections}["production_autonomy_blocked"]
        self.assertFalse(section.available)
        self.assertEqual(section.status, "blocked")

    def test_content_hash_deterministic(self):
        first = build_system_readiness_matrix(
            matrix_id="matrix-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_system_readiness_matrix(
            matrix_id="matrix-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(first.content_hash, second.content_hash)

    def test_observed_at_excluded(self):
        first = build_system_readiness_matrix(
            matrix_id="matrix-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_system_readiness_matrix(
            matrix_id="matrix-001",
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/system_readiness_matrix.py").read_text(encoding="utf-8")
        for marker in (
            "import subprocess",
            "import socket",
            "import requests",
            "import httpx",
            "import sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
