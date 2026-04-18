"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``review_self_summary_rejected`` rejection-path audit record.

When the caller threads the durable ``intent_anchor_records.intent_id``
into ``ReviewService.render_review`` and the C22.14 self-summary policy
rejects the rendering, the ``review_self_summary_rejected`` audit
record must name the same id in both ``artifact_refs`` and ``payload``
so a reviewer reading only that rejection record can recover the
AUDIT-003 / §22.1 linkage without a second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this service performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly (that null-safe branch is already covered
by the existing happy-path tests and is unchanged here).

The mainline phase-1 policy sets ``FORBID_SELF_SUMMARY = False``, so
reaching this rejection branch through the live surface requires
flipping the class attribute for the duration of the call. That is
precisely what ``unittest.mock.patch.object`` is for, and it matches
the injection pattern used by the approval-barrier evaluation-error
parity test (landed in PR #48).
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.lifecycle.stage_types import Stage
from kernel.services.review_service import (
    RenderingProvenance,
    ReviewRejected,
    ReviewService,
)
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestReviewSelfSummaryRejectionNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 rejection-path parity for
    ``review_self_summary_rejected``."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_self_summary_rejection_names_intent_id_when_supplied(self) -> None:
        """With ``FORBID_SELF_SUMMARY`` flipped to True for the duration
        of the call, invoking ``render_review`` with a self-summary
        provenance and a non-empty ``intent_id`` must raise
        ``ReviewRejected`` and emit a ``review_self_summary_rejected``
        audit row whose ``payload`` and ``artifact_refs`` both name the
        supplied ``intent_id`` (and whose prior fields are unchanged)."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.VALIDATION)

        supplied_intent_id = f"intent-{uuid4().hex[:8]}"
        provenance = RenderingProvenance(
            renderer_id="same_worker_renderer",
            renderer_version="v1",
            self_summary_flag=True,
        )

        with patch.object(ReviewService, "FORBID_SELF_SUMMARY", True):
            with self.assertRaises(ReviewRejected):
                self.harness.rev_svc.render_review(
                    task_id=task_id,
                    patch_proposal_id=ids["patch_proposal_id"],
                    validation_receipt_id=ids["validation_receipt_id"],
                    rendering_provenance=provenance,
                    intent_id=supplied_intent_id,
                )

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'review_self_summary_rejected' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], supplied_intent_id)
        self.assertIn(supplied_intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["renderer_id"], provenance.renderer_id)
        self.assertIn(ids["patch_proposal_id"], refs)
        self.assertIn(ids["validation_receipt_id"], refs)


if __name__ == "__main__":
    unittest.main()
