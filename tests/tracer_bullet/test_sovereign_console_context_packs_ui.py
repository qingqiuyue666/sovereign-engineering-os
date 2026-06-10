"""Context Packs UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.context_packs_page import CONTEXT_PACKET_OPTIONS, ContextPacksPage
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleContextPacksUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_packet_options_include_required_targets(self) -> None:
        page = ContextPacksPage()
        self.assertEqual(page.packet_options(), CONTEXT_PACKET_OPTIONS)
        for option in (
            "Gemini packet",
            "Codex task packet",
            "Claude review packet",
            "HFX-only packet",
            "desktop-only packet",
            "tests-only packet",
            "branch diff packet",
        ):
            self.assertIn(option, page.packet_options())

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_budget_and_controls_are_projection_only(self) -> None:
        page = ContextPacksPage()
        page.render_snapshot(fake_phase1_snapshot())
        self.assertIn("Token / Size Budget", page.token_budget.text())
        self.assertFalse(page.copy_button.isEnabled())
        self.assertFalse(page.open_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
