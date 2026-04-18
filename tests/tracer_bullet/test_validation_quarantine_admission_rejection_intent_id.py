"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``validation_quarantine_admission_rejected`` rejection-path audit
record.

When the caller threads the durable ``intent_anchor_records.intent_id``
into ``ValidationService.validate`` and the C22.4 quarantine
admissibility check rejects the proposal, the
``validation_quarantine_admission_rejected`` audit record must name the
same id in both ``artifact_refs`` and ``payload`` so a reviewer reading
only that rejection record can recover the AUDIT-003 / §22.1 linkage
without a second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this service performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly (already covered by the existing happy-path
tests and unchanged here).

The mainline phase-1 quarantine posture (``network_off``,
``host_read_only``, ``isolated_caches``, ``disposable_workspace``,
``secret_scrubbed_env``; ``secret_bearing=False``) passes
``assert_proposal_admissible`` by construction, so reaching the
rejection branch through the live surface requires patching
``assert_proposal_admissible`` for the duration of the call. That
matches the injection pattern used for the approval-barrier
evaluation-error parity test (PR #48) and the review self-summary
rejection parity test (PR #49).
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

from kernel.contracts.quarantine_rules import QuarantineAdmissibilityError
from kernel.lifecycle.stage_types import Stage
from kernel.services.validation_service import ValidationRejected
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestValidationQuarantineAdmissionRejectionNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 rejection-path parity for
    ``validation_quarantine_admission_rejected``."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_quarantine_admission_rejection_names_intent_id_when_supplied(self) -> None:
        """With ``assert_proposal_admissible`` patched to raise
        ``QuarantineAdmissibilityError`` for the duration of the call,
        invoking ``validate`` with a non-empty ``intent_id`` must raise
        ``ValidationRejected`` and emit a
        ``validation_quarantine_admission_rejected`` audit row whose
        ``payload`` and ``artifact_refs`` both name the supplied
        ``intent_id`` (and whose prior fields are unchanged)."""
        task_id = f"task-{uuid4().hex[:8]}"
        ids = self.harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)

        supplied_intent_id = f"intent-{uuid4().hex[:8]}"
        with patch(
            "kernel.services.validation_service.assert_proposal_admissible",
            side_effect=QuarantineAdmissibilityError("injected"),
        ):
            with self.assertRaises(ValidationRejected):
                self.harness.val_svc.validate(
                    task_id=task_id,
                    patch_proposal_id=ids["patch_proposal_id"],
                    intent_id=supplied_intent_id,
                )

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'validation_quarantine_admission_rejected' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], supplied_intent_id)
        self.assertIn(supplied_intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["reason"], "injected")
        self.assertIn(ids["patch_proposal_id"], refs)


if __name__ == "__main__":
    unittest.main()
