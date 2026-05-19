"""Tracer-bullet tests for private production sprint artifacts."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path("docs/operator/sprints")


class ProductionSprintArtifactsTests(unittest.TestCase):
    def test_sprint_index_exists(self):
        self.assertTrue((ROOT / "README.md").is_file())

    def test_all_day_docs_exist(self):
        for name in (
            "sprint_001_production_activation.md",
            "sprint_001_day_1_code_audit.md",
            "sprint_001_day_2_merge_readiness.md",
            "sprint_001_day_3_retrospective_daily_loop.md",
            "sprint_001_day_4_creative_bible.md",
            "sprint_001_day_5_tool_specs.md",
            "sprint_001_day_6_review_rubric.md",
            "sprint_001_day_7_review_next_sprint.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_sprint_overview_says_no_kernel_expansion_enforcement(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("no-kernel-expansion enforcement", text)

    def test_day_1_mentions_code_audit(self):
        text = (ROOT / "sprint_001_day_1_code_audit.md").read_text(encoding="utf-8").lower()
        self.assertIn("code audit", text)

    def test_day_5_mentions_houdini_comfyui_davinci_but_no_execution(self):
        text = (ROOT / "sprint_001_day_5_tool_specs.md").read_text(encoding="utf-8").lower()
        self.assertIn("houdini", text)
        self.assertIn("comfyui", text)
        self.assertIn("davinci", text)
        self.assertIn("no execution", text)

    def test_day_7_includes_next_sprint_decision(self):
        text = (ROOT / "sprint_001_day_7_review_next_sprint.md").read_text(encoding="utf-8").lower()
        self.assertIn("next sprint decision", text)


if __name__ == "__main__":
    unittest.main()
