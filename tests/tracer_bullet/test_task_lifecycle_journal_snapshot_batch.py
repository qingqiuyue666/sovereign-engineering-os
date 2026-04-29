"""P1-02 task lifecycle journal snapshot batch read surface.

Pins the read-only batch digest over the existing P1-01
`TaskLifecycleSnapshot` contract. The production surface consumes only
already materialized snapshots or rendered contract payloads.
"""

from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch import (
    TaskLifecycleJournalSnapshotBatchDigest,
    build_task_lifecycle_journal_snapshot_batch_digest,
    render_task_lifecycle_journal_snapshot_batch_digest,
    task_lifecycle_journal_snapshot_batch_manifest,
)
from kernel.lifecycle.task_lifecycle_journal_snapshot_contract import (
    check_task_lifecycle_journal_snapshot_contract,
    render_task_lifecycle_journal_snapshot_contract_check,
)
from kernel.lifecycle.task_recovery import (
    TaskLifecycleSnapshot,
    TaskRecoveryReader,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    IntentAnchorRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


EXPECTED_MANIFEST = {
    "surface": "task_lifecycle_journal_snapshot_batch",
    "version": 1,
    "input_shape": (
        "sequence_of_TaskLifecycleSnapshot_or_rendered_snapshot_contract_check"
    ),
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_batch", "not_ready", "ready"],
    "failure_values": [
        "batch_not_sequence",
        "batch_empty",
        "item_invalid_type",
        "item_contract_not_ready",
        "item_contract_invalid",
        "duplicate_task_id",
        "mixed_ready_state",
    ],
}

EXPECTED_DIGEST_KEYS = {
    "surface",
    "version",
    "item_count",
    "ready_count",
    "not_ready_count",
    "invalid_count",
    "unique_task_count",
    "duplicate_task_ids",
    "reason_counts",
    "failure_counts",
    "ready_task_ids",
    "not_ready_task_ids",
    "operator_safe",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
}

REPR_MARKERS = (
    "TaskLifecycleSnapshot(",
    "<Stage.",
    " object at 0x",
    "sqlite3.Connection",
    "<sqlite3.",
)


def _valid_snapshot(**overrides: object) -> TaskLifecycleSnapshot:
    base: dict[str, object] = {
        "task_id": "task-001",
        "intent_id": "intent-001",
        "current_stage": Stage.CONTEXT,
        "artifact_ids": {Stage.CONTEXT: "ctx-1"},
        "terminal_state": None,
        "last_event_sequence": 1,
        "lifecycle_record_count": 1,
        "malformed_event_count": 0,
        "intent_anchor_count": 1,
        "intent_created_at": "2025-01-01T00:00:00Z",
    }
    base.update(overrides)
    return TaskLifecycleSnapshot(**base)  # type: ignore[arg-type]


def _rendered_snapshot_payload(
    snapshot: TaskLifecycleSnapshot | None = None,
) -> dict[str, object]:
    check = check_task_lifecycle_journal_snapshot_contract(
        snapshot or _valid_snapshot()
    )
    return render_task_lifecycle_journal_snapshot_contract_check(check)


def _rendered_batch(
    items: object,
) -> dict[str, object]:
    digest = build_task_lifecycle_journal_snapshot_batch_digest(items)
    return render_task_lifecycle_journal_snapshot_batch_digest(digest)


def _recursive_values(payload: object) -> list[object]:
    values: list[object] = [payload]
    if isinstance(payload, dict):
        for key, value in payload.items():
            values.extend(_recursive_values(key))
            values.extend(_recursive_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_recursive_values(value))
    return values


def _assert_json_safe(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    if decoded != payload:
        raise AssertionError("payload did not round-trip through JSON")
    for value in _recursive_values(payload):
        if isinstance(value, (set, frozenset, tuple)):
            raise AssertionError(
                f"payload leaked runtime collection {type(value).__name__}"
            )


def _assert_no_runtime_repr(payload: object) -> None:
    text = json.dumps(payload, sort_keys=True)
    for marker in REPR_MARKERS:
        if marker in text:
            raise AssertionError(f"runtime repr marker leaked: {marker}")


def _quote_sql_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_row_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        table_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name;"
            )
        ]
        return {
            table_name: conn.execute(
                f"SELECT COUNT(*) FROM {_quote_sql_identifier(table_name)};"
            ).fetchone()[0]
            for table_name in table_names
        }
    finally:
        conn.close()


