"""Tracer-bullet tests for merge readiness reports."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.merge_readiness_report import (
    MergeReadinessReport,
    build_merge_readiness_report,
    render_merge_readiness_report_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "report_id": "merge-readiness-report-v1-sample",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "source_branch": "codex-production-workbench-activation-v1",
        "target_branch": "main",
        "source_commit": "3d25ab23f371a9539855d8271e5743f3e83afa99",
        "target_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "changed_files": ["kernel/runtime/merge_readiness_report.py"],
        "protected_files_status": {
            "Makefile": {"status": "unchanged", "safe": True},
            "root_README": {"status": "unchanged", "safe": True},
            "root_integrity_manifests": {"status": "unchanged", "safe": True},
            "health_gate_wiring": {"status": "unchanged", "safe": True},
            "governance_files": {"status": "unchanged", "safe": True},
            "schema_files": {"status": "unchanged", "safe": True},
        },
        "test_matrix": {"merge_readiness_report": "caller reported pass"},
        "clean_tree_status": {"status": "caller reported clean"},
        "diff_check_status": {"status": "caller reported checked"},
        "root_integrity_status": {"status": "caller reported preserved"},
        "blocked_capability_status": {"violations": []},
        "merge_decision": "approved_for_merge",
        "merge_blockers": [],
        "rollback_plan": ["revert merge readiness report files as a unit"],
        "policy_version": "merge-readiness-report-v1",
        "code_version": "0.1.0",
    }


class MergeReadinessReportTests(unittest.TestCase):
    def test_valid_merge_readiness_report_builds_deterministic_object(self):
        report = build_merge_readiness_report(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(report, MergeReadinessReport)
        self.assertTrue(report.content_hash.startswith("sha256:"))
        self.assertEqual(report.content_hash, digest_payload(report.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_merge_readiness_report(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_merge_readiness_report(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_merge_readiness_report_markdown(
            build_merge_readiness_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_merge_readiness_report_markdown(
            build_merge_readiness_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_unsafe_protected_file_mutation_blocks_approved_merge(self):
        material = valid_material()
        material["protected_files_status"]["Makefile"] = {"status": "unsafe", "safe": False}

        with self.assertRaises(ValueError):
            build_merge_readiness_report(material)

    def test_blocked_capability_violation_blocks_approved_merge(self):
        material = valid_material()
        material["blocked_capability_status"]["violations"] = ["provider execution introduced"]

        with self.assertRaises(ValueError):
            build_merge_readiness_report(material)

    def test_missing_test_matrix_fails_closed(self):
        material = valid_material()
        del material["test_matrix"]

        with self.assertRaises(ValueError):
            build_merge_readiness_report(material)

    def test_invalid_merge_decision_fails_closed(self):
        material = valid_material()
        material["merge_decision"] = "merge_now"

        with self.assertRaises(ValueError):
            build_merge_readiness_report(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "env", "secret", "token", "api_key", "password"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material["test_matrix"][field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_merge_readiness_report(material)

    def test_generated_workflow_doc_exists(self):
        self.assertTrue(Path("docs/operator/merge_readiness_report_workflow.md").is_file())

    def test_workflow_doc_says_this_is_not_a_merge_executor(self):
        text = Path("docs/operator/merge_readiness_report_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("not a merge executor", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/merge_readiness_report.py").read_text(encoding="utf-8")

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
