"""Tracer-bullet tests for the PySide6 desktop module boundary."""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest

_HAS_PYSIDE6 = importlib.util.find_spec("PySide6") is not None


class SovereignDesktopHeadlessBoundaryTests(unittest.TestCase):
    def test_module_import_is_safe_without_starting_qt(self) -> None:
        desktop = importlib.import_module("apps.sovereign_desktop")

        self.assertIn(desktop.PYSIDE6_AVAILABLE, {True, False})
        self.assertTrue(callable(desktop.main))


@unittest.skipUnless(_HAS_PYSIDE6, "PySide6 is not installed in this CI environment")
class SovereignDesktopGuiTests(unittest.TestCase):
    def test_gui_symbols_are_available_when_pyside6_is_installed(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        desktop = importlib.import_module("apps.sovereign_desktop")

        self.assertTrue(desktop.PYSIDE6_AVAILABLE)
        self.assertTrue(issubclass(desktop.SovereignDesktopWindow, desktop.QMainWindow))


if __name__ == "__main__":
    unittest.main()
