"""Test Gate Panel contract tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.anime_micro_fx import GateVisualState
from apps.ui.coding_activity_panel import TestGatePanel


class SovereignConsoleTestGatePanelTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_test_gate_panel_supports_required_gates_and_states(self) -> None:
        panel = TestGatePanel(language="en")
        self.assertEqual(panel.gate_names(), ("Unit Tests", "Schemas", "Acceptance", "make ci"))
        self.assertEqual(panel.supported_gate_states(), ("Pending", "Running", "OK", "Failed", "Skipped"))

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_gate_panel_stamps_ok_without_claiming_unknown_gates(self) -> None:
        panel = TestGatePanel(language="en")
        panel.render_gates(
            (
                GateVisualState("Unit Tests", "OK"),
                GateVisualState("Schemas", "Running"),
                GateVisualState("Acceptance", "Pending"),
                GateVisualState("make ci", "Skipped"),
            )
        )
        self.assertEqual(panel.gate_statuses(), ("OK", "Running", "Pending", "Skipped"))
        self.assertEqual(panel.ok_stamp_count(), 1)


if __name__ == "__main__":
    unittest.main()
