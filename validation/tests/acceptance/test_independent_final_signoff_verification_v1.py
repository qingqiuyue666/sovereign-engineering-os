"""Acceptance tests for Independent Final Signoff Verification Harness V1."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.independent_final_signoff_verification import (
    ZERO_HASH,
    FileBackedIndependentFinalSignoffVerification,
)
from tests.tracer_bullet.test_independent_final_signoff_verification_v1 import (
    MAIN_HEAD,
    OBSERVED_AT,
    _create_signoff_artifacts,
    _verification_evidence,
)


class IndependentFinalSignoffVerificationV1AcceptanceTests(unittest.TestCase):
    def test_independent_verification_accepts_complete_chain_and_rejects_bad_head(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            accepted = FileBackedIndependentFinalSignoffVerification(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).verify(_verification_evidence(root), observed_at=OBSERVED_AT)

        self.assertTrue(accepted.accepted, accepted.failures)
        self.assertEqual(accepted.current_repo_head, MAIN_HEAD)
        self.assertNotEqual(accepted.receipt_hash, ZERO_HASH)
        self.assertNotEqual(accepted.wal_record_hash, ZERO_HASH)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _create_signoff_artifacts(root)
            evidence = _verification_evidence(root)
            evidence["current_repo_head"] = "1" * 40
            rejected = FileBackedIndependentFinalSignoffVerification(
                runtime_root=root,
                repo_root=Path.cwd(),
            ).verify(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(rejected.accepted)
        self.assertIn("main_head_mismatch", rejected.failures)


if __name__ == "__main__":
    unittest.main()
