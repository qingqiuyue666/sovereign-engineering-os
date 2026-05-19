"""Tracer-bullet tests for operator task intake templates."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path("docs/operator/task_intake")


class OperatorTaskIntakeTemplatesTests(unittest.TestCase):
    def test_all_intake_templates_exist(self):
        for name in (
            "README.md",
            "code_audit_task_intake.md",
            "creative_asset_task_intake.md",
            "macro_research_task_intake.md",
            "bugfix_task_intake.md",
            "documentation_task_intake.md",
            "review_only_task_intake.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_each_template_includes_required_sections(self):
        required_sections = (
            "## allowed files",
            "## forbidden files",
            "## required tests",
            "## blocked capabilities",
            "## human review requirement",
        )
        for path in ROOT.glob("*_task_intake.md"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                for section in required_sections:
                    self.assertIn(section, text)


if __name__ == "__main__":
    unittest.main()
