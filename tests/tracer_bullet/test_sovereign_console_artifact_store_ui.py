"""Artifact Store UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE, Qt
from apps.ui.artifact_store_page import ArtifactStorePage
from apps.ui.models import ArtifactStoreTableModel
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleArtifactStoreUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_artifact_store_displays_required_fields(self) -> None:
        page = ArtifactStorePage()
        fields = set(page.required_fields())
        for field in (
            "type",
            "artifact_id",
            "job_id",
            "sha256",
            "size",
            "review_status",
            "quarantine_status",
            "local_only",
            "safe_to_publish",
        ):
            self.assertIn(field, fields)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_artifact_model_truncates_sha_and_keeps_actions_gated(self) -> None:
        snapshot = fake_phase1_snapshot()
        model = ArtifactStoreTableModel(snapshot.latest_artifacts)
        sha_index = model.index(0, 3)
        displayed = model.data(sha_index, Qt.ItemDataRole.DisplayRole)
        self.assertEqual(displayed, snapshot.latest_artifacts[0].sha256_short())

        page = ArtifactStorePage()
        page.render_snapshot(snapshot)
        self.assertIn("artifact_id", page.preview_metadata.text())
        self.assertFalse(page.open_folder_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
