"""Tests for Independent Final Signoff Verification Harness V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.independent_final_signoff_verification import (
    ZERO_HASH,
    FileBackedIndependentFinalSignoffVerification,
    IndependentFinalSignoffVerificationError,
    compute_independent_evidence_snapshot_hash,
    compute_independent_final_signoff_verification_receipt_hash,
)
from kernel.runtime.release_candidate_final_signoff import (
    FileBackedReleaseCandidateFinalSignoff,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

SOURCE_PATH = Path("kernel/runtime/independent_final_signoff_verification.py")
OBSERVED_AT = "2026-05-29T03:00:00+00:00"
EXPIRES_AT = "2026-05-30T03:00:00+00:00"
MAIN_HEAD = "4cf29d2f65e20db7a1efef3ab7e36f10e8581533"
TAG = "v0.1.0-rc.529+4cf29d2"
REQUIRED_VALIDATION_COMMANDS = (
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests",
    "make ci",
    "git diff --check",
    "git status --short",
)


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _priority_matrix() -> dict[str, str]:
    return {
        f"#{number}": "merged and post-merge validated"
        for number in range(517, 530)
    }


def _signoff_evidence() -> dict[str, object]:
    return {
        "signoff_id": "release-candidate-final-signoff-529",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_head": MAIN_HEAD,
        "branch": "codex/529-release-candidate-final-signoff-v1",
        "release_tag_proposal": TAG,
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


def _with_snapshot_hash(snapshot: dict[str, object]) -> dict[str, object]:
    snapshot["snapshot_hash"] = compute_independent_evidence_snapshot_hash(snapshot)
    return snapshot


def _validation_transcript(command: str, status: str = "green") -> dict[str, object]:
    transcript = {
        "command": command,
        "status": status,
        "transcript": "local validation completed",
        "observed_at": OBSERVED_AT,
        "expires_at": EXPIRES_AT,
    }
    transcript["transcript_digest"] = _sha256_json(
        {
            "command": transcript["command"],
            "status": transcript["status"],
            "transcript": transcript["transcript"],
        }
    )
    return transcript


def _create_signoff_artifacts(root: Path) -> None:
    FileBackedReleaseCandidateFinalSignoff(runtime_root=root).close(
        _signoff_evidence(),
        observed_at=OBSERVED_AT,
    )


def _verification_evidence(root: Path) -> dict[str, object]:
    receipt_relpath = next(
        (root / "release-candidate-final-signoff" / "receipts").glob("*.json")
    ).relative_to(root)
    snapshots = [
        _with_snapshot_hash(
            {
                "priority_id": priority_id,
                "status": "merged and post-merge validated",
                "immutable": True,
                "post_merge_validation": "green",
                "head_sha": MAIN_HEAD,
                "merge_sha": MAIN_HEAD,
                "observed_at": OBSERVED_AT,
                "expires_at": EXPIRES_AT,
            }
        )
        for priority_id in _priority_matrix()
    ]
    ci_snapshot = _with_snapshot_hash(
        {
            "check_name": "canonical-health",
            "status": "SUCCESS",
            "immutable": True,
            "observed_at": OBSERVED_AT,
            "expires_at": EXPIRES_AT,
        }
    )
    worktree_evidence = _with_snapshot_hash(
        {
            "git_diff_check": "clean",
            "git_status_short": "clean",
            "status_short_output": "",
            "observed_at": OBSERVED_AT,
        }
    )
    release_tag_evidence = _with_snapshot_hash(
        {
            "release_tag_proposal": TAG,
            "release_tag_created": False,
            "observed_at": OBSERVED_AT,
        }
    )
    return {
        "verification_id": "independent-final-signoff-verification-530",
        "final_signoff_receipt_relpath": str(receipt_relpath),
        "final_signoff_report_relpath": "release-candidate-final-signoff/reports/final-signoff-report.json",
        "final_system_status_report_relpath": "release-candidate-final-signoff/reports/final-system-status-report.json",
        "expected_main_head": MAIN_HEAD,
        "current_repo_head": MAIN_HEAD,
        "pr_status_snapshots": snapshots,
        "validation_transcripts": [
            _validation_transcript(command) for command in REQUIRED_VALIDATION_COMMANDS
        ],
        "ci_status_snapshots": [ci_snapshot],
        "worktree_evidence": worktree_evidence,
        "release_tag_evidence": release_tag_evidence,
    }


class IndependentFinalSignoffVerificationV1Tests(unittest.TestCase):
    def test_accepts_complete_evidence_and_persists_receipt_report_and_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            receipt = FileBackedIndependentFinalSignoffVerification(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).verify(_verification_evidence(root), observed_at=OBSERVED_AT)
            report = json.loads(
                (
                    root
                    / "independent-final-signoff-verification"
                    / "reports"
                    / "independent-verification-report.json"
                ).read_text(encoding="utf-8")
            )
            persisted_receipt = json.loads(
                next(
                    (
                        root
                        / "independent-final-signoff-verification"
                        / "receipts"
                    ).glob("*.json")
                ).read_text(encoding="utf-8")
            )
            wal_records = FileBackedRealWalStorage(
                root
                / "independent-final-signoff-verification"
                / "verification.real-wal.jsonl"
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(
            receipt.receipt_hash,
            compute_independent_final_signoff_verification_receipt_hash(receipt),
        )
        self.assertEqual(persisted_receipt["receipt_hash"], receipt.receipt_hash)
        self.assertEqual(report["receipt_hash"], receipt.receipt_hash)
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, receipt.wal_record_hash)
        self.assertNotEqual(receipt.wal_record_hash, ZERO_HASH)

    def test_missing_receipt_rejects_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            evidence = _verification_evidence(root)
            evidence["final_signoff_receipt_relpath"] = "missing-receipt.json"

            with self.assertRaisesRegex(
                IndependentFinalSignoffVerificationError,
                "final_signoff_receipt_relpath_missing",
            ):
                FileBackedIndependentFinalSignoffVerification(
                    runtime_root=root,
                    repo_root=Path.cwd(),
                ).verify(evidence, observed_at=OBSERVED_AT)

    def test_main_head_mismatch_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            evidence = _verification_evidence(root)
            evidence["current_repo_head"] = "0" * 40
            receipt = FileBackedIndependentFinalSignoffVerification(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).verify(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn("main_head_mismatch", receipt.failures)

    def test_pr_status_validation_digest_ci_runbook_verdict_and_stale_rejections(self) -> None:
        cases = (
            (
                "pr-status",
                lambda evidence: evidence["pr_status_snapshots"][0].update(  # type: ignore[index,union-attr]
                    {
                        "status": "open",
                        "snapshot_hash": compute_independent_evidence_snapshot_hash(
                            {
                                **evidence["pr_status_snapshots"][0],  # type: ignore[index]
                                "status": "open",
                            }
                        ),
                    }
                ),
                "pr_status_snapshot_status_mismatch:#517",
            ),
            (
                "validation-digest",
                lambda evidence: evidence["validation_transcripts"][0].update(  # type: ignore[index,union-attr]
                    {"transcript_digest": ZERO_HASH}
                ),
                "validation_transcript_digest_mismatch:"
                + REQUIRED_VALIDATION_COMMANDS[0],
            ),
            (
                "ci-pending",
                lambda evidence: evidence["ci_status_snapshots"][0].update(  # type: ignore[index,union-attr]
                    {
                        "status": "PENDING",
                        "snapshot_hash": compute_independent_evidence_snapshot_hash(
                            {
                                **evidence["ci_status_snapshots"][0],  # type: ignore[index]
                                "status": "PENDING",
                            }
                        ),
                    }
                ),
                "canonical_health_snapshot_not_success",
            ),
            (
                "stale",
                lambda evidence: evidence["pr_status_snapshots"][0].update(  # type: ignore[index,union-attr]
                    {
                        "stale": True,
                        "snapshot_hash": compute_independent_evidence_snapshot_hash(
                            {
                                **evidence["pr_status_snapshots"][0],  # type: ignore[index]
                                "stale": True,
                            }
                        ),
                    }
                ),
                "pr_status_snapshot_stale",
            ),
        )
        for label, mutate, expected_failure in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                _create_signoff_artifacts(root)
                evidence = _verification_evidence(root)
                mutate(evidence)
                receipt = FileBackedIndependentFinalSignoffVerification(
                    runtime_root=root,
                    repo_root=Path.cwd(),
                ).verify(evidence, observed_at=OBSERVED_AT)

            self.assertFalse(receipt.accepted)
            self.assertIn(expected_failure, receipt.failures)

    def test_missing_linked_runbook_and_contradictory_verdict_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            missing_runbook_receipt = FileBackedIndependentFinalSignoffVerification(
                runtime_root=root,
                repo_root=root / "empty-repo",
            ).verify(_verification_evidence(root), observed_at=OBSERVED_AT)

        self.assertFalse(missing_runbook_receipt.accepted)
        self.assertIn(
            "linked_runbook_missing:docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
            missing_runbook_receipt.failures,
        )

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            report_path = (
                root
                / "release-candidate-final-signoff"
                / "reports"
                / "final-signoff-report.json"
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["final_verdict"] = "BLOCKED"
            report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
            contradictory_receipt = FileBackedIndependentFinalSignoffVerification(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).verify(_verification_evidence(root), observed_at=OBSERVED_AT)

        self.assertFalse(contradictory_receipt.accepted)
        self.assertIn("contradictory_final_verdict", contradictory_receipt.failures)

    def test_no_network_subprocess_or_credential_api_imports(self) -> None:
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        forbidden_imports = {
            "http",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr == "environ"
            ):
                self.fail("os.environ access is forbidden")

        self.assertFalse(imports & forbidden_imports)


if __name__ == "__main__":
    unittest.main()
