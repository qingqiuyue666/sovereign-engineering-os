"""i18n coverage for the new workspace IA labels."""

from __future__ import annotations

import unittest

from apps.ui.i18n import translate
from apps.ui.read_models import EventRow


class SovereignConsoleI18nWorkspaceLabelsTests(unittest.TestCase):
    def test_primary_navigation_labels_resolve_in_english_and_chinese(self) -> None:
        expected = {
            "page.workspace": ("Workspace", "工作台"),
            "page.runs": ("Runs", "运行"),
            "page.artifacts": ("Artifacts", "产物"),
            "page.reviews": ("Reviews", "审查"),
            "page.settings": ("Settings", "设置"),
            "common.mission": ("Mission", "任务"),
            "common.current_mission": ("Current Mission", "当前任务"),
            "common.next_action": ("Next Required Action", "下一步必需动作"),
            "event_stream.title": ("Event Stream", "事件流"),
            "event_stream.black_box": ("Black Box", "黑匣子"),
            "reviews.pending": ("Pending Reviews", "待审查"),
            "reviews.quarantined": ("Quarantined", "已隔离"),
            "reviews.failures": ("Failures", "失败"),
            "settings.boundaries": ("Boundaries", "边界"),
            "common.local_only": ("Local-only", "仅本地"),
            "settings.external_network_disabled": ("External network disabled", "外部网络已禁用"),
        }
        for key, (english, chinese) in expected.items():
            with self.subTest(key=key):
                self.assertEqual(translate(key, "en"), english)
                self.assertEqual(translate(key, "zh"), chinese)

    def test_degraded_and_lost_sync_messages_resolve_exactly(self) -> None:
        self.assertEqual(
            translate("sync.degraded.detail", "en"),
            "Runtime projection unavailable. Read-only workspace is active.",
        )
        self.assertEqual(translate("sync.degraded.detail", "zh"), "运行时投影不可用。当前为只读工作台。")
        self.assertEqual(translate("sync.lost.title", "en"), "SYSTEM SYNC LOST — ACTIONS LOCKED")
        self.assertEqual(translate("sync.lost.title", "zh"), "系统同步丢失 — 操作已锁定")

    def test_canonical_event_codes_remain_english(self) -> None:
        event = EventRow("evt", "job", 1, "HumanReviewRequested", "2026-05-20T00:00:00+00:00")
        self.assertIn("HumanReviewRequested", event.line())


if __name__ == "__main__":
    unittest.main()
