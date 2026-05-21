"""Bilingual labels for coding activity and anime micro-FX."""

from __future__ import annotations

import unittest

from apps.ui.i18n import translate


class SovereignConsoleAnimeFxI18nTests(unittest.TestCase):
    def test_required_english_and_chinese_labels_exist(self) -> None:
        expectations = {
            "coding_activity.title": ("Coding Activity", "编码活动"),
            "coding_activity.state.thinking": ("Thinking", "思考中"),
            "coding_activity.state.reading": ("Reading", "读取中"),
            "coding_activity.state.coding": ("Coding", "写代码中"),
            "coding_activity.state.testing": ("Testing", "测试中"),
            "coding_activity.state.writing_report": ("Writing Report", "写报告中"),
            "coding_activity.state.waiting_review": ("Waiting Review", "等待审查"),
            "coding_activity.state.failed": ("Failed", "失败"),
            "coding_activity.state.stage_complete": ("Stage Complete", "阶段完成"),
            "coding_activity.message.coding": ("Writing bounded changes", "正在写入受限变更"),
            "coding_activity.message.testing": ("Running validation gates", "正在运行验证门"),
            "coding_activity.message.failed": ("Failure isolated. Evidence preserved.", "失败已隔离，证据已保留"),
            "coding_activity.message.idle": ("No active run. The engine is quiet.", "暂无运行任务，引擎安静"),
            "settings.anime_fx": ("Anime FX", "动漫微特效"),
            "settings.motion_intensity": ("Motion Intensity", "动效强度"),
            "motion.off": ("Off", "关闭"),
            "motion.minimal": ("Minimal", "最小"),
            "motion.standard": ("Standard", "标准"),
            "motion.playful": ("Playful", "活泼"),
        }
        for key, (english, chinese) in expectations.items():
            with self.subTest(key=key):
                self.assertEqual(translate(key, "en"), english)
                self.assertEqual(translate(key, "zh"), chinese)

    def test_command_bar_placeholder_is_bilingual(self) -> None:
        self.assertEqual(translate("workspace.command_placeholder", "en"), "Ask, generate, inspect, or run a mission...")
        self.assertEqual(translate("workspace.command_placeholder", "zh"), "询问、生成、检查或运行任务…")


if __name__ == "__main__":
    unittest.main()
