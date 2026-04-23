"""
AT-024: Taint propagation durability.

Constitutional anchors:
- v11 Section 22.11 Taint Propagation Graph Contract
- v11 Section 24.1 AT-024
- v11 Section 24.2 INV-019 (taint propagation auditable)
- Foundation Section 5.1 test #9 (taint transition durability)

What this test proves:
  Taint transitions are durably recorded via append-only TaintRecord
  emission. Once a taint record is inserted, it cannot be updated or
  deleted at the SQL layer.
"""

from __future__ import annotations

import json
import unittest
import sqlite3
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.lifecycle.stage_types import Stage
from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import TaintRepository
from kernel.version.version_tuple import compose_version_tuple_hash
from validation.quarantine.runner_adapter import QuarantineRun, QuarantineState
from validation.tests.acceptance.conftest import AcceptanceHarness


class TestTaintPropagation(unittest.TestCase):
    """AT-024 / INV-019: taint propagation is durable and append-only."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.taint_repo = TaintRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_taint_record_insertable(self) -> None:
        """A taint record can be inserted and read back."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="ctx-test-123",
            taint_class="quarantine_breach_suspect",
            taint_state="tainted",
            source_ref="at-024-test",
        )
        row = self.conn.execute(
            "SELECT * FROM taint_records WHERE taint_record_id = ?;",
            (taint_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["taint_class"], "quarantine_breach_suspect")
        self.assertEqual(row["taint_state"], "tainted")

    def test_taint_records_queryable_by_subject(self) -> None:
        """TaintRepository exposes deterministic subject-scoped reads."""
        first_id = "taint-subject-a"
        second_id = "taint-subject-b"
        self.taint_repo.append(
            taint_record_id=second_id,
            subject_id="vr-subject",
            taint_class="policy_degraded",
            taint_state="downgraded",
            source_ref="at-024-query-b",
        )
        self.taint_repo.append(
            taint_record_id=first_id,
            subject_id="vr-subject",
            taint_class="quarantine_breach_suspect",
            taint_state="tainted",
            source_ref="at-024-query-a",
        )
        self.taint_repo.append(
            taint_record_id="taint-other-subject",
            subject_id="vr-other",
            taint_class="policy_degraded",
            taint_state="downgraded",
            source_ref="at-024-query-other",
        )

        rows = self.taint_repo.list_for_subject("vr-subject")

        self.assertEqual(
            [row["taint_record_id"] for row in rows],
            [first_id, second_id],
        )
        self.assertEqual({row["subject_id"] for row in rows}, {"vr-subject"})

    def test_validation_emits_quarantine_classification_taint_records(self) -> None:
        """ValidationService must durably emit new quarantine taints."""
        cases = (
            (
                QuarantineRun(
                    quarantine_run_id=f"qr-{uuid4().hex}",
                    state=QuarantineState.EXITED_CLEAN,
                    entered_at="2026-04-22T00:00:00+00:00",
                    exited_at="2026-04-22T00:00:01+00:00",
                    host_pollution_suspected=False,
                    workspace_preserved_for_forensics=False,
                    env_scrub_violations=("HOME=/real/home",),
                    network_attempts=(),
                ),
                "policy_degraded",
                "downgraded",
            ),
            (
                QuarantineRun(
                    quarantine_run_id=f"qr-{uuid4().hex}",
                    state=QuarantineState.EXITED_TAINTED,
                    entered_at="2026-04-22T00:00:00+00:00",
                    exited_at="2026-04-22T00:00:01+00:00",
                    host_pollution_suspected=True,
                    workspace_preserved_for_forensics=True,
                    env_scrub_violations=(),
                    network_attempts=(),
                ),
                "quarantine_breach_suspect",
                "tainted",
            ),
        )
        for run, expected_class, expected_state in cases:
            with self.subTest(expected_class=expected_class):
                harness = AcceptanceHarness()
                try:
                    task_id = f"task-{uuid4().hex[:8]}"
                    ids = harness.run_through_stage(task_id, Stage.PATCH_PROPOSAL)

                    receipt_id = harness.val_svc.validate(
                        task_id=task_id,
                        patch_proposal_id=ids["patch_proposal_id"],
                        run=run,
                    )

                    receipt = harness.vr_repo.fetch(receipt_id)
                    self.assertIsNotNone(receipt)
                    self.assertIn(expected_class, receipt["taint_set"])

                    rows = harness.conn.execute(
                        "SELECT subject_id, taint_class, taint_state, source_ref "
                        "FROM taint_records WHERE subject_id = ?;",
                        (receipt_id,),
                    ).fetchall()
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["subject_id"], receipt_id)
                    self.assertEqual(rows[0]["taint_class"], expected_class)
                    self.assertEqual(rows[0]["taint_state"], expected_state)
                    self.assertEqual(
                        rows[0]["source_ref"],
                        f"quarantine_run:{run.quarantine_run_id}",
                    )
                finally:
                    harness.close()

    def test_validation_does_not_reemit_upstream_proposal_taints(self) -> None:
        """Only new quarantine classification taints get durable records."""
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            patch_id = f"pp-{uuid4().hex}"
            harness.pp_repo.insert(
                {
                    "patch_proposal_id": patch_id,
                    "task_id": task_id,
                    "root_revision_id": "rev-genesis-000",
                    "inference_artifact_id": f"inf-{uuid4().hex}",
                    "target_file_ids": ["src/main.py"],
                    "patch_group_hash": "sha256:" + "a" * 64,
                    "side_effect_class_proposal": "local_text_substitution",
                    "capability_requirements": [],
                    "taint_set": ["untrusted_text"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "version_tuple_hash": compose_version_tuple_hash(),
                }
            )
            clean_run = QuarantineRun(
                quarantine_run_id=f"qr-{uuid4().hex}",
                state=QuarantineState.EXITED_CLEAN,
                entered_at="2026-04-22T00:00:00+00:00",
                exited_at="2026-04-22T00:00:01+00:00",
                host_pollution_suspected=False,
                workspace_preserved_for_forensics=False,
                env_scrub_violations=(),
                network_attempts=(),
            )

            receipt_id = harness.val_svc.validate(
                task_id=task_id,
                patch_proposal_id=patch_id,
                run=clean_run,
            )

            receipt = harness.vr_repo.fetch(receipt_id)
            self.assertIsNotNone(receipt)
            self.assertIn("untrusted_text", receipt["taint_set"])
            rows = harness.conn.execute(
                "SELECT * FROM taint_records WHERE subject_id = ?;",
                (receipt_id,),
            ).fetchall()
            self.assertEqual(rows, [])
        finally:
            harness.close()

    def test_evidence_closure_binds_validation_taint_record_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries durable validation taints."""
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            ids = harness.run_through_stage(task_id, Stage.VALIDATION)
            receipt_id = ids["validation_receipt_id"]
            taint_record_id = f"taint-{uuid4().hex}"
            harness.taint_repo.append(
                taint_record_id=taint_record_id,
                subject_id=receipt_id,
                taint_class="policy_degraded",
                taint_state="downgraded",
                source_ref="at-024-evidence-visibility",
            )

            taint_rows = harness.taint_repo.list_for_subject(receipt_id)
            self.assertEqual(len(taint_rows), 1)
            self.assertEqual(taint_rows[0]["taint_record_id"], taint_record_id)

            cap_review = harness.issue_capability("render_review", task_id)
            harness.orch.admit_review(
                task_id=task_id,
                capability_token=cap_review,
            )
            cap_approval = harness.issue_capability("grant_approval", task_id)
            harness.orch.admit_approval(
                task_id=task_id,
                capability_token=cap_approval,
            )
            cap_seal = harness.issue_capability("seal_revision", task_id)
            harness.orch.admit_revision_seal(
                task_id=task_id,
                capability_token=cap_seal,
            )
            replay_anchor_id = harness.orch.admit_evidence(task_id=task_id)
            anchor = harness.ra_repo.fetch(replay_anchor_id)
            self.assertIsNotNone(anchor)
            self.assertIn(taint_record_id, anchor["required_artifact_ids"])

            closure_row = harness.conn.execute(
                "SELECT payload_json FROM audit_records "
                "WHERE task_id = ? AND record_type = 'evidence_closure' "
                "AND replay_anchor_id = ?;",
                (task_id, replay_anchor_id),
            ).fetchone()
            self.assertIsNotNone(closure_row)
            payload = json.loads(closure_row["payload_json"])
            self.assertIn(taint_record_id, payload["required_artifact_ids"])
            self.assertNotIn("taint_record_ids", payload)
        finally:
            harness.close()

    def test_taint_record_append_only_no_update(self) -> None:
        """INV-022: taint records cannot be updated in place."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="ctx-test-456",
            taint_class="policy_degraded",
            taint_state="suspected",
            source_ref="at-024-update-test",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "UPDATE taint_records SET taint_state = 'clean' "
                "WHERE taint_record_id = ?;",
                (taint_id,),
            )

    def test_taint_record_append_only_no_delete(self) -> None:
        """INV-022: taint records cannot be deleted."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="ctx-test-789",
            taint_class="untrusted_text",
            taint_state="tainted",
            source_ref="at-024-delete-test",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "DELETE FROM taint_records WHERE taint_record_id = ?;",
                (taint_id,),
            )

    def test_taint_escalation_requires_new_record(self) -> None:
        """Clearing taint requires inserting a new record, not updating."""
        # Insert initial taint.
        taint_id_1 = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id_1,
            subject_id="ctx-escalation",
            taint_class="quarantine_breach_suspect",
            taint_state="tainted",
            source_ref="escalation-source",
        )

        # "Clear" by inserting a new record with cleared state.
        taint_id_2 = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id_2,
            subject_id="ctx-escalation",
            taint_class="quarantine_breach_suspect",
            taint_state="cleared_by_policy",
            source_ref="clearing-source",
            cleared_at=datetime.now(timezone.utc).isoformat(),
            clearing_identity="operator:admin",
            clearing_reason="manual investigation confirmed clean",
        )

        # Both records must exist.
        rows = self.conn.execute(
            "SELECT * FROM taint_records WHERE subject_id = ? ORDER BY created_at;",
            ("ctx-escalation",),
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["taint_state"], "tainted")
        self.assertEqual(rows[1]["taint_state"], "cleared_by_policy")


if __name__ == "__main__":
    unittest.main()
