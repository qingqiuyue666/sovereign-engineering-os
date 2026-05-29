"""Acceptance for #526 recovery / rollback / disaster procedure."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import stable_content_hash
from kernel.runtime.recovery_rollback_disaster_procedure import (
    FileBackedRecoveryRollbackDisasterProcedure,
    build_wal_event,
    snapshot_payload,
)


class RecoveryRollbackDisasterProcedureAcceptanceTests(unittest.TestCase):
    def test_recovery_paths_are_receipt_backed_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "runtime"
            root.mkdir()
            procedure = FileBackedRecoveryRollbackDisasterProcedure(root)
            _write_json(root / "state/current.json", {"schema": 1, "status": "stable"})
            _write_json(root / "snapshots/snap.json", snapshot_payload("snap", {"schema": 1, "status": "snapshot"}))

            backup = procedure.create_runtime_backup(reason="acceptance")
            snapshot_restore = procedure.restore_from_snapshot("snapshots/snap.json")

            artifact = _write_text(root / "artifacts/output.json", '{"ok":true}\n')
            _write_json(
                root / "artifacts/manifest.json",
                {"artifacts": [{"path": "artifacts/output.json", "sha256": _file_hash(artifact)}]},
            )
            event = build_wal_event(sequence=1, event_id="evt-1", state_patch={"status": "wal-restored"})
            _write_text(root / "wal/events.jsonl", json.dumps(event, sort_keys=True) + "\n")
            wal_restore = procedure.restore_from_wal_and_artifact_manifest(
                "wal/events.jsonl",
                "artifacts/manifest.json",
            )

            _write_json(root / "snapshots/corrupt.json", {"snapshot_id": "bad", "state": {"x": 1}, "state_hash": "0" * 64})
            corrupt = procedure.restore_from_snapshot("snapshots/corrupt.json")

            _write_json(root / "state/current.json", {"schema": 2, "broken": True})
            _write_json(root / "migrations/failed.json", {"migration_id": "failed", "status": "failed"})
            rollback = procedure.rollback_failed_migration(backup.backup_path, "migrations/failed.json")

            _write_text(root / "state/current.json.partial", '{"schema":')
            partial = procedure.recover_partial_write("state/current.json", "state/current.json.partial")
            _write_text(root / "state/current.json.tmp", '{"schema":')
            write_crash = procedure.recover_crash_during_write("state/current.json", "state/current.json.tmp")

            _write_text(root / "snapshots/recover.tmp", '{"state":')
            _write_json(root / "snapshots/recover-marker.json", {"status": "in_progress"})
            snapshot_crash = procedure.recover_crash_during_snapshot(
                "snapshots/recover.tmp",
                "snapshots/recover-marker.json",
            )

            _write_json(root / "queues/job.json", {"job": "queued"})
            _write_json(root / "approvals/job.json", {"approval": "granted"})
            _write_json(root / "transitions/job.json", {"status": "in_progress"})
            transition_crash = procedure.recover_approval_queue_transition(
                "queues/job.json",
                "approvals/job.json",
                "transitions/job.json",
            )

            accepted_receipts = (backup, snapshot_restore, wal_restore, rollback, partial, write_crash)
            rejected_receipts = (corrupt, snapshot_crash, transition_crash)
            for receipt in accepted_receipts:
                self.assertTrue(receipt.accepted, receipt)
                self.assertTrue(receipt.recovery_receipt_written)
                self.assertFalse(receipt.network_accessed)
                self.assertFalse(receipt.subprocess_spawned)
                self.assertFalse(receipt.sensitive_material_read)
                self.assertFalse(receipt.repair_performed)
                self.assertTrue(receipt.no_silent_repair)
                self.assertTrue(receipt.deterministic_verification_hash)
            for receipt in rejected_receipts:
                self.assertFalse(receipt.accepted)
                self.assertEqual(receipt.status, "quarantined")
                self.assertTrue(receipt.quarantined_paths)
                self.assertTrue(receipt.corrupted_source_preserved)
                self.assertFalse(receipt.repair_performed)

            self.assertEqual(_read_json(root / "state/restored-from-snapshot.json"), {"schema": 1, "status": "snapshot"})
            self.assertEqual(_read_json(root / "state/restored-from-wal.json"), {"status": "wal-restored"})
            self.assertEqual(_read_json(root / "state/current.json"), {"schema": 1, "status": "stable"})
            self.assertTrue((root / "snapshots/corrupt.json").is_file())
            self.assertTrue((root / "quarantine/snapshot-corruption/snapshots/corrupt.json").is_file())


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> str:
    return stable_content_hash({"bytes_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})


if __name__ == "__main__":
    unittest.main()
