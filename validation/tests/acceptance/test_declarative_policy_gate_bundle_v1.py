"""Acceptance tests for Declarative Policy Gate Bundle V1."""

from __future__ import annotations

import tempfile
import unittest

from kernel.runtime.declarative_policy_gate_bundle import (
    ZERO_HASH,
    FileBackedDeclarativePolicyGateBundle,
)
from tests.tracer_bullet.test_declarative_policy_gate_bundle_v1 import (
    OBSERVED_AT,
    _evidence,
    _policy_bundle,
)


class DeclarativePolicyGateBundleV1AcceptanceTests(unittest.TestCase):
    def test_policy_allows_complete_evidence_and_denies_missing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            accepted = FileBackedDeclarativePolicyGateBundle(
                runtime_root=tempdir,
            ).evaluate(_policy_bundle(), _evidence(), observed_at=OBSERVED_AT)

        self.assertTrue(accepted.allowed, accepted.failures)
        self.assertEqual(accepted.decision, "allow")
        self.assertNotEqual(accepted.receipt_hash, ZERO_HASH)

        with tempfile.TemporaryDirectory() as tempdir:
            evidence = _evidence()
            del evidence["transparency"]
            denied = FileBackedDeclarativePolicyGateBundle(
                runtime_root=tempdir,
            ).evaluate(_policy_bundle(), evidence, observed_at=OBSERVED_AT)

        self.assertFalse(denied.allowed)
        self.assertEqual(denied.decision, "deny")
        self.assertIn("transparency-root-bound", denied.failed_rule_ids)


if __name__ == "__main__":
    unittest.main()
