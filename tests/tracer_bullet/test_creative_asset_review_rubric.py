"""Tracer-bullet tests for creative asset review rubrics."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.creative_asset_review_rubric import (
    CREATIVE_RUBRIC_REQUIRED_SCORING_CATEGORIES,
    CreativeAssetReviewRubric,
    build_creative_asset_review_rubric,
    render_creative_asset_review_rubric_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "rubric_id": "creative-asset-review-rubric-v1",
        "project_name": "VFX AI 3D Hybrid Sample",
        "scoring_categories": list(CREATIVE_RUBRIC_REQUIRED_SCORING_CATEGORIES),
        "rejection_rules": ["reject cheap AI artifact look", "reject unmotivated transition"],
        "pass_thresholds": {"pass": 85, "needs_rework": 65},
        "artifact_checks": ["texture crawl", "warped detail"],
        "motion_checks": ["motion coherence", "motivated transition"],
        "lighting_checks": ["highlight control", "subject separation"],
        "compositing_checks": ["depth consistency", "edge believability"],
        "ai_overuse_checks": ["prompt-only aesthetic", "style drift"],
        "commercial_usability_checks": ["portfolio ready", "thumbnail readable"],
        "review_decision_options": ["pass", "needs_rework", "reject"],
        "rollback_plan": ["revert creative rubric files as a unit"],
        "policy_version": "creative-asset-review-rubric-v1",
        "code_version": "0.1.0",
    }


class CreativeAssetReviewRubricTests(unittest.TestCase):
    def test_valid_rubric_builds_deterministic_object(self):
        rubric = build_creative_asset_review_rubric(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(rubric, CreativeAssetReviewRubric)
        self.assertTrue(rubric.content_hash.startswith("sha256:"))
        self.assertEqual(rubric.content_hash, digest_payload(rubric.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_creative_asset_review_rubric(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_creative_asset_review_rubric(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_creative_asset_review_rubric_markdown(
            build_creative_asset_review_rubric(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_creative_asset_review_rubric_markdown(
            build_creative_asset_review_rubric(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_required_scoring_category_fails_closed(self):
        material = valid_material()
        material["scoring_categories"].remove("commercial_usability")

        with self.assertRaises(ValueError):
            build_creative_asset_review_rubric(material)

    def test_invalid_review_decision_option_fails_closed(self):
        material = valid_material()
        material["review_decision_options"] = ["pass", "auto_approve"]

        with self.assertRaises(ValueError):
            build_creative_asset_review_rubric(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/creative_asset_review_rubric_v1.md").is_file())

    def test_doc_includes_ai_overuse_control(self):
        text = Path("docs/operator/creative_asset_review_rubric_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("ai overuse control", text)

    def test_doc_includes_commercial_usability(self):
        text = Path("docs/operator/creative_asset_review_rubric_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("commercial usability", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/creative_asset_review_rubric.py").read_text(encoding="utf-8")

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
