"""Tests for Integrated Hard Audit Acceptance V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.evidence_transparency_merkle_proof import (
    FileBackedEvidenceTransparencyMerkleLog,
)
from kernel.runtime.integrated_hard_audit_acceptance import (
    ZERO_HASH,
    FileBackedIntegratedHardAuditAcceptance,
    compute_integrated_hard_audit_receipt_hash,
)
from kernel.runtime.release_ceremony_tagging_artifact_gate import (
    FileBackedReleaseCeremonyTaggingArtifactGate,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

SOURCE_PATH = Path("kernel/runtime/integrated_hard_audit_acceptance.py")
OBSERVED_AT = "2026-05-29T08:00:00+00:00"
MAIN_HEAD = "ad42d720818c83924803473783b4d8a30debb185"
TAG = "v0.1.0-rc.529+ad42d72"


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _final_signoff_receipt() -> dict[str, object]:
    return {
        "integration_version": "release_candidate_final_signoff_v1",
        "accepted": True,
        "final_verdict": "READY_TO_REVIEW_AND_MERGE",
        "main_head": MAIN_HEAD,
        "release_tag_proposal": TAG,
        "receipt_hash": _digest("final-signoff"),
        "final_signoff_report_hash": _digest("final-signoff-report"),
        "final_system_status_report_hash": _digest("final-system-status-report"),
        "wal_record_hash": _digest("final-signoff-wal"),
        "rollback_recovery_link": "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
        "e2e_acceptance_link": "docs/runbooks/system_e2e_acceptance_v1.md",
        "security_hardening_link": "docs/runbooks/security_abuse_boundary_hardening_v1.md",
    }


def _independent_receipt(final_receipt: dict[str, object]) -> dict[str, object]:
    return {
        "integration_version": "independent_final_signoff_verification_v1",
        "accepted": True,
        "receipt_hash": _digest("independent-verification"),
        "final_signoff_report_hash": final_receipt["final_signoff_report_hash"],
        "wal_record_hash": _digest("independent-verification-wal"),
    }


def _policy_receipt(allowed: bool = True) -> dict[str, object]:
    return {
        "decision_version": "declarative_policy_gate_bundle_v1",
        "allowed": allowed,
        "decision": "allow" if allowed else "deny",
        "receipt_hash": _digest("policy-allow" if allowed else "policy-deny"),
        "wal_record_hash": _digest("policy-wal" if allowed else "policy-deny-wal"),
    }


def _fault_report(accepted: bool = True) -> dict[str, object]:
    return {
        "simulation_version": "deterministic_fault_simulation_harness_v1",
        "accepted": accepted,
        "fault_results": [
            {
                "fault_id": "crash",
                "fault_type": "crash_before_write",
                "detected": True,
                "safe_recovery": accepted,
            }
        ],
        "report_hash": _digest("fault-report" if accepted else "fault-report-failed"),
        "wal_record_hash": _digest("fault-wal" if accepted else "fault-failed-wal"),
    }


def _release_evidence(
    *,
    final_signoff: dict[str, object],
    independent: dict[str, object],
    transparency: dict[str, object],
    policy: dict[str, object],
    fault: dict[str, object],
) -> dict[str, object]:
    return {
        "release_id": "post-529-release-ceremony-534",
        "expected_main_head": MAIN_HEAD,
        "current_main_head": MAIN_HEAD,
        "release_tag_proposal": TAG,
        "final_signoff_receipt": final_signoff,
        "independent_verification_receipt": independent,
        "transparency_root_receipt": transparency,
        "policy_decision_receipt": policy,
        "fault_simulation_report": fault,
    }


def _audit_evidence(root: Path, *, policy_allowed: bool = True, fault_accepted: bool = True) -> dict[str, object]:
    final_signoff = _final_signoff_receipt()
    independent = _independent_receipt(final_signoff)
    publication = FileBackedEvidenceTransparencyMerkleLog(
        runtime_root=root / "transparency",
    ).publish(
        [
            {
                "item_id": "final-signoff-receipt",
                "evidence_kind": "release_signoff",
                "evidence_digest": final_signoff["receipt_hash"],
            },
            {
                "item_id": "independent-verification-receipt",
                "evidence_kind": "independent_verification",
                "evidence_digest": independent["receipt_hash"],
            },
        ],
        independent_verification_receipt=independent,
        observed_at=OBSERVED_AT,
    )
    transparency = publication.root_receipt.as_dict()
    proof = next(
        proof.as_dict()
        for proof in publication.inclusion_proofs
        if proof.item_id == "independent-verification-receipt"
    )
    policy = _policy_receipt(policy_allowed)
    fault = _fault_report(fault_accepted)
    release = FileBackedReleaseCeremonyTaggingArtifactGate(
        runtime_root=root / "release",
        repo_root=Path.cwd(),
    ).prepare(
        _release_evidence(
            final_signoff=final_signoff,
            independent=independent,
            transparency=transparency,
            policy=policy,
            fault=fault,
        ),
        observed_at=OBSERVED_AT,
    ).as_dict()
    return {
        "audit_id": "post-529-integrated-hard-audit-535",
        "final_signoff_receipt": final_signoff,
        "independent_verification_receipt": independent,
        "transparency_root_receipt": transparency,
        "transparency_inclusion_proof": proof,
        "policy_decision_receipt": policy,
        "fault_simulation_report": fault,
        "release_ceremony_receipt": release,
    }


class IntegratedHardAuditAcceptanceV1Tests(unittest.TestCase):
    def test_happy_path_persists_operator_report_receipt_and_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            evidence = _audit_evidence(root)
            receipt = FileBackedIntegratedHardAuditAcceptance(
                runtime_root=root / "audit",
                repo_root=Path.cwd(),
            ).verify(evidence, observed_at=OBSERVED_AT)
            report = (
                root
                / "audit"
                / "integrated-hard-audit"
                / "reports"
                / "integrated-hard-audit-report.md"
            ).read_text(encoding="utf-8")
            report_json = json.loads(
                (
                    root
                    / "audit"
                    / "integrated-hard-audit"
                    / "reports"
                    / "integrated-hard-audit-report.json"
                ).read_text(encoding="utf-8")
            )
            wal_records = FileBackedRealWalStorage(
                root
                / "audit"
                / "integrated-hard-audit"
                / "hard-audit.real-wal.jsonl"
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.receipt_hash, compute_integrated_hard_audit_receipt_hash(receipt))
        self.assertIn("Integrated Hard Audit Report", report)
        self.assertIn("Failures:", report)
        self.assertEqual(report_json["receipt_hash"], receipt.receipt_hash)
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, receipt.wal_record_hash)
        self.assertNotEqual(receipt.operator_report_digest, ZERO_HASH)
        self.assertNotEqual(receipt.runbook_link_digest, ZERO_HASH)

    def test_each_missing_receipt_rejects(self) -> None:
        keys = (
            "final_signoff_receipt",
            "independent_verification_receipt",
            "transparency_root_receipt",
            "policy_decision_receipt",
            "fault_simulation_report",
            "release_ceremony_receipt",
        )
        for key in keys:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                evidence = _audit_evidence(root)
                del evidence[key]
                receipt = FileBackedIntegratedHardAuditAcceptance(
                    runtime_root=root / "audit",
                    repo_root=Path.cwd(),
                ).verify(evidence, observed_at=OBSERVED_AT)

            self.assertFalse(receipt.accepted)
            self.assertIn("missing_upstream_receipt:" + key, receipt.failures)

    def test_corrupted_transparency_proof_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            evidence = _audit_evidence(root)
            proof = dict(evidence["transparency_inclusion_proof"])  # type: ignore[arg-type]
            proof["proof_path"] = [("right", _digest("tampered-proof"))]
            proof["proof_hash"] = ""
            evidence["transparency_inclusion_proof"] = proof
            receipt = FileBackedIntegratedHardAuditAcceptance(
                runtime_root=root / "audit",
                repo_root=Path.cwd(),
            ).verify(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(receipt.accepted)
        self.assertIn("corrupted_transparency_proof", receipt.failures)

    def test_failed_policy_and_failed_simulation_deny_release_ceremony(self) -> None:
        cases = (
            ("policy", {"policy_allowed": False, "fault_accepted": True}, "policy_decision_not_allowed"),
            ("fault", {"policy_allowed": True, "fault_accepted": False}, "fault_simulation_report_not_accepted"),
        )
        for label, kwargs, expected_failure in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                evidence = _audit_evidence(root, **kwargs)
                release = evidence["release_ceremony_receipt"]
                receipt = FileBackedIntegratedHardAuditAcceptance(
                    runtime_root=root / "audit",
                    repo_root=Path.cwd(),
                ).verify(evidence, observed_at=OBSERVED_AT)

            self.assertFalse(release["accepted"])  # type: ignore[index]
            self.assertFalse(receipt.accepted)
            self.assertIn(expected_failure, receipt.failures)
            self.assertIn("release_ceremony_receipt_not_accepted", receipt.failures)

    def test_integrated_receipt_is_deterministic_and_runbook_links_exist(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_root = Path(first_dir)
            second_root = Path(second_dir)
            first_evidence = _audit_evidence(first_root)
            second_evidence = _audit_evidence(second_root)
            first = FileBackedIntegratedHardAuditAcceptance(
                runtime_root=first_root / "audit",
                repo_root=Path.cwd(),
            ).verify(first_evidence, observed_at=OBSERVED_AT)
            second = FileBackedIntegratedHardAuditAcceptance(
                runtime_root=second_root / "audit",
                repo_root=Path.cwd(),
            ).verify(second_evidence, observed_at=OBSERVED_AT)

        self.assertTrue(first.accepted, first.failures)
        self.assertEqual(first.receipt_hash, second.receipt_hash)
        for relpath in (
            "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
            "docs/runbooks/system_e2e_acceptance_v1.md",
            "docs/runbooks/security_abuse_boundary_hardening_v1.md",
        ):
            self.assertTrue(Path(relpath).is_file(), relpath)

    def test_source_has_no_network_or_credential_access(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        self.assertTrue({"requests", "urllib", "http", "socket", "subprocess"}.isdisjoint(imports))
        self.assertNotIn(".env", source)


if __name__ == "__main__":
    unittest.main()
