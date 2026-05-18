"""Tracer-bullet tests for shared production workbench validation helpers."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.runtime._production_workbench_validation import (
    contains_required_terms,
    has_nonempty_violation,
    has_unsafe_status,
    prepare_material,
)


class ProductionWorkbenchValidationTests(unittest.TestCase):
    def test_prepare_material_rejects_caller_content_hash(self):
        with self.assertRaises(ValueError):
            prepare_material({"content_hash": "sha256:" + ("0" * 64)}, observed_at=None, material_name="sample")

    def test_prepare_material_excludes_observed_at_from_normalized_material(self):
        material, observed_at = prepare_material(
            {"report_id": "sample", "observed_at": "2026-05-19T00:00:00+08:00"},
            observed_at=None,
            material_name="sample",
        )

        self.assertEqual(material, {"report_id": "sample"})
        self.assertEqual(observed_at, "2026-05-19T00:00:00+08:00")

    def test_status_helpers_detect_unsafe_and_violation_signals(self):
        self.assertTrue(has_unsafe_status({"Makefile": {"status": "unsafe"}}))
        self.assertTrue(has_nonempty_violation({"violations": ["provider execution"]}))
        self.assertFalse(has_nonempty_violation({"violations": []}))

    def test_required_terms_helper_is_deterministic(self):
        material = {"blocked_execution": ["No external tool execution."]}

        self.assertTrue(contains_required_terms(material, ("external", "tool", "execution")))

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/_production_workbench_validation.py").read_text(encoding="utf-8")

        for marker in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
