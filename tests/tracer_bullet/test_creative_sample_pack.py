"""Tracer-bullet tests for the creative production sample pack."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path("docs/operator/examples/creative_asset_factory")


class CreativeSamplePackTests(unittest.TestCase):
    def test_creative_sample_docs_exist(self):
        for name in (
            "README.md",
            "sample_project_brief.md",
            "shot_bible_v1.md",
            "houdini_asset_requirements.md",
            "comfyui_workflow_requirements.md",
            "davinci_finishing_requirements.md",
            "ae_assembly_notes.md",
            "asset_directory_contract.md",
            "review_checklist.md",
            "rejection_rules.md",
            "day_by_day_execution_plan.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_shot_bible_includes_required_targets(self):
        text = (ROOT / "shot_bible_v1.md").read_text(encoding="utf-8").lower()
        self.assertIn("8-12 seconds", text)
        self.assertIn("motivated transition", text)
        self.assertIn("hero frame", text)

    def test_houdini_requirements_forbid_execution(self):
        text = (ROOT / "houdini_asset_requirements.md").read_text(encoding="utf-8").lower()
        self.assertIn("no houdini execution", text)
        self.assertIn("no hython execution", text)

    def test_comfyui_requirements_forbid_execution(self):
        text = (ROOT / "comfyui_workflow_requirements.md").read_text(encoding="utf-8").lower()
        self.assertIn("no comfyui execution", text)
        self.assertIn("no model execution", text)
        self.assertIn("no network execution", text)

    def test_davinci_requirements_forbid_execution(self):
        text = (ROOT / "davinci_finishing_requirements.md").read_text(encoding="utf-8").lower()
        self.assertIn("no davinci execution", text)

    def test_review_checklist_mentions_artifact_control_and_commercial_usability(self):
        text = (ROOT / "review_checklist.md").read_text(encoding="utf-8").lower()
        self.assertIn("artifact control", text)
        self.assertIn("commercial usability", text)


if __name__ == "__main__":
    unittest.main()
