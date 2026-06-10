"""Sync Lost Overlay behavior tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE, QPushButton
from apps.ui.read_models import SYNC_STALE_AFTER_MS, fake_phase1_snapshot
from apps.ui.sync_lost_overlay import SyncLostOverlay


class SovereignConsoleSyncLostOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_snapshot_age_and_stale_flags_drive_sync_loss(self) -> None:
        healthy = fake_phase1_snapshot()
        stale = fake_phase1_snapshot(stale=True)
        self.assertFalse(healthy.is_sync_lost())
        self.assertFalse(stale.is_sync_lost())
        self.assertTrue(stale.is_sync_lost(had_healthy_projection=True))
        self.assertFalse(healthy.is_sync_lost(now_ms=healthy.captured_at_ms + SYNC_STALE_AFTER_MS + 1))
        self.assertTrue(
            healthy.is_sync_lost(
                now_ms=healthy.captured_at_ms + SYNC_STALE_AFTER_MS + 1,
                had_healthy_projection=True,
            )
        )

    def test_overlay_visible_when_stale_and_hidden_when_healthy(self) -> None:
        overlay = SyncLostOverlay()
        button = QPushButton("Submit")
        button.setEnabled(True)

        overlay.apply_snapshot(fake_phase1_snapshot(stale=True), action_controls=(button,), had_healthy_projection=True)
        self.assertTrue(overlay.is_sync_lost())
        self.assertTrue(overlay.isVisible())
        self.assertFalse(button.isEnabled())

        overlay.apply_snapshot(fake_phase1_snapshot(), action_controls=(button,))
        self.assertFalse(overlay.is_sync_lost())
        self.assertFalse(overlay.isVisible())
        self.assertTrue(button.isEnabled())

    def test_stale_overlay_locks_action_controls(self) -> None:
        overlay = SyncLostOverlay()
        submit = QPushButton("Issue Command")
        submit.setEnabled(True)
        overlay.bind_action_controls((submit,))
        overlay.set_sync_lost(True)
        self.assertFalse(submit.isEnabled())


if __name__ == "__main__":
    unittest.main()
