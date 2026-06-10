from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.pr_factory.merge_audit import (
    AUDIT_RECOMMENDATIONS,
    REQUIRED_PR_BODY_SECTIONS,
    FixtureCIStatusReader,
    MergeAuditInput,
    build_merge_audit_artifact,
    check_changed_file_scope,
    scan_forbidden_surfaces,
    validate_pr_body_contract,
    validate_required_test_checklist,
    write_merge_audit_artifact,
)


def valid_pr_body() -> str:
    return "\n\n".join(REQUIRED_PR_BODY_SECTIONS)


def valid_material(**overrides: object) -> MergeAuditInput:
    material: dict[str, object] = {
        "milestone": "A3 PR Factory And Merge Audit V1",
        "branch": "feat/pr-factory-merge-audit-v1",
        "pr_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/999",
        "head_sha": "a" * 40,
        "base_sha": "b" * 40,
        "changed_files": (
            "tools/pr_factory/merge_audit.py",
            "tests/tools/test_pr_factory_merge_audit.py",
            "docs/operator/pr_factory_merge_audit_v1.md",
        ),
        "allowed_file_prefixes": (
            "tools/pr_factory",
            "tests/tools",
            "docs/operator",
        ),
        "file_text_by_path": {
            "tools/pr_factory/merge_audit.py": "def inert():\n    return 'metadata only'\n",
            "tests/tools/test_pr_factory_merge_audit.py": "class Test: pass\n",
        },
        "test_results": {
            "focused_tests": "pass",
            "python3 -m unittest discover tests": "pass",
            "make ci": "pass",
            "git diff --check": "pass",
        },
        "pr_body": valid_pr_body(),
        "ci_status_payload": {
            "status": "pass",
            "run_url": "https://github.com/example/actions/runs/1",
            "checks": [{"name": "canonical-health", "conclusion": "success"}],
        },
        "blockers": (),
        "dependency_notes": ("independent",),
    }
    material.update(overrides)
    return MergeAuditInput(**material)  # type: ignore[arg-type]


class PRFactoryMergeAuditTests(unittest.TestCase):
    def test_all_recommendation_values_are_declared(self) -> None:
        self.assertEqual(
            set(AUDIT_RECOMMENDATIONS),
            {"MERGE_ALLOWED", "DO_NOT_MERGE", "WAITING_FOR_CI", "BLOCKED"},
        )

    def test_changed_file_scope_accepts_allowed_prefixes_and_rejects_escape(self) -> None:
        result = check_changed_file_scope(
            ["tools/pr_factory/merge_audit.py", "../outside.py", "kernel/runtime/other.py"],
            ["tools/pr_factory"],
        )

        self.assertFalse(result.passed)
        self.assertIn("../outside.py", result.invalid_paths)
        self.assertIn("kernel/runtime/other.py", result.out_of_scope_files)

    def test_forbidden_surface_scanner_finds_disallowed_text(self) -> None:
        result = scan_forbidden_surfaces(
            {
                "tools/pr_factory/example.py": "runner(shell=True)\n",
                "docs/operator/example.md": "No issue here.\n",
            }
        )

        self.assertFalse(result.passed)
        self.assertEqual(result.violations[0]["surface"], "shell_true")

    def test_required_test_checklist_requires_all_global_commands(self) -> None:
        result = validate_required_test_checklist(
            {
                "focused_tests": "pass",
                "python3 -m unittest discover tests": "pass",
                "make ci": "fail",
            }
        )

        self.assertFalse(result.passed)
        self.assertIn("make ci", result.failed_commands)
        self.assertIn("git diff --check", result.missing_commands)

    def test_pr_body_contract_requires_all_sections(self) -> None:
        result = validate_pr_body_contract("## Scope summary\n")

        self.assertFalse(result.passed)
        self.assertIn("## Audit packet", result.missing_sections)

    def test_fixture_ci_reader_never_marks_live_api_called(self) -> None:
        status = FixtureCIStatusReader(
            {"status": "pending", "run_url": "https://example.invalid/run", "checks": []}
        ).read()

        self.assertEqual(status["reader"], "fixture_only")
        self.assertIs(status["live_github_api_called"], False)

    def test_merge_allowed_artifact_records_false_authority_flags(self) -> None:
        artifact = build_merge_audit_artifact(valid_material())

        self.assertEqual(artifact.recommendation, "MERGE_ALLOWED")
        payload = artifact.as_dict()
        self.assertIs(payload["human_merge_required"], True)
        self.assertIs(payload["merge_performed"], False)
        self.assertIs(payload["branch_deleted"], False)
        self.assertIs(payload["direct_main_push_performed"], False)
        self.assertIs(payload["auto_merge_enabled"], False)

    def test_pending_ci_recommends_waiting_for_ci(self) -> None:
        material = valid_material(
            ci_status_payload={"status": "pending", "run_url": "https://example.invalid/run", "checks": []}
        )

        artifact = build_merge_audit_artifact(material)

        self.assertEqual(artifact.recommendation, "WAITING_FOR_CI")

    def test_blocker_recommends_blocked(self) -> None:
        artifact = build_merge_audit_artifact(valid_material(blockers=("human decision required",)))

        self.assertEqual(artifact.recommendation, "BLOCKED")

    def test_failed_evidence_recommends_do_not_merge(self) -> None:
        artifact = build_merge_audit_artifact(
            valid_material(test_results={"focused_tests": "pass"})
        )

        self.assertEqual(artifact.recommendation, "DO_NOT_MERGE")

    def test_writer_refuses_overwrite_and_writes_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "merge_audit.json"
            artifact = build_merge_audit_artifact(valid_material())

            write_merge_audit_artifact(output, artifact)
            payload = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(payload["artifact_type"], "pr_factory_merge_audit_v1")
            with self.assertRaisesRegex(ValueError, "output_exists"):
                write_merge_audit_artifact(output, artifact)

    def test_source_contains_no_git_or_network_write_operations(self) -> None:
        source = Path("tools/pr_factory/merge_audit.py").read_text(encoding="utf-8")

        for marker in (
            "import subprocess",
            "from subprocess",
            "requests.",
            "urllib.",
            "import socket",
            "from socket",
            "gh pr merge",
            "git push origin main",
            "git branch -D",
            "auto_merge_enabled = True",
            "shell=True",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
