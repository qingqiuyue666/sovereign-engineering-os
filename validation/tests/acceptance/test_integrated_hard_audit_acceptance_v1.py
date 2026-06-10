"""Acceptance tests for Integrated Hard Audit Acceptance V1."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.integrated_hard_audit_acceptance import (
    ZERO_HASH,
    FileBackedIntegratedHardAuditAcceptance,
)
from tests.tracer_bullet.test_integrated_hard_audit_acceptance_v1 import (
    OBSERVED_AT,
    _audit_evidence,
)


class IntegratedHardAuditAcceptanceV1AcceptanceTests(unittest.TestCase):
    def test_integrated_hard_audit_accepts_complete_chain_and_rejects_corrupted_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            accepted = FileBackedIntegratedHardAuditAcceptance(
                runtime_root=root / "audit",
                repo_root=Path.cwd(),
            ).verify(_audit_evidence(root), observed_at=OBSERVED_AT)

        self.assertTrue(accepted.accepted, accepted.failures)
        self.assertNotEqual(accepted.receipt_hash, ZERO_HASH)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            evidence = _audit_evidence(root)
            proof = dict(evidence["transparency_inclusion_proof"])  # type: ignore[arg-type]
            proof["proof_path"] = [("right", "sha256:" + ("1" * 64))]
            proof["proof_hash"] = ""
            evidence["transparency_inclusion_proof"] = proof
            rejected = FileBackedIntegratedHardAuditAcceptance(
                runtime_root=root / "audit",
                repo_root=Path.cwd(),
            ).verify(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(rejected.accepted)
        self.assertIn("corrupted_transparency_proof", rejected.failures)


if __name__ == "__main__":
    unittest.main()
