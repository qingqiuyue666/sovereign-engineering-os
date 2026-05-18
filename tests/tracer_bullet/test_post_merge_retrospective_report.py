"""Tracer-bullet tests for post-merge retrospective reports."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.post_merge_retrospective_report import (
    PostMergeRetrospectiveReport,
    build_post_merge_retrospective_report,
    render_post_merge_retrospective_report_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "report_id": "post-merge-retrospective-v1-sample",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "merge_commit": "4d25ab23f371a9539855d8271e5743f3e83afa99",
        "merged_branch": "codex-production-workbench-activation-v1",
        "merged_capabilities": ["branch audit report"],
        "files_added": ["kernel/runtime/post_merge_retrospective_report.py"],
        "files_modified": [],
        "files_deleted": [],
        "tests_after_merge": ["caller reported tracer tests pass"],
        "risks_retained": [],
        "blocked_capabilities_preserved": ["provider execution remains blocked"],
        "lessons_learned": ["keep retrospective material summarized"],
        "next_actions": ["update daily report"],
        "rollback_route": ["revert merge commit after human approval"],
        "policy_version": "post-merge-retrospective-report-v1",
        "code_version": "0.1.0",
    }


class PostMergeRetrospectiveReportTests(unittest.TestCase):
    def test_valid_retrospective_builds_deterministic_object(self):
        report = build_post_merge_retrospective_report(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(report, PostMergeRetrospectiveReport)
        self.assertTrue(report.content_hash.startswith("sha256:"))
        self.assertEqual(report.content_hash, digest_payload(report.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_post_merge_retrospective_report(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_post_merge_retrospective_report(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_post_merge_retrospective_report_markdown(
            build_post_merge_retrospective_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_post_merge_retrospective_report_markdown(
            build_post_merge_retrospective_report(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_merge_commit_fails_closed(self):
        material = valid_material()
        del material["merge_commit"]

        with self.assertRaises(ValueError):
            build_post_merge_retrospective_report(material)

    def test_missing_tests_after_merge_fails_closed(self):
        material = valid_material()
        del material["tests_after_merge"]

        with self.assertRaises(ValueError):
            build_post_merge_retrospective_report(material)

    def test_missing_blocked_capabilities_preserved_fails_closed(self):
        material = valid_material()
        del material["blocked_capabilities_preserved"]

        with self.assertRaises(ValueError):
            build_post_merge_retrospective_report(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "env", "secret", "token", "api_key", "password"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_post_merge_retrospective_report(material)

    def test_generated_workflow_doc_exists(self):
        self.assertTrue(Path("docs/operator/post_merge_retrospective_workflow.md").is_file())

    def test_workflow_doc_says_blocked_capabilities_must_remain_preserved(self):
        text = Path("docs/operator/post_merge_retrospective_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("blocked capabilities must remain preserved", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/post_merge_retrospective_report.py").read_text(encoding="utf-8")

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
