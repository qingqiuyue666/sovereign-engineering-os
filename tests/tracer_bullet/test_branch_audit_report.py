"""Tracer-bullet tests for branch audit reports."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.branch_audit_report import (
    BranchAuditReport,
    build_branch_audit_report,
    render_branch_audit_report_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "report_id": "branch-audit-report-v1-sample",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "base_branch": "main",
        "feature_branch": "codex-production-workbench-activation-v1",
        "base_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "head_commit": "3d25ab23f371a9539855d8271e5743f3e83afa99",
        "changed_files": ["kernel/runtime/branch_audit_report.py"],
        "added_files": ["kernel/runtime/branch_audit_report.py"],
        "modified_files": [],
        "deleted_files": [],
        "test_matrix": {"branch_audit_report": "caller reported pass"},
        "risk_matrix": [{"risk_id": "R1", "status": "review", "summary": "caller evidence may be stale"}],
        "boundary_findings": ["no provider execution introduced"],
        "forbidden_changes": [],
        "merge_blockers": [],
        "recommended_action": "merge_ready",
        "rollback_plan": ["revert branch audit report files as a unit"],
        "policy_version": "branch-audit-report-v1",
        "code_version": "0.1.0",
    }


class BranchAuditReportTests(unittest.TestCase):
    def test_valid_branch_audit_report_builds_deterministic_object(self):
        report = build_branch_audit_report(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(report, BranchAuditReport)
        self.assertTrue(report.content_hash.startswith("sha256:"))
        self.assertEqual(report.content_hash, digest_payload(report.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_branch_audit_report_markdown(
            build_branch_audit_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_branch_audit_report_markdown(
            build_branch_audit_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_branch_audit_report(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_branch_audit_report(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_invalid_recommended_action_fails_closed(self):
        material = valid_material()
        material["recommended_action"] = "ship_it"

        with self.assertRaises(ValueError):
            build_branch_audit_report(material)

    def test_missing_changed_files_fails_closed(self):
        material = valid_material()
        del material["changed_files"]

        with self.assertRaises(ValueError):
            build_branch_audit_report(material)

    def test_missing_test_matrix_fails_closed(self):
        material = valid_material()
        del material["test_matrix"]

        with self.assertRaises(ValueError):
            build_branch_audit_report(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "env", "secret", "token", "api_key", "password"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material["test_matrix"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_branch_audit_report(material)

    def test_invalid_digest_field_fails_closed(self):
        material = valid_material()
        material["risk_matrix"][0]["declared_hash"] = "not-a-valid-digest"

        with self.assertRaises(ValueError):
            build_branch_audit_report(material)

    def test_generated_workflow_doc_exists(self):
        self.assertTrue(Path("docs/operator/branch_audit_report_workflow.md").is_file())

    def test_workflow_doc_says_caller_provided_material_only(self):
        text = Path("docs/operator/branch_audit_report_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("caller-provided material only", text)

    def test_workflow_doc_says_it_does_not_run_git_or_tests_internally(self):
        text = Path("docs/operator/branch_audit_report_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("does not run git or tests internally", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/branch_audit_report.py").read_text(encoding="utf-8")

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
