"""Tracer bullet tests for durable human review gating."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import OSDatabase, UnsafePayloadError
from kernel.os_engine.human_review_gate import HumanReviewGate, HumanReviewGateError
from kernel.os_engine.materialization import MaterializationPlan, TargetArtifact, UpstreamInput, decide_materialization


class OSEngineHumanReviewGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.gate = HumanReviewGate(OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_review_request_creates_durable_record(self) -> None:
        review = self.gate.request_review(job_id="job_1", artifact_id="artifact_1", reason="visual proof")
        self.assertEqual(review.decision, "pending")
        self.assertEqual(self.gate.get_review(review.review_id).content_hash, review.content_hash)  # type: ignore[union-attr]

    def test_approve_and_reject_paths_validate_required_fields(self) -> None:
        approve = self.gate.request_review(job_id="job_1", artifact_id="artifact_1", reason="visual proof")
        with self.assertRaises(HumanReviewGateError):
            self.gate.approve_review(review_id=approve.review_id, reviewer="")
        approved = self.gate.approve_review(review_id=approve.review_id, reviewer="operator", reason="looks valid")
        self.assertEqual(approved.decision, "approved")

        reject = self.gate.request_review(job_id="job_2", artifact_id="artifact_2", reason="visual proof")
        with self.assertRaises(HumanReviewGateError):
            self.gate.reject_review(review_id=reject.review_id, reviewer="operator", reason="")
        rejected = self.gate.reject_review(review_id=reject.review_id, reviewer="operator", reason="bad frame")
        self.assertEqual(rejected.decision, "rejected")

    def test_double_decision_and_secret_fields_are_rejected(self) -> None:
        review = self.gate.request_review(job_id="job_1", artifact_id="artifact_1", reason="visual proof")
        self.gate.approve_review(review_id=review.review_id, reviewer="operator", reason="ok")
        with self.assertRaises(HumanReviewGateError):
            self.gate.reject_review(review_id=review.review_id, reviewer="operator", reason="changed mind")
        with self.assertRaises(UnsafePayloadError):
            self.gate.request_review(job_id="job_secret", artifact_id="artifact_1", reason="Bearer abcdefghijklmnopqrstuvwxyz")

    def test_review_gates_materialization_final_claim(self) -> None:
        upstream = self.root / "input.txt"
        target = self.root / "target.json"
        upstream.write_text("in", encoding="utf-8")
        target.write_text("{}", encoding="utf-8")
        plan = MaterializationPlan(
            plan_id="reviewed_plan",
            target=TargetArtifact(
                artifact_id="artifact_1",
                name="target",
                artifact_type="materialization_summary",
                local_path=str(target),
                human_review_required=True,
            ),
            upstream_inputs=(UpstreamInput(name="upstream", local_path=str(upstream)),),
        )
        self.assertFalse(decide_materialization(plan).final_claim_allowed)
        review = self.gate.request_review(job_id="job_1", artifact_id="artifact_1", reason="visual proof")
        self.gate.approve_review(review_id=review.review_id, reviewer="operator", reason="ok")
        decision = decide_materialization(
            plan,
            human_review_approved=self.gate.final_claim_allowed(job_id="job_1", artifact_id="artifact_1"),
        )
        self.assertTrue(decision.final_claim_allowed)

    def test_db_reopen_preserves_review(self) -> None:
        review = self.gate.request_review(job_id="job_1", artifact_id="artifact_1", reason="visual proof")
        reopened = HumanReviewGate(OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3"))
        self.assertEqual(reopened.get_review(review.review_id).review_id, review.review_id)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
