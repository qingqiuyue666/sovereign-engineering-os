"""Tracer-bullet tests for read-only operator console contract v1."""

from dataclasses import replace
from pathlib import Path
import unittest

from kernel.runtime.operator_console_readonly_contract import (
    build_console_readonly_data_source,
    build_operator_console_readonly_snapshot,
    validate_console_readonly_data_source,
    validate_operator_console_readonly_snapshot,
)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
D4 = "sha256:" + "4" * 64
D5 = "sha256:" + "5" * 64
D6 = "sha256:" + "6" * 64
D7 = "sha256:" + "7" * 64
D8 = "sha256:" + "8" * 64
D9 = "sha256:" + "9" * 64
DA = "sha256:" + "a" * 64
DB = "sha256:" + "b" * 64
DC = "sha256:" + "c" * 64


class OperatorConsoleReadOnlyContractV1Tests(unittest.TestCase):
    def _source_payload(self, source_id: str = "source-wal", source_type: str = "wal") -> dict[str, object]:
        return {
            "source_id": source_id,
            "source_type": source_type,
            "source_hash": D1,
            "wal_record_hash": D2,
            "redaction_policy_hash": D3,
            "read_only": True,
            "mutation_enabled": False,
            "command_enabled": False,
            "dispatch_enabled": False,
            "live_fetch_enabled": False,
            "external_tool_enabled": False,
        }

    def _source(self):
        return build_console_readonly_data_source(self._source_payload())

    def _snapshot(self, data_sources=None):
        return build_operator_console_readonly_snapshot(
            console_snapshot_id="console-snapshot-001",
            task_id="task-001",
            run_id="run-001",
            data_sources=tuple(data_sources or (self._source(),)),
            wal_head_hash=D4,
            artifact_store_root_hash=D5,
            approval_runtime_hash=D6,
            failure_center_manifest_hash=D7,
            worker_registry_manifest_hash=D8,
            watchdog_chain_head_hash=D9,
            replay_report_hash=DA,
            snapshot_reconstruction_hash=DB,
            observed_at="2026-01-01T00:00:00Z",
        )

    def test_data_source_hash_is_deterministic_and_excludes_observed_at(self):
        first = build_console_readonly_data_source(
            self._source_payload(),
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_console_readonly_data_source(
            self._source_payload(),
            observed_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_console_readonly_data_source(first))
        self.assertEqual(first.data_source_hash, second.data_source_hash)
        self.assertNotIn("observed_at", first.deterministic_material())

    def test_data_source_rejects_mutation_command_dispatch_and_live_fetch(self):
        for field in (
            "read_only",
            "mutation_enabled",
            "command_enabled",
            "dispatch_enabled",
            "live_fetch_enabled",
            "external_tool_enabled",
        ):
            payload = self._source_payload()
            payload[field] = False if field == "read_only" else True
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    build_console_readonly_data_source(payload)

    def test_data_source_rejects_raw_secret_and_execution_material(self):
        forbidden_payloads = [
            {"raw_stdout": "raw"},
            {"stderr": "raw"},
            {"secret_value": "secret"},
            {"env": {"TOKEN": "value"}},
            {"argv": ["python"]},
            {"command": "make ci"},
            {"payload": {"raw": "data"}},
            {"filesystem_path": "/tmp/console.json"},
        ]
        for forbidden in forbidden_payloads:
            payload = self._source_payload()
            payload.update(forbidden)
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    build_console_readonly_data_source(payload)

    def test_snapshot_binds_required_evidence_and_is_read_only(self):
        snapshot = self._snapshot()

        self.assertTrue(validate_operator_console_readonly_snapshot(snapshot))
        self.assertTrue(snapshot.read_only)
        self.assertFalse(snapshot.mutation_enabled)
        self.assertFalse(snapshot.command_enabled)
        self.assertFalse(snapshot.dispatch_enabled)
        self.assertFalse(snapshot.live_fetch_enabled)
        self.assertFalse(snapshot.external_tool_enabled)
        self.assertIn("watchdog", snapshot.panel_ids)
        self.assertIn("workers", snapshot.panel_ids)
        self.assertNotIn("observed_at", snapshot.deterministic_material())

    def test_snapshot_hash_is_deterministic(self):
        first = self._snapshot()
        second = build_operator_console_readonly_snapshot(
            console_snapshot_id="console-snapshot-001",
            task_id="task-001",
            run_id="run-001",
            data_sources=(self._source(),),
            wal_head_hash=D4,
            artifact_store_root_hash=D5,
            approval_runtime_hash=D6,
            failure_center_manifest_hash=D7,
            worker_registry_manifest_hash=D8,
            watchdog_chain_head_hash=D9,
            replay_report_hash=DA,
            snapshot_reconstruction_hash=DB,
            observed_at="2026-05-27T00:00:00Z",
        )

        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertNotEqual(first.observed_at, second.observed_at)

    def test_snapshot_rejects_missing_panels_duplicate_sources_and_tampering(self):
        source = self._source()
        with self.assertRaises(ValueError):
            build_operator_console_readonly_snapshot(
                console_snapshot_id="console-snapshot-001",
                task_id="task-001",
                run_id="run-001",
                data_sources=(source,),
                wal_head_hash=D4,
                artifact_store_root_hash=D5,
                approval_runtime_hash=D6,
                failure_center_manifest_hash=D7,
                worker_registry_manifest_hash=D8,
                watchdog_chain_head_hash=D9,
                replay_report_hash=DA,
                snapshot_reconstruction_hash=DB,
                panel_ids=("summary",),
            )
        with self.assertRaises(ValueError):
            build_operator_console_readonly_snapshot(
                console_snapshot_id="console-snapshot-001",
                task_id="task-001",
                run_id="run-001",
                data_sources=(source, source),
                wal_head_hash=D4,
                artifact_store_root_hash=D5,
                approval_runtime_hash=D6,
                failure_center_manifest_hash=D7,
                worker_registry_manifest_hash=D8,
                watchdog_chain_head_hash=D9,
                replay_report_hash=DA,
                snapshot_reconstruction_hash=DB,
            )
        self.assertFalse(
            validate_operator_console_readonly_snapshot(
                replace(self._snapshot(), snapshot_hash=DC)
            )
        )

    def test_snapshot_rejects_invalid_source_and_bad_digest(self):
        with self.assertRaises(ValueError):
            build_console_readonly_data_source(self._source_payload(source_type="unknown"))

        with self.assertRaises(ValueError):
            build_operator_console_readonly_snapshot(
                console_snapshot_id="console-snapshot-001",
                task_id="task-001",
                run_id="run-001",
                data_sources=(self._source(),),
                wal_head_hash="not-a-digest",
                artifact_store_root_hash=D5,
                approval_runtime_hash=D6,
                failure_center_manifest_hash=D7,
                worker_registry_manifest_hash=D8,
                watchdog_chain_head_hash=D9,
                replay_report_hash=DA,
                snapshot_reconstruction_hash=DB,
            )

    def test_source_has_no_ui_runtime_execution_provider_or_storage_surface(self):
        source = Path("kernel/runtime/operator_console_readonly_contract.py").read_text()

        forbidden = [
            "sqlite3",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "argparse",
            "click",
            "typer",
            "schedule",
            "daemon",
            "os.environ",
            "Path(",
            "open(",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
