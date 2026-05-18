"""Tracer-bullet tests for Creative Asset Factory production bibles."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.creative_asset_production_bible import (
    CreativeAssetProductionBible,
    build_creative_asset_production_bible,
    render_creative_asset_production_bible_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "bible_id": "creative-asset-production-bible-v1",
        "project_name": "VFX AI 3D Hybrid Sample",
        "target_duration_seconds": 10,
        "target_platforms": ["portfolio reel", "social vertical crop", "thumbnail hero frame"],
        "visual_reference_language": ["cinematic field simulation", "one strong hero frame"],
        "story_beat": "Energy condenses into a readable hero frame through a motivated transition.",
        "shot_list": [
            {"shot": "01", "duration": 3, "intent": "field emergence"},
            {"shot": "02", "duration": 4, "intent": "hero frame lock"},
            {"shot": "03", "duration": 3, "intent": "clean resolve"},
        ],
        "tool_roles": {
            "houdini": "particle/VDB/field assets",
            "comfyui": "controlled enhancement/stylization",
            "davinci_resolve": "finishing/color",
            "after_effects": "assembly or polish if needed",
        },
        "asset_requirements": ["hero frame reference", "pass map", "review notes"],
        "pass_requirements": ["depth", "normal", "emission", "velocity"],
        "quality_gates": ["one hero frame", "motivated transition", "no cheap AI artifact look"],
        "rejection_rules": ["reject random prompt-only generation", "reject unmanaged artifacts"],
        "delivery_outputs": ["production bible", "tool specs", "review rubric"],
        "blocked_execution": ["No external tool execution is allowed."],
        "rollback_plan": ["revert production bible files as a unit"],
        "policy_version": "creative-asset-production-bible-v1",
        "code_version": "0.1.0",
    }


class CreativeAssetProductionBibleTests(unittest.TestCase):
    def test_valid_production_bible_builds_deterministic_object(self):
        bible = build_creative_asset_production_bible(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(bible, CreativeAssetProductionBible)
        self.assertTrue(bible.content_hash.startswith("sha256:"))
        self.assertEqual(bible.content_hash, digest_payload(bible.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_creative_asset_production_bible(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_creative_asset_production_bible(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_creative_asset_production_bible_markdown(
            build_creative_asset_production_bible(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_creative_asset_production_bible_markdown(
            build_creative_asset_production_bible(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_invalid_duration_fails_closed(self):
        material = valid_material()
        material["target_duration_seconds"] = 13

        with self.assertRaises(ValueError):
            build_creative_asset_production_bible(material)

    def test_missing_shot_list_fails_closed(self):
        material = valid_material()
        del material["shot_list"]

        with self.assertRaises(ValueError):
            build_creative_asset_production_bible(material)

    def test_missing_quality_gates_fails_closed(self):
        material = valid_material()
        del material["quality_gates"]

        with self.assertRaises(ValueError):
            build_creative_asset_production_bible(material)

    def test_missing_rejection_rules_fails_closed(self):
        material = valid_material()
        del material["rejection_rules"]

        with self.assertRaises(ValueError):
            build_creative_asset_production_bible(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "env", "secret", "token", "api_key", "password"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_creative_asset_production_bible(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/creative_asset_factory_production_bible_v1.md").is_file())

    def test_doc_says_no_external_tool_execution(self):
        text = Path("docs/operator/creative_asset_factory_production_bible_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no external tool execution", text)

    def test_doc_includes_one_hero_frame(self):
        text = Path("docs/operator/creative_asset_factory_production_bible_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("one strong hero frame", text)

    def test_doc_includes_motivated_transition(self):
        text = Path("docs/operator/creative_asset_factory_production_bible_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("motivated transition", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/creative_asset_production_bible.py").read_text(encoding="utf-8")

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
