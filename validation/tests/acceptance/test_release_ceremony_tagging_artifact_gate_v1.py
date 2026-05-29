"""Acceptance tests for Release Ceremony / Tagging Artifact Gate V1."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.release_ceremony_tagging_artifact_gate import (
    ZERO_HASH,
    FileBackedReleaseCeremonyTaggingArtifactGate,
)
from tests.tracer_bullet.test_release_ceremony_tagging_artifact_gate_v1 import (
    OBSERVED_AT,
    _evidence,
)


class ReleaseCeremonyTaggingArtifactGateV1AcceptanceTests(unittest.TestCase):
    def test_release_ceremony_accepts_complete_chain_and_denies_failed_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            accepted = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(_evidence(), observed_at=OBSERVED_AT)

        self.assertTrue(accepted.accepted, accepted.failures)
        self.assertNotEqual(accepted.receipt_hash, ZERO_HASH)
        self.assertFalse(accepted.tag_created)
        self.assertFalse(accepted.tag_pushed)

        evidence = _evidence()
        evidence["policy_decision_receipt"]["allowed"] = False  # type: ignore[index]
        evidence["policy_decision_receipt"]["decision"] = "deny"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as tempdir:
            rejected = FileBackedReleaseCeremonyTaggingArtifactGate(
                runtime_root=tempdir,
                repo_root=Path.cwd(),
            ).prepare(evidence, observed_at=OBSERVED_AT)

        self.assertFalse(rejected.accepted)
        self.assertIn("policy_decision_not_allowed", rejected.failures)


if __name__ == "__main__":
    unittest.main()