def _seed_file_backed_lifecycle_snapshot(
    db_path: Path,
    *,
    task_id: str,
    intent_id: str,
) -> None:
    conn = open_connection(db_path)
    try:
        apply_migrations(conn)
        IntentAnchorRepository(conn).insert(
            intent_id=intent_id,
            task_id=task_id,
            state="admitted",
        )
        AuditRepository(conn).append(
            audit_record_id=f"audit-{uuid4().hex[:8]}",
            record_type="stage_entered",
            actor_identity="p1_02_batch_test",
            version_tuple_hash="version-test",
            task_id=task_id,
            artifact_refs=["ctx-real"],
            payload={"stage": Stage.CONTEXT.value},
        )
    finally:
        conn.close()


class TestSnapshotBatchSyntheticSnapshots(unittest.TestCase):
    """Synthetic snapshot batches pin batch-level aggregation behavior."""

    def test_valid_single_snapshot_batch_ready(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [_valid_snapshot()]
        )
        self.assertIsInstance(result, TaskLifecycleJournalSnapshotBatchDigest)
        self.assertTrue(result.ready)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())
        self.assertEqual(result.digest["item_count"], 1)
        self.assertEqual(result.digest["ready_count"], 1)
        self.assertEqual(result.digest["not_ready_count"], 0)
        self.assertEqual(result.digest["invalid_count"], 0)
        self.assertEqual(result.digest["unique_task_count"], 1)
        self.assertEqual(result.digest["ready_task_ids"], ["task-001"])
        self.assertTrue(result.digest["operator_safe"])

    def test_valid_multiple_snapshot_batch_ready(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _valid_snapshot(task_id="task-001"),
                _valid_snapshot(task_id="task-002", intent_id="intent-002"),
            ]
        )
        self.assertTrue(result.ready)
        self.assertEqual(result.digest["item_count"], 2)
        self.assertEqual(result.digest["ready_count"], 2)
        self.assertEqual(result.digest["unique_task_count"], 2)
        self.assertEqual(
            result.digest["ready_task_ids"], ["task-001", "task-002"]
        )

    def test_malformed_non_sequence_rejected(self) -> None:
        rendered = _rendered_batch("not-a-batch")
        self.assertFalse(rendered["ready"])
        self.assertEqual(rendered["reason_code"], "invalid_batch")
        self.assertEqual(rendered["failures"], ["batch_not_sequence"])
        self.assertEqual(rendered["digest"]["item_count"], 0)
        self.assertEqual(rendered["digest"]["failure_counts"], {"batch_not_sequence": 1})

    def test_empty_sequence_rejected(self) -> None:
        rendered = _rendered_batch([])
        self.assertFalse(rendered["ready"])
        self.assertEqual(rendered["reason_code"], "invalid_batch")
        self.assertEqual(rendered["failures"], ["batch_empty"])
        self.assertEqual(rendered["digest"]["item_count"], 0)
        self.assertEqual(rendered["digest"]["failure_counts"], {"batch_empty": 1})

    def test_non_snapshot_non_rendered_item_rejected(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest([object()])
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_batch")
        self.assertEqual(result.failures, ("item_invalid_type",))
        self.assertEqual(result.digest["invalid_count"], 1)
        self.assertEqual(
            result.digest["failure_counts"], {"item_invalid_type": 1}
        )

    def test_invalid_snapshot_contract_not_ready(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [_valid_snapshot(task_id="")]
        )
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("item_contract_not_ready",))
        self.assertEqual(result.digest["ready_count"], 0)
        self.assertEqual(result.digest["not_ready_count"], 1)
        self.assertEqual(result.digest["invalid_count"], 0)
        self.assertEqual(
            result.digest["failure_counts"],
            {"item_contract_not_ready": 1, "task_id_invalid": 1},
        )

    def test_duplicate_task_id_detected(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _valid_snapshot(task_id="task-dup"),
                _valid_snapshot(task_id="task-dup", intent_id="intent-002"),
            ]
        )
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("duplicate_task_id",))
        self.assertEqual(result.digest["duplicate_task_ids"], ["task-dup"])
        self.assertEqual(
            result.digest["failure_counts"], {"duplicate_task_id": 1}
        )
        self.assertFalse(result.digest["operator_safe"])

    def test_mixed_ready_state_detected(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _valid_snapshot(task_id="task-ready"),
                _valid_snapshot(task_id="", intent_id="intent-not-ready"),
            ]
        )
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(
            result.failures,
            ("item_contract_not_ready", "mixed_ready_state"),
        )
        self.assertEqual(result.digest["ready_count"], 1)
        self.assertEqual(result.digest["not_ready_count"], 1)
        self.assertEqual(result.digest["ready_task_ids"], ["task-ready"])
        self.assertEqual(result.digest["not_ready_task_ids"], [""])
        self.assertFalse(result.digest["operator_safe"])

    def test_failure_counts_deterministic(self) -> None:
        first = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _valid_snapshot(
                    task_id="",
                    lifecycle_record_count=-1,
                ),
                _valid_snapshot(task_id="task-002", intent_id=""),
            ]
        )
        second = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _valid_snapshot(
                    task_id="",
                    lifecycle_record_count=-1,
                ),
                _valid_snapshot(task_id="task-002", intent_id=""),
            ]
        )
        expected = {
            "item_contract_not_ready": 2,
            "intent_id_invalid": 1,
            "lifecycle_record_count_invalid": 1,
            "task_id_invalid": 1,
        }
        self.assertEqual(first.digest["failure_counts"], expected)
        self.assertEqual(first.digest["failure_counts"], second.digest["failure_counts"])

    def test_reason_counts_deterministic(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _valid_snapshot(task_id="task-ready"),
                _valid_snapshot(task_id="", intent_id="intent-not-ready"),
            ]
        )
        self.assertEqual(result.digest["reason_counts"], {"not_ready": 1, "ready": 1})
        self.assertEqual(
            list(result.digest["reason_counts"].keys()),
            ["not_ready", "ready"],
        )

    def test_rendered_output_exact_shape(self) -> None:
        rendered = _rendered_batch([_valid_snapshot()])
        self.assertEqual(
            set(rendered.keys()), {"ready", "reason_code", "failures", "digest"}
        )
        self.assertEqual(set(rendered["digest"].keys()), EXPECTED_DIGEST_KEYS)

    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            task_lifecycle_journal_snapshot_batch_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = task_lifecycle_journal_snapshot_batch_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"
        self.assertEqual(
            task_lifecycle_journal_snapshot_batch_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_renderer_defensive_copy(self) -> None:
        digest = build_task_lifecycle_journal_snapshot_batch_digest(
            [_valid_snapshot()]
        )
        rendered = render_task_lifecycle_journal_snapshot_batch_digest(digest)
        rendered["digest"]["reason_counts"]["ready"] = 99  # type: ignore[index]
        rendered_again = render_task_lifecycle_journal_snapshot_batch_digest(
            digest
        )
        self.assertEqual(rendered_again["digest"]["reason_counts"], {"ready": 1})

    def test_input_not_mutated(self) -> None:
        snapshot = _valid_snapshot()
        rendered_payload = _rendered_snapshot_payload(snapshot)
        rendered_before = copy.deepcopy(rendered_payload)
        artifact_ids_before = dict(snapshot.artifact_ids)
        items = [snapshot, rendered_payload]

        build_task_lifecycle_journal_snapshot_batch_digest(items)

        self.assertEqual(snapshot.artifact_ids, artifact_ids_before)
        self.assertEqual(rendered_payload, rendered_before)
        self.assertEqual(items, [snapshot, rendered_payload])

    def test_json_safe_output(self) -> None:
        _assert_json_safe(_rendered_batch([_valid_snapshot()]))

    def test_no_runtime_repr_leakage(self) -> None:
        _assert_no_runtime_repr(_rendered_batch([_valid_snapshot()]))

    def test_public_api_exact(self) -> None:
        import kernel.lifecycle.task_lifecycle_journal_snapshot_batch as mod

        self.assertEqual(
            sorted(mod.__all__),
            sorted(
                [
                    "TaskLifecycleJournalSnapshotBatchDigest",
                    "build_task_lifecycle_journal_snapshot_batch_digest",
                    "render_task_lifecycle_journal_snapshot_batch_digest",
                    "task_lifecycle_journal_snapshot_batch_manifest",
                ]
            ),
        )
        digest = build_task_lifecycle_journal_snapshot_batch_digest(
            [_valid_snapshot()]
        )
        with self.assertRaises(Exception):
            digest.ready = False  # type: ignore[misc]

    def test_no_restore_cli_db_source_creep(self) -> None:
        import kernel.lifecycle.task_lifecycle_journal_snapshot_batch as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        imported_modules: set[str] = set()
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
                    imported_names.add(alias.name.rsplit(".", 1)[-1])
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
                for alias in node.names:
                    imported_names.add(alias.name)

        forbidden_imports = {
            "kernel.lifecycle.recovery_session_host",
            "kernel.lifecycle.recovery_session_host_cli",
            "kernel.lifecycle.recovery_cli",
            "kernel.stores.sqlite.repositories",
            "kernel.stores.sqlite.unit_of_work",
            "kernel.stores.sqlite.wal_recovery",
            "sqlite3",
            "os",
            "pathlib",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_modules))
        self.assertNotIn("TaskRecoveryReader", imported_names)
        self.assertNotIn("RecoverySessionHost", source)
        self.assertNotIn("build_parser", source)
        self.assertNotIn("open_connection", source)
        self.assertNotIn("apply_migrations", source)
        self.assertNotIn("KernelUnitOfWork", source)
        self.assertNotIn(".restore", source)
        self.assertNotIn("restore_dry_run", source)


