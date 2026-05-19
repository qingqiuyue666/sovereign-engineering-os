"""Tracer-bullet tests for the non-core asset kit manifest."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.runtime.noncore_asset_kit_manifest import (
    NONCORE_REQUIRED_ASSET_GROUPS,
    NoncoreAssetKitManifest,
    build_noncore_asset_kit_manifest,
    render_noncore_asset_kit_manifest_markdown,
)
from kernel.runtime._production_workbench_validation import compute_content_hash


def valid_material() -> dict[str, object]:
    return {
        "manifest_id": "noncore-production-asset-kit-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "15c09fe5b7a2d7d5e2bb53a873eceadd458f2e32",
        "asset_groups": list(NONCORE_REQUIRED_ASSET_GROUPS),
        "documents": [
            "docs/operator/report_gallery.md",
            "docs/operator/noncore_asset_kit_manifest.md",
            "docs/operator/workspace_hygiene.md",
        ],
        "templates": [
            "docs/operator/task_intake/code_audit_task_intake.md",
            "docs/operator/examples/macro_signal_research/research_note_template.md",
        ],
        "examples": [
            "docs/operator/examples/code_audit/README.md",
            "docs/operator/examples/creative_asset_factory/README.md",
            "docs/operator/examples/macro_signal_research/README.md",
        ],
        "forms": [
            "docs/operator/forms/README.md",
            "docs/operator/forms/creative_asset_review_form.md",
        ],
        "sprint_artifacts": [
            "docs/operator/sprints/README.md",
            "docs/operator/sprints/sprint_001_production_activation.md",
        ],
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "financial execution remains blocked",
        ],
        "verification_matrix": {
            "tracer_bullet": "required",
            "schemas": "required",
            "acceptance": "required",
            "make_ci": "required",
        },
        "policy_version": "noncore-asset-kit-manifest-v1",
        "code_version": "0.1.0",
    }


class NoncoreAssetKitManifestTests(unittest.TestCase):
    def test_valid_manifest_builds_deterministic_object(self):
        manifest = build_noncore_asset_kit_manifest(valid_material(), observed_at="2026-05-19T00:00:00+08:00")
        self.assertIsInstance(manifest, NoncoreAssetKitManifest)
        self.assertEqual(manifest.content_hash, compute_content_hash(manifest.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        first = build_noncore_asset_kit_manifest(valid_material(), observed_at="2026-05-19T00:00:00+08:00")
        second = build_noncore_asset_kit_manifest(valid_material(), observed_at="2027-05-19T00:00:00+08:00")
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_is_deterministic(self):
        first = render_noncore_asset_kit_manifest_markdown(
            build_noncore_asset_kit_manifest(valid_material(), observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_noncore_asset_kit_manifest_markdown(
            build_noncore_asset_kit_manifest(valid_material(), observed_at="2026-05-19T00:00:00+08:00")
        )
        self.assertEqual(first, second)

    def test_missing_required_fields_fail_closed(self):
        for field_name in ("manifest_id", "asset_groups", "documents", "blocked_capabilities"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                del material[field_name]
                with self.assertRaises(ValueError):
                    build_noncore_asset_kit_manifest(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in (
            "raw_prompt",
            "raw_response",
            "env",
            "secret",
            "credential",
            "token",
            "api_key",
            "password",
            "private_key",
            "authorization",
        ):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"
                with self.assertRaises(ValueError):
                    build_noncore_asset_kit_manifest(material)

    def test_caller_supplied_content_hash_fails_closed(self):
        material = valid_material()
        material["content_hash"] = "sha256:" + "a" * 64
        with self.assertRaises(ValueError):
            build_noncore_asset_kit_manifest(material)

    def test_invalid_relative_paths_fail_closed(self):
        material = valid_material()
        material["documents"][0] = "/absolute/path.md"
        with self.assertRaises(ValueError):
            build_noncore_asset_kit_manifest(material)

    def test_manifest_doc_exists_and_lists_required_families(self):
        text = Path("docs/operator/noncore_asset_kit_manifest.md").read_text(encoding="utf-8").lower()
        self.assertIn("code audit examples", text)
        self.assertIn("creative sample pack", text)
        self.assertIn("macro templates", text)
        self.assertIn("operator review forms", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/noncore_asset_kit_manifest.py").read_text(encoding="utf-8")
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
