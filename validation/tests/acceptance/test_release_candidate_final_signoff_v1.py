"""Acceptance tests for Release Candidate / Final Signoff V1."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.release_candidate_final_signoff import (
    ZERO_HASH,
    FileBackedReleaseCandidateFinalSignoff,
)

OBSERVED_AT = "2026-05-29T01:10:00+00:00"


def _evidence() -> dict[str, object]:
    return {
        "signoff_id": "release-candidate-final-signoff-acceptance-529",
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
        "priority_status_matrix": {
            f"#{number}": "merged and post-merge validated"
            for number in range(517, 530)
        },
        "rollback_recovery_link": "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
        "e2e_acceptance_link": "docs/runbooks/system_e2e_acceptance_v1.md",
        "security_hardening_link": "docs/runbooks/security_abuse_boundary_hardening_v1.md",
    }


class ReleaseCandidateFinalSignoffV1AcceptanceTests(unittest.TestCase):
    def test_final_signoff_acceptance_report_is_signable_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime = FileBackedReleaseCandidateFinalSignoff(runtime_root=root)
            accepted = runtime.close(_evidence(), observed_at=OBSERVED_AT)
            rejected_evidence = _evidence()
            rejected_evidence["known_blockers"] = ["untriaged-blocker"]
            rejected = FileBackedReleaseCandidateFinalSignoff(
                runtime_root=root / "rejected"
            ).close(rejected_evidence, observed_at=OBSERVED_AT)

        self.assertTrue(accepted.accepted, accepted.failures)
        self.assertFalse(rejected.accepted)
        self.assertNotEqual(accepted.receipt_hash, ZERO_HASH)
        self.assertNotEqual(accepted.final_signoff_report_hash, ZERO_HASH)
        self.assertNotEqual(accepted.final_system_status_report_hash, ZERO_HASH)
        self.assertIn("known_blockers_must_be_empty", rejected.failures)
        self.assertEqual(
            accepted.rollback_recovery_link,
            "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
        )
        self.assertEqual(
            accepted.e2e_acceptance_link,
            "docs/runbooks/system_e2e_acceptance_v1.md",
        )
        self.assertEqual(
            accepted.security_hardening_link,
            "docs/runbooks/security_abuse_boundary_hardening_v1.md",
        )


if __name__ == "__main__":
    unittest.main()
