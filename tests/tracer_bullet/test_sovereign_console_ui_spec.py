"""Spec checks for Sovereign Console unified workspace UI."""

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
            "unified production workspace",
            "Workspace",
            "Runs",
            "Artifacts",
            "Reviews",
            "Settings",
            "read-model and command-issuer only",
            "OS Runtime Facade",
            "System Pulse",
            "Reduced left rail",
            "QStackedWidget",
            "Inspector",
            "Event Stream / Black Box",
            "QTableView",
            "QAbstractTableModel",
            "QTableWidget",
            "HFX_008 Energy Shockwave",
            "Runtime projection unavailable. Read-only workspace is active.",
            "SYSTEM SYNC LOST",
            "Startup with no runtime projection must be Degraded",
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
