"""
Runtime ingress schema validation for previously-descriptive artifact families.

Constitutional anchors:
- v11 §23.14 AuditRecord
- v11 §23.15 FailureBundle
- v11 §23.17 TaintRecord
- v11 §23.19 DriftEventRecord
- foundation §3.4 (runtime enforcement: ingress + pre-persist)

Proves:
- `AppendOnlyLedger.append` validates candidate AuditRecord shape before
  persist and raises `LedgerViolation` on violations.
- `DriftEventRecordRepository.insert` validates before persist and raises
  `SchemaValidationError`.
- `FailureBundleRepository.append` validates before persist and raises
  `SchemaValidationError`.
- `TaintRepository.append` validates before persist and raises
  `SchemaValidationError`.
- The happy-path valid shapes still succeed and persist a single row.
"""

from __future__ import annotations

import sqlite3
import sys
import os
import unittest
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.evidence.append_only_ledger import AppendOnlyLedger, LedgerViolation
from kernel.schemas.validator import SchemaValidationError
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    DriftEventRecordRepository,
    FailureBundleRepository,
    TaintRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


def _valid_drift_record(task_id: str, root_revision_id: str) -> dict:
    return {
        "drift_event_id": f"dr-{uuid4().hex[:8]}",
        "task_id": task_id,
        "root_revision_id": root_revision_id,
        "drift_class": "ingress_probe",
        "detected_at": "2026-01-01T00:00:00+00:00",
        "affected_artifact_ids": ["aff-a", "aff-b"],
        "consequence_class": "ingress_probe_no_op",
    }


def _valid_failure_bundle(task_id: str, root_revision_id: str) -> dict:
    bundle_id = f"fb-{uuid4().hex[:8]}"
    return {
        "failure_bundle_id": bundle_id,
        "task_id": task_id,
        "root_revision_id": root_revision_id,
        "failure_class": "ingress_probe",
        "cause_hash": f"sha256:{bundle_id}",
        "evidence_refs": ["ctx-a"],
        "taint_set": [],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


class TestAuditLedgerIngressValidation(unittest.TestCase):
    """AppendOnlyLedger validates candidate AuditRecord shape before persist."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="ingress-validation-test",
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_valid_audit_append_persists_one_row(self) -> None:
        """Happy path: schema-valid append writes exactly one row."""
        aud_id = self.ledger.append(
            record_type="ingress_probe_ok",
            task_id="t-ok",
            artifact_refs=["ref-a", "ref-b"],
            payload={"detail": "probe"},
        )
        self.assertTrue(aud_id)
        row = self.conn.execute(
            "SELECT audit_record_id, record_type, task_id FROM audit_records "
            "WHERE audit_record_id = ?;",
            (aud_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["record_type"], "ingress_probe_ok")
        self.assertEqual(row["task_id"], "t-ok")

    def test_invalid_artifact_refs_item_rejected(self) -> None:
        """Schema: artifact_refs items must be strings. None item rejected."""
        with self.assertRaises(LedgerViolation) as ctx:
            self.ledger.append(
                record_type="ingress_probe_bad_ref",
                task_id="t-bad",
                artifact_refs=["ref-a", None],
            )
        self.assertIn("artifact_refs", str(ctx.exception))

    def test_invalid_task_id_type_rejected(self) -> None:
        """Schema: task_id must be string, not integer."""
        with self.assertRaises(LedgerViolation) as ctx:
            self.ledger.append(
                record_type="ingress_probe_bad_task",
                task_id=12345,  # type: ignore[arg-type]
            )
        self.assertIn("task_id", str(ctx.exception))

    def test_empty_record_type_still_rejected(self) -> None:
        """Pre-validation LedgerViolation on empty record_type still fires."""
        with self.assertRaises(LedgerViolation):
            self.ledger.append(record_type="", task_id="t-empty")

    def test_rejected_append_does_not_persist(self) -> None:
        """Fail-closed: a rejected append must not leave a row behind."""
        before = self.conn.execute(
            "SELECT COUNT(*) FROM audit_records;"
        ).fetchone()[0]
        with self.assertRaises(LedgerViolation):
            self.ledger.append(
                record_type="ingress_probe_nopersist",
                task_id="t-np",
                artifact_refs=[None],
            )
        after = self.conn.execute(
            "SELECT COUNT(*) FROM audit_records;"
        ).fetchone()[0]
        self.assertEqual(before, after)


class TestDriftEventIngressValidation(unittest.TestCase):
    """DriftEventRecordRepository validates before persist."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.drift_repo = DriftEventRecordRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_valid_drift_record_persists(self) -> None:
        record = _valid_drift_record("t-drift", "rev-drift")
        self.drift_repo.insert(record)
        rows = self.drift_repo.list_for_task_root("t-drift", "rev-drift")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["drift_event_id"], record["drift_event_id"])

    def test_missing_required_field_rejected(self) -> None:
        record = _valid_drift_record("t-drift-x", "rev-drift-x")
        del record["consequence_class"]
        with self.assertRaises(SchemaValidationError) as ctx:
            self.drift_repo.insert(record)
        self.assertIn("consequence_class", str(ctx.exception))

    def test_invalid_affected_artifact_ids_type_rejected(self) -> None:
        record = _valid_drift_record("t-drift-y", "rev-drift-y")
        record["affected_artifact_ids"] = "not-a-list"
        with self.assertRaises(SchemaValidationError):
            self.drift_repo.insert(record)

    def test_rejected_drift_does_not_persist(self) -> None:
        record = _valid_drift_record("t-drift-z", "rev-drift-z")
        del record["drift_class"]
        with self.assertRaises(SchemaValidationError):
            self.drift_repo.insert(record)
        rows = self.drift_repo.list_for_task_root("t-drift-z", "rev-drift-z")
        self.assertEqual(rows, [])


