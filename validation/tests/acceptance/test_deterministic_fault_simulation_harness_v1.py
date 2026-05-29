"""Acceptance tests for Deterministic Fault Simulation Harness V1."""

from __future__ import annotations

import tempfile
import unittest

from kernel.runtime.deterministic_fault_simulation_harness import (
    ZERO_HASH,
    FileBackedDeterministicFaultSimulationHarness,
)
from tests.tracer_bullet.test_deterministic_fault_simulation_harness_v1 import (
    OBSERVED_AT,
    _scenario,
)


class DeterministicFaultSimulationHarnessV1AcceptanceTests(unittest.TestCase):
    def test_fault_simulation_accepts_safe_recovery_and_rejects_unsafe_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            accepted = FileBackedDeterministicFaultSimulationHarness(
                runtime_root=tempdir,
            ).simulate(_scenario(), observed_at=OBSERVED_AT)

        self.assertTrue(accepted.accepted, accepted.failures)
        self.assertNotEqual(accepted.report_hash, ZERO_HASH)

        scenario = _scenario()
        scenario["faults"] = [
            {
                "fault_id": "unsafe",
                "fault_type": "watchdog_timeout",
                "target": "watchdog",
                "force_unsafe_recovery": True,
            }
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            rejected = FileBackedDeterministicFaultSimulationHarness(
                runtime_root=tempdir,
            ).simulate(scenario, observed_at=OBSERVED_AT)

        self.assertFalse(rejected.accepted)
        self.assertIn("unsafe_recovery:unsafe", rejected.failures)


if __name__ == "__main__":
    unittest.main()
