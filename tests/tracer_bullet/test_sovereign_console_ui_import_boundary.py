"""Import boundary tests for the Sovereign Console desktop shell."""

from __future__ import annotations

import importlib
import os
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.dashboard_page import DashboardPage
from apps.ui.read_models import fake_phase1_snapshot
from apps.ui.right_inspector import RightInspector

UI_MODULES = (
    "apps.sovereign_desktop",
    "apps.ui.theme",
    "apps.ui.main_window",
    "apps.ui.system_pulse_bar",
    "apps.ui.navigation_rail",
    "apps.ui.workspace_page",
    "apps.ui.runs_page",
    "apps.ui.artifacts_page",
    "apps.ui.reviews_page",
    "apps.ui.dashboard_page",
    "apps.ui.job_queue_page",
    "apps.ui.right_inspector",
    "apps.ui.live_event_stream",
    "apps.ui.status_chip_delegate",
    "apps.ui.sync_lost_overlay",
    "apps.ui.models",
    "apps.ui.read_models",
)


class SovereignConsoleUiImportBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_importing_ui_modules_does_not_launch_gui_jobs_network_or_tools(self) -> None:
        for module_name in UI_MODULES:
            sys.modules.pop(module_name, None)
        with (
            patch("subprocess.run") as subprocess_run,
            patch("subprocess.Popen") as subprocess_popen,
            patch.object(socket, "create_connection") as socket_connect,
        ):
            modules = [importlib.import_module(module_name) for module_name in UI_MODULES]
        self.assertTrue(all(modules))
        subprocess_run.assert_not_called()
        subprocess_popen.assert_not_called()
        socket_connect.assert_not_called()

    def test_desktop_module_import_is_passive_and_exposes_entrypoint(self) -> None:
        desktop = importlib.import_module("apps.sovereign_desktop")
        self.assertIn(desktop.PYSIDE6_AVAILABLE, {True, False})
        self.assertTrue(callable(desktop.main))
        self.assertTrue(hasattr(desktop, "DesktopOsEngineFacade"))
        self.assertTrue(hasattr(desktop, "SovereignDesktopWindow"))

    def test_ui_source_has_no_external_tool_names_or_network_clients(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8").lower() for path in _ui_source_paths())
        forbidden = (
            "hython",
            "houdini",
            "comfyui",
            "davinci",
            "requests.",
            "httpx.",
            "urllib.request",
            "socket.",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_dashboard_and_inspector_build_from_fake_snapshot(self) -> None:
        snapshot = fake_phase1_snapshot()
        dashboard = DashboardPage()
        dashboard.render_snapshot(snapshot)
        self.assertEqual(dashboard.rendered_values()["runtime_status"], "Available")

        inspector = RightInspector()
        inspector.show_job(snapshot.latest_jobs[0])
        self.assertEqual(inspector.state_label.text(), "Selected Run")


def _ui_source_paths() -> tuple[Path, ...]:
    return (Path("apps/sovereign_desktop.py"), *tuple(sorted(Path("apps/ui").glob("*.py"))))


if __name__ == "__main__":
    unittest.main()
