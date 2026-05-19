"""Tracer-bullet tests for operator asset registry closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_asset_registry_closure import (
    OperatorAssetRegistryClosure,
    build_operator_asset_registry_closure,
    render_operator_asset_registry_closure_markdown,
)


REGISTRY_DOCS = (
    "docs/operator/registries/README.md",
    "docs/operator/registries/code_report_registry.md",
    "docs/operator/registries/ai_worker_output_registry.md",
    "docs/operator/registries/decision_log_registry.md",
    "docs/operator/registries/rollback_registry.md",
    "docs/operator/registries/evidence_registry.md",
    "docs/operator/registries/production_asset_registry.md",
)


def valid_material() -> dict[str, object]:
    gates = {
        "all_registry_docs_exist": True,
        "registry_contract_exists": True,
        "at_least_one_entry_per_registry": True,
        "blocked_capabilities_preserved": True,
        "no_houdini_execution_assets_unless_external_line_reference_only": True,
        "registry_update_policy_defined": True,
        "rollback_notes_defined": True,
    }
    status = {
        "code_report_registry": True,
        "ai_worker_output_registry": True,
        "decision_log_registry": True,
        "rollback_registry": True,
        "evidence_registry": True,
        "production_asset_registry": True,
    }
    return {
        "closure_id": "operator-asset-registry-closure-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "closure_gates": gates,
        "registry_status": status,
        "registry_docs": list(REGISTRY_DOCS),
        "blocked_capabilities": [
            "provider execution blocked",
            "trading automation blocked",
            "Houdini/VFX execution assets excluded from this slice",
        ],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert registries"],
        "policy_version": "operator-asset-registry-closure-v1",
        "code_version": "0.1.0",
    }


class OperatorAssetRegistryClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_operator_asset_registry_closure(valid_material())

        self.assertIsInstance(closure, OperatorAssetRegistryClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operator_asset_registry_closure(valid_material(), observed_at="one").content_hash,
            build_operator_asset_registry_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_operator_asset_registry_closure(valid_material())

        self.assertEqual(
            render_operator_asset_registry_closure_markdown(closure),
            render_operator_asset_registry_closure_markdown(closure),
        )

    def test_closure_complete_blocked_if_any_registry_missing(self):
        material = valid_material()
        material["registry_status"]["evidence_registry"] = False

        with self.assertRaises(ValueError):
            build_operator_asset_registry_closure(material)

    def test_generated_docs_exist(self):
        for path in REGISTRY_DOCS:
            self.assertTrue(Path(path).is_file(), path)
        self.assertTrue(Path("docs/operator/generated/operator_asset_registry_closure.md").is_file())

    def test_registries_exclude_houdini_vfx_execution_assets(self):
        text = "\n".join(Path(path).read_text(encoding="utf-8").lower() for path in REGISTRY_DOCS)

        self.assertIn("houdini/vfx execution assets are excluded", text)
        self.assertNotIn("houdini execution asset", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operator_asset_registry_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
