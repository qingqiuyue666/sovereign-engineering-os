"""Tests for Release Candidate / Final Signoff V1."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.release_candidate_final_signoff import (
    ZERO_HASH,
    FileBackedReleaseCandidateFinalSignoff,
    ReleaseCandidateFinalSignoffError,
    compute_release_candidate_final_signoff_receipt_hash,
    compute_release_candidate_gate_result_hash,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

SOURCE_PATH = Path("kernel/runtime/release_candidate_final_signoff.py")
OBSERVED_AT = "2026-05-29T01:10:00+00:00"


def _priority_matrix() -> dict[str, str]:
    return {
        f"#{number}": "merged and post-merge validated"
        for number in range(517, 530)
    }


def _complete_evidence() -> dict[str, object]:
    return {
        "signoff_id": "release-candidate-final-signoff-529",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_head": "af031b6108717438276928a46d27ec3520b30267",
        "branch": "codex/529-release-candidate-final-signoff-v1",
        "release_tag_proposal": "v0.1.0-rc.529+af031b610871",
        "release_tag_created": False,
        "final_verdict": "READY_TO_REVIEW_AND_MERGE",
        "final_signoff_report_ready": True,
        "final_system_status_report_ready": True,
        "version_tuple": {
            "product": "sovereign-engineering-os",
            "release_candidate": "0.1.0-rc.529",
            "priority_range": "#517-#529",
            "schema_bundle": "schema-freeze-v1",
            "frozen": True,
        },
        "schema_freeze": {
            "status": "frozen",
            "unknown_schema_rejected": True,
            "schema_drift_detected": False,
            "changed_schema_files": [],
        },
        "acceptance_matrix": {
            "focused_release_candidate_tests": "green",
            "tracer_bullet_discovery": "green",
            "full_unittest_discovery": "green",
            "make_ci": "green",
            "git_diff_check": "clean",
            "git_status_short": "clean",
        },
        "validation_commands": [
            {
                "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet",
                "status": "green",
            },
            {
                "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests",
                "status": "green",
            },
            {"command": "make ci", "status": "green"},
            {"command": "git diff --check", "status": "clean"},
            {"command": "git status --short", "status": "clean"},
        ],
        "ci_status": {"canonical-health": "SUCCESS"},
        "worktree_status": {
            "git_diff_check": "clean",
            "git_status_short": "clean",
        },
        "invariant_sweep": {
            "evidence_first": True,
            "contract_first": True,
            "test_first": True,
            "failure_path_first": True,
            "fail_closed_by_default": True,
            "local_first": True,
            "deterministic_replay": True,
            "no_silent_repair": True,
            "no_fake_acceptance": True,
            "no_direct_main_mutation": True,
            "no_hidden_runtime_autonomy": True,
            "no_unsafe_process_launch": True,
            "no_hidden_network_calls": True,
            "no_credential_access": True,
            "no_uncontrolled_dependencies": True,
            "no_external_code_copying": True,
        },
        "docs_runbook_alignment": {
            "rollback_recovery_link": "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
            "e2e_acceptance_link": "docs/runbooks/system_e2e_acceptance_v1.md",
            "security_hardening_link": "docs/runbooks/security_abuse_boundary_hardening_v1.md",
            "rollback_recovery_audit_link": "docs/audit/recovery_rollback_disaster_procedure_v1.md",
            "e2e_acceptance_audit_link": "docs/audit/system_e2e_acceptance_v1.md",
            "security_hardening_audit_link": "docs/audit/security_abuse_boundary_hardening_v1.md",
            "runbooks_match_runtime_boundaries": True,
            "audit_notes_match_validation": True,
        },
        "cleanup_status": {
            "stale_pr_body_text_removed": True,
            "stale_docs_aligned": True,
            "single_priority_scope_confirmed": True,
            "todo_as_implementation_found": False,
            "placeholder_blockers_hidden": False,
            "known_untriaged_blockers": False,
        },
        "known_blockers": [],
        "priority_status_matrix": _priority_matrix(),
        "rollback_recovery_link": "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
        "e2e_acceptance_link": "docs/runbooks/system_e2e_acceptance_v1.md",
        "security_hardening_link": "docs/runbooks/security_abuse_boundary_hardening_v1.md",
    }


class ReleaseCandidateFinalSignoffV1Tests(unittest.TestCase):
    def test_accepts_complete_release_evidence_and_persists_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = FileBackedReleaseCandidateFinalSignoff(runtime_root=root).close(
                _complete_evidence(),
                observed_at=OBSERVED_AT,
            )
            signoff_report = json.loads(
                (root / "release-candidate-final-signoff" / "reports" / "final-signoff-report.json").read_text(
                    encoding="utf-8"
                )
            )
            status_report = json.loads(
                (
                    root
                    / "release-candidate-final-signoff"
                    / "reports"
                    / "final-system-status-report.json"
                ).read_text(encoding="utf-8")
            )
            receipt_path = next((root / "release-candidate-final-signoff" / "receipts").glob("*.json"))
            persisted_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            wal_records = FileBackedRealWalStorage(
                root / "release-candidate-final-signoff" / "signoff.real-wal.jsonl"
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(
            receipt.receipt_hash,
            compute_release_candidate_final_signoff_receipt_hash(receipt),
        )
        self.assertEqual(persisted_receipt["receipt_hash"], receipt.receipt_hash)
        self.assertEqual(signoff_report["final_verdict"], "READY_TO_REVIEW_AND_MERGE")
        self.assertEqual(status_report["priority_status_matrix"], _priority_matrix())
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, receipt.wal_record_hash)
        self.assertNotEqual(receipt.final_signoff_report_hash, ZERO_HASH)
        self.assertNotEqual(receipt.final_system_status_report_hash, ZERO_HASH)
        self.assertTrue(all(gate.accepted for gate in receipt.gate_results))
        for gate in receipt.gate_results:
            self.assertEqual(gate.gate_hash, compute_release_candidate_gate_result_hash(gate))

    def test_rejects_if_any_priority_is_not_post_merge_validated(self) -> None:
        evidence = _complete_evidence()
        matrix = _priority_matrix()
        matrix["#528"] = "open draft"
        evidence["priority_status_matrix"] = matrix

        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedReleaseCandidateFinalSignoff(runtime_root=tempdir).close(
                evidence,
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(receipt.accepted)
        self.assertIn("priority_not_post_merge_validated:#528", receipt.failures)
        self.assertNotEqual(receipt.wal_record_hash, ZERO_HASH)

    def test_rejects_todo_placeholder_or_blocker_evidence(self) -> None:
        cases = (
            ("todo_as_implementation_found", "todo_as_implementation_found_must_be_false"),
            ("placeholder_blockers_hidden", "placeholder_blockers_hidden_must_be_false"),
            ("known_untriaged_blockers", "known_untriaged_blockers_must_be_false"),
        )
        for flag, expected_failure in cases:
            with self.subTest(flag=flag):
                evidence = _complete_evidence()
                cleanup = dict(evidence["cleanup_status"])  # type: ignore[arg-type]
                cleanup[flag] = True
                evidence["cleanup_status"] = cleanup
                if flag == "known_untriaged_blockers":
                    evidence["known_blockers"] = ["untriaged-blocker"]

                with tempfile.TemporaryDirectory() as tempdir:
                    receipt = FileBackedReleaseCandidateFinalSignoff(runtime_root=tempdir).close(
                        evidence,
                        observed_at=OBSERVED_AT,
                    )

                self.assertFalse(receipt.accepted)
                self.assertIn(expected_failure, receipt.failures)

    def test_rejects_ci_schema_or_tag_regressions_fail_closed(self) -> None:
        cases = (
            ("ci", {"ci_status": {"canonical-health": "FAILURE"}}, "canonical_health_success_required"),
            (
                "schema",
                {"schema_freeze": {"status": "open", "unknown_schema_rejected": True, "schema_drift_detected": False, "changed_schema_files": []}},
                "schema_freeze_status_frozen_required",
            ),
            ("tag", {"release_tag_created": True}, "release_tag_must_be_proposal_only"),
        )
        for label, patch, expected_failure in cases:
            with self.subTest(label=label):
                evidence = _complete_evidence()
                evidence.update(patch)

                with tempfile.TemporaryDirectory() as tempdir:
                    receipt = FileBackedReleaseCandidateFinalSignoff(runtime_root=tempdir).close(
                        evidence,
                        observed_at=OBSERVED_AT,
                    )

                self.assertFalse(receipt.accepted)
                self.assertIn(expected_failure, receipt.failures)

    def test_rejects_contradictory_verdict_tag_and_links_without_raising(self) -> None:
        cases = (
            ("verdict", {"final_verdict": "DO_NOT_MERGE"}, "final_verdict_ready_required"),
            ("tag", {"release_tag_proposal": "latest"}, "release_tag_proposal_invalid"),
            (
                "link",
                {"security_hardening_link": "docs/runbooks/missing.md"},
                "security_hardening_link_invalid",
            ),
        )
        for label, patch, expected_failure in cases:
            with self.subTest(label=label):
                evidence = _complete_evidence()
                evidence.update(patch)

                with tempfile.TemporaryDirectory() as tempdir:
                    receipt = FileBackedReleaseCandidateFinalSignoff(runtime_root=tempdir).close(
                        evidence,
                        observed_at=OBSERVED_AT,
                    )

                self.assertFalse(receipt.accepted)
                self.assertIn(expected_failure, receipt.failures)
                self.assertNotEqual(receipt.wal_record_hash, ZERO_HASH)

    def test_source_has_no_external_authority_imports_and_docs_are_linked(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        forbidden_imports = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in ("requests.", "urllib.", "socket.", "Popen", "os.system", "while True", "TODO"):
            self.assertNotIn(marker, source)
        for path in (
            "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
            "docs/runbooks/system_e2e_acceptance_v1.md",
            "docs/runbooks/security_abuse_boundary_hardening_v1.md",
            "docs/audit/recovery_rollback_disaster_procedure_v1.md",
            "docs/audit/system_e2e_acceptance_v1.md",
            "docs/audit/security_abuse_boundary_hardening_v1.md",
        ):
            self.assertTrue(Path(path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
