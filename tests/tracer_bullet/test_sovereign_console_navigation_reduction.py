"""Navigation reduction tests for the five-entry console rail."""

from __future__ import annotations

import unittest

from apps.ui.navigation_rail import NAVIGATION_ITEMS, REMOVED_FIRST_LEVEL_LABELS


class SovereignConsoleNavigationReductionTests(unittest.TestCase):
    def test_navigation_items_are_exactly_five(self) -> None:
        labels = tuple(label for _page_id, label, _key in NAVIGATION_ITEMS)
        self.assertEqual(labels, ("Workspace", "Runs", "Artifacts", "Reviews", "Settings"))
        self.assertEqual(len(labels), 5)

    def test_removed_first_level_labels_are_declared_and_absent(self) -> None:
        labels = tuple(label for _page_id, label, _key in NAVIGATION_ITEMS)
        for removed in REMOVED_FIRST_LEVEL_LABELS:
            with self.subTest(label=removed):
                self.assertNotIn(removed, labels)


if __name__ == "__main__":
    unittest.main()
