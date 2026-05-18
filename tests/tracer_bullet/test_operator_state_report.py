"""Tracer-bullet tests for the private operator state report."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_state_report import (
    OperatorStateReport,
    build_operator_state_report,
    render_operator_state_report_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "report_id": "private-operator-state-report-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "branch_state": {
            "source_branch": "main",
            "implementation_branch": "codex-private-production-command-center-v1",
            "tree_state": "caller-provided",
        },
        "completed_capabilities": [
            "durable operator decision store",
            "durable operator review store",
            "operator recovery",
        ],
        "active_assets": [
            "docs/operator/operator_command_center.md",
            "docs/reports/sovereign_engineering_os_mainline_audit_report.md",
        ],
        "frozen_kernel_rules": [
            "kernel expansion is frozen unless needed for output assets",
            "root README edits are frozen",
        ],
        "allowed_next_work": [
            "operator command center",
            "code audit daily report",
            "creative asset factory",
            "macro signal research boundary",
        ],
        "forbidden_work": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "financial execution and trading automation remain blocked",
        ],
        "test_matrix": {
            "priority_tests": "required",
            "make_ci": "required",
        },
        "risk_register": [
            {"risk_id": "R1", "status": "controlled", "summary": "private docs can drift"},
        ],
        "next_actions": [
            "add daily code audit report workflow",
        ],
        "rollback_plan": [
            "revert private state report files as a unit",
        ],
        "policy_version": "operator-state-report-v1",
        "code_version": "0.1.0",
    }


class OperatorStateReportTests(unittest.TestCase):
    def test_valid_report_builds_deterministic_object(self):
        report = build_operator_state_report(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(report, OperatorStateReport)
        self.assertTrue(report.content_hash.startswith("sha256:"))
        self.assertEqual(report.content_hash, digest_payload(report.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_operator_state_report_markdown(
            build_operator_state_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_operator_state_report_markdown(
            build_operator_state_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_operator_state_report(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_operator_state_report(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_missing_report_id_fails_closed(self):
        material = valid_material()
        del material["report_id"]

        with self.assertRaises(ValueError):
            build_operator_state_report(material)

    def test_missing_main_commit_fails_closed(self):
        material = valid_material()
        del material["main_commit"]

        with self.assertRaises(ValueError):
            build_operator_state_report(material)

    def test_missing_test_matrix_fails_closed(self):
        material = valid_material()
        del material["test_matrix"]

        with self.assertRaises(ValueError):
            build_operator_state_report(material)

    def test_forbidden_raw_and_sensitive_fields_fail_closed(self):
        for field_name in (
            "raw_prompt",
            "raw_response",
            "raw_exception",
            "raw_traceback",
            "env",
            "secret",
            "token",
            "api_key",
            "password",
            "private_key",
            "authorization",
        ):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material["branch_state"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_operator_state_report(material)

    def test_generated_private_state_report_exists(self):
        self.assertTrue(Path("docs/operator/private_operator_state_report.md").is_file())

    def test_report_says_kernel_expansion_is_frozen(self):
        text = Path("docs/operator/private_operator_state_report.md").read_text(encoding="utf-8").lower()

        self.assertIn("kernel expansion is frozen", text)

    def test_report_says_trading_automation_is_blocked(self):
        text = Path("docs/operator/private_operator_state_report.md").read_text(encoding="utf-8").lower()

        self.assertIn("trading automation remain blocked", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/operator_state_report.py").read_text(encoding="utf-8")

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
