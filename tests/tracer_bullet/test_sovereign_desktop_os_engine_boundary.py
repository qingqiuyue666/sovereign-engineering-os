"""Desktop boundary tests for OS engine integration."""

from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path
from unittest import mock


DESKTOP_PATH = Path("apps/sovereign_desktop.py")


class SovereignDesktopOsEngineBoundaryTests(unittest.TestCase):
    def test_import_is_safe_and_does_not_start_gui_or_execute_jobs(self) -> None:
        sys.modules.pop("apps.sovereign_desktop", None)
        with mock.patch("asyncio.create_subprocess_exec", side_effect=AssertionError("subprocess forbidden")):
            with mock.patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
                desktop = importlib.import_module("apps.sovereign_desktop")
        self.assertIn(desktop.PYSIDE6_AVAILABLE, {True, False})
        self.assertTrue(callable(desktop.main))

    def test_import_does_not_connect_external_creative_services(self) -> None:
        source = DESKTOP_PATH.read_text(encoding="utf-8").lower()
        forbidden = ("comfyui", "davinci", "hython", "houdini", "requests.", "httpx.", "urllib.request")
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_import_does_not_run_subprocess_commands_or_jobs(self) -> None:
        source = DESKTOP_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        module_level_calls: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                module_level_calls.append(ast.unparse(node.value))
        self.assertEqual(module_level_calls, [])
        self.assertNotIn("subprocess", source)

    def test_missing_optional_dependencies_are_handled_lazily(self) -> None:
        desktop = importlib.import_module("apps.sovereign_desktop")
        if not desktop.PYSIDE6_AVAILABLE:
            with self.assertRaises(RuntimeError):
                desktop.QApplication([])
        else:
            self.assertTrue(hasattr(desktop, "SovereignDesktopWindow"))

    def test_phase1_gui_actions_are_read_only_and_facade_backed(self) -> None:
        source = DESKTOP_PATH.read_text(encoding="utf-8")
        self.assertIn("DesktopOsEngineFacade", source)
        self.assertIn("ReadModelProvider", source)
        self.assertNotIn(".create_job(", source)
        self.assertNotIn(".enqueue_job(", source)
        self.assertNotIn("run_whitelisted_command", source)
        self.assertNotIn("submit_prompt", source)
        self.assertNotIn("create_subprocess_exec", source)

    def test_no_dangerous_delete_overwrite_or_external_network_surface_is_exposed(self) -> None:
        source = DESKTOP_PATH.read_text(encoding="utf-8")
        forbidden = ("unlink(", "rmtree(", "remove(", "replace(", "requests.", "http://", "https://")
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
