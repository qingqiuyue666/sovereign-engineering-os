"""
AT-018: Capability token single-use lifecycle.

Constitutional anchors:
- v11 Section 22.6 Capability Token Lifecycle Contract
- v11 Section 24.1 AT-018
- v11 Section 24.2 INV-012 (single-use token consumed once)
- v11 Section 24.2 INV-013 (admissibility check before effect)
- Foundation Section 5.1 test #8 (capability token lifecycle)

What this test proves:
  A single-use capability token can be consumed exactly once. The
  second consumption attempt must fail closed with deterministic
  rejection evidence.
"""

from __future__ import annotations

import unittest
import sys
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.services.capability_service import CapabilityDenied


class TestCapabilitySingleUse(unittest.TestCase):
    """AT-018 / INV-012: single-use token consumed exactly once."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_single_use_consumed_once(self) -> None:
        """First consume succeeds; second must fail."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        # First consume: must succeed.
        result = self.harness.cap_repo.atomic_consume(token_id)
        self.assertTrue(result.winner)

        # Second consume: must fail.
        result2 = self.harness.cap_repo.atomic_consume(token_id)
        self.assertFalse(result2.winner)
        self.assertEqual(result2.reason, "already_consumed")

    def test_expired_token_cannot_be_consumed(self) -> None:
        """An expired token must not be consumable."""
        task_id = f"task-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        token = self.harness.cap_svc.issue_token(
            subject_identity="test",
            capability_name="read_repository_snapshot",
            scope_hash="scope:test",
            issued_at=(now - timedelta(hours=2)).isoformat(),
            expires_at=(now - timedelta(hours=1)).isoformat(),
            single_use=True,
            bound_task_id=task_id,
        )
        result = self.harness.cap_repo.atomic_consume(token["capability_token_id"])
        self.assertFalse(result.winner)

    def test_revoked_token_cannot_be_consumed(self) -> None:
        """A revoked token must not be consumable."""
        task_id = f"task-{uuid4().hex[:8]}"
        token = self.harness.issue_capability(
            "read_repository_snapshot", task_id, single_use=True,
        )
        token_id = token["capability_token_id"]

        # Revoke.
        self.harness.cap_repo.revoke(
            capability_token_id=token_id,
            reason="test_revocation",
        )

        # Consume attempt must fail.
        result = self.harness.cap_repo.atomic_consume(token_id)
        self.assertFalse(result.winner)
        self.assertEqual(result.reason, "revoked")


if __name__ == "__main__":
    unittest.main()
