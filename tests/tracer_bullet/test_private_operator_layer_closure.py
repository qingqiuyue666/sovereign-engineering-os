"""Tracer-bullet tests for private operator layer closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.private_operator_layer_closure import (
    PrivateOperatorLayerClosure,
    build_private_operator_layer_closure,
    render_private_operator_layer_closure_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "closure_id": "private-operator-layer-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "operator_docs": [
            "operator command center",
            "current state",
            "operating rules",
            "blocked capabilities",
            "report gallery",
            "knowledge base index",
            "workspace hygiene",
            "current operator control pack",
        ],
        "operator_rules": ["private operator only"],
        "handoff_packets": ["ai worker handoff"],
        "review_forms": ["branch review form"],
        "task_intake_templates": ["code audit task intake"],
        "knowledge_indexes": ["knowledge base index"],
        "sprint_artifacts": ["sprint artifacts"],
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini execution excluded",
        ],
        "daily_usage_path": "docs/operator/operator_daily_loop_usage.md",
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert control pack"],
        "policy_version": "private-operator-layer-closure-v1",
        "code_version": "0.1.0",
    }


class PrivateOperatorLayerClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_private_operator_layer_closure(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(closure, PrivateOperatorLayerClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_private_operator_layer_closure(valid_material(), observed_at="one").content_hash,
            build_private_operator_layer_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_private_operator_layer_closure(valid_material())

        self.assertEqual(
            render_private_operator_layer_closure_markdown(closure),
            render_private_operator_layer_closure_markdown(closure),
        )

    def test_missing_closure_id_fails_closed(self):
        material = valid_material()
        del material["closure_id"]

        with self.assertRaises(ValueError):
            build_private_operator_layer_closure(material)

    def test_missing_operator_docs_fails_closed(self):
        material = valid_material()
        del material["operator_docs"]

        with self.assertRaises(ValueError):
            build_private_operator_layer_closure(material)

    def test_missing_blocked_capabilities_fails_closed(self):
        material = valid_material()
        del material["blocked_capabilities"]

        with self.assertRaises(ValueError):
            build_private_operator_layer_closure(material)

    def test_missing_daily_usage_path_fails_closed(self):
        material = valid_material()
        del material["daily_usage_path"]

        with self.assertRaises(ValueError):
            build_private_operator_layer_closure(material)

    def test_generated_docs_exist(self):
        self.assertTrue(Path("docs/operator/generated/private_operator_layer_closure.md").is_file())
        self.assertTrue(Path("docs/operator/generated/current_operator_control_pack.md").is_file())

    def test_generated_docs_preserve_blocked_capability_language(self):
        text = Path("docs/operator/generated/current_operator_control_pack.md").read_text(encoding="utf-8").lower()

        self.assertIn("provider execution remains blocked", text)
        self.assertIn("production autonomy remains blocked", text)
        self.assertIn("trading automation remains blocked", text)
        self.assertIn("houdini/vfx execution is excluded", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/private_operator_layer_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
