"""Settings view tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.read_models import fake_phase1_snapshot
from apps.ui.settings_page import SettingsPage


class SovereignConsoleSettingsPageTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_settings_absorbs_boundaries_and_system_health(self) -> None:
        page = SettingsPage(language="en")
        self.assertEqual(
            page.required_sections(),
            ("Runtime", "Language", "Motion", "Boundaries", "Paths", "Workers", "Publishing", "System Health"),
        )
        fields = set(page.required_fields())
        for field in (
            "Language: Auto / English / Chinese",
            "Motion Intensity: Minimal / Standard / High Energy",
            "Local-only mode",
            "External network disabled",
            "Allowed workers",
            "Dangerous action gates",
            "Human review gates",
            "Publish policy",
            "GitHub summary-only policy",
            "System Health",
            "memory",
            "WAL state",
            "DB connection state",
            "last smoke result",
            "last CI result",
            "warnings",
        ):
            self.assertIn(field, fields)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_settings_renders_system_health_projection(self) -> None:
        page = SettingsPage(language="en")
        page.render_snapshot(fake_phase1_snapshot())
        health = page.rendered_system_health()
        self.assertIn("Nominal", health["memory"])
        self.assertEqual(health["WAL state"], "WAL")
        self.assertEqual(health["DB connection state"], "Available")


if __name__ == "__main__":
    unittest.main()
