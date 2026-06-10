"""i18n tests for Sovereign Console Phase 2."""

from __future__ import annotations

from dataclasses import replace
import unittest

from apps.ui.i18n import Language, localize_status, snapshot_with_display_language, translate
from apps.ui.read_models import EventRow, fake_phase1_snapshot


class SovereignConsoleI18nTests(unittest.TestCase):
    def test_english_labels_resolve(self) -> None:
        self.assertEqual(translate("page.dashboard", Language.ENGLISH), "Dashboard")
        self.assertEqual(translate("settings.language", "en"), "Language")

    def test_chinese_labels_resolve(self) -> None:
        self.assertEqual(translate("page.dashboard", Language.CHINESE), "仪表盘")
        self.assertEqual(translate("sync.lost.title", "zh"), "系统同步丢失 — 操作已锁定")

    def test_missing_key_fails_closed_with_placeholder(self) -> None:
        self.assertEqual(translate("missing.phase2.key", "en"), "[[missing.phase2.key]]")

    def test_canonical_status_enum_is_not_mutated(self) -> None:
        canonical = "Requires Human Review"
        display = localize_status(canonical, "zh")
        self.assertEqual(canonical, "Requires Human Review")
        self.assertEqual(display, "需要人工审核")

    def test_event_type_remains_canonical(self) -> None:
        event = EventRow("evt", "job", 1, "HumanReviewRequested", "2026-05-20T00:00:00+00:00")
        self.assertIn("HumanReviewRequested", event.line())

    def test_language_switching_does_not_mutate_snapshots(self) -> None:
        snapshot = fake_phase1_snapshot()
        switched = snapshot_with_display_language(snapshot, "zh")
        self.assertEqual(snapshot, switched)
        self.assertEqual(snapshot.latest_events[0].event_type, switched.latest_events[0].event_type)
        self.assertEqual(snapshot.latest_jobs[0].status, switched.latest_jobs[0].status)

    def test_replace_snapshot_keeps_canonical_status(self) -> None:
        snapshot = fake_phase1_snapshot()
        clone = replace(snapshot)
        self.assertEqual(clone.latest_jobs[0].status, "Dry Run Complete")


if __name__ == "__main__":
    unittest.main()