class TestSnapshotBatchRenderedContractPayloads(unittest.TestCase):
    """Rendered P1-01 payloads are accepted or rejected locally."""

    def test_accepts_valid_rendered_snapshot_contract_payloads(self) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest(
            [
                _rendered_snapshot_payload(
                    _valid_snapshot(task_id="task-rendered-a")
                ),
                _rendered_snapshot_payload(
                    _valid_snapshot(task_id="task-rendered-b")
                ),
            ]
        )
        self.assertTrue(result.ready)
        self.assertEqual(result.digest["item_count"], 2)
        self.assertEqual(result.digest["ready_task_ids"], ["rendered::0", "rendered::1"])
        self.assertEqual(result.digest["unique_task_count"], 2)

    def test_rejects_malformed_rendered_payload(self) -> None:
        payload = _rendered_snapshot_payload()
        payload.pop("contract")
        result = build_task_lifecycle_journal_snapshot_batch_digest([payload])
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_batch")
        self.assertEqual(result.failures, ("item_contract_invalid",))
        self.assertEqual(result.digest["invalid_count"], 1)

    def test_rejects_rendered_payload_with_restore_supported_true(self) -> None:
        payload = _rendered_snapshot_payload()
        payload["contract"]["restore_supported"] = True  # type: ignore[index]
        self._assert_rendered_payload_invalid(payload)

    def test_rejects_rendered_payload_with_durable_writes_true(self) -> None:
        payload = _rendered_snapshot_payload()
        payload["contract"]["durable_writes"] = True  # type: ignore[index]
        self._assert_rendered_payload_invalid(payload)

    def test_rejects_rendered_payload_with_cli_commands_non_empty(self) -> None:
        payload = _rendered_snapshot_payload()
        payload["contract"]["cli_commands"] = ["evaluate"]  # type: ignore[index]
        self._assert_rendered_payload_invalid(payload)

    def test_rejects_rendered_payload_with_runtime_dependencies_non_empty(
        self,
    ) -> None:
        payload = _rendered_snapshot_payload()
        payload["contract"]["runtime_dependencies"] = ["sqlite3"]  # type: ignore[index]
        self._assert_rendered_payload_invalid(payload)

    def test_rejects_rendered_payload_with_json_safe_false(self) -> None:
        payload = _rendered_snapshot_payload()
        payload["contract"]["json_safe"] = False  # type: ignore[index]
        self._assert_rendered_payload_invalid(payload)

    def test_rejects_rendered_payload_with_bool_version(self) -> None:
        payload = _rendered_snapshot_payload()
        payload["contract"]["version"] = True  # type: ignore[index]
        self._assert_rendered_payload_invalid(payload)

    def _assert_rendered_payload_invalid(
        self,
        payload: dict[str, object],
    ) -> None:
        result = build_task_lifecycle_journal_snapshot_batch_digest([payload])
        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_batch")
        self.assertEqual(result.failures, ("item_contract_invalid",))
        self.assertEqual(
            result.digest["failure_counts"],
            {"item_contract_invalid": 1},
        )


