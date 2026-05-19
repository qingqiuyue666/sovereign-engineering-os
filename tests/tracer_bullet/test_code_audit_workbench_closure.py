"""Tracer-bullet tests for Code Audit Workbench closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.code_audit_workbench_closure import (
    CodeAuditWorkbenchClosure,
    build_code_audit_workbench_closure,
    render_code_audit_workbench_closure_markdown,
)


RUN_DIR = Path("docs/operator/generated/code_audit_real_run_001")


def valid_material() -> dict[str, object]:
    gates = {
        "branch_audit_report_contract_exists": True,
        "merge_readiness_report_contract_exists": True,
        "ai_worker_result_review_packet_exists": True,
        "post_merge_retrospective_exists": True,
        "daily_report_workflow_exists": True,
        "operational_loop_exists": True,
        "sample_pack_exists": True,
        "real_run_001_generated": True,
        "next_action_queue_generated": True,
        "blocked_capabilities_preserved": True,
        "no_fake_verification_claims": True,
    }
    return {
        "closure_id": "code-audit-workbench-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "branch": "codex-nonhoudini-system-completion-v1",
        "closure_gates": gates,
        "verification_matrix": {"policy": "exact final command results only"},
        "real_run_artifacts": [
            "mainline branch audit",
            "mainline merge readiness",
            "ai worker result review summary",
            "post merge retrospective",
            "daily report",
            "next action queue",
        ],
        "blocked_capabilities": ["provider execution blocked", "Houdini/VFX execution excluded"],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert run packet"],
        "policy_version": "code-audit-workbench-closure-v1",
        "code_version": "0.1.0",
    }


class CodeAuditWorkbenchClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_code_audit_workbench_closure(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(closure, CodeAuditWorkbenchClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_code_audit_workbench_closure(valid_material(), observed_at="one").content_hash,
            build_code_audit_workbench_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_code_audit_workbench_closure(valid_material())

        self.assertEqual(
            render_code_audit_workbench_closure_markdown(closure),
            render_code_audit_workbench_closure_markdown(closure),
        )

    def test_incomplete_real_run_blocks_complete(self):
        material = valid_material()
        material["real_run_artifacts"] = ["mainline branch audit"]

        with self.assertRaises(ValueError):
            build_code_audit_workbench_closure(material)

    def test_fake_verification_claim_blocks_complete(self):
        material = valid_material()
        material["verification_matrix"]["claim"] = "fake green"

        with self.assertRaises(ValueError):
            build_code_audit_workbench_closure(material)

    def test_generated_real_run_directory_exists(self):
        self.assertTrue(RUN_DIR.is_dir())

    def test_all_real_run_reports_exist(self):
        for name in (
            "README.md",
            "mainline_branch_audit.md",
            "mainline_merge_readiness.md",
            "ai_worker_result_review_summary.md",
            "post_merge_retrospective.md",
            "daily_report.md",
            "next_action_queue.md",
        ):
            self.assertTrue((RUN_DIR / name).is_file(), name)

    def test_readme_says_real_run_not_sample(self):
        text = (RUN_DIR / "README.md").read_text(encoding="utf-8").lower()

        self.assertIn("real code audit workbench run artifact", text)
        self.assertIn("not a sample", text)

    def test_reports_do_not_claim_provider_or_houdini_vfx_execution(self):
        for path in RUN_DIR.glob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("provider execution completed", text)
            self.assertNotIn("houdini/vfx execution completed", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/code_audit_workbench_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
