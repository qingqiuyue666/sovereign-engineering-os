"""Human Review UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.human_review_page import MIN_REJECT_REASON_LENGTH, HumanReviewPage
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleHumanReviewUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_page_exposes_required_review_fields(self) -> None:
        page = HumanReviewPage()
        fields = set(page.required_fields())
        for field in (
            "pending reviews list",
            "preview placeholder",
            "metadata panel",
            "approve button",
            "reject button",
            "reject reason field",
            "quarantine button",
            "final claim warning",
        ):
            self.assertIn(field, fields)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_reject_reason_requires_minimum_length_when_actions_active(self) -> None:
        page = HumanReviewPage()
        page.set_facade_actions_enabled(True)
        page.set_reject_reason("bad")
        self.assertFalse(page.reject_reason_is_valid())
        self.assertFalse(page.reject_button.isEnabled())
        page.set_reject_reason("valid")
        self.assertGreaterEqual(len("valid"), MIN_REJECT_REASON_LENGTH)
        self.assertTrue(page.reject_reason_is_valid())
        self.assertTrue(page.reject_button.isEnabled())

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_default_action_buttons_are_gated(self) -> None:
        page = HumanReviewPage()
        page.render_snapshot(fake_phase1_snapshot())
        self.assertTrue(all(not button.isEnabled() for button in page.action_controls()))


if __name__ == "__main__":
    unittest.main()
