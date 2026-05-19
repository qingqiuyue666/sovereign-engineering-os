"""Tracer-bullet tests for operator daily loop closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_daily_loop_closure import (
    OperatorDailyLoopClosure,
    build_operator_daily_loop_closure,
    render_operator_daily_loop_closure_markdown,
)


def valid_material() -> dict[str, object]:
    gates = {
        "daily_report_contract_exists": True,
        "generated_daily_report_exists": True,
        "usage_doc_exists": True,
        "next_action_queue_exists": True,
        "stop_conditions_defined": True,
        "verification_required": True,
        "blocked_capabilities_preserved": True,
        "houdini_vfx_excluded_from_this_slice": True,
    }
    return {
        "closure_id": "operator-daily-loop-closure-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "daily_report_path": "docs/operator/generated/operator_daily_loop_report.md",
        "usage_doc_path": "docs/operator/operator_daily_loop_usage.md",
        "closure_gates": gates,
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini/VFX execution excluded from this slice",
        ],
        "next_action_queue": ["run tests"],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert loop closure"],
        "policy_version": "operator-daily-loop-closure-v1",
        "code_version": "0.1.0",
    }


class OperatorDailyLoopClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_operator_daily_loop_closure(valid_material())

        self.assertIsInstance(closure, OperatorDailyLoopClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operator_daily_loop_closure(valid_material(), observed_at="one").content_hash,
            build_operator_daily_loop_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_operator_daily_loop_closure(valid_material())

        self.assertEqual(
            render_operator_daily_loop_closure_markdown(closure),
            render_operator_daily_loop_closure_markdown(closure),
        )

    def test_closure_complete_blocked_if_generated_report_missing(self):
        material = valid_material()
        material["closure_gates"]["generated_daily_report_exists"] = False

        with self.assertRaises(ValueError):
            build_operator_daily_loop_closure(material)

    def test_generated_usage_doc_exists(self):
        self.assertTrue(Path("docs/operator/operator_daily_loop_usage.md").is_file())

    def test_report_says_houdini_vfx_excluded(self):
        text = Path("docs/operator/generated/operator_daily_loop_report.md").read_text(encoding="utf-8").lower()

        self.assertIn("houdini/vfx execution excluded from this slice", text)

    def test_blocked_capabilities_preserved(self):
        text = Path("docs/operator/generated/operator_daily_loop_closure.md").read_text(encoding="utf-8").lower()

        self.assertIn("provider execution blocked", text)
        self.assertIn("trading automation blocked", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operator_daily_loop_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
