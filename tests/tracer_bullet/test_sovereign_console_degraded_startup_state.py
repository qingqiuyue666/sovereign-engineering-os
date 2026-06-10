"""Startup degraded/lost sync behavior tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from apps.sovereign_desktop import DesktopOsEngineFacade
from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.main_window import SovereignConsoleMainWindow
from apps.ui.motion import SyncState, resolve_sync_state
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleDegradedStartupStateTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_no_runtime_projection_defaults_to_degraded_not_lost(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            facade = DesktopOsEngineFacade(repo_root=Path.cwd(), runtime_root=Path(temp_dir_name))
            snapshot = facade.snapshot()
        self.assertEqual(resolve_sync_state(snapshot), SyncState.DEGRADED)
        self.assertFalse(snapshot.is_sync_lost())

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_window_shows_degraded_banner_without_lost_overlay_on_startup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            facade = DesktopOsEngineFacade(repo_root=Path.cwd(), runtime_root=Path(temp_dir_name))
            window = SovereignConsoleMainWindow(snapshot_provider=facade.snapshot, language="en")
            self.assertEqual(window.pulse_bar.rendered_text()["sync_health"], "Degraded")
            self.assertFalse(window.degraded_banner.isHidden())
            self.assertFalse(window.sync_lost_overlay.isVisible())
            self.assertEqual(window.sync_lost_overlay.sync_state(), "Degraded")
            window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_lost_overlay_only_after_previous_healthy_projection_is_lost(self) -> None:
        snapshots = [fake_phase1_snapshot(), fake_phase1_snapshot(stale=True)]

        def provider():
            return snapshots.pop(0) if snapshots else fake_phase1_snapshot(stale=True)

        window = SovereignConsoleMainWindow(snapshot_provider=provider, language="en")
        window.refresh_snapshot()
        self.assertEqual(window.sync_lost_overlay.sync_state(), "Lost")
        self.assertFalse(window.sync_lost_overlay.isHidden())
        window.close()


if __name__ == "__main__":
    unittest.main()
