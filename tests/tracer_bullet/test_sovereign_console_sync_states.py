"""Sync state refinement tests."""

from __future__ import annotations

from dataclasses import replace
import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE, QPushButton
from apps.ui.motion import SyncState, resolve_sync_state
from apps.ui.read_models import SYNC_STALE_AFTER_MS, fake_phase1_snapshot
from apps.ui.sync_lost_overlay import SyncLostOverlay


class SovereignConsoleSyncStatesTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_sync_states_resolve_healthy_degraded_lost(self) -> None:
        healthy = fake_phase1_snapshot()
        degraded = replace(healthy, sync_stale=True, runtime_available=True, database_available=True)
        unavailable = replace(healthy, runtime_available=False)

        self.assertEqual(resolve_sync_state(healthy), SyncState.HEALTHY)
        self.assertEqual(resolve_sync_state(degraded, now_ms=degraded.captured_at_ms), SyncState.DEGRADED)
        self.assertEqual(resolve_sync_state(unavailable), SyncState.DEGRADED)
        self.assertEqual(resolve_sync_state(unavailable, had_healthy_projection=True), SyncState.LOST)
        self.assertEqual(
            resolve_sync_state(healthy, now_ms=healthy.captured_at_ms + SYNC_STALE_AFTER_MS + 1),
            SyncState.DEGRADED,
        )
        self.assertEqual(
            resolve_sync_state(
                healthy,
                now_ms=healthy.captured_at_ms + SYNC_STALE_AFTER_MS + 1,
                had_healthy_projection=True,
            ),
            SyncState.LOST,
        )

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_lost_state_locks_actions_and_shows_required_text(self) -> None:
        overlay = SyncLostOverlay(language="en")
        button = QPushButton("Issue Intent")
        button.setEnabled(True)
        overlay.bind_action_controls((button,))
        overlay.set_sync_state(SyncState.LOST)

        self.assertTrue(overlay.is_sync_lost())
        self.assertTrue(overlay.actions_locked())
        self.assertFalse(button.isEnabled())
        self.assertEqual(overlay.title.text(), "SYSTEM SYNC LOST — ACTIONS LOCKED")
        self.assertEqual(
            overlay.detail.text(),
            "Runtime projection is stale. Read-only navigation remains available.",
        )

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_chinese_lost_state_text(self) -> None:
        overlay = SyncLostOverlay(language="zh")
        overlay.set_sync_state(SyncState.LOST)
        self.assertEqual(overlay.title.text(), "系统同步丢失 — 操作已锁定")
        self.assertEqual(overlay.detail.text(), "运行时投影已过期。只读导航仍可使用。")


if __name__ == "__main__":
    unittest.main()
