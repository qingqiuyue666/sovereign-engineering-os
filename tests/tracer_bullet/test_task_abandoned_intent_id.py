"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the ``task_abandoned``
orchestrator terminal audit record.

When ``SignablePathOrchestrator.abandon`` fires the terminal
``task_abandoned`` record, that record must name the durable
``intent_anchor_records.intent_id`` (the one ``_emit_intent_anchor``
minted at ``admit_context`` and stored on ``state.intent_anchor``) in
both ``artifact_refs`` and ``payload`` so a reviewer reading only that
terminal record can recover the originating-intent linkage without a
second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this surface performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly.

Triggering the terminal through the live surface is direct: after
``admit_context`` establishes state and mints the durable anchor,
calling ``abandon`` transitions the task to ``Stage.ABANDONED`` and
emits ``task_abandoned`` with ``state.intent_anchor.intent_id`` in
scope. No patching required.
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


class TestTaskAbandonedNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 terminal-path parity for ``task_abandoned``."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_task_abandoned_names_intent_id(self) -> None:
        """After ``admit_context`` mints the durable intent anchor,
        calling ``abandon`` must emit a ``task_abandoned`` audit row
        whose ``payload`` and ``artifact_refs`` both name the anchor's
        ``intent_id`` while preserving the prior ``reason`` payload
        field and the prior ``state.artifact_ids`` contribution to
        ``artifact_refs``."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.CONTEXT)
        anchor_intent_id = ids["intent_id"]
        context_artifact_id = ids["context_artifact_id"]

        reason = "test-abandon-reason"
        self.harness.orch.abandon(task_id=task_id, reason=reason)

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'task_abandoned' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], anchor_intent_id)
        self.assertIn(anchor_intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["reason"], reason)
        self.assertIn(context_artifact_id, refs)


if __name__ == "__main__":
    unittest.main()
