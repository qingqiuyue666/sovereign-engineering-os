"""Settings / Boundaries UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.settings_page import SettingsPage


class SovereignConsoleSettingsBoundariesUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_settings_include_language_and_motion_options(self) -> None:
        page = SettingsPage()
        self.assertEqual(page.language_options(), ("auto", "en", "zh"))
        self.assertEqual(page.motion_options(), ("Minimal", "Standard", "High Energy"))
        fields = set(page.required_fields())
        self.assertIn("Language: Auto / English / Chinese", fields)
        self.assertIn("Motion Intensity: Minimal / Standard / High Energy", fields)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_boundaries_are_visible_and_read_only_by_default(self) -> None:
        page = SettingsPage()
        values = page.rendered_boundaries()
        self.assertEqual(values["Local-only mode"], "Enabled")
        self.assertIn("GUI execution surface", values["External network disabled"])
        self.assertIn("review", values["Publish policy"])


if __name__ == "__main__":
    unittest.main()
