"""Tracer-bullet tests for deterministic public asset manifests."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.public_asset_manifest import (
    PublicAssetManifest,
    build_public_asset_manifest,
    render_public_asset_manifest_markdown,
)

VALID_DIGEST = "sha256:" + "a" * 64


def valid_material() -> dict[str, object]:
    return {
        "manifest_id": "sovereign-production-os-public-asset-pack-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "1f4f77b8141e04343ace0d6ee62205d73805381e",
        "asset_items": [
            {
                "asset_id": "mainline-audit-report",
                "path": "docs/reports/sovereign_engineering_os_mainline_audit_report.md",
                "asset_type": "markdown_report",
                "public_safe": True,
                "purpose": "Deterministic public-safe engineering audit report.",
                "verification_status": "tracked in tracer-bullet public asset checks",
                "declared_hash": VALID_DIGEST,
            },
            {
                "asset_id": "code-audit-workbench",
                "path": "kernel/runtime/code_audit_workbench.py",
                "asset_type": "deterministic_validator_module",
                "public_safe": True,
                "purpose": "Pure deterministic builder and Markdown renderer.",
                "verification_status": "covered by existing code audit workbench tests",
            },
        ],
        "verification_matrix": {
            "tracer_bullet": "5543 tests, 4 skipped, OK",
            "schemas": "70 tests, OK",
            "acceptance": "156 tests, OK",
            "make_ci": "passed",
            "git_diff_check": "passed",
            "clean_tree_guard": "passed",
        },
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "external actions remain blocked",
        ],
        "safety_boundaries": [
            "local-only",
            "no provider calls",
            "no network",
            "no production autonomy",
            "no real external execution",
        ],
        "public_release_notes": [
            "The current audit report is caller-input driven.",
            "The report generator does not discover hidden facts.",
            "This asset is not a trading system.",
        ],
        "policy_version": "public-asset-manifest-v1",
        "code_version": "0.1.0",
    }


class PublicAssetManifestTests(unittest.TestCase):
    def test_valid_manifest_builds_deterministic_object(self):
        manifest = build_public_asset_manifest(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(manifest, PublicAssetManifest)
        self.assertTrue(manifest.content_hash.startswith("sha256:"))
        self.assertEqual(manifest.content_hash, digest_payload(manifest.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_public_asset_manifest(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_public_asset_manifest(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_is_deterministic(self):
        material = valid_material()

        first = render_public_asset_manifest_markdown(
            build_public_asset_manifest(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_public_asset_manifest_markdown(
            build_public_asset_manifest(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_public_safe_false_fails_closed(self):
        material = valid_material()
        material["asset_items"][0]["public_safe"] = False

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_missing_manifest_id_fails_closed(self):
        material = valid_material()
        del material["manifest_id"]

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_missing_asset_items_fails_closed(self):
        material = valid_material()
        del material["asset_items"]

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_empty_asset_items_fails_closed(self):
        material = valid_material()
        material["asset_items"] = []

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_asset_item_missing_path_fails_closed(self):
        material = valid_material()
        del material["asset_items"][0]["path"]

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_asset_item_missing_purpose_fails_closed(self):
        material = valid_material()
        del material["asset_items"][0]["purpose"]

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_raw_prompt_field_fails_closed(self):
        material = valid_material()
        material["verification_matrix"]["raw_prompt"] = "blocked"

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_raw_response_field_fails_closed(self):
        material = valid_material()
        material["verification_matrix"]["raw_response"] = "blocked"

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_sensitive_field_names_fail_closed(self):
        for field_name in (
            "env",
            "secret",
            "token",
            "api_key",
            "password",
            "credential",
            "private_key",
            "authorization",
        ):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material["verification_matrix"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_public_asset_manifest(material)

    def test_invalid_digest_field_fails_closed(self):
        material = valid_material()
        material["asset_items"] = deepcopy(material["asset_items"])
        material["asset_items"][0]["declared_hash"] = "not-a-digest"

        with self.assertRaises(ValueError):
            build_public_asset_manifest(material)

    def test_generated_overview_doc_exists(self):
        self.assertTrue(Path("docs/reports/sovereign_production_os_public_asset_overview.md").is_file())

    def test_generated_manifest_doc_exists(self):
        self.assertTrue(Path("docs/reports/sovereign_production_os_public_asset_manifest.md").is_file())

    def test_reports_readme_exists(self):
        self.assertTrue(Path("docs/reports/README.md").is_file())

    def test_overview_doc_says_real_provider_execution_remains_blocked(self):
        text = Path("docs/reports/sovereign_production_os_public_asset_overview.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("real provider execution remains blocked", text)

    def test_overview_doc_says_production_autonomy_remains_blocked(self):
        text = Path("docs/reports/sovereign_production_os_public_asset_overview.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("production autonomy remains blocked", text)

    def test_overview_doc_says_this_is_not_a_trading_system(self):
        text = Path("docs/reports/sovereign_production_os_public_asset_overview.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("this asset is not a trading system", text)

    def test_manifest_doc_lists_mainline_audit_report(self):
        text = Path("docs/reports/sovereign_production_os_public_asset_manifest.md").read_text(encoding="utf-8")

        self.assertIn("docs/reports/sovereign_engineering_os_mainline_audit_report.md", text)

    def test_manifest_doc_lists_code_audit_workbench(self):
        text = Path("docs/reports/sovereign_production_os_public_asset_manifest.md").read_text(encoding="utf-8")

        self.assertIn("kernel/runtime/code_audit_workbench.py", text)

    def test_public_docs_do_not_contain_blocked_raw_markers(self):
        text = "\n".join(
            Path(path).read_text(encoding="utf-8").lower()
            for path in (
                "docs/reports/sovereign_production_os_public_asset_overview.md",
                "docs/reports/sovereign_production_os_public_asset_manifest.md",
            )
        )

        for marker in (
            "raw_prompt",
            "raw_response",
            "raw_exception",
            "raw_traceback",
        ):
            self.assertNotIn(marker, text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/public_asset_manifest.py").read_text(encoding="utf-8")

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
