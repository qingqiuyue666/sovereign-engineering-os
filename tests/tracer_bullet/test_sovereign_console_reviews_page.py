"""Reviews gate view tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.read_models import fake_phase1_snapshot
from apps.ui.reviews_page import MIN_REJECT_REASON_LENGTH, ReviewsPage


class SovereignConsoleReviewsPageTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_reviews_absorbs_human_review_and_quarantine(self) -> None:
        page = ReviewsPage(language="en")
        page.render_snapshot(fake_phase1_snapshot())
        self.assertEqual(page.title.text(), "Reviews")
        self.assertEqual(page.required_sections(), ("Pending Reviews", "Rejected", "Quarantined", "Failures"))
        self.assertEqual(page.absorbed_domains(), ("Human Review", "Failure Quarantine"))
        for field in (
            "review list",
            "selected artifact preview placeholder",
            "approve control",
            "reject control",
            "reject reason validation",
            "quarantine state",
            "failure reason",
            "traceback dark panel",
            "event trail",
            "recommended fix",
            "final claim warning",
        ):
            self.assertIn(field, page.required_fields())
        self.assertTrue(all(not button.isEnabled() for button in page.action_controls()))

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_reject_reason_validation_remains_gated(self) -> None:
        page = ReviewsPage(language="en")
        page.set_facade_actions_enabled(True)
        page.set_reject_reason("bad")
        self.assertFalse(page.reject_reason_is_valid())
        self.assertFalse(page.reject_button.isEnabled())
        page.set_reject_reason("valid")
        self.assertGreaterEqual(len("valid"), MIN_REJECT_REASON_LENGTH)
        self.assertTrue(page.reject_reason_is_valid())
        self.assertTrue(page.reject_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
