"""Tracer-bullet tests for Creative Asset Factory planning contracts."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.creative_asset_factory_plan import (
    CreativeAssetFactoryPlan,
    build_creative_asset_factory_plan,
    render_creative_asset_factory_plan_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "plan_id": "creative-asset-factory-v1-sample",
        "project_name": "VFX AI 3D Hybrid Sample",
        "target_output": "8-12 second VFX/AI/3D hybrid sample",
        "duration_seconds": 10,
        "visual_style": "cinematic abstract field simulation with AI-enhanced texture passes",
        "shot_plan": [
            {"shot": "opening", "duration": 3, "description": "field emergence"},
            {"shot": "middle", "duration": 4, "description": "particle/VDB interaction"},
            {"shot": "end", "duration": 3, "description": "finished logo-free resolve"},
        ],
        "tool_roles": {
            "houdini": "particle/VDB/field design",
            "comfyui": "image/video style enhancement",
            "davinci_resolve": "finishing/color",
            "ae": "final assembly if needed",
        },
        "asset_requirements": [
            "style frame reference",
            "simulation notes",
            "delivery format notes",
        ],
        "production_steps": [
            "write shot plan",
            "assign tool roles",
            "run human review before external execution",
        ],
        "blocked_execution": [
            "no provider execution",
            "no tool launching",
            "no file deletion",
        ],
        "quality_gates": [
            "duration remains 8-12 seconds",
            "planning-only boundary preserved",
        ],
        "rollback_notes": [
            "revert plan files as a unit",
        ],
        "policy_version": "creative-asset-factory-plan-v1",
        "code_version": "0.1.0",
    }


class CreativeAssetFactoryPlanTests(unittest.TestCase):
    def test_valid_plan_builds_deterministic_object(self):
        plan = build_creative_asset_factory_plan(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(plan, CreativeAssetFactoryPlan)
        self.assertTrue(plan.content_hash.startswith("sha256:"))
        self.assertEqual(plan.content_hash, digest_payload(plan.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_creative_asset_factory_plan_markdown(
            build_creative_asset_factory_plan(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_creative_asset_factory_plan_markdown(
            build_creative_asset_factory_plan(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_creative_asset_factory_plan(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_creative_asset_factory_plan(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_missing_plan_id_fails_closed(self):
        material = valid_material()
        del material["plan_id"]

        with self.assertRaises(ValueError):
            build_creative_asset_factory_plan(material)

    def test_invalid_duration_fails_closed(self):
        material = valid_material()
        material["duration_seconds"] = 0

        with self.assertRaises(ValueError):
            build_creative_asset_factory_plan(material)

    def test_missing_shot_plan_fails_closed(self):
        material = valid_material()
        del material["shot_plan"]

        with self.assertRaises(ValueError):
            build_creative_asset_factory_plan(material)

    def test_forbidden_raw_and_sensitive_fields_fail_closed(self):
        for field_name in (
            "raw_prompt",
            "raw_response",
            "raw_exception",
            "raw_traceback",
            "env",
            "secret",
            "token",
            "api_key",
            "password",
            "private_key",
            "authorization",
        ):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material["tool_roles"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_creative_asset_factory_plan(material)

    def test_generated_creative_doc_exists(self):
        self.assertTrue(Path("docs/operator/creative_asset_factory_v1.md").is_file())

    def test_doc_says_no_houdini_comfyui_davinci_execution_is_performed(self):
        text = Path("docs/operator/creative_asset_factory_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no houdini/comfyui/davinci execution is performed", text)

    def test_doc_includes_8_to_12_second_sample_target(self):
        text = Path("docs/operator/creative_asset_factory_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("8-12 second vfx/ai/3d hybrid sample", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/creative_asset_factory_plan.py").read_text(encoding="utf-8")

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
