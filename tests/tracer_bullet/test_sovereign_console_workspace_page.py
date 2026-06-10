"""Workspace page contract tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.motion import SyncState
from apps.ui.read_models import fake_phase1_snapshot
from apps.ui.workspace_page import WorkspacePage


class SovereignConsoleWorkspacePageTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_workspace_contains_required_mission_surface(self) -> None:
        page = WorkspacePage(language="en")
        page.render_snapshot(fake_phase1_snapshot())
        fields = set(page.required_fields())
        for field in (
            "current mission",
            "command area",
            "next required action",
            "HFX_008 compact chain",
            "recent runs",
            "recent artifacts",
            "pending reviews count",
            "quarantined count",
            "local runtime status",
            "context packet quick actions",
        ):
            self.assertIn(field, fields)
        self.assertEqual(page.rendered_mission()["mission_id"], "HFX_008")
        self.assertEqual(page.rendered_mission()["mission_name"], "HFX_008 Energy Shockwave")
        self.assertEqual(
            page.compact_chain_stages(),
            ("Topology Audit", "Proof Artifact", "Validation", "Human Review", "Summary", "Claim Gate"),
        )

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_workspace_actions_are_gated_and_degraded_banner_is_card_not_overlay(self) -> None:
        page = WorkspacePage(language="en")
        page.render_snapshot(fake_phase1_snapshot(stale=True), sync_state=SyncState.DEGRADED)
        self.assertFalse(page.degraded_banner.isHidden())
        self.assertTrue(all(not button.isEnabled() for button in page.action_controls()))


if __name__ == "__main__":
    unittest.main()
