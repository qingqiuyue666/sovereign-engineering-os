"""Tracer-bullet tests for operator asset registries."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_asset_registry import (
    OperatorAssetRegistry,
    build_operator_asset_registry,
    render_operator_asset_registry_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "registry_id": "code-report-registry-test",
        "registry_type": "code_report_registry",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "entries": [
            {
                "entry_id": "entry-001",
                "path": "docs/operator/generated/code_audit_workbench_closure.md",
                "title": "code report registry entry",
                "status": "active",
            }
        ],
        "blocked_capabilities": [
            "provider execution blocked",
            "trading automation blocked",
            "Houdini/VFX execution assets excluded from this slice",
        ],
        "update_policy": "deterministic Markdown review",
        "rollback_notes": ["revert registry doc"],
        "policy_version": "operator-asset-registry-v1",
        "code_version": "0.1.0",
    }


class OperatorAssetRegistryTests(unittest.TestCase):
    def test_valid_registry_builds_deterministic_object(self):
        registry = build_operator_asset_registry(valid_material())

        self.assertIsInstance(registry, OperatorAssetRegistry)
        self.assertEqual(registry.content_hash, digest_payload(registry.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operator_asset_registry(valid_material(), observed_at="one").content_hash,
            build_operator_asset_registry(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        registry = build_operator_asset_registry(valid_material())

        self.assertEqual(render_operator_asset_registry_markdown(registry), render_operator_asset_registry_markdown(registry))

    def test_invalid_registry_type_fails_closed(self):
        material = valid_material()
        material["registry_type"] = "unknown"

        with self.assertRaises(ValueError):
            build_operator_asset_registry(material)

    def test_empty_entries_fail_closed(self):
        material = valid_material()
        material["entries"] = []

        with self.assertRaises(ValueError):
            build_operator_asset_registry(material)

    def test_entry_missing_path_fails_closed(self):
        material = valid_material()
        del material["entries"][0]["path"]

        with self.assertRaises(ValueError):
            build_operator_asset_registry(material)

    def test_registries_exclude_houdini_vfx_execution_assets(self):
        material = valid_material()
        material["entries"][0]["title"] = "Houdini execution asset"

        with self.assertRaises(ValueError):
            build_operator_asset_registry(material)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operator_asset_registry.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
