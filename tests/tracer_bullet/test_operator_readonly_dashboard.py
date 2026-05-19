"""Tracer-bullet tests for read-only operator dashboard."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_readonly_dashboard import (
    OperatorReadonlyDashboard,
    build_operator_readonly_dashboard,
    render_operator_readonly_dashboard_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "dashboard_id": "operator-readonly-dashboard-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "branch": "codex-nonhoudini-system-completion-v1",
        "working_tree_status": "reported by final command output",
        "latest_reports": ["docs/operator/generated/engineering_foundation_closure.md"],
        "registries": {"code_report_registry": "docs/operator/registries/code_report_registry.md"},
        "active_workbenches": ["Code Audit Workbench"],
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini/VFX execution excluded from this slice",
        ],
        "verification_commands": ["make ci"],
        "next_actions": ["run exact commands"],
        "stop_conditions": ["failed command"],
        "policy_version": "operator-readonly-dashboard-v1",
        "code_version": "0.1.0",
    }


class OperatorReadonlyDashboardTests(unittest.TestCase):
    def test_valid_dashboard_builds_deterministic_object(self):
        dashboard = build_operator_readonly_dashboard(valid_material())

        self.assertIsInstance(dashboard, OperatorReadonlyDashboard)
        self.assertEqual(dashboard.content_hash, digest_payload(dashboard.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_operator_readonly_dashboard(valid_material(), observed_at="one").content_hash,
            build_operator_readonly_dashboard(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        dashboard = build_operator_readonly_dashboard(valid_material())

        self.assertEqual(
            render_operator_readonly_dashboard_markdown(dashboard),
            render_operator_readonly_dashboard_markdown(dashboard),
        )

    def test_missing_latest_reports_fails_closed(self):
        material = valid_material()
        del material["latest_reports"]

        with self.assertRaises(ValueError):
            build_operator_readonly_dashboard(material)

    def test_missing_registries_fails_closed(self):
        material = valid_material()
        del material["registries"]

        with self.assertRaises(ValueError):
            build_operator_readonly_dashboard(material)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/operator_readonly_dashboard.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
