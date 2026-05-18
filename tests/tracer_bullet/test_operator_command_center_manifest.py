"""Tracer-bullet tests for the private operator command-center manifest."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_command_center_manifest import (
    OperatorCommandCenterManifest,
    build_operator_command_center_manifest,
    render_operator_command_center_manifest_markdown,
)

VALID_DIGEST = "sha256:" + "a" * 64


def valid_material() -> dict[str, object]:
    return {
        "manifest_id": "private-operator-command-center-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "documents": [
            {
                "document_id": "operator-command-center",
                "path": "docs/operator/operator_command_center.md",
                "title": "Private Operator Command Center",
                "purpose": "Private navigation and control layer for the operator.",
                "private_operator_only": True,
                "required_sections": [
                    "Operator Summary",
                    "Current System State",
                    "What Is Frozen",
                    "What Is Allowed Next",
                    "What Is Forbidden",
                    "Mandatory Verification Commands",
                    "AI Worker Handoff Rules",
                    "Merge Rules",
                    "Rollback Rules",
                    "Next Production Priorities",
                ],
                "declared_hash": VALID_DIGEST,
            },
            {
                "document_id": "blocked-capabilities",
                "path": "docs/operator/blocked_capabilities.md",
                "title": "Blocked Capabilities",
                "purpose": "Private statement of blocked execution boundaries.",
                "private_operator_only": True,
                "required_sections": [
                    "Blocked Means Blocked",
                    "Real Provider Execution",
                    "Production Autonomy",
                    "External Actions",
                    "Financial Execution",
                    "Network Execution",
                    "Subprocess Execution",
                    "Environment / Secret Access",
                    "Trading Automation",
                    "Conditions Required Before Any Future Unblock",
                ],
            },
        ],
        "linked_reports": [
            "docs/reports/README.md",
            "docs/reports/sovereign_engineering_os_mainline_audit_report.md",
            "docs/reports/sovereign_production_os_public_asset_overview.md",
            "docs/reports/sovereign_production_os_public_asset_manifest.md",
        ],
        "current_priorities": [
            "private operator command center",
            "private operator state report",
            "code audit daily report workflow",
        ],
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "external actions remain blocked",
            "financial execution is out of scope",
            "trading automation is blocked",
        ],
        "mandatory_verification": [
            "python3 -m unittest tests.tracer_bullet.test_operator_command_center_manifest -v",
            "python3 -m unittest discover -s tests/tracer_bullet -v",
            "make ci",
        ],
        "policy_version": "operator-command-center-manifest-v1",
        "code_version": "0.1.0",
    }


class OperatorCommandCenterManifestTests(unittest.TestCase):
    def test_valid_manifest_builds_deterministic_object(self):
        manifest = build_operator_command_center_manifest(
            valid_material(),
            observed_at="2026-05-19T00:00:00+08:00",
        )

        self.assertIsInstance(manifest, OperatorCommandCenterManifest)
        self.assertTrue(manifest.content_hash.startswith("sha256:"))
        self.assertEqual(manifest.content_hash, digest_payload(manifest.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_operator_command_center_manifest(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_operator_command_center_manifest(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_operator_command_center_manifest_markdown(
            build_operator_command_center_manifest(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_operator_command_center_manifest_markdown(
            build_operator_command_center_manifest(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_manifest_id_fails_closed(self):
        material = valid_material()
        del material["manifest_id"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_missing_repository_url_fails_closed(self):
        material = valid_material()
        del material["repository_url"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_missing_main_commit_fails_closed(self):
        material = valid_material()
        del material["main_commit"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_missing_documents_fails_closed(self):
        material = valid_material()
        del material["documents"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_empty_documents_fails_closed(self):
        material = valid_material()
        material["documents"] = []

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_document_missing_path_fails_closed(self):
        material = valid_material()
        del material["documents"][0]["path"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_document_missing_title_fails_closed(self):
        material = valid_material()
        del material["documents"][0]["title"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_document_missing_purpose_fails_closed(self):
        material = valid_material()
        del material["documents"][0]["purpose"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_private_operator_only_false_fails_closed(self):
        material = valid_material()
        material["documents"][0]["private_operator_only"] = False

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_missing_linked_reports_fails_closed(self):
        material = valid_material()
        del material["linked_reports"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_missing_current_priorities_fails_closed(self):
        material = valid_material()
        del material["current_priorities"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_missing_mandatory_verification_fails_closed(self):
        material = valid_material()
        del material["mandatory_verification"]

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_forbidden_raw_prompt_fails_closed(self):
        material = valid_material()
        material["documents"][0]["raw_prompt"] = "blocked"

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_forbidden_raw_response_fails_closed(self):
        material = valid_material()
        material["documents"][0]["raw_response"] = "blocked"

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

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
                material["documents"][0][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_operator_command_center_manifest(material)

    def test_invalid_digest_field_fails_closed(self):
        material = valid_material()
        material["documents"] = deepcopy(material["documents"])
        material["documents"][0]["declared_hash"] = "not-a-digest"

        with self.assertRaises(ValueError):
            build_operator_command_center_manifest(material)

    def test_operator_readme_exists(self):
        self.assertTrue(Path("docs/operator/README.md").is_file())

    def test_command_center_doc_exists(self):
        self.assertTrue(Path("docs/operator/operator_command_center.md").is_file())

    def test_current_state_doc_exists(self):
        self.assertTrue(Path("docs/operator/current_state.md").is_file())

    def test_operating_rules_doc_exists(self):
        self.assertTrue(Path("docs/operator/operating_rules.md").is_file())

    def test_blocked_capabilities_doc_exists(self):
        self.assertTrue(Path("docs/operator/blocked_capabilities.md").is_file())

    def test_blocked_doc_says_blocked_means_blocked(self):
        text = Path("docs/operator/blocked_capabilities.md").read_text(encoding="utf-8").lower()

        self.assertIn("blocked means blocked", text)

    def test_blocked_doc_says_trading_automation_is_blocked(self):
        text = Path("docs/operator/blocked_capabilities.md").read_text(encoding="utf-8").lower()

        self.assertIn("trading automation is blocked", text)

    def test_command_center_doc_says_output_assets_have_priority(self):
        text = Path("docs/operator/operator_command_center.md").read_text(encoding="utf-8").lower()

        self.assertIn("output assets have priority over kernel expansion", text)

    def test_source_safety_no_forbidden_runtime_surfaces(self):
        source = Path("kernel/runtime/operator_command_center_manifest.py").read_text(encoding="utf-8")

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
