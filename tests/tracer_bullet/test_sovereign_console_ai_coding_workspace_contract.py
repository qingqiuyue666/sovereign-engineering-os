"""AI coding workspace contract tests for Sovereign Console."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.navigation_rail import NAVIGATION_ITEMS
from apps.ui.read_models import fake_phase1_snapshot
from apps.ui.workspace_page import WorkspacePage


class SovereignConsoleAiCodingWorkspaceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_top_level_navigation_remains_exactly_five_entries(self) -> None:
        labels = tuple(label for _page_id, label, _key in NAVIGATION_ITEMS)
        self.assertEqual(labels, ("Workspace", "Runs", "Artifacts", "Reviews", "Settings"))

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_workspace_contract_contains_ai_coding_mission_surfaces(self) -> None:
        page = WorkspacePage(language="en")
        page.render_snapshot(fake_phase1_snapshot())
        fields = set(page.required_fields())
        for field in (
            "large command bar",
            "mission thread",
            "activity stream",
            "Coding Activity Panel",
            "Test Gate Panel",
            "HFX_008 compact chain",
            "compact black box/event stream",
        ):
            self.assertIn(field, fields)
        self.assertEqual(page.command_placeholder(), "Ask, generate, inspect, or run a mission...")
        self.assertEqual(page.rendered_mission()["mission_name"], "HFX_008 Energy Shockwave")

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_workspace_includes_required_mission_thread_cards(self) -> None:
        page = WorkspacePage(language="en")
        self.assertEqual(
            page.mission_thread_cards(),
            (
                "User command placeholder",
                "AI planning card",
                "Coding activity card",
                "Test gate card",
                "Artifact/review summary card",
                "Final report placeholder card",
            ),
        )


if __name__ == "__main__":
    unittest.main()
