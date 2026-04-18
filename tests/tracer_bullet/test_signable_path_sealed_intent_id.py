"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``signable_path_sealed`` orchestrator terminal audit record.

When ``SignablePathOrchestrator`` fires the terminal
``signable_path_sealed`` record (either via the eight-stage
``admit_evidence`` terminal or the real-fix ``run_real_fix_chain``
terminal), the record must name the durable
``intent_anchor_records.intent_id`` (the one ``_emit_intent_anchor``
minted and that lives on ``state.intent_anchor``) in both
``artifact_refs`` and ``payload`` so a reviewer reading only that
terminal seal record can recover the originating-intent linkage
without a second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this surface performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly.

Driving the eight-stage terminal through the live surface is direct:
running the harness through ``Stage.EVIDENCE`` fires
``admit_evidence`` which transitions to ``Stage.SEALED`` and emits
``signable_path_sealed`` with ``state.intent_anchor.intent_id`` in
scope. No patching required. The real-fix terminal site carries the
same shape by construction; it is covered by the existing
``run_real_fix_chain`` regression tests.
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

from kernel.lifecycle.stage_types import Stage
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestSignablePathSealedNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 terminal-path parity for ``signable_path_sealed``."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_signable_path_sealed_names_intent_id_at_eight_stage_terminal(
        self,
    ) -> None:
        """Running the harness through ``Stage.EVIDENCE`` must emit a
        ``signable_path_sealed`` audit row whose ``payload`` and
        ``artifact_refs`` both name the anchor's ``intent_id`` while
        preserving the prior ``stage`` payload field and the prior
        ``state.artifact_ids`` contribution to ``artifact_refs``."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.EVIDENCE)
        anchor_intent_id = ids["intent_id"]
        replay_anchor_id = ids["replay_anchor_id"]

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'signable_path_sealed' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], anchor_intent_id)
        self.assertIn(anchor_intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["stage"], Stage.SEALED.value)
        # The prior ``list(state.artifact_ids.values())`` contribution
        # is preserved: at the evidence terminal, the replay anchor id
        # is the most-recently-added artifact id on ``state`` and must
        # still appear in refs.
        self.assertIn(replay_anchor_id, refs)


if __name__ == "__main__":
    unittest.main()
