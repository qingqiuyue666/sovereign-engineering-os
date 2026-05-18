"""Tracer-bullet tests for the private code audit daily report workflow."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.code_audit_daily_report import (
    CodeAuditDailyReport,
    build_code_audit_daily_report,
    render_code_audit_daily_report_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "daily_report_id": "code-audit-daily-report-2026-05-19",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "branch_state": {
            "branch": "codex-private-production-command-center-v1",
            "source": "caller-provided",
        },
        "verification_matrix": {
            "operator_command_center_manifest": "pending",
            "make_ci": "pending",
        },
        "changed_capabilities": [
            "private operator command center",
            "private state report",
        ],
        "risk_matrix": [
            {"risk_id": "R1", "status": "watch", "summary": "verification material can be stale"},
        ],
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
        ],
        "recommended_next_actions": [
            "run required verification commands outside the report builder",
        ],
        "rollback_notes": [
            "revert daily report workflow files as a unit",
        ],
        "policy_version": "code-audit-daily-report-v1",
        "code_version": "0.1.0",
    }


class CodeAuditDailyReportTests(unittest.TestCase):
    def test_valid_daily_report_builds_deterministic_object(self):
        report = build_code_audit_daily_report(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(report, CodeAuditDailyReport)
        self.assertTrue(report.content_hash.startswith("sha256:"))
        self.assertEqual(report.content_hash, digest_payload(report.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_code_audit_daily_report_markdown(
            build_code_audit_daily_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_code_audit_daily_report_markdown(
            build_code_audit_daily_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_code_audit_daily_report(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_code_audit_daily_report(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_missing_daily_report_id_fails_closed(self):
        material = valid_material()
        del material["daily_report_id"]

        with self.assertRaises(ValueError):
            build_code_audit_daily_report(material)

    def test_missing_verification_matrix_fails_closed(self):
        material = valid_material()
        del material["verification_matrix"]

        with self.assertRaises(ValueError):
            build_code_audit_daily_report(material)

    def test_missing_blocked_capabilities_fails_closed(self):
        material = valid_material()
        del material["blocked_capabilities"]

        with self.assertRaises(ValueError):
            build_code_audit_daily_report(material)

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
                material["verification_matrix"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_code_audit_daily_report(material)

    def test_generated_workflow_doc_exists(self):
        self.assertTrue(Path("docs/operator/code_audit_daily_report_workflow.md").is_file())

    def test_workflow_doc_says_it_does_not_run_tests_internally(self):
        text = Path("docs/operator/code_audit_daily_report_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("does not run tests internally", text)

    def test_workflow_doc_says_caller_provided_material_only(self):
        text = Path("docs/operator/code_audit_daily_report_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("caller-provided material only", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/code_audit_daily_report.py").read_text(encoding="utf-8")

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
