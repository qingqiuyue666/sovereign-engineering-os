"""
AT-018 (double-consume race): concurrent double-consume determinism.

Constitutional anchors:
- v11 Section 22.6 Capability Token Lifecycle Contract
- v11 Section 24.2 INV-012 (single-use token: exactly one winner)
- v11 Section 24.2 INV-013 (admissibility check before effect)
- Foundation Section 4.2 (capability consume concurrency closure)

What this test proves:
  Two consume attempts on the same single-use token resolve
  deterministically with exactly one winner and explicit rejection
  evidence for the loser. In SQLite single-connection mode, this
  serializes naturally; the test verifies the one-winner invariant.
"""

from __future__ import annotations

import unittest
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness


class TestCapabilityDoubleConsumeRace(unittest.TestCase):
    """AT-018 / INV-012: double-consume deterministic one-winner."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_double_consume_one_winner(self) -> None:
        """Two serial consumes: exactly one wins, one loses."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        r1 = self.harness.cap_repo.atomic_consume(token_id)
        r2 = self.harness.cap_repo.atomic_consume(token_id)

        winners = [r1.winner, r2.winner]
        self.assertEqual(winners.count(True), 1, "exactly one winner expected")
        self.assertEqual(winners.count(False), 1, "exactly one loser expected")

    def test_loser_has_explicit_reason(self) -> None:
        """The losing consume must carry an explicit rejection reason."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "invoke_inference", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        self.harness.cap_repo.atomic_consume(token_id)
        loser = self.harness.cap_repo.atomic_consume(token_id)
        self.assertFalse(loser.winner)
        self.assertEqual(loser.reason, "already_consumed")

    def test_triple_consume_still_one_winner(self) -> None:
        """Even three attempts produce exactly one winner."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        results = [
            self.harness.cap_repo.atomic_consume(token_id)
            for _ in range(3)
        ]
        winner_count = sum(1 for r in results if r.winner)
        self.assertEqual(winner_count, 1)


if __name__ == "__main__":
    unittest.main()
