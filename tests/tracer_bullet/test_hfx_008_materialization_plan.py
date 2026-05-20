"""Tracer bullet tests for the HFX_008 materialization plan."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.hfx_materialization_plans import (
    HFX_008_TARGET_NAMES,
    HFX_008_UPSTREAM_NAMES,
    build_hfx_008_materialization_plan,
    evaluate_hfx_008_materialization,
)
from kernel.os_engine.materialization import MaterializationStatus


class HFX008MaterializationPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "proof"
        self.workspace.mkdir()
        self.hip = self.root / "HFX_008.hip"
        self.hip.write_text("placeholder hip metadata for tests", encoding="utf-8")
        self.plan = build_hfx_008_materialization_plan(
            repo_root=Path.cwd(),
            hfx_008_hip_path=self.hip,
            proof_workspace=self.workspace,
            hython_executable_metadata="/opt/hfs/bin/hython",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _materialized_summary(self) -> None:
        (self.workspace / "HFX_008_materialization_summary.json").write_text("{}", encoding="utf-8")

    def test_plan_exists_with_required_targets_upstreams_and_deterministic_hash(self) -> None:
        self.assertEqual(self.plan.plan_id, "HFX_008_materialization_plan_v1")
        self.assertTrue(set(HFX_008_TARGET_NAMES).issubset({target.name for target in self.plan.target_artifacts}))
        self.assertTrue(set(HFX_008_UPSTREAM_NAMES).issubset({upstream.name for upstream in self.plan.upstream_inputs}))
        again = build_hfx_008_materialization_plan(
            repo_root=Path.cwd(),
            hfx_008_hip_path=self.hip,
            proof_workspace=self.workspace,
            hython_executable_metadata="/opt/hfs/bin/hython",
        )
        self.assertEqual(self.plan.plan_hash, again.plan_hash)

    def test_topology_failure_and_placeholder_guide_block_proof_or_final_claim(self) -> None:
        self._materialized_summary()
        topology = evaluate_hfx_008_materialization(self.plan, topology_audit_passed=False, human_review_approved=True)
        self.assertEqual(topology.status, MaterializationStatus.BLOCKED_VALIDATION_FAILED.value)
        placeholder = evaluate_hfx_008_materialization(
            self.plan,
            classification="placeholder guide",
            human_review_approved=True,
        )
        self.assertEqual(placeholder.status, MaterializationStatus.BLOCKED_PLACEHOLDER_GUIDE.value)
        self.assertFalse(placeholder.final_claim_allowed)

    def test_missing_visual_proof_and_human_review_missing_block_final_claim(self) -> None:
        self._materialized_summary()
        visual = evaluate_hfx_008_materialization(self.plan, visual_frame_present=False, human_review_approved=True)
        self.assertEqual(visual.status, MaterializationStatus.BLOCKED_VISUAL_PROOF_MISSING.value)
        review = evaluate_hfx_008_materialization(self.plan, human_review_approved=False)
        self.assertEqual(review.status, MaterializationStatus.BLOCKED_HUMAN_REVIEW_REQUIRED.value)
        self.assertFalse(review.final_claim_allowed)

    def test_missing_resource_and_render_node_block(self) -> None:
        self._materialized_summary()
        resource = evaluate_hfx_008_materialization(
            self.plan,
            resource_package_required=True,
            resource_package_present=False,
            human_review_approved=True,
        )
        self.assertEqual(resource.status, MaterializationStatus.BLOCKED_RESOURCE_MISSING.value)
        render_node = evaluate_hfx_008_materialization(
            self.plan,
            render_node_present=False,
            human_review_approved=True,
        )
        self.assertEqual(render_node.status, MaterializationStatus.BLOCKED_VALIDATION_FAILED.value)

    def test_approved_review_unlocks_only_when_artifact_validation_passed(self) -> None:
        self._materialized_summary()
        failed = evaluate_hfx_008_materialization(
            self.plan,
            artifact_validation_passed=False,
            human_review_approved=True,
        )
        self.assertEqual(failed.status, MaterializationStatus.BLOCKED_VALIDATION_FAILED.value)
        self.assertFalse(failed.final_claim_allowed)
        passed = evaluate_hfx_008_materialization(self.plan, human_review_approved=True)
        self.assertEqual(passed.status, MaterializationStatus.MATERIALIZED_VALID.value)
        self.assertTrue(passed.final_claim_allowed)

    def test_module_does_not_launch_houdini_or_subprocesses(self) -> None:
        source = (Path.cwd() / "kernel" / "os_engine" / "hfx_materialization_plans.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("Popen", source)


if __name__ == "__main__":
    unittest.main()
