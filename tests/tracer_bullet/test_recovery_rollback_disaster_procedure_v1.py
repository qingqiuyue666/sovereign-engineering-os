"""Tests for #526 recovery / rollback / disaster procedure."""

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


class RecoveryRollbackDisasterProcedureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "runtime"
        self.root.mkdir()
        self.procedure = FileBackedRecoveryRollbackDisasterProcedure(self.root)

    def test_runtime_backup_and_restore_from_snapshot_are_receipt_backed(self) -> None:
        self.write_json("state/current.json", {"task": "before"})
        self.write_json("snapshots/snap-1.json", snapshot_payload("snap-1", {"task": "restored"}))

        backup = self.procedure.create_runtime_backup(reason="pre-snapshot-test")
        restored = self.procedure.restore_from_snapshot("snapshots/snap-1.json")

        self.assertTrue(backup.accepted)
        self.assertTrue(restored.accepted)
        self.assertEqual(restored.status, "restored")
        self.assertTrue(Path(backup.backup_path, "backup-manifest.json").is_file())
        self.assertEqual(self.read_json("state/restored-from-snapshot.json"), {"task": "restored"})
        self.assertTrue(self.receipt_path("restore_from_snapshot").is_file())
        for receipt in (backup, restored):
            self.assertFalse(receipt.network_accessed)
            self.assertFalse(receipt.subprocess_spawned)
            self.assertFalse(receipt.sensitive_material_read)
            self.assertFalse(receipt.repair_performed)
            self.assertTrue(receipt.no_silent_repair)
            self.assertTrue(receipt.deterministic_verification_hash)

    def test_restore_from_wal_and_artifact_manifest_reconstructs_state(self) -> None:
        artifact = self.write_text("artifacts/output.json", '{"ok": true}\n')
        self.write_json(
            "artifacts/manifest.json",
            {"artifacts": [{"path": "artifacts/output.json", "sha256": self.file_hash(artifact)}]},
        )
        first = build_wal_event(sequence=1, event_id="evt-1", state_patch={"task": "created"})
        second = build_wal_event(
            sequence=2,
            event_id="evt-2",
            state_patch={"status": "done"},
            previous_hash=str(first["event_hash"]),
        )
        self.write_text("wal/runtime.jsonl", json.dumps(first, sort_keys=True) + "\n" + json.dumps(second, sort_keys=True) + "\n")

        receipt = self.procedure.restore_from_wal_and_artifact_manifest(
            "wal/runtime.jsonl",
            "artifacts/manifest.json",
        )

        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.status, "restored")
        self.assertEqual(self.read_json("state/restored-from-wal.json"), {"status": "done", "task": "created"})
        self.assertEqual(receipt.failure_codes, ())
        self.assertTrue(receipt.backup_hash)

    def test_corrupt_snapshot_is_quarantined_and_not_silently_repaired(self) -> None:
        self.write_json("snapshots/bad.json", {"snapshot_id": "bad", "state": {"x": 1}, "state_hash": "0" * 64})

        receipt = self.procedure.restore_from_snapshot("snapshots/bad.json")

        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.status, "quarantined")
        self.assertIn("snapshot_state_hash_mismatch", receipt.failure_codes)
        self.assertTrue((self.root / "snapshots/bad.json").is_file())
        self.assertTrue((self.root / "quarantine/snapshot-corruption/snapshots/bad.json").is_file())
        self.assertFalse((self.root / "state/restored-from-snapshot.json").exists())
        self.assertFalse(receipt.repair_performed)
        self.assertTrue(receipt.corrupted_source_preserved)

    def test_corrupt_wal_or_artifact_manifest_fails_closed_and_quarantines_sources(self) -> None:
        artifact = self.write_text("artifacts/output.json", "tampered\n")
        self.write_json(
            "artifacts/manifest.json",
            {"artifacts": [{"path": "artifacts/output.json", "sha256": "0" * 64}]},
        )
        event = build_wal_event(sequence=1, event_id="evt-1", state_patch={"task": "created"})
        event["event_hash"] = "bad"
        self.write_text("wal/runtime.jsonl", json.dumps(event, sort_keys=True) + "\n")

        receipt = self.procedure.restore_from_wal_and_artifact_manifest(
            "wal/runtime.jsonl",
            "artifacts/manifest.json",
        )

        self.assertFalse(receipt.accepted)
        self.assertIn("wal_event_hash_mismatch:1", receipt.failure_codes)
        self.assertIn("artifact_hash_mismatch:0", receipt.failure_codes)
        self.assertTrue((self.root / "quarantine/wal-artifact-corruption/wal/runtime.jsonl").is_file())
        self.assertTrue((self.root / "quarantine/wal-artifact-corruption/artifacts/manifest.json").is_file())
        self.assertTrue(artifact.is_file())
        self.assertFalse((self.root / "state/restored-from-wal.json").exists())

    def test_failed_migration_rollback_restores_backup_and_quarantines_marker(self) -> None:
        self.write_json("state/current.json", {"schema": 1})
        backup = self.procedure.create_runtime_backup(reason="before-migration")
        self.write_json("state/current.json", {"schema": 2, "broken": True})
        self.write_json("migrations/migration-2.json", {"migration_id": "migration-2", "status": "failed"})

        receipt = self.procedure.rollback_failed_migration(
            backup.backup_path,
            "migrations/migration-2.json",
        )

        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.status, "rolled_back")
        self.assertEqual(self.read_json("state/current.json"), {"schema": 1})
        self.assertTrue((self.root / "quarantine/failed-migration-marker/migrations/migration-2.json").is_file())
        self.assertTrue((self.root / "migrations/migration-2.json").is_file())

    def test_partial_and_crashed_write_recovery_preserve_stable_state(self) -> None:
        self.write_json("state/stable.json", {"value": "stable"})
        self.write_text("state/stable.json.partial", '{"value":')
        partial = self.procedure.recover_partial_write("state/stable.json", "state/stable.json.partial")

        self.assertTrue(partial.accepted)
        self.assertEqual(partial.status, "stable_state_preserved")
        self.assertEqual(self.read_json("state/stable.json"), {"value": "stable"})
        self.assertTrue((self.root / "quarantine/partial-write/state/stable.json.partial").is_file())

        self.write_text("state/stable.json.tmp", '{"value":"crashed"')
        crashed = self.procedure.recover_crash_during_write("state/stable.json", "state/stable.json.tmp")
        self.assertTrue(crashed.accepted)
        self.assertEqual(self.read_json("state/stable.json"), {"value": "stable"})
        self.assertTrue((self.root / "quarantine/crash-during-write/state/stable.json.tmp").is_file())

    def test_snapshot_and_approval_queue_crashes_fail_closed(self) -> None:
        self.write_text("snapshots/snap-restore.tmp", '{"state":')
        self.write_json("snapshots/restore-in-progress.json", {"snapshot_id": "snap-restore", "status": "in_progress"})
        snapshot_crash = self.procedure.recover_crash_during_snapshot(
            "snapshots/snap-restore.tmp",
            "snapshots/restore-in-progress.json",
        )

        self.assertFalse(snapshot_crash.accepted)
        self.assertIn("snapshot_recovery_crash_marker_present", snapshot_crash.failure_codes)
        self.assertTrue((self.root / "quarantine/crash-during-snapshot/snapshots/snap-restore.tmp").is_file())

        self.write_json("queues/job-1.json", {"job": "queued"})
        self.write_json("approvals/job-1.json", {"approval": "granted"})
        self.write_json("transitions/job-1.json", {"status": "in_progress"})
        transition = self.procedure.recover_approval_queue_transition(
            "queues/job-1.json",
            "approvals/job-1.json",
            "transitions/job-1.json",
        )

        self.assertFalse(transition.accepted)
        self.assertIn("approval_queue_transition_ambiguous", transition.failure_codes)
        self.assertTrue((self.root / "quarantine/approval-queue-transition/transitions/job-1.json").is_file())
        self.assertEqual(self.read_json("queues/job-1.json"), {"job": "queued"})
        self.assertEqual(self.read_json("approvals/job-1.json"), {"approval": "granted"})

    def test_recovery_verification_is_deterministic_for_same_snapshot(self) -> None:
        self.write_json("state/current.json", {"task": "before"})
        self.write_json("snapshots/snap-1.json", snapshot_payload("snap-1", {"task": "restored"}))
        first = self.procedure.restore_from_snapshot("snapshots/snap-1.json")

        with tempfile.TemporaryDirectory() as other:
            other_root = Path(other) / "runtime"
            other_root.mkdir()
            other_procedure = FileBackedRecoveryRollbackDisasterProcedure(other_root)
            (other_root / "state").mkdir()
            (other_root / "snapshots").mkdir()
            (other_root / "state/current.json").write_text(
                json.dumps({"task": "before"}, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (other_root / "snapshots/snap-1.json").write_text(
                json.dumps(snapshot_payload("snap-1", {"task": "restored"}), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            second = other_procedure.restore_from_snapshot("snapshots/snap-1.json")

        self.assertEqual(first.restored_state_hash, second.restored_state_hash)
        self.assertEqual(first.deterministic_verification_hash, second.deterministic_verification_hash)

    def test_source_has_no_network_subprocess_or_silent_repair_surface(self) -> None:
        source = Path("kernel/runtime/recovery_rollback_disaster_procedure.py").read_text(encoding="utf-8")
        for marker in (
            "subprocess.",
            "Popen",
            "os.system",
            "requests.",
            "urllib.",
            "socket",
            "repair_performed=True",
        ):
            self.assertNotIn(marker, source)

    def write_json(self, relpath: str, payload: dict[str, object]) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def write_text(self, relpath: str, text: str) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read_json(self, relpath: str) -> dict[str, object]:
        return json.loads((self.root / relpath).read_text(encoding="utf-8"))

    def receipt_path(self, procedure: str) -> Path:
        return self.root / "receipts" / ("recovery-" + procedure + ".json")

    @staticmethod
    def file_hash(path: Path) -> str:
        raw = hashlib.sha256(path.read_bytes()).hexdigest()
        return stable_content_hash({"bytes_sha256": raw})


if __name__ == "__main__":
    unittest.main()
