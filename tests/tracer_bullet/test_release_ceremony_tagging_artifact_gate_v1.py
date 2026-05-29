"""Tests for Release Ceremony / Tagging Artifact Gate V1."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.release_ceremony_tagging_artifact_gate import (
    ZERO_HASH,
    FileBackedReleaseCeremonyTaggingArtifactGate,
    compute_release_ceremony_receipt_hash,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

OBSERVED_AT = "2026-05-29T07:00:00+00:00"
MAIN_HEAD = "06d04091a45b84ce42de42889aaaf14a1683361a"
TAG = "v0.1.0-rc.529+06d0409"


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _fault_results() -> list[dict[str, object]]:
    return [
        {
            "fault_id": "crash",
            "fault_type": "crash_before_write",
            "detected": True,
            "safe_recovery": True,
        },
        {
            "fault_id": "hash",
            "fault_type": "hash_mismatch",
            "detected": True,
            "safe_recovery": True,
        },
    ]


def _evidence() -> dict[str, object]:
    return {
        "release_id": "post-529-release-ceremony-534",
        "expected_main_head": MAIN_HEAD,
        "current_main_head": MAIN_HEAD,
        "release_tag_proposal": TAG,
        "final_signoff_receipt": {
            "integration_version": "release_candidate_final_signoff_v1",
            "accepted": True,
            "final_verdict": "READY_TO_REVIEW_AND_MERGE",
            "main_head": MAIN_HEAD,
            "release_tag_proposal": TAG,
            "receipt_hash": _digest("final-signoff"),
        },
        "independent_verification_receipt": {
            "integration_version": "independent_final_signoff_verification_v1",
            "accepted": True,
            "receipt_hash": _digest("independent-verification"),
        },
        "transparency_root_receipt": {
            "transparency_version": "evidence_transparency_merkle_proof_v1",
            "accepted": True,
            "root_hash": _digest("transparency-root"),
            "receipt_hash": _digest("transparency-receipt"),
        },
        "policy_decision_receipt": {
            "decision_version": "declarative_policy_gate_bundle_v1",
            "allowed": True,
            "decision": "allow",
            "receipt_hash": _digest("policy-decision"),
        },
        "fault_simulation_report": {
            "simulation_version": "deterministic_fault_simulation_harness_v1",
            "accepted": True,
            "fault_results": _fault_results(),
            "report_hash": _digest("fault-report"),
        },
    }


class ReleaseCeremonyTaggingArtifactGateV1Tests(unittest.TestCase):
    def test_accepts_full_evidence_and_persists_receipt_report_notes_tag_proposal_and_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).prepare(_evidence(), observed_at=OBSERVED_AT)
            report = json.loads(
                (
                    root
                    / "release-ceremony-tagging"
                    / "reports"
                    / "release-ceremony-report.json"
                ).read_text(encoding="utf-8")
            )
            notes = (
                root
                / "release-ceremony-tagging"
                / "release-notes"
                / "release-notes-draft.md"
            ).read_text(encoding="utf-8")
            tag_proposal = json.loads(
                (
                    root
                    / "release-ceremony-tagging"
                    / "tag-command"
                    / "tag-command-proposal.json"
                ).read_text(encoding="utf-8")
            )
            persisted_receipt = json.loads(
                next(
                    (
                        root
                        / "release-ceremony-tagging"
                        / "receipts"
                    ).glob("*.json")
                ).read_text(encoding="utf-8")
            )
            wal_records = FileBackedRealWalStorage(
                root
                / "release-ceremony-tagging"
                / "release-ceremony.real-wal.jsonl"
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.receipt_hash, compute_release_ceremony_receipt_hash(receipt))
        self.assertEqual(persisted_receipt["receipt_hash"], receipt.receipt_hash)
        self.assertEqual(report["receipt_hash"], receipt.receipt_hash)
        self.assertIn(TAG, notes)
        self.assertIn(MAIN_HEAD, notes)
        self.assertEqual(tag_proposal["command"], receipt.tag_command_proposal)
        self.assertTrue(tag_proposal["proposal_only"])
        self.assertFalse(tag_proposal["tag_created"])
        self.assertFalse(tag_proposal["tag_pushed"])
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, receipt.wal_record_hash)
        self.assertNotEqual(receipt.wal_record_hash, ZERO_HASH)

    def test_missing_upstream_receipt_rejects_fail_closed(self) -> None:
        evidence = _evidence()
        del evidence["independent_verification_receipt"]
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn(
            "missing_upstream_receipt:independent_verification_receipt",
            receipt.failures,
        )

    def test_bad_tag_rejects(self) -> None:
        evidence = _evidence()
        evidence["release_tag_proposal"] = "latest"
        evidence["final_signoff_receipt"]["release_tag_proposal"] = "latest"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn("release_tag_proposal_invalid", receipt.failures)

    def test_head_mismatch_rejects(self) -> None:
        evidence = _evidence()
        evidence["current_main_head"] = "16d04091a45b84ce42de42889aaaf14a1683361a"
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn("main_head_mismatch", receipt.failures)

    def test_failed_policy_rejects(self) -> None:
        evidence = _evidence()
        evidence["policy_decision_receipt"]["allowed"] = False  # type: ignore[index]
        evidence["policy_decision_receipt"]["decision"] = "deny"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn("policy_decision_not_allowed", receipt.failures)

    def test_failed_fault_simulation_rejects(self) -> None:
        evidence = _evidence()
        evidence["fault_simulation_report"]["accepted"] = False  # type: ignore[index]
        evidence["fault_simulation_report"]["fault_results"][0]["safe_recovery"] = False  # type: ignore[index]
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn("fault_simulation_report_not_accepted", receipt.failures)
        self.assertIn("fault_simulation_unsafe_recovery:crash", receipt.failures)

    def test_release_notes_and_tag_command_are_proposal_only(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).prepare(_evidence(), observed_at=OBSERVED_AT)
            tag_proposal = json.loads(
                (
                    root
                    / "release-ceremony-tagging"
                    / "tag-command"
                    / "tag-command-proposal.json"
                ).read_text(encoding="utf-8")
            )

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertFalse(receipt.tag_created)
        self.assertFalse(receipt.tag_pushed)
        self.assertFalse(receipt.external_artifacts_published)
        self.assertEqual(
            tag_proposal["command"],
            f'git tag -a {TAG} {MAIN_HEAD} -m "Release candidate {TAG}"',
        )
        self.assertNotIn("push", tag_proposal["command"])


if __name__ == "__main__":
    unittest.main()