class TestFailureBundleIngressValidation(unittest.TestCase):
    """FailureBundleRepository validates before persist."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.failure_repo = FailureBundleRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_valid_failure_bundle_persists(self) -> None:
        artifact = _valid_failure_bundle("t-fb", "rev-fb")
        self.failure_repo.append(artifact=artifact)
        rows = self.failure_repo.list_for_task_root("t-fb", "rev-fb")
        self.assertEqual(len(rows), 1)

    def test_missing_required_field_rejected(self) -> None:
        artifact = _valid_failure_bundle("t-fb-x", "rev-fb-x")
        del artifact["cause_hash"]
        with self.assertRaises(SchemaValidationError) as ctx:
            self.failure_repo.append(artifact=artifact)
        self.assertIn("cause_hash", str(ctx.exception))

    def test_none_valued_optional_rejected(self) -> None:
        """Non-nullable optional string field cannot be None when present."""
        artifact = _valid_failure_bundle("t-fb-y", "rev-fb-y")
        artifact["incident_id"] = None
        with self.assertRaises(SchemaValidationError):
            self.failure_repo.append(artifact=artifact)

    def test_rejected_failure_bundle_does_not_persist(self) -> None:
        artifact = _valid_failure_bundle("t-fb-z", "rev-fb-z")
        del artifact["failure_class"]
        with self.assertRaises(SchemaValidationError):
            self.failure_repo.append(artifact=artifact)
        rows = self.failure_repo.list_for_task_root("t-fb-z", "rev-fb-z")
        self.assertEqual(rows, [])


class TestTaintRecordIngressValidation(unittest.TestCase):
    """TaintRepository validates before persist."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.taint_repo = TaintRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_valid_taint_record_persists(self) -> None:
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="subj-a",
            taint_class="policy_degraded",
            taint_state="downgraded",
            source_ref="ingress-probe",
        )
        rows = self.taint_repo.list_for_subject("subj-a")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["taint_record_id"], taint_id)

    def test_invalid_taint_class_enum_rejected(self) -> None:
        with self.assertRaises(SchemaValidationError) as ctx:
            self.taint_repo.append(
                taint_record_id=f"taint-{uuid4().hex[:8]}",
                subject_id="subj-b",
                taint_class="not_in_enum",
                taint_state="downgraded",
                source_ref="ingress-probe",
            )
        self.assertIn("taint_class", str(ctx.exception))

    def test_invalid_taint_state_enum_rejected(self) -> None:
        with self.assertRaises(SchemaValidationError) as ctx:
            self.taint_repo.append(
                taint_record_id=f"taint-{uuid4().hex[:8]}",
                subject_id="subj-c",
                taint_class="policy_degraded",
                taint_state="not_in_enum",
                source_ref="ingress-probe",
            )
        self.assertIn("taint_state", str(ctx.exception))

    def test_empty_required_field_rejected(self) -> None:
        with self.assertRaises(SchemaValidationError) as ctx:
            self.taint_repo.append(
                taint_record_id="",  # minLength 1 violation
                subject_id="subj-d",
                taint_class="policy_degraded",
                taint_state="downgraded",
                source_ref="ingress-probe",
            )
        self.assertIn("taint_record_id", str(ctx.exception))

    def test_rejected_taint_does_not_persist(self) -> None:
        with self.assertRaises(SchemaValidationError):
            self.taint_repo.append(
                taint_record_id=f"taint-{uuid4().hex[:8]}",
                subject_id="subj-e",
                taint_class="bogus",
                taint_state="downgraded",
                source_ref="ingress-probe",
            )
        rows = self.taint_repo.list_for_subject("subj-e")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
