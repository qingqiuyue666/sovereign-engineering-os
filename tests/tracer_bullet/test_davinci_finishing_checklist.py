"""Tracer-bullet tests for DaVinci finishing checklists."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.davinci_finishing_checklist import (
    DaVinciFinishingChecklist,
    build_davinci_finishing_checklist,
    render_davinci_finishing_checklist_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "checklist_id": "davinci-finishing-checklist-v1",
        "project_name": "VFX AI 3D Hybrid Sample",
        "color_pipeline": ["neutral working transform", "cinematic finishing look"],
        "contrast_targets": ["readable hero frame", "controlled black floor"],
        "highlight_policy": ["preserve detail", "motivated bloom only"],
        "subject_separation": ["clear silhouette", "readable depth"],
        "grain_halation_bloom_policy": ["subtle grain", "no smeared halos"],
        "artifact_review": ["check flicker", "check texture crawl"],
        "export_formats": ["review master", "vertical crop", "thumbnail frame"],
        "platform_deliverables": ["portfolio", "social"],
        "rejection_rules": ["reject artifact hiding", "reject unauthorized execution"],
        "blocked_execution": ["No DaVinci Resolve execution is allowed."],
        "rollback_plan": ["revert DaVinci checklist files as a unit"],
        "policy_version": "davinci-finishing-checklist-v1",
        "code_version": "0.1.0",
    }


class DaVinciFinishingChecklistTests(unittest.TestCase):
    def test_valid_checklist_builds_deterministic_object(self):
        checklist = build_davinci_finishing_checklist(
            valid_material(),
            observed_at="2026-05-19T00:00:00+08:00",
        )

        self.assertIsInstance(checklist, DaVinciFinishingChecklist)
        self.assertTrue(checklist.content_hash.startswith("sha256:"))
        self.assertEqual(checklist.content_hash, digest_payload(checklist.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_davinci_finishing_checklist(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_davinci_finishing_checklist(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_davinci_finishing_checklist_markdown(
            build_davinci_finishing_checklist(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_davinci_finishing_checklist_markdown(
            build_davinci_finishing_checklist(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_color_pipeline_fails_closed(self):
        material = valid_material()
        del material["color_pipeline"]

        with self.assertRaises(ValueError):
            build_davinci_finishing_checklist(material)

    def test_missing_export_formats_fails_closed(self):
        material = valid_material()
        del material["export_formats"]

        with self.assertRaises(ValueError):
            build_davinci_finishing_checklist(material)

    def test_missing_rejection_rules_fails_closed(self):
        material = valid_material()
        del material["rejection_rules"]

        with self.assertRaises(ValueError):
            build_davinci_finishing_checklist(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/davinci_finishing_checklist_v1.md").is_file())

    def test_doc_says_no_davinci_execution(self):
        text = Path("docs/operator/davinci_finishing_checklist_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no davinci execution", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/davinci_finishing_checklist.py").read_text(encoding="utf-8")

        for marker in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
