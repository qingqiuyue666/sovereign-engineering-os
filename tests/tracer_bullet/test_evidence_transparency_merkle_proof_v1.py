"""Tests for Evidence Transparency / Merkle Inclusion Proof V1."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.evidence_transparency_merkle_proof import (
    ZERO_HASH,
    EvidenceTransparencyInclusionProof,
    FileBackedEvidenceTransparencyMerkleLog,
    compute_evidence_transparency_inclusion_proof_hash,
    compute_evidence_transparency_root_receipt_hash,
    verify_evidence_transparency_inclusion_proof,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

OBSERVED_AT = "2026-05-29T04:00:00+00:00"


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _items() -> list[dict[str, object]]:
    return [
        {
            "item_id": "final-signoff-receipt",
            "evidence_kind": "release_signoff",
            "evidence_digest": _digest("receipt"),
        },
        {
            "item_id": "independent-verification-receipt",
            "evidence_kind": "independent_verification",
            "evidence_digest": _digest("verification"),
        },
        {
            "item_id": "validation-transcript-bundle",
            "evidence_kind": "validation",
            "evidence_digest": _digest("validation"),
        },
    ]


def _independent_receipt() -> dict[str, object]:
    return {
        "accepted": True,
        "receipt_hash": _digest("p530-independent-verification-receipt"),
    }


class EvidenceTransparencyMerkleProofV1Tests(unittest.TestCase):
    def test_deterministic_root_valid_proofs_and_wal_report_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            first = FileBackedEvidenceTransparencyMerkleLog(runtime_root=root / "a").publish(
                _items(),
                independent_verification_receipt=_independent_receipt(),
                observed_at=OBSERVED_AT,
            )
            second = FileBackedEvidenceTransparencyMerkleLog(runtime_root=root / "b").publish(
                list(reversed(_items())),
                independent_verification_receipt=_independent_receipt(),
                observed_at=OBSERVED_AT,
            )
            report = json.loads(
                (
                    root
                    / "a"
                    / "evidence-transparency-merkle"
                    / "reports"
                    / "transparency-report.json"
                ).read_text(encoding="utf-8")
            )
            proof_files = list(
                (
                    root
                    / "a"
                    / "evidence-transparency-merkle"
                    / "proofs"
                ).glob("*.json")
            )
            wal_records = FileBackedRealWalStorage(
                root
                / "a"
                / "evidence-transparency-merkle"
                / "transparency.real-wal.jsonl"
            ).read_records()

        self.assertTrue(first.root_receipt.accepted, first.root_receipt.failures)
        self.assertEqual(first.root_receipt.root_hash, second.root_receipt.root_hash)
        self.assertEqual(
            first.root_receipt.receipt_hash,
            compute_evidence_transparency_root_receipt_hash(first.root_receipt),
        )
        self.assertEqual(len(proof_files), len(_items()))
        self.assertEqual(report["root_hash"], first.root_receipt.root_hash)
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, first.root_receipt.wal_record_hash)
        self.assertNotEqual(first.root_receipt.wal_record_hash, ZERO_HASH)
        for proof in first.inclusion_proofs:
            self.assertEqual(
                proof.proof_hash,
                compute_evidence_transparency_inclusion_proof_hash(proof),
            )
            verification = verify_evidence_transparency_inclusion_proof(
                proof,
                first.root_receipt,
            )
            self.assertTrue(verification.accepted, verification.failures)

    def test_tampered_proof_changed_leaf_missing_leaf_and_order_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            publication = FileBackedEvidenceTransparencyMerkleLog(
                runtime_root=tempdir,
            ).publish(_items(), observed_at=OBSERVED_AT)

        proof = publication.inclusion_proofs[0]
        tampered = EvidenceTransparencyInclusionProof(
            proof_version=proof.proof_version,
            item_id=proof.item_id,
            evidence_digest=proof.evidence_digest,
            evidence_kind=proof.evidence_kind,
            leaf_index=proof.leaf_index,
            leaf_hash=proof.leaf_hash,
            proof_path=(("right", _digest("tampered-sibling")),),
            root_hash=proof.root_hash,
        )
        tampered_result = verify_evidence_transparency_inclusion_proof(
            tampered,
            publication.root_receipt,
        )
        self.assertFalse(tampered_result.accepted)
        self.assertIn("tampered_inclusion_proof", tampered_result.failures)

        changed_leaf_receipt = publication.root_receipt.as_dict()
        changed_leaf_receipt["leaf_hashes"] = tuple(
            [ZERO_HASH, *publication.root_receipt.leaf_hashes[1:]]
        )
        changed_leaf_receipt["receipt_hash"] = ""
        changed_leaf_result = verify_evidence_transparency_inclusion_proof(
            proof,
            changed_leaf_receipt,
        )
        self.assertFalse(changed_leaf_result.accepted)
        self.assertIn("leaf_digest_changed", changed_leaf_result.failures)

        missing_leaf_receipt = publication.root_receipt.as_dict()
        missing_leaf_receipt["evidence_item_ids"] = tuple(
            item_id
            for item_id in publication.root_receipt.evidence_item_ids
            if item_id != proof.item_id
        )
        missing_leaf_receipt["leaf_hashes"] = publication.root_receipt.leaf_hashes[1:]
        missing_leaf_receipt["leaf_count"] = len(missing_leaf_receipt["leaf_hashes"])
        missing_leaf_receipt["receipt_hash"] = ""
        missing_leaf_result = verify_evidence_transparency_inclusion_proof(
            proof,
            missing_leaf_receipt,
        )
        self.assertFalse(missing_leaf_result.accepted)
        self.assertIn("unknown_evidence_item", missing_leaf_result.failures)

        order_tampered = EvidenceTransparencyInclusionProof(
            proof_version=proof.proof_version,
            item_id=proof.item_id,
            evidence_digest=proof.evidence_digest,
            evidence_kind=proof.evidence_kind,
            leaf_index=proof.leaf_index + 1,
            leaf_hash=proof.leaf_hash,
            proof_path=proof.proof_path,
            root_hash=proof.root_hash,
        )
        order_result = verify_evidence_transparency_inclusion_proof(
            order_tampered,
            publication.root_receipt,
        )
        self.assertFalse(order_result.accepted)
        self.assertIn("proof_order_mismatch", order_result.failures)

    def test_duplicate_item_id_is_rejected_but_duplicate_digest_is_explicitly_allowed(self) -> None:
        duplicate_id_items = [_items()[0], {**_items()[0]}]
        with tempfile.TemporaryDirectory() as tempdir:
            duplicate_id = FileBackedEvidenceTransparencyMerkleLog(
                runtime_root=Path(tempdir) / "duplicate-id",
            ).publish(duplicate_id_items, observed_at=OBSERVED_AT)

        self.assertFalse(duplicate_id.root_receipt.accepted)
        self.assertIn(
            "duplicate_evidence_item_id:final-signoff-receipt",
            duplicate_id.root_receipt.failures,
        )

        duplicate_digest_items = [
            _items()[0],
            {
                "item_id": "same-digest-different-item",
                "evidence_kind": "release_signoff_copy",
                "evidence_digest": _items()[0]["evidence_digest"],
            },
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            duplicate_digest = FileBackedEvidenceTransparencyMerkleLog(
                runtime_root=Path(tempdir) / "duplicate-digest",
            ).publish(duplicate_digest_items, observed_at=OBSERVED_AT)

        self.assertTrue(duplicate_digest.root_receipt.accepted)
        self.assertEqual(duplicate_digest.root_receipt.leaf_count, 2)
        self.assertNotEqual(
            duplicate_digest.root_receipt.leaf_hashes[0],
            duplicate_digest.root_receipt.leaf_hashes[1],
        )


if __name__ == "__main__":
    unittest.main()
