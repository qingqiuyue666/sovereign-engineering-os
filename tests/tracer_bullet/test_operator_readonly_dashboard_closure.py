"""Tracer-bullet tests for read-only operator dashboard closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_readonly_dashboard_closure import (
    OperatorReadonlyDashboardClosure,
    build_operator_readonly_dashboard_closure,
    render_operator_readonly_dashboard_closure_markdown,
)


def valid_material() -> dict[str, object]:
    gates = {
        "dashboard_contract_exists": True,
        "generated_dashboard_exists": True,
        "usage_doc_exists": True,
        "latest_reports_listed": True,
        "registries_listed": True,
        "blocked_capabilities_listed": True,
        "verification_commands_listed": True,
        "no_execution_runner_behavior": True,
        "no_server_behavior": True,
        "no_gui_behavior": True,
        "no_houdini_vfx_execution_in_this_slice": True,
    }
    return {
        "closure_id": "operator-readonly-dashboard-closure-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "dashboard_path": "docs/operator/generated/operator_readonly_dashboard.md",
        "usage_doc_path": "docs/operator/operator_readonly_dashboard_usage.md",
        "closure_gates": gates,
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini/VFX execution excluded from this slice",
        ],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert dashboard docs"],
        "policy_version": "operator-readonly-dashboard-closure-v1",
        "code_version": "0.1.0",
    }


class OperatorReadonlyDashboardClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_operator_readonly_dashboard_closure(valid_material())

        self.assertIsInstance(closure, OperatorReadonlyDashboardClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operator_readonly_dashboard_closure(valid_material(), observed_at="one").content_hash,
            build_operator_readonly_dashboard_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_operator_readonly_dashboard_closure(valid_material())

        self.assertEqual(
            render_operator_readonly_dashboard_closure_markdown(closure),
            render_operator_readonly_dashboard_closure_markdown(closure),
        )

    def test_closure_complete_blocked_if_usage_doc_missing(self):
        material = valid_material()
        material["closure_gates"]["usage_doc_exists"] = False

        with self.assertRaises(ValueError):
            build_operator_readonly_dashboard_closure(material)

    def test_generated_dashboard_exists(self):
        self.assertTrue(Path("docs/operator/generated/operator_readonly_dashboard.md").is_file())

    def test_usage_doc_says_readonly_not_server_not_runner(self):
        text = Path("docs/operator/operator_readonly_dashboard_usage.md").read_text(encoding="utf-8").lower()

        self.assertIn("read-only", text)
        self.assertIn("not a server", text)
        self.assertIn("not an execution runner", text)

    def test_report_says_no_houdini_vfx_execution(self):
        text = Path("docs/operator/generated/operator_readonly_dashboard.md").read_text(encoding="utf-8").lower()

        self.assertIn("houdini/vfx execution excluded from this slice", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operator_readonly_dashboard_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
