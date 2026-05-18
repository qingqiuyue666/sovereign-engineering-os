"""Tracer-bullet tests for code audit operational loop manifests."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.code_audit_operational_loop import (
    CODE_AUDIT_REQUIRED_LOOP_STEPS,
    CodeAuditOperationalLoop,
    build_code_audit_operational_loop,
    render_code_audit_operational_loop_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "loop_id": "code-audit-operational-loop-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "loop_steps": list(CODE_AUDIT_REQUIRED_LOOP_STEPS),
        "required_reports": [
            "AI worker handoff packet",
            "AI worker result review packet",
            "branch audit report",
            "merge readiness report",
            "post-merge retrospective report",
            "code audit daily report",
        ],
        "required_verification": ["caller-provided test summaries", "human review"],
        "human_review_points": ["before merge", "before rollback"],
        "blocked_actions": ["provider execution", "production autonomy"],
        "success_criteria": ["all required reports exist", "human approval recorded"],
        "stop_conditions": ["missing evidence", "blocked capability violation"],
        "policy_version": "code-audit-operational-loop-v1",
        "code_version": "0.1.0",
    }


class CodeAuditOperationalLoopTests(unittest.TestCase):
    def test_valid_loop_manifest_builds_deterministic_object(self):
        loop = build_code_audit_operational_loop(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(loop, CodeAuditOperationalLoop)
        self.assertTrue(loop.content_hash.startswith("sha256:"))
        self.assertEqual(loop.content_hash, digest_payload(loop.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_code_audit_operational_loop(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_code_audit_operational_loop(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_code_audit_operational_loop_markdown(
            build_code_audit_operational_loop(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_code_audit_operational_loop_markdown(
            build_code_audit_operational_loop(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_loop_steps_fails_closed(self):
        material = valid_material()
        del material["loop_steps"]

        with self.assertRaises(ValueError):
            build_code_audit_operational_loop(material)

    def test_missing_human_review_points_fails_closed(self):
        material = valid_material()
        del material["human_review_points"]

        with self.assertRaises(ValueError):
            build_code_audit_operational_loop(material)

    def test_missing_blocked_actions_fails_closed(self):
        material = valid_material()
        del material["blocked_actions"]

        with self.assertRaises(ValueError):
            build_code_audit_operational_loop(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "env", "secret", "token", "api_key", "password"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_code_audit_operational_loop(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/code_audit_operational_loop.md").is_file())

    def test_doc_includes_all_10_required_loop_steps(self):
        text = Path("docs/operator/code_audit_operational_loop.md").read_text(encoding="utf-8")

        for step in CODE_AUDIT_REQUIRED_LOOP_STEPS:
            self.assertIn(step, text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/code_audit_operational_loop.py").read_text(encoding="utf-8")

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
