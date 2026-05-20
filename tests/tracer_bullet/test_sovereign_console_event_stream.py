"""Live Event Stream tests."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.live_event_stream import MAX_EVENT_BLOCKS, LiveEventStream
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleEventStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_event_stream_is_capped(self) -> None:
        stream = LiveEventStream()
        self.assertEqual(stream.capped_blocks(), 1000)
        self.assertEqual(MAX_EVENT_BLOCKS, 1000)
        source = Path("apps/ui/live_event_stream.py").read_text(encoding="utf-8")
        self.assertIn("setMaximumBlockCount", source)

    def test_fake_snapshot_contains_required_event_names(self) -> None:
        event_types = {event.event_type for event in fake_phase1_snapshot().latest_events}
        required = {
            "JobCreated",
            "WorkerSelected",
            "ArtifactRecorded",
            "HumanReviewRequested",
            "JobSucceeded",
            "JobQuarantined",
            "MaterializationBlocked",
            "ReviewApproved",
            "ReviewRejected",
        }
        self.assertTrue(required.issubset(event_types))


if __name__ == "__main__":
    unittest.main()
