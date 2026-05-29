"""Acceptance tests for Evidence Transparency / Merkle Inclusion Proof V1."""

from __future__ import annotations

import tempfile
import unittest

from kernel.runtime.evidence_transparency_merkle_proof import (
    ZERO_HASH,
    FileBackedEvidenceTransparencyMerkleLog,
    verify_evidence_transparency_inclusion_proof,
)
from tests.tracer_bullet.test_evidence_transparency_merkle_proof_v1 import (
    OBSERVED_AT,
    _items,
)


class EvidenceTransparencyMerkleProofV1AcceptanceTests(unittest.TestCase):
    def test_transparency_root_and_inclusion_proof_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            publication = FileBackedEvidenceTransparencyMerkleLog(
                runtime_root=tempdir,
            ).publish(_items(), observed_at=OBSERVED_AT)

        self.assertTrue(publication.root_receipt.accepted)
        self.assertNotEqual(publication.root_receipt.root_hash, ZERO_HASH)
        self.assertEqual(
            len(publication.inclusion_proofs),
            publication.root_receipt.leaf_count,
        )
        for proof in publication.inclusion_proofs:
            verification = verify_evidence_transparency_inclusion_proof(
                proof,
                publication.root_receipt,
            )
            self.assertTrue(verification.accepted, verification.failures)


if __name__ == "__main__":
    unittest.main()
