"""System Health UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.energy_widgets import SystemPulseBoiler
from apps.ui.system_health_page import SystemHealthPage
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleSystemHealthUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_system_health_includes_required_fields(self) -> None:
        page = SystemHealthPage()
        fields = set(page.required_fields())
        for field in (
            "memory usage",
            "worker count",
            "active process count",
            "DB connection state",
            "SQLite WAL state",
            "artifact store size",
            "sync health",
        ):
            self.assertIn(field, fields)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_system_pulse_boiler_classifies_memory_and_wal(self) -> None:
        boiler = SystemPulseBoiler()
        boiler.render(memory_pressure="High (2048 MB)", wal_status="error")
        self.assertEqual(boiler.severity_tuple(), ("fatal", "fatal"))

        page = SystemHealthPage()
        page.render_snapshot(fake_phase1_snapshot())
        values = page.rendered_values()
        self.assertIn("memory usage", values)
        self.assertIn("SQLite WAL state", values)


if __name__ == "__main__":
    unittest.main()
