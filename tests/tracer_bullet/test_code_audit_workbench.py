"""Tracer-bullet tests for the deterministic code audit workbench."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.code_audit_workbench import (
    CodeAuditReport,
    build_code_audit_report,
    render_code_audit_markdown,
)

VALID_DIGEST = "sha256:" + "a" * 64


def valid_material() -> dict[str, object]:
    return {
        "report_id": "audit-report-001",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "3d219bc9efa961d315db48afbaec9f3d8c6bf458",
        "branch_state": {
            "branch": "main",
            "main_commit": "3d219bc9efa961d315db48afbaec9f3d8c6bf458",
            "tree_state": "clean",
        },
        "merged_slices": [
            "durable operator decision store",
            "durable operator review store",
        ],
        "test_matrix": {
            "tracer_bullet": "5521 tests, 4 skipped, OK",
            "schemas": "70 tests, OK",
            "acceptance": "156 tests, OK",
            "make_ci": "passed",
        },
        "root_integrity_state": {
            "status": "verified",
            "verification_digest": VALID_DIGEST,
        },
        "durable_decision_store_state": {
            "status": "available",
        },
        "durable_review_store_state": {
            "status": "available",
        },
        "recovery_state": {
            "status": "available",
        },
        "audit_export_state": {
            "status": "available",
        },
        "status_surface_state": {
            "status": "read-only",
        },
        "work_queue_state": {
            "status": "available",
        },
        "runbook_shell_state": {
            "status": "symbolic-only",
        },
        "provider_preflight_state": {
            "status": "available",
            "real_provider_execution": "blocked",
        },
        "readiness_matrix_state": {
            "status": "available",
            "production_autonomy": "blocked",
        },
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
        ],
        "risk_matrix": [
            {
                "risk_id": "R1",
                "risk": "caller-provided inputs can be stale",
                "status": "controlled",
            }
        ],
        "next_actions": [
            "review generated Markdown report",
        ],
        "rollback_plan": [
            "revert code audit workbench files",
        ],
        "public_safe_summary": "Public-safe local-only audit report.",
        "policy_version": "code-audit-workbench-v1",
        "code_version": "0.1.0",
    }


class CodeAuditWorkbenchTests(unittest.TestCase):
    def test_valid_report_material_builds_deterministic_report_object(self):
        report = build_code_audit_report(valid_material(), observed_at="2026-01-01T00:00:00Z")

        self.assertIsInstance(report, CodeAuditReport)
        self.assertTrue(report.content_hash.startswith("sha256:"))
        self.assertEqual(report.content_hash, digest_payload(report.deterministic_material()))

    def test_markdown_rendering_includes_all_required_sections(self):
        report = build_code_audit_report(valid_material(), observed_at="2026-01-01T00:00:00Z")
        markdown = render_code_audit_markdown(report)

        for section in (
            "Executive Summary",
            "Repository State",
            "Recently Integrated Capabilities",
            "Verification Matrix",
            "Root Integrity / Governance Status",
            "Durable Store Status",
            "Operator Review / Decision Chain Status",
            "Recovery / Audit Export Status",
            "Blocked Capabilities",
            "Risk Matrix",
            "Next Actions",
            "Rollback Plan",
            "Public-Safe Summary",
        ):
            self.assertIn(f"## {section}", markdown)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_code_audit_report(material, observed_at="2026-01-01T00:00:00Z")
        second = build_code_audit_report(material, observed_at="2027-01-01T00:00:00Z")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_identical_material_renders_identical_markdown(self):
        material = valid_material()

        first = render_code_audit_markdown(
            build_code_audit_report(material, observed_at="2026-01-01T00:00:00Z")
        )
        second = render_code_audit_markdown(
            build_code_audit_report(material, observed_at="2026-01-01T00:00:00Z")
        )

        self.assertEqual(first, second)

    def test_missing_repository_url_fails_closed(self):
        material = valid_material()
        del material["repository_url"]

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_missing_main_commit_fails_closed(self):
        material = valid_material()
        del material["main_commit"]

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_missing_test_matrix_fails_closed(self):
        material = valid_material()
        del material["test_matrix"]

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_missing_rollback_plan_fails_closed(self):
        material = valid_material()
        del material["rollback_plan"]

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_raw_prompt_field_fails_closed(self):
        material = valid_material()
        material["branch_state"]["raw_prompt"] = "blocked"

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_raw_response_field_fails_closed(self):
        material = valid_material()
        material["risk_matrix"].append({"raw_response": "blocked"})

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_raw_exception_field_fails_closed(self):
        material = valid_material()
        material["recovery_state"]["raw_exception"] = "blocked"

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_raw_traceback_field_fails_closed(self):
        material = valid_material()
        material["audit_export_state"]["raw_traceback"] = "blocked"

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_sensitive_field_names_fail_closed(self):
        for field_name in ("env", "secret", "token", "api_key", "password", "private_key", "authorization"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material["branch_state"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_code_audit_report(material)

    def test_non_list_merged_slices_fails_closed(self):
        material = valid_material()
        material["merged_slices"] = "durable operator decision store"

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_non_list_risk_matrix_fails_closed(self):
        material = valid_material()
        material["risk_matrix"] = {"risk_id": "R1"}

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_non_dict_branch_state_fails_closed(self):
        material = valid_material()
        material["branch_state"] = "main"

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_invalid_digest_field_fails_closed(self):
        material = valid_material()
        material["root_integrity_state"] = deepcopy(material["root_integrity_state"])
        material["root_integrity_state"]["verification_digest"] = "not-a-digest"

        with self.assertRaises(ValueError):
            build_code_audit_report(material)

    def test_generated_public_safe_report_sample_exists(self):
        report_path = Path("docs/reports/sovereign_engineering_os_mainline_audit_report.md")

        self.assertTrue(report_path.is_file())

    def test_generated_report_sample_contains_blocked_real_provider_execution(self):
        report_path = Path("docs/reports/sovereign_engineering_os_mainline_audit_report.md")
        text = report_path.read_text(encoding="utf-8").lower()

        self.assertIn("real provider execution remains blocked", text)

    def test_generated_report_sample_contains_blocked_production_autonomy(self):
        report_path = Path("docs/reports/sovereign_engineering_os_mainline_audit_report.md")
        text = report_path.read_text(encoding="utf-8").lower()

        self.assertIn("production autonomy remains blocked", text)

    def test_generated_report_sample_is_public_safe(self):
        report_path = Path("docs/reports/sovereign_engineering_os_mainline_audit_report.md")
        text = report_path.read_text(encoding="utf-8").lower()

        for marker in (
            "raw_prompt",
            "raw_response",
            "raw_exception",
            "raw_traceback",
            "api_key",
            "password",
            "private_key",
            "authorization",
        ):
            self.assertNotIn(marker, text)

    def test_source_safety_checks_pass(self):
        source = "\n".join(
            Path(path).read_text(encoding="utf-8")
            for path in (
                "kernel/runtime/code_audit_workbench.py",
                "tools/generate_mainline_audit_report.py",
            )
        )
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
