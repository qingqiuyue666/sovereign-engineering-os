"""Coding Activity Panel contract tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.coding_activity_panel import (
    CODE_VISUALIZATION_CONTRACT,
    CODING_ACTIVITY_STATES,
    CodingActivityPanel,
    CodingActivitySnapshot,
    DiffPreviewRow,
    default_test_gates,
)


class SovereignConsoleCodingActivityPanelTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_activity_states_are_supported_by_contract(self) -> None:
        self.assertEqual(
            CODING_ACTIVITY_STATES,
            (
                "Idle",
                "Thinking",
                "Reading",
                "Coding",
                "Testing",
                "Writing Report",
                "Waiting Review",
                "Failed",
                "Stage Complete",
            ),
        )

    def test_code_visualization_contract_declares_required_diff_surface(self) -> None:
        for item in (
            "code block area",
            "file pill",
            "diff-like rows",
            "+ rows in success green",
            "- rows in muted red",
            "current line highlight",
            "cursor placeholder",
            "monospace font",
            "visualization only",
        ):
            self.assertIn(item, CODE_VISUALIZATION_CONTRACT)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_panel_renders_projected_code_activity_without_execution(self) -> None:
        panel = CodingActivityPanel(language="en")
        snapshot = CodingActivitySnapshot(
            state="Coding",
            current_action="Writing bounded changes",
            current_file="apps/ui/workspace_page.py",
            active_worker="ui-worker",
            activity_message="Writing bounded changes",
            diff_preview=(
                DiffPreviewRow("-", "old_static_panel()", current=False),
                DiffPreviewRow("+", "coding_activity_panel.render()", current=True),
            ),
            test_gate_summary=default_test_gates("Pending"),
        )
        panel.render_activity(snapshot)
        rendered = panel.rendered_activity()
        self.assertEqual(rendered["state"], "Coding")
        self.assertEqual(rendered["current_file"], "apps/ui/workspace_page.py")
        self.assertEqual(panel.diff_markers(), ("-", "+"))
        self.assertIn("+ coding_activity_panel.render()", panel.rendered_code_lines())


if __name__ == "__main__":
    unittest.main()
