"""
AT-023: Worker / stage lifecycle transition legality.

Constitutional anchors:
- v11 Section 24.1 AT-023
- v11 Section 24.2 INV-018 (worker/stage transition legality)
- Foundation Section 5.1 test #10 (worker lifecycle transition legality)

What this test proves:
  Illegal stage transitions (e.g. CONTEXT -> APPROVAL, skipping
  INFERENCE) must be rejected by the orchestrator. Only legal
  forward transitions along the eight-stage path are admitted.
"""

from __future__ import annotations

import unittest
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.lifecycle.stage_types import (
    Stage,
    IllegalStageTransition,
    is_legal_transition,
    assert_legal_transition,
    ORDERED_PATH,
)
from kernel.lifecycle.signable_path_orchestrator import OrchestratorRejected


class TestWorkerLifecycleTransitions(unittest.TestCase):
    """AT-023 / INV-018: worker/stage transition legality."""

    def test_forward_transitions_legal(self) -> None:
        """Each consecutive pair in the ordered path is a legal transition."""
        for i in range(len(ORDERED_PATH) - 1):
            current = ORDERED_PATH[i]
            nxt = ORDERED_PATH[i + 1]
            self.assertTrue(
                is_legal_transition(current, nxt),
                f"transition {current.name}->{nxt.name} should be legal",
            )

    def test_skip_transition_illegal(self) -> None:
        """Skipping a stage is illegal."""
        self.assertFalse(is_legal_transition(Stage.CONTEXT, Stage.PATCH_PROPOSAL))
        self.assertFalse(is_legal_transition(Stage.CONTEXT, Stage.APPROVAL))
        self.assertFalse(is_legal_transition(Stage.INFERENCE, Stage.REVIEW))

    def test_backward_transition_illegal(self) -> None:
        """Backward transitions are illegal."""
        self.assertFalse(is_legal_transition(Stage.REVIEW, Stage.CONTEXT))
        self.assertFalse(is_legal_transition(Stage.APPROVAL, Stage.INFERENCE))

    def test_abandon_from_any_non_terminal(self) -> None:
        """ABANDONED is reachable from any non-terminal stage."""
        for stage in ORDERED_PATH:
            if stage not in (Stage.SEALED, Stage.ABANDONED):
                self.assertTrue(
                    is_legal_transition(stage, Stage.ABANDONED),
                    f"abandon from {stage.name} should be legal",
                )

    def test_assert_raises_on_illegal(self) -> None:
        """assert_legal_transition must raise IllegalStageTransition."""
        with self.assertRaises(IllegalStageTransition):
            assert_legal_transition(Stage.CONTEXT, Stage.APPROVAL)

    def test_orchestrator_rejects_stage_skip(self) -> None:
        """Orchestrator must reject an out-of-order admission."""
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            # Admit context.
            harness.run_through_stage(task_id, Stage.CONTEXT)
            # Skip inference and try patch proposal.
            with self.assertRaises(OrchestratorRejected):
                harness.orch.admit_patch_proposal(task_id=task_id)
        finally:
            harness.close()

    def test_evidence_to_sealed_is_legal(self) -> None:
        """EVIDENCE -> SEALED must be a legal terminal transition."""
        self.assertTrue(is_legal_transition(Stage.EVIDENCE, Stage.SEALED))

    def test_sealed_to_anything_illegal(self) -> None:
        """SEALED is terminal — no further transitions."""
        for stage in Stage:
            if stage != Stage.SEALED:
                self.assertFalse(
                    is_legal_transition(Stage.SEALED, stage),
                    f"SEALED->{stage.name} should be illegal",
                )


if __name__ == "__main__":
    unittest.main()
