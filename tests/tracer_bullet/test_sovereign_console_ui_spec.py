"""Spec checks for Sovereign Console UI Phase 1."""

from __future__ import annotations

import unittest
from pathlib import Path

SPEC = Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md")


class SovereignConsoleUiSpecTests(unittest.TestCase):
    def test_spec_exists_and_contains_architecture_decisions(self) -> None:
        self.assertTrue(SPEC.exists())
        text = SPEC.read_text(encoding="utf-8")
        required = (
            "Sovereign Console",
            "Sovereign C2",
            "Light-Dark Hybrid Living Production Console",
            "single-window workspace",
            "read-model and command-issuer only",
            "never owns execution",
            "System Pulse Bar",
            "Navigation",
            "QStackedWidget",
            "Right Inspector",
            "Live Event Stream",
            "QTableView",
            "QAbstractTableModel",
            "QTableWidget",
            "QStyledItemDelegate",
            "Sync Lost Overlay",
            "strict status lexicon",
            "forbidden fake completion labels",
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "macOS `.app` packaging",
            "Command Palette",
            "HFX chain custom view",
            "Qt main thread",
            "bounded queries with `LIMIT`",
            "full-table scans",
            "write SQLite from GUI widgets",
            "direct process APIs",
            "network by default",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_design_tokens_are_recorded(self) -> None:
        text = SPEC.read_text(encoding="utf-8")
        for color in ("#ECECEE", "#FFFFFF", "#0D0D0D", "#0066CC", "#34C759", "#FF9500", "#FF3B30"):
            with self.subTest(color=color):
                self.assertIn(color, text)


if __name__ == "__main__":
    unittest.main()
