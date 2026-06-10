"""Artifacts view tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.artifacts_page import ArtifactsPage
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleArtifactsPageTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_artifacts_absorbs_store_and_asset_library(self) -> None:
        page = ArtifactsPage(language="en")
        page.render_snapshot(fake_phase1_snapshot())
        self.assertEqual(page.title.text(), "Artifacts")
        self.assertEqual(page.required_sections(), ("Artifact Store", "Asset Library", "Resource Intake"))
        self.assertEqual(page.absorbed_domains(), ("Artifact Store", "Asset Library"))
        for field in (
            "artifact table",
            "artifact preview placeholder",
            "checksum",
            "size",
            "local path alias",
            "review status",
            "quarantine status",
            "safe_to_publish",
            "local_only",
            "asset library section placeholder",
            "resource intake placeholder",
        ):
            self.assertIn(field, page.required_fields())
        self.assertIn("local_path_alias", page.preview_metadata.text())
        self.assertFalse(page.open_folder_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
