"""
AT-016: Patch coherence (phase-1 narrowed: single-file only).

Constitutional anchors:
- v11 Section 22.13 Multi-File Patch Coherence Contract
- v11 Section 24.1 AT-016
- v11 Section 24.2 INV-016 (patch coherence)
- Foundation Section 1 (phase-1 narrowing: single-file text substitution)

What this test proves:
  Phase-1 admits only single-file patches. A multi-file proposal must
  be rejected fail-closed. A single-file proposal must succeed.
"""

from __future__ import annotations

import unittest
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.services.patch_proposal_service import (
    PatchProposalRejected,
    PatchProposalRequest,
    PatchProposalService,
)
from kernel.lifecycle.stage_types import Stage


class TestPatchCoherenceMinimal(unittest.TestCase):
    """AT-016 / INV-016: patch coherence (phase-1 single-file)."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_multi_file_proposal_rejected(self) -> None:
        """A proposal with >1 target file must be rejected."""
        request = PatchProposalRequest(
            target_file_ids=["src/a.py", "src/b.py"],
            patch_body_hash="hash:multi",
            side_effect_class_proposal="none",
            capability_requirements=[],
            manifest_touch_flag=False,
        )
        # Drive to INFERENCE so we can try proposing.
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.INFERENCE)

        with self.assertRaises(PatchProposalRejected):
            self.harness.pp_svc.propose(
                task_id=task_id,
                inference_artifact_id=ids["inference_artifact_id"],
                request=request,
            )

    def test_manifest_touch_rejected(self) -> None:
        """A proposal with manifest_touch_flag=True must be rejected."""
        request = PatchProposalRequest(
            target_file_ids=["src/main.py"],
            patch_body_hash="hash:manifest",
            side_effect_class_proposal="none",
            capability_requirements=[],
            manifest_touch_flag=True,
        )
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.INFERENCE)

        with self.assertRaises(PatchProposalRejected):
            self.harness.pp_svc.propose(
                task_id=task_id,
                inference_artifact_id=ids["inference_artifact_id"],
                request=request,
            )

    def test_single_file_proposal_accepted(self) -> None:
        """A single-file proposal must succeed through the orchestrator."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)
        self.assertIn("patch_proposal_id", ids)
        pp = self.harness.pp_repo.fetch(ids["patch_proposal_id"])
        self.assertIsNotNone(pp)


if __name__ == "__main__":
    unittest.main()
