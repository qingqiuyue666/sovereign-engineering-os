"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``illegal_stage_transition_rejected`` rejection-path audit record.

When the orchestrator refuses an out-of-path stage admission, the
``illegal_stage_transition_rejected`` audit record emitted by
``SignablePathOrchestrator._advance`` must name the durable
``intent_anchor_records.intent_id`` (the one ``_emit_intent_anchor``
minted at ``admit_context`` and stored on
``state.intent_anchor``) in both ``artifact_refs`` and ``payload`` so a
reviewer reading only that rejection record can recover the
originating-intent linkage without a second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this surface performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly.

Triggering the rejection branch through the live surface is direct:
after ``admit_context`` establishes state at ``Stage.CONTEXT``, calling
``admit_patch_proposal`` targets ``Stage.PATCH_PROPOSAL`` and skips
``Stage.INFERENCE`` - not in ``LEGAL_TRANSITIONS[Stage.CONTEXT]`` - so
``assert_legal_transition`` raises ``IllegalStageTransition`` and
``_advance`` emits the rejection record before raising
``OrchestratorRejected``. No patching required.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.lifecycle.signable_path_orchestrator import OrchestratorRejected
from kernel.lifecycle.stage_types import Stage
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestIllegalStageTransitionRejectionNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 rejection-path parity for
    ``illegal_stage_transition_rejected``."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_illegal_stage_transition_rejection_names_intent_id(self) -> None:
        """After ``admit_context`` mints the durable intent anchor,
        calling ``admit_patch_proposal`` (which targets
        ``Stage.PATCH_PROPOSAL`` and skips ``Stage.INFERENCE``) must
        raise ``OrchestratorRejected`` and emit an
        ``illegal_stage_transition_rejected`` audit row whose
        ``payload`` and ``artifact_refs`` both name the anchor's
        ``intent_id`` (and whose prior fields are unchanged)."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.CONTEXT)
        anchor_intent_id = ids["intent_id"]

        with self.assertRaises(OrchestratorRejected):
            self.harness.orch.admit_patch_proposal(task_id=task_id)

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'illegal_stage_transition_rejected' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], anchor_intent_id)
        self.assertIn(anchor_intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["from"], Stage.CONTEXT.value)
        self.assertEqual(payload["to"], Stage.PATCH_PROPOSAL.value)
        self.assertIn("reason", payload)


if __name__ == "__main__":
    unittest.main()
