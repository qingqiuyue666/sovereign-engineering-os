"""Acceptance tests for System E2E Acceptance V1."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.system_e2e_acceptance import (
    ZERO_HASH,
    FileBackedSystemE2EAcceptance,
)

OBSERVED_AT = "2026-05-29T00:30:00+00:00"


class SystemE2EAcceptanceV1AcceptanceTests(unittest.TestCase):
    def test_system_e2e_acceptance_is_receipt_backed_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            receipt = FileBackedSystemE2EAcceptance(runtime_root=Path(tempdir)).run(
                observed_at=OBSERVED_AT,
            )

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertTrue(receipt.deterministic_replay_verified)
        self.assertTrue(receipt.final_acceptance_report_signable)
        self.assertFalse(receipt.failures)
        self.assertFalse(receipt.network_accessed)
        self.assertFalse(receipt.provider_called)
        self.assertFalse(receipt.background_daemon_enabled)
        self.assertFalse(receipt.direct_mutation_enabled)
        self.assertNotEqual(receipt.receipt_chain_hash, ZERO_HASH)
        self.assertTrue(all(gate.accepted for gate in receipt.gate_results))
        self.assertIn(
            "corrupt_wal_fail_closed",
            {gate.gate_id for gate in receipt.gate_results},
        )
        self.assertIn(
            "missing_approval_fail_closed",
            {gate.gate_id for gate in receipt.gate_results},
        )


if __name__ == "__main__":
    unittest.main()
