"""Tests for System E2E Acceptance V1."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.operator_console_runtime_surface import (
    FileBackedOperatorConsoleRuntimeSurface,
    validate_operator_console_runtime_snapshot,
)
from kernel.runtime.system_e2e_acceptance import (
    SYSTEM_E2E_QUEUE_ID,
    ZERO_HASH,
    FileBackedSystemE2EAcceptance,
    compute_system_e2e_acceptance_receipt_hash,
    compute_system_e2e_gate_result_hash,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

SOURCE_PATH = Path("kernel/runtime/system_e2e_acceptance.py")
OBSERVED_AT = "2026-05-29T00:30:00+00:00"
TASK_ID = "task-527-system-e2e"
RUN_ID = "run-527-system-e2e"
REQUIRED_GATES = (
    "task_created",
    "worker_admission",
    "approval_gate",
    "queue_submit",
    "wal_append",
    "lease_heartbeat",
    "controlled_execution_boundary",
    "artifact_write",
    "snapshot_create",
    "replay_reconstruct",
    "operator_console_read",
    "failure_bundle_path",
    "watchdog_path",
    "corrupt_wal_fail_closed",
    "corrupt_artifact_fail_closed",
    "missing_approval_fail_closed",
    "replay_final_state_verified",
    "final_acceptance_report_signable",
)


def _run(root: Path):
    return FileBackedSystemE2EAcceptance(runtime_root=root).run(
        observed_at=OBSERVED_AT,
    )


class SystemE2EAcceptanceV1Tests(unittest.TestCase):
    def test_runs_real_system_path_and_persists_signable_report(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = _run(root)
            persisted_report = json.loads(
                (root / "system-e2e" / "reports" / "final-acceptance-report.json").read_text(
                    encoding="utf-8",
                )
            )
            persisted_receipt = json.loads(
                (root / "system-e2e" / "receipts" / "final-acceptance-receipt.json").read_text(
                    encoding="utf-8",
                )
            )

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(tuple(gate.gate_id for gate in receipt.gate_results), REQUIRED_GATES)
        self.assertTrue(all(gate.accepted for gate in receipt.gate_results))
        self.assertEqual(
            receipt.receipt_hash,
            compute_system_e2e_acceptance_receipt_hash(receipt),
        )
        for gate in receipt.gate_results:
            self.assertEqual(gate.gate_hash, compute_system_e2e_gate_result_hash(gate))
            self.assertNotEqual(gate.evidence_hash, ZERO_HASH)
        for field_name in (
            "task_wal_record_hash",
            "queue_record_hash",
            "worker_admission_receipt_hash",
            "worker_capability_consumption_receipt_hash",
            "approval_gate_receipt_hash",
            "watchdog_receipt_hash",
            "controlled_execution_receipt_hash",
            "result_artifact_record_hash",
            "failure_bundle_receipt_hash",
            "snapshot_receipt_hash",
            "final_snapshot_receipt_hash",
            "operator_console_snapshot_hash",
            "signable_report_hash",
            "signable_report_artifact_record_hash",
        ):
            self.assertNotEqual(getattr(receipt, field_name), ZERO_HASH, field_name)
        self.assertTrue(receipt.deterministic_replay_verified)
        self.assertTrue(receipt.final_acceptance_report_signable)
        self.assertFalse(receipt.network_accessed)
        self.assertFalse(receipt.provider_called)
        self.assertFalse(receipt.background_daemon_enabled)
        self.assertFalse(receipt.direct_mutation_enabled)
        self.assertTrue(persisted_report["final_acceptance_report_signable"])
        self.assertEqual(persisted_receipt["receipt_hash"], receipt.receipt_hash)

    def test_corruption_and_missing_approval_probes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = _run(root)
            corrupt_wal_replay = FileBackedRealWalStorage(
                root / "system-e2e" / "probes" / "corrupt-wal" / "wal.jsonl"
            ).replay()
            corrupt_artifact_replay = FileBackedArtifactStore(
                root / "system-e2e" / "probes" / "corrupt-artifact" / "store",
                store_id="system-e2e-corrupt-artifact-probe-v1",
            ).replay()

        gate_by_id = {gate.gate_id: gate for gate in receipt.gate_results}
        self.assertTrue(gate_by_id["corrupt_wal_fail_closed"].accepted)
        self.assertTrue(gate_by_id["corrupt_artifact_fail_closed"].accepted)
        self.assertTrue(gate_by_id["missing_approval_fail_closed"].accepted)
        self.assertFalse(corrupt_wal_replay.accepted)
        self.assertFalse(corrupt_artifact_replay.accepted)
        self.assertNotEqual(receipt.missing_approval_probe_hash, ZERO_HASH)

    def test_replay_receipt_console_and_wal_bind_final_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = _run(root)
            system_wal = FileBackedRealWalStorage(
                root / "system-e2e" / "system.real-wal.jsonl"
            ).read_records()
            console = FileBackedOperatorConsoleRuntimeSurface(
                runtime_root=root,
                wal_source_relpaths=(
                    "system-e2e/system.real-wal.jsonl",
                    "queue/jobs.jsonl.real-wal.jsonl",
                    "approval-runtime/approval.real-wal.jsonl",
                    "artifact-store/artifact-store.real-wal.jsonl",
                    "failure-bundle-center/failure.real-wal.jsonl",
                    "worker-registry-runtime/worker-registry.real-wal.jsonl",
                    "watchdog-runtime/watchdog.real-wal.jsonl",
                    "controlled-execution/execution.real-wal.jsonl",
                    "controlled-execution/queue/jobs.jsonl.real-wal.jsonl",
                    "controlled-execution/artifacts/artifact-store.real-wal.jsonl",
                ),
                queue_source_relpath="queue/jobs.jsonl",
                queue_id=SYSTEM_E2E_QUEUE_ID,
                artifact_store_relpath="artifact-store",
                artifact_store_id="failure-bundle-center-artifacts-v1",
            ).read_snapshot(
                task_id=TASK_ID,
                run_id=RUN_ID,
                observed_at=OBSERVED_AT,
            )

        self.assertEqual({record.record_type for record in system_wal}, {"SYSTEM_ACCEPTANCE_EVENT"})
        self.assertEqual(system_wal[0].record_hash, receipt.task_wal_record_hash)
        self.assertTrue(validate_operator_console_runtime_snapshot(console))
        self.assertEqual(console.status, "ok")
        self.assertTrue(console.read_only)
        self.assertFalse(console.mutation_enabled)
        self.assertEqual(console.snapshot_hash, receipt.operator_console_snapshot_hash)

    def test_source_has_no_mocked_or_external_execution_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        forbidden_imports = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in (
            "unittest.mock",
            "requests.",
            "urllib.",
            "socket.",
            "Popen",
            "os.system",
            "while True",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
