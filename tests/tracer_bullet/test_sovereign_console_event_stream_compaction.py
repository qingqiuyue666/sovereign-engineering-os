"""Event stream compaction tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.live_event_stream import COLLAPSED_HEIGHT, EXPANDED_HEIGHT, MAX_EVENT_BLOCKS, LiveEventStream
from apps.ui.read_models import EventRow, RuntimeSnapshot, fake_phase1_snapshot


class SovereignConsoleEventStreamCompactionTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_stream_is_collapsed_compact_and_capped(self) -> None:
        stream = LiveEventStream(language="en")
        self.assertFalse(stream.is_expanded())
        self.assertEqual(COLLAPSED_HEIGHT, 42)
        self.assertEqual(EXPANDED_HEIGHT, 120)
        self.assertEqual(MAX_EVENT_BLOCKS, 120)
        self.assertEqual(stream.capped_blocks(), 120)
        stream.set_expanded(True)
        self.assertTrue(stream.is_expanded())

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_stream_renders_structured_capped_rows(self) -> None:
        base = fake_phase1_snapshot()
        events = tuple(
            EventRow(f"evt_{index}", "job", index, "JobCreated", "2026-05-20T09:00:00+00:00", "ok")
            for index in range(MAX_EVENT_BLOCKS + 5)
        )
        snapshot = RuntimeSnapshot(
            captured_at_ms=base.captured_at_ms,
            runtime_status=base.runtime_status,
            wal_status=base.wal_status,
            queue_depth=base.queue_depth,
            workers=base.workers,
            memory_pressure=base.memory_pressure,
            warning_count=base.warning_count,
            next_required_action=base.next_required_action,
            sync_stale=base.sync_stale,
            runtime_available=base.runtime_available,
            database_available=base.database_available,
            latest_events=events,
        )
        stream = LiveEventStream(language="en")
        stream.render_snapshot(snapshot)
        lines = stream.rendered_lines()
        self.assertEqual(len(lines), MAX_EVENT_BLOCKS)
        self.assertIn("info | 2026-05-20T09:00:00+00:00 | JobCreated | job | ok", lines[-1])


if __name__ == "__main__":
    unittest.main()
