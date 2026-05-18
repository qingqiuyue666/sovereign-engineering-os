"""Tracer-bullet tests for Houdini asset specifications."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.houdini_asset_spec import (
    HOUDINI_REQUIRED_ASSET_CLASSES,
    HoudiniAssetSpec,
    build_houdini_asset_spec,
    render_houdini_asset_spec_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "spec_id": "houdini-asset-spec-v1",
        "project_name": "VFX AI 3D Hybrid Sample",
        "asset_classes": list(HOUDINI_REQUIRED_ASSET_CLASSES),
        "particle_requirements": ["directional field flow", "hero frame convergence"],
        "vdb_requirements": ["smoke or energy volume", "readable subject separation"],
        "field_requirements": ["motivated transition vector field"],
        "pass_exports": ["velocity", "depth", "normal", "emission"],
        "camera_metadata": {"focal_length": "caller supplied", "frame_range": "caller supplied"},
        "naming_contract": {"pattern": "project_shot_asset_pass_version"},
        "directory_contract": {"source_notes": "planned", "pass_specs": "planned"},
        "blocked_execution": ["No Houdini/hython/tool execution is allowed."],
        "quality_gates": ["all required asset classes present", "passes support review"],
        "rollback_plan": ["revert Houdini asset spec files as a unit"],
        "policy_version": "houdini-asset-spec-v1",
        "code_version": "0.1.0",
    }


class HoudiniAssetSpecTests(unittest.TestCase):
    def test_valid_houdini_spec_builds_deterministic_object(self):
        spec = build_houdini_asset_spec(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(spec, HoudiniAssetSpec)
        self.assertTrue(spec.content_hash.startswith("sha256:"))
        self.assertEqual(spec.content_hash, digest_payload(spec.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_houdini_asset_spec(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_houdini_asset_spec(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_houdini_asset_spec_markdown(
            build_houdini_asset_spec(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_houdini_asset_spec_markdown(
            build_houdini_asset_spec(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_required_asset_class_fails_closed(self):
        material = valid_material()
        material["asset_classes"].remove("normal_pass")

        with self.assertRaises(ValueError):
            build_houdini_asset_spec(material)

    def test_missing_pass_exports_fails_closed(self):
        material = valid_material()
        del material["pass_exports"]

        with self.assertRaises(ValueError):
            build_houdini_asset_spec(material)

    def test_missing_naming_contract_fails_closed(self):
        material = valid_material()
        del material["naming_contract"]

        with self.assertRaises(ValueError):
            build_houdini_asset_spec(material)

    def test_missing_directory_contract_fails_closed(self):
        material = valid_material()
        del material["directory_contract"]

        with self.assertRaises(ValueError):
            build_houdini_asset_spec(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/houdini_asset_spec_v1.md").is_file())

    def test_doc_says_no_houdini_hython_tool_execution(self):
        text = Path("docs/operator/houdini_asset_spec_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no houdini/hython/tool execution", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/houdini_asset_spec.py").read_text(encoding="utf-8")

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
