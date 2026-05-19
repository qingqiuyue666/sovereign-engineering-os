"""Tracer-bullet tests for the private report gallery."""

from __future__ import annotations

from pathlib import Path
import unittest


class PrivateReportGalleryTests(unittest.TestCase):
    def test_report_gallery_exists(self):
        self.assertTrue(Path("docs/operator/report_gallery.md").is_file())

    def test_examples_index_exists(self):
        self.assertTrue(Path("docs/operator/examples/README.md").is_file())

    def test_report_gallery_links_to_required_families(self):
        text = Path("docs/operator/report_gallery.md").read_text(encoding="utf-8").lower()
        self.assertIn("code audit examples", text)
        self.assertIn("creative sample pack", text)
        self.assertIn("macro research templates", text)
        self.assertIn("operator review forms", text)

    def test_report_gallery_says_no_live_execution_readiness_is_implied(self):
        text = Path("docs/operator/report_gallery.md").read_text(encoding="utf-8").lower()
        self.assertIn("nothing here proves live execution readiness is implied", text)


if __name__ == "__main__":
    unittest.main()
