"""
AT-020: Review provenance governance.

Constitutional anchors:
- v11 Section 22.14 Review Surface Governance Contract
- v11 Section 24.1 AT-020
- v11 Section 24.2 INV-015 (review provenance auditable)
- Foundation Section 5.1 test #5 (review provenance governance)

What this test proves:
  A review artifact must carry explicit rendering provenance including
  the self_summary_flag disclosure. If the policy forbids same-worker
  self-summary, the review must be rejected. Phase-1 policy: self-
  summary is admissible but must be flagged.
"""

from __future__ import annotations

import unittest
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.lifecycle.stage_types import Stage


class TestReviewProvenanceGovernance(unittest.TestCase):
    """AT-020 / INV-015: review provenance governance."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_review_carries_rendering_provenance(self) -> None:
        """A review artifact must carry rendering_provenance with
        renderer_id, renderer_version, self_summary_flag."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)
        review = self.harness.rv_repo.fetch(ids["review_artifact_id"])
        self.assertIsNotNone(review)

        provenance = review["rendering_provenance"]
        self.assertIn("renderer_id", provenance)
        self.assertIn("renderer_version", provenance)
        self.assertIn("self_summary_flag", provenance)

    def test_review_has_diff_hash(self) -> None:
        """Review artifact must carry a diff_hash for replay binding."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)
        review = self.harness.rv_repo.fetch(ids["review_artifact_id"])
        self.assertIsNotNone(review["diff_hash"])
        self.assertTrue(review["diff_hash"].startswith("sha256:"))

    def test_review_taint_surfaces_upstream(self) -> None:
        """Review taint_set must surface upstream taint (empty on happy path)."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)
        review = self.harness.rv_repo.fetch(ids["review_artifact_id"])
        # Happy path: no upstream taint, so review taint must be empty.
        self.assertEqual(review.get("taint_set", []), [])

    def test_review_risk_class_present(self) -> None:
        """Review must declare a risk_class."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.REVIEW)
        review = self.harness.rv_repo.fetch(ids["review_artifact_id"])
        self.assertIn(review["risk_class"], ["low", "medium", "high", "critical"])


if __name__ == "__main__":
    unittest.main()
