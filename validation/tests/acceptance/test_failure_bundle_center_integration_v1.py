"""Acceptance tests for Failure Bundle Center Integration V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.failure_bundle_center_integration import (
    FileBackedFailureBundleCenterIntegration,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class FailureBundleCenterIntegrationAcceptanceV1Tests(unittest.TestCase):
    def test_approval_rejection_and_watchdog_breach_are_durable_and_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            center = FileBackedFailureBundleCenterIntegration(runtime_root=root)
            approval_receipt = center.record_critical_failure(
                failure_kind="approval_rejection",
                task_id="task-acceptance-519",
                job_id="job-acceptance-519",
                run_id="run-acceptance-519",
                context_hashes=_contexts(),
                recovery_plan_hash=_hash("recovery-plan"),
                snapshot_reconstruction_hash=_hash("snapshot-reconstruction"),
                evidence_hashes={"operator_report_hash": _hash("operator-report")},
                observed_at="2026-05-28T00:00:00+00:00",
            )
            watchdog_receipt = center.record_critical_failure(
                failure_kind="watchdog_resource_breach",
                task_id="task-acceptance-519",
                job_id="job-acceptance-519",
                run_id="run-acceptance-519",
                context_hashes=_contexts(),
                recovery_plan_hash=_hash("recovery-plan"),
                snapshot_reconstruction_hash=_hash("snapshot-reconstruction"),
                evidence_hashes={"watchdog_receipt_hash": _hash("watchdog-receipt")},
                observed_at="2026-05-28T00:01:00+00:00",
            )
            approval_bundle = center.read_persisted_bundle(
                approval_receipt.failure_bundle_id
            )
            watchdog_manifest = center.read_center_manifest(
                watchdog_receipt.center_manifest_hash
            )
            wal_records = FileBackedRealWalStorage(
                root / "failure-bundle-center" / "failure.real-wal.jsonl"
            ).read_records()
            artifact_records = FileBackedArtifactStore(
                root / "artifact-store",
                store_id="failure-bundle-center-artifacts-v1",
            ).read_records()

        self.assertTrue(approval_receipt.accepted)
        self.assertTrue(watchdog_receipt.accepted)
        self.assertEqual(len(wal_records), 2)
        self.assertEqual(len(artifact_records), 2)
        self.assertEqual(
            approval_bundle["bundle"]["failure_code"],
            "approval_rejected",
        )
        self.assertTrue(watchdog_manifest.quarantine_required)
        self.assertEqual(watchdog_manifest.terminal_failure_count, 1)


def _contexts() -> dict[str, str]:
    return {
        "task_context_hash": _hash("task-context"),
        "job_context_hash": _hash("job-context"),
        "run_context_hash": _hash("run-context"),
        "wal_pointer_hash": _hash("wal-pointer"),
        "artifact_ids_hash": _hash("artifact-ids"),
        "replay_snapshot_context_hash": _hash("replay-snapshot"),
        "approval_rejection_context_hash": _hash("approval-rejection"),
        "queue_transition_context_hash": _hash("queue-transition"),
        "corruption_evidence_hash": _hash("corruption-evidence"),
        "watchdog_failure_context_hash": _hash("watchdog-failure"),
        "worker_failure_context_hash": _hash("worker-failure"),
        "missing_record_context_hash": _hash("missing-record"),
        "hash_mismatch_context_hash": _hash("hash-mismatch"),
    }


if __name__ == "__main__":
    unittest.main()