class TestSnapshotBatchRealReaderAcceptance(unittest.TestCase):
    """A real reader snapshot can flow through P1-01 and P1-02."""

    def test_real_task_recovery_reader_snapshot_batch_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            db_path = tmpdir / "reader.db"
            missing_path = tmpdir / "missing.db"
            task_id = f"task-{uuid4().hex[:8]}"
            intent_id = f"intent-{uuid4().hex[:8]}"
            _seed_file_backed_lifecycle_snapshot(
                db_path,
                task_id=task_id,
                intent_id=intent_id,
            )
            self.assertFalse(missing_path.exists())
            before_counts = _table_row_counts(db_path)

            conn = open_connection(db_path)
            try:
                reader = TaskRecoveryReader(
                    audit_repository=AuditRepository(conn),
                    intent_anchor_repository=IntentAnchorRepository(conn),
                )
                snapshot = reader.reconstruct(task_id)
                self.assertIsNotNone(snapshot)
                check = check_task_lifecycle_journal_snapshot_contract(
                    snapshot
                )
                rendered_check = (
                    render_task_lifecycle_journal_snapshot_contract_check(
                        check
                    )
                )
                batch = build_task_lifecycle_journal_snapshot_batch_digest(
                    [snapshot]
                )
                rendered_batch = (
                    render_task_lifecycle_journal_snapshot_batch_digest(batch)
                )
            finally:
                conn.close()

            self.assertTrue(rendered_check["ready"])
            self.assertTrue(batch.ready)
            self.assertTrue(rendered_batch["ready"])
            self.assertEqual(rendered_batch["digest"]["item_count"], 1)
            self.assertEqual(_table_row_counts(db_path), before_counts)
            self.assertFalse(missing_path.exists())
            _assert_json_safe(rendered_batch)


class TestSnapshotBatchCiDisplaySummary(unittest.TestCase):
    """The local CI summary shape stays small and JSON-safe."""

    def test_batch_level_ci_display_summary_round_trips(self) -> None:
        rendered = _rendered_batch([_valid_snapshot()])
        summary = {
            "phase": "task_lifecycle_journal_snapshot_batch",
            "ready": rendered["ready"],
            "reason_code": rendered["reason_code"],
            "item_count": rendered["digest"]["item_count"],
            "ready_count": rendered["digest"]["ready_count"],
            "not_ready_count": rendered["digest"]["not_ready_count"],
            "invalid_count": rendered["digest"]["invalid_count"],
            "operator_safe": rendered["digest"]["operator_safe"],
        }
        self.assertEqual(json.loads(json.dumps(summary, sort_keys=True)), summary)


if __name__ == "__main__":
    unittest.main()
