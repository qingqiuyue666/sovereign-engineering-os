"""Failure Quarantine UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.failure_quarantine_page import FailureQuarantinePage
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleFailureQuarantineUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_page_includes_traceback_event_and_quarantine_fields(self) -> None:
        page = FailureQuarantinePage()
        fields = set(page.required_fields())
        for field in (
            "traceback excerpt",
            "event trail",
            "quarantine path",
            "failed worker",
            "failure reason",
            "recommended fix",
        ):
            self.assertIn(field, fields)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_failure_projection_renders_and_export_is_gated(self) -> None:
        page = FailureQuarantinePage()
        page.render_snapshot(fake_phase1_snapshot())
        self.assertIn("JobQuarantined", page.event_trail.text())
        self.assertFalse(page.export_bundle_button.isEnabled())
        self.assertEqual(page.traceback_excerpt.objectName(), "TracebackExcerptPanel")


if __name__ == "__main__":
    unittest.main()
