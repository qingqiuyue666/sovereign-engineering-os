"""
AT-007: WAL mid-segment halt classification.

Constitutional anchors:
- v11 Section 22.1 WAL Durability and Recovery Contract
- v11 Section 22.2 Seal Transaction Ordering Contract
- v11 Section 24.1 AT-007
- v11 Section 24.2 INV-004 / INV-005
- Foundation Section 5.1 test #4 (seal durability ordering crash-window)

What this test proves:
  A crash that interrupts the nine-step seal ordering mid-sequence
  must not leave a pre-durable sealed revision visible. The
  seal-ordering enforcement must detect incomplete step sequences.
"""

from __future__ import annotations

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.contracts.seal_ordering import (
    SealStep,
    SealExecutionLog,
    SealOrderingViolation,
    SealPreconditions,
    SEAL_STEP_ORDER,
)


class TestWalMidsegmentHalt(unittest.TestCase):
    """AT-007: mid-segment halt classification."""

    def test_incomplete_seal_step_sequence_detected(self) -> None:
        """ensure_complete must raise if not all 9 steps were recorded."""
        log = SealExecutionLog()
        # Record only the first 3 steps.
        log.record(SealStep.PREPARE_METADATA)
        log.record(SealStep.WRITE_PENDING_PAYLOAD)
        log.record(SealStep.PERSIST_SNAPSHOT_ROOT)
        with self.assertRaises(SealOrderingViolation):
            log.ensure_complete()

    def test_out_of_order_step_rejected(self) -> None:
        """Steps must proceed in exact canonical order."""
        log = SealExecutionLog()
        log.record(SealStep.PREPARE_METADATA)
        # Skip WRITE_PENDING_PAYLOAD and try PERSIST_SNAPSHOT_ROOT.
        with self.assertRaises(SealOrderingViolation):
            log.record(SealStep.PERSIST_SNAPSHOT_ROOT)

    def test_complete_seal_step_sequence(self) -> None:
        """All 9 steps in order must pass ensure_complete."""
        log = SealExecutionLog()
        for step in SEAL_STEP_ORDER:
            log.record(step)
        log.ensure_complete()  # Should not raise.

    def test_preconditions_must_be_satisfied(self) -> None:
        """Seal preconditions must be asserted before starting."""
        preconditions = SealPreconditions(
            intent_executable=True,
            current_root_matches_validated_root=True,
            required_receipts_valid=True,
            approval_valid_and_not_expired=True,
            barrier_checks_passed=False,  # Not yet passed.
        )
        with self.assertRaises(SealOrderingViolation):
            preconditions.assert_satisfied()

    def test_all_preconditions_satisfied(self) -> None:
        """All preconditions True must pass."""
        preconditions = SealPreconditions(
            intent_executable=True,
            current_root_matches_validated_root=True,
            required_receipts_valid=True,
            approval_valid_and_not_expired=True,
            barrier_checks_passed=True,
        )
        preconditions.assert_satisfied()  # Should not raise.

    def test_seal_step_order_has_nine_steps(self) -> None:
        """The canonical seal order must have exactly 9 steps."""
        self.assertEqual(len(SEAL_STEP_ORDER), 9)


if __name__ == "__main__":
    unittest.main()
