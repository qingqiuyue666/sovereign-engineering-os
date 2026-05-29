"""Tests for Deterministic Fault Simulation Harness V1."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.deterministic_fault_simulation_harness import (
    ZERO_HASH,
    FileBackedDeterministicFaultSimulationHarness,
    compute_fault_simulation_report_hash,
    compute_fault_simulation_result_hash,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

OBSERVED_AT = "2026-05-29T06:00:00+00:00"


def _scenario() -> dict[str, object]:
    return {
        "scenario_id": "post-529-fault-simulation",
        "seed": "post-529-seed-533",
        "faults": [
            {"fault_id": "crash", "fault_type": "crash_before_write", "target": "wal"},
            {"fault_id": "partial", "fault_type": "partial_write", "target": "artifact"},
            {"fault_id": "jsonl", "fault_type": "corrupted_jsonl", "target": "wal"},
            {"fault_id": "hash", "fault_type": "hash_mismatch", "target": "artifact"},
            {"fault_id": "missing-artifact", "fault_type": "missing_artifact", "target": "artifact"},
            {"fault_id": "stale-lease", "fault_type": "stale_queue_lease", "target": "queue"},
            {"fault_id": "missing-approval", "fault_type": "missing_approval", "target": "approval"},
            {"fault_id": "revoked-approval", "fault_type": "revoked_approval", "target": "approval"},
            {"fault_id": "expired-approval", "fault_type": "expired_approval", "target": "approval"},
            {"fault_id": "revoked-capability", "fault_type": "revoked_capability", "target": "capability"},
            {"fault_id": "reused-capability", "fault_type": "reused_capability", "target": "capability"},
            {"fault_id": "watchdog", "fault_type": "watchdog_timeout", "target": "watchdog"},
            {"fault_id": "replay", "fault_type": "replay_missing_record", "target": "replay"},
            {"fault_id": "recovery", "fault_type": "corrupted_recovery_source", "target": "recovery"},
        ],
    }


class DeterministicFaultSimulationHarnessV1Tests(unittest.TestCase):
    def test_complete_scenario_is_repeatable_and_persists_report_receipts_and_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            first = FileBackedDeterministicFaultSimulationHarness(
                runtime_root=root / "first",
            ).simulate(_scenario(), observed_at=OBSERVED_AT)
            second = FileBackedDeterministicFaultSimulationHarness(
                runtime_root=root / "second",
            ).simulate(_scenario(), observed_at=OBSERVED_AT)
            report = json.loads(
                (
                    root
                    / "first"
                    / "deterministic-fault-simulation"
                    / "reports"
                    / "fault-simulation-report.json"
                ).read_text(encoding="utf-8")
            )
            wal_records = FileBackedRealWalStorage(
                root
                / "first"
                / "deterministic-fault-simulation"
                / "simulation.real-wal.jsonl"
            ).read_records()

        self.assertTrue(first.accepted, first.failures)
        self.assertEqual(first.report_hash, second.report_hash)
        self.assertEqual(first.report_hash, compute_fault_simulation_report_hash(first))
        self.assertEqual(report["report_hash"], first.report_hash)
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, first.wal_record_hash)
        self.assertNotEqual(first.wal_record_hash, ZERO_HASH)
        for result in first.fault_results:
            self.assertTrue(result.detected)
            self.assertTrue(result.safe_recovery)
            self.assertEqual(result.result_hash, compute_fault_simulation_result_hash(result))

    def test_fault_type_outcomes_cover_required_fail_closed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            report = FileBackedDeterministicFaultSimulationHarness(
                runtime_root=tempdir,
            ).simulate(_scenario(), observed_at=OBSERVED_AT)

        results = {result.fault_type: result for result in report.fault_results}
        self.assertEqual(results["crash_before_write"].recovery_action, "block_before_write")
        self.assertEqual(results["partial_write"].recovery_action, "recover_from_last_complete_record")
        self.assertTrue(results["partial_write"].quarantine_required)
        self.assertEqual(results["corrupted_jsonl"].recovery_action, "reject_corrupted_wal")
        self.assertEqual(results["hash_mismatch"].recovery_action, "reject_hash_mismatch")
        self.assertEqual(results["missing_artifact"].recovery_action, "reject_missing_artifact")
        self.assertEqual(results["missing_approval"].recovery_action, "deny_missing_approval")
        self.assertEqual(results["revoked_approval"].recovery_action, "deny_revoked_approval")
        self.assertEqual(results["expired_approval"].recovery_action, "deny_expired_approval")
        self.assertEqual(results["revoked_capability"].recovery_action, "deny_revoked_capability")
        self.assertEqual(results["reused_capability"].recovery_action, "deny_reused_capability")
        self.assertEqual(results["stale_queue_lease"].recovery_action, "reclaim_stale_lease")
        self.assertEqual(results["watchdog_timeout"].recovery_action, "quarantine_timed_out_run")
        self.assertEqual(results["replay_missing_record"].recovery_action, "reject_replay_gap")
        self.assertEqual(results["corrupted_recovery_source"].recovery_action, "quarantine_recovery_source")
        self.assertTrue(results["corrupted_recovery_source"].quarantine_required)

    def test_unsafe_recovery_fails_closed(self) -> None:
        scenario = _scenario()
        scenario["faults"] = [
            {
                "fault_id": "unsafe",
                "fault_type": "corrupted_recovery_source",
                "target": "recovery",
                "force_unsafe_recovery": True,
            }
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            report = FileBackedDeterministicFaultSimulationHarness(
                runtime_root=tempdir,
            ).simulate(scenario, observed_at=OBSERVED_AT)

        self.assertFalse(report.accepted)
        self.assertIn("unsafe_recovery:unsafe", report.failures)
        self.assertEqual(report.fault_results[0].recovery_action, "unsafe_recovery_attempt")
        self.assertFalse(report.fault_results[0].safe_recovery)


if __name__ == "__main__":
    unittest.main()
