"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``inference_artifact_created`` service-level audit record.

When the orchestrator threads the durable
``intent_anchor_records.intent_id`` into
``InferenceService.run_inference`` (as ``admit_inference`` does from
``state.intent_anchor.intent_id``), the ``inference_artifact_created``
audit record must name the same id in both ``artifact_refs`` and
``payload`` so a reviewer reading only that record can recover the
AUDIT-003 / §22.1 linkage without a second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this service performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly.

The orchestrator drives ``admit_inference`` as a normal stage
admission; no patching is required. Running the harness through
``Stage.INFERENCE`` is sufficient.
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


class TestInferenceArtifactCreatedNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 happy-path parity for ``inference_artifact_created``."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_inference_artifact_created_names_intent_id_when_threaded(self) -> None:
        """Running the harness through ``Stage.INFERENCE`` must emit an
        ``inference_artifact_created`` audit row whose ``payload`` and
        ``artifact_refs`` both name the anchor's ``intent_id`` (threaded
        by ``admit_inference`` from ``state.intent_anchor.intent_id``),
        while preserving the prior ``worker_profile`` / ``model_route_id``
        / ``policy`` payload fields and the prior
        ``[inference_artifact_id, context_artifact_id]`` refs
        contribution."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.INFERENCE)
        anchor_intent_id = ids["intent_id"]
        inference_artifact_id = ids["inference_artifact_id"]
        context_artifact_id = ids["context_artifact_id"]

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'inference_artifact_created' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], anchor_intent_id)
        self.assertIn(anchor_intent_id, refs)
        # Prior fields preserved.
        self.assertIn("worker_profile", payload)
        self.assertIn("model_route_id", payload)
        self.assertIn("policy", payload)
        self.assertIn(inference_artifact_id, refs)
        self.assertIn(context_artifact_id, refs)


if __name__ == "__main__":
    unittest.main()
