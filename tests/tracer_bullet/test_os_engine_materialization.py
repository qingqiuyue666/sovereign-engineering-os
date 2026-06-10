"""Tracer bullet tests for asset-centric materialization decisions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.materialization import (
    MaterializationPlan,
    MaterializationStatus,
    TargetArtifact,
    UpstreamInput,
    ValidationResult,
    compute_freshness_hash,
    decide_materialization,
)
from kernel.os_engine.sqlite_artifact_store import sha256_file


class OSEngineMaterializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.upstream = self.root / "input.txt"
        self.upstream.write_text("v1", encoding="utf-8")
        self.target = self.root / "target.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _plan(self, *, review: bool = False, expected_sha256: str | None = None, classification: str = "asset") -> MaterializationPlan:
        return MaterializationPlan(
            plan_id="plan_materialization",
            target=TargetArtifact(
                artifact_id="artifact_target",
                name="target",
                artifact_type="materialization_summary",
                local_path=str(self.target),
                expected_sha256=expected_sha256,
                human_review_required=review,
                classification=classification,
            ),
            upstream_inputs=(UpstreamInput(name="upstream", local_path=str(self.upstream)),),
        )

    def test_missing_target_requires_materialization(self) -> None:
        decision = decide_materialization(self._plan())
        self.assertEqual(decision.status, MaterializationStatus.MATERIALIZATION_REQUIRED.value)
        self.assertTrue(decision.materialization_required)
        self.assertFalse(decision.final_claim_allowed)

    def test_changed_upstream_marks_stale_and_freshness_hash_is_deterministic(self) -> None:
        self.target.write_text("{}", encoding="utf-8")
        plan = self._plan()
        before = compute_freshness_hash(plan.upstream_inputs)
        self.assertEqual(before, compute_freshness_hash(plan.upstream_inputs))
        self.upstream.write_text("v2", encoding="utf-8")
        decision = decide_materialization(plan, previous_freshness_hash=before)
        self.assertEqual(decision.status, MaterializationStatus.MATERIALIZED_STALE.value)

    def test_checksum_mismatch_and_validation_failure_block(self) -> None:
        self.target.write_text("{}", encoding="utf-8")
        mismatch = decide_materialization(self._plan(expected_sha256="0" * 64))
        self.assertEqual(mismatch.status, MaterializationStatus.BLOCKED_VALIDATION_FAILED.value)
        valid_sha = sha256_file(self.target)
        failed = decide_materialization(
            self._plan(expected_sha256=valid_sha),
            validation=ValidationResult(passed=False, message="schema invalid"),
        )
        self.assertEqual(failed.status, MaterializationStatus.BLOCKED_VALIDATION_FAILED.value)

    def test_human_review_blocks_until_approved(self) -> None:
        self.target.write_text("{}", encoding="utf-8")
        plan = self._plan(review=True, expected_sha256=sha256_file(self.target))
        blocked = decide_materialization(plan)
        self.assertEqual(blocked.status, MaterializationStatus.BLOCKED_HUMAN_REVIEW_REQUIRED.value)
        approved = decide_materialization(plan, human_review_approved=True)
        self.assertEqual(approved.status, MaterializationStatus.MATERIALIZED_VALID.value)
        self.assertTrue(approved.final_claim_allowed)

    def test_placeholder_resource_and_visual_proof_gates_block_final_claim(self) -> None:
        self.target.write_text("{}", encoding="utf-8")
        self.assertEqual(
            decide_materialization(self._plan(classification="placeholder guide")).status,
            MaterializationStatus.BLOCKED_PLACEHOLDER_GUIDE.value,
        )
        self.assertEqual(
            decide_materialization(self._plan(), validation=ValidationResult(passed=True, resource_missing=True)).status,
            MaterializationStatus.BLOCKED_RESOURCE_MISSING.value,
        )
        self.assertEqual(
            decide_materialization(self._plan(), validation=ValidationResult(passed=True, visual_proof_missing=True)).status,
            MaterializationStatus.BLOCKED_VISUAL_PROOF_MISSING.value,
        )


if __name__ == "__main__":
    unittest.main()
