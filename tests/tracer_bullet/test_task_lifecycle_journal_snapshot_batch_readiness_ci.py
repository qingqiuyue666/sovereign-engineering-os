"""P1-03 task lifecycle batch readiness and flat CI consumer tests."""

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
from unittest import mock
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle import (
    task_lifecycle_journal_snapshot_batch_ci as ci_module,
)
from kernel.lifecycle import (
    task_lifecycle_journal_snapshot_batch_readiness as readiness_module,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch import (
    build_task_lifecycle_journal_snapshot_batch_digest,
    render_task_lifecycle_journal_snapshot_batch_digest,
)
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch_ci import (
    consume_task_lifecycle_journal_snapshot_batch_ci,
    task_lifecycle_journal_snapshot_batch_ci_manifest,
)
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch_readiness import (
    TaskLifecycleJournalSnapshotBatchReadinessCheck,
    check_task_lifecycle_journal_snapshot_batch_readiness,
    render_task_lifecycle_journal_snapshot_batch_readiness_check,
    task_lifecycle_journal_snapshot_batch_readiness_manifest,
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


EXPECTED_READINESS_MANIFEST = {
    "surface": "task_lifecycle_journal_snapshot_batch_readiness",
    "version": 1,
    "input_shape": "rendered_task_lifecycle_journal_snapshot_batch_digest",
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_batch_digest", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "digest_invalid",
        "digest_shape_mismatch",
        "digest_counter_invalid",
        "digest_bool_invalid",
        "digest_list_invalid",
        "digest_mapping_invalid",
        "status_inconsistent",
        "safety_inconsistent",
        "operator_not_safe",
    ],
}

EXPECTED_CI_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "contract_ready",
    "contract_reason_code",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
]

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


def _rendered_batch(items: object) -> dict[str, object]:
    digest = build_task_lifecycle_journal_snapshot_batch_digest(items)
    return render_task_lifecycle_journal_snapshot_batch_digest(digest)


def _valid_rendered_batch() -> dict[str, object]:
    return _rendered_batch([_valid_snapshot()])


def _rendered_readiness_payload(
    rendered_batch: dict[str, object] | None = None,
) -> dict[str, object]:
    check = check_task_lifecycle_journal_snapshot_batch_readiness(
        rendered_batch or _valid_rendered_batch()
    )
    return render_task_lifecycle_journal_snapshot_batch_readiness_check(check)


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
            actor_identity="p1_03_batch_readiness_test",
            version_tuple_hash="version-test",
            task_id=task_id,
            artifact_refs=["ctx-real"],
            payload={"stage": Stage.CONTEXT.value},
        )
    finally:
        conn.close()


def _read_real_snapshot(db_path: Path, task_id: str) -> TaskLifecycleSnapshot:
    conn = open_connection(db_path)
    try:
        reader = TaskRecoveryReader(
            audit_repository=AuditRepository(conn),
            intent_anchor_repository=IntentAnchorRepository(conn),
        )
        snapshot = reader.reconstruct(task_id)
        if snapshot is None:
            raise AssertionError("expected real reader snapshot")
        return snapshot
    finally:
        conn.close()


class TestBatchReadinessContract(unittest.TestCase):
    def test_accepts_valid_rendered_p1_02_batch_digest(self) -> None:
        check = check_task_lifecycle_journal_snapshot_batch_readiness(
            _valid_rendered_batch()
        )

        self.assertIsInstance(
            check, TaskLifecycleJournalSnapshotBatchReadinessCheck
        )
        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        self.assertEqual(
            check.contract["surface"],
            "task_lifecycle_journal_snapshot_batch_readiness",
        )

    def test_rejects_non_mapping_payload(self) -> None:
        check = check_task_lifecycle_journal_snapshot_batch_readiness("bad")

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "invalid_batch_digest")
        self.assertEqual(check.failures, ("payload_not_mapping",))

    def test_rejects_top_level_shape_mismatch(self) -> None:
        payload = _valid_rendered_batch()
        payload["extra"] = True

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertEqual(check.reason_code, "invalid_batch_digest")
        self.assertIn("payload_shape_mismatch", check.failures)

    def test_rejects_invalid_failures_list(self) -> None:
        payload = _valid_rendered_batch()
        payload["failures"] = ["ok", 1]

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertEqual(check.reason_code, "invalid_batch_digest")
        self.assertIn("payload_failures_invalid", check.failures)

    def test_rejects_invalid_digest_object(self) -> None:
        payload = _valid_rendered_batch()
        payload["digest"] = []

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertEqual(check.failures, ("digest_invalid",))

    def test_rejects_missing_digest_keys(self) -> None:
        payload = _valid_rendered_batch()
        digest = payload["digest"]
        assert isinstance(digest, dict)
        digest.pop("item_count")

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertEqual(check.reason_code, "invalid_batch_digest")
        self.assertIn("digest_shape_mismatch", check.failures)

    def test_rejects_invalid_counters_and_bool_as_int(self) -> None:
        for field in ("version", "item_count", "ready_count"):
            with self.subTest(field=field):
                payload = _valid_rendered_batch()
                digest = payload["digest"]
                assert isinstance(digest, dict)
                digest[field] = True

                check = (
                    check_task_lifecycle_journal_snapshot_batch_readiness(
                        payload
                    )
                )

                self.assertIn("digest_counter_invalid", check.failures)

    def test_rejects_invalid_bool_fields(self) -> None:
        for field in (
            "operator_safe",
            "restore_supported",
            "durable_writes",
            "json_safe",
        ):
            with self.subTest(field=field):
                payload = _valid_rendered_batch()
                digest = payload["digest"]
                assert isinstance(digest, dict)
                digest[field] = "bad"

                check = (
                    check_task_lifecycle_journal_snapshot_batch_readiness(
                        payload
                    )
                )

                self.assertIn("digest_bool_invalid", check.failures)

    def test_rejects_invalid_list_fields(self) -> None:
        for field in (
            "duplicate_task_ids",
            "ready_task_ids",
            "not_ready_task_ids",
        ):
            with self.subTest(field=field):
                payload = _valid_rendered_batch()
                digest = payload["digest"]
                assert isinstance(digest, dict)
                digest[field] = ["task", 1]

                check = (
                    check_task_lifecycle_journal_snapshot_batch_readiness(
                        payload
                    )
                )

                self.assertIn("digest_list_invalid", check.failures)

    def test_rejects_invalid_mapping_count_fields(self) -> None:
        cases = [
            ("reason_counts", {"ready": True}),
            ("failure_counts", {"x": -1}),
            ("failure_counts", []),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                payload = _valid_rendered_batch()
                digest = payload["digest"]
                assert isinstance(digest, dict)
                digest[field] = value

                check = (
                    check_task_lifecycle_journal_snapshot_batch_readiness(
                        payload
                    )
                )

                self.assertIn("digest_mapping_invalid", check.failures)

    def test_detects_status_inconsistency(self) -> None:
        payload = _valid_rendered_batch()
        payload["reason_code"] = "not_ready"

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertEqual(check.reason_code, "invalid_batch_digest")
        self.assertIn("status_inconsistent", check.failures)

    def test_detects_safety_inconsistency(self) -> None:
        payload = _valid_rendered_batch()
        digest = payload["digest"]
        assert isinstance(digest, dict)
        digest["restore_supported"] = True

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertEqual(check.reason_code, "invalid_batch_digest")
        self.assertIn("safety_inconsistent", check.failures)

    def test_marks_operator_safe_false_batch_as_not_ready(self) -> None:
        payload = _rendered_batch(
            [
                _valid_snapshot(task_id="task-dup"),
                _valid_snapshot(task_id="task-dup", intent_id="intent-002"),
            ]
        )
        self.assertIs(payload["ready"], False)
        self.assertEqual(payload["reason_code"], "not_ready")

        check = check_task_lifecycle_journal_snapshot_batch_readiness(payload)

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "not_ready")
        self.assertEqual(check.failures, ("operator_not_safe",))

    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            task_lifecycle_journal_snapshot_batch_readiness_manifest(),
            EXPECTED_READINESS_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = task_lifecycle_journal_snapshot_batch_readiness_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"

        self.assertEqual(
            task_lifecycle_journal_snapshot_batch_readiness_manifest(),
            EXPECTED_READINESS_MANIFEST,
        )

    def test_renderer_exact_shape(self) -> None:
        check = check_task_lifecycle_journal_snapshot_batch_readiness(
            _valid_rendered_batch()
        )
        rendered = render_task_lifecycle_journal_snapshot_batch_readiness_check(
            check
        )

        self.assertEqual(
            set(rendered.keys()), {"ready", "reason_code", "failures", "contract"}
        )
        self.assertEqual(rendered["contract"], EXPECTED_READINESS_MANIFEST)

    def test_renderer_defensive_copy(self) -> None:
        check = check_task_lifecycle_journal_snapshot_batch_readiness(
            _valid_rendered_batch()
        )
        rendered = render_task_lifecycle_journal_snapshot_batch_readiness_check(
            check
        )
        rendered["contract"]["surface"] = "tampered"  # type: ignore[index]
        rendered["contract"]["failure_values"].append(  # type: ignore[index]
            "INJECTED"
        )

        rendered_again = (
            render_task_lifecycle_journal_snapshot_batch_readiness_check(
                check
            )
        )

        self.assertEqual(rendered_again["contract"], EXPECTED_READINESS_MANIFEST)

    def test_output_json_safe(self) -> None:
        rendered = _rendered_readiness_payload()
        _assert_json_safe(rendered)

    def test_no_runtime_repr_leakage(self) -> None:
        rendered = _rendered_readiness_payload()
        _assert_no_runtime_repr(rendered)

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(readiness_module.__all__),
            sorted(
                [
                    "TaskLifecycleJournalSnapshotBatchReadinessCheck",
                    "check_task_lifecycle_journal_snapshot_batch_readiness",
                    "render_task_lifecycle_journal_snapshot_batch_readiness_check",
                    "task_lifecycle_journal_snapshot_batch_readiness_manifest",
                ]
            ),
        )
        check = check_task_lifecycle_journal_snapshot_batch_readiness(
            _valid_rendered_batch()
        )
        with self.assertRaises(Exception):
            check.ready = False  # type: ignore[misc]

    def test_no_restore_cli_db_source_creep(self) -> None:
        source = inspect.getsource(readiness_module)
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
            "kernel.lifecycle.task_lifecycle_journal_snapshot_batch",
            "kernel.lifecycle.task_lifecycle_journal_snapshot_contract",
            "kernel.lifecycle.task_recovery",
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
        self.assertNotIn("TaskRecoveryReader", source)
        self.assertNotIn("RecoverySessionHost", source)
        self.assertNotIn("build_parser", source)
        self.assertNotIn("open_connection", source)
        self.assertNotIn("apply_migrations", source)
        self.assertNotIn("KernelUnitOfWork", source)
        self.assertNotIn(".restore", source)
        self.assertNotIn("restore_dry_run", source)


class TestBatchReadinessCiConsumer(unittest.TestCase):
    def test_accepts_rendered_readiness_contract_ready_payload(self) -> None:
        payload = _rendered_readiness_payload()

        result = consume_task_lifecycle_journal_snapshot_batch_ci(payload)

        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["surface"],
            "task_lifecycle_journal_snapshot_batch_readiness",
        )
        self.assertEqual(result["version"], 1)
        self.assertIs(result["contract_ready"], True)
        self.assertEqual(result["contract_reason_code"], "ready")
        self.assertIs(result["restore_supported"], False)
        self.assertIs(result["durable_writes"], False)
        self.assertEqual(result["cli_command_count"], 0)
        self.assertEqual(result["runtime_dependency_count"], 0)
        self.assertIs(result["json_safe"], True)

    def test_invalid_payload_returns_invalid_ci_payload(self) -> None:
        result = consume_task_lifecycle_journal_snapshot_batch_ci(None)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["invalid_ci_payload"])
        self.assertIs(result["contract_ready"], False)
        self.assertEqual(result["contract_reason_code"], "invalid_ci_payload")
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])

    def test_not_ready_payload_returns_ci_ok_false(self) -> None:
        rendered_batch = _rendered_batch(
            [
                _valid_snapshot(task_id="task-dup"),
                _valid_snapshot(task_id="task-dup", intent_id="intent-002"),
            ]
        )
        payload = _rendered_readiness_payload(rendered_batch)

        result = consume_task_lifecycle_journal_snapshot_batch_ci(payload)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIs(result["contract_ready"], False)
        self.assertEqual(result["contract_reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["operator_not_safe"])

    def test_detects_restore_durable_cli_runtime_json_safe_hazards(
        self,
    ) -> None:
        hazard_cases = [
            ("restore_supported", True, "restore_supported"),
            ("durable_writes", True, "durable_writes"),
            ("cli_commands", ["restore"], "has_cli_commands"),
            ("runtime_dependencies", ["sqlite3"], "has_runtime_dependencies"),
            ("json_safe", False, "not_json_safe"),
        ]
        for field, value, expected_failure in hazard_cases:
            with self.subTest(field=field):
                payload = _rendered_readiness_payload()
                contract = payload["contract"]
                assert isinstance(contract, dict)
                contract[field] = value

                result = consume_task_lifecycle_journal_snapshot_batch_ci(
                    payload
                )

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn(expected_failure, result["failures"])

    def test_output_exact_shape(self) -> None:
        result = consume_task_lifecycle_journal_snapshot_batch_ci(
            _rendered_readiness_payload()
        )

        self.assertEqual(list(result.keys()), EXPECTED_CI_OUTPUT_KEYS)

    def test_manifest_defensive_copy(self) -> None:
        manifest = task_lifecycle_journal_snapshot_batch_ci_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"
        manifest_again = task_lifecycle_journal_snapshot_batch_ci_manifest()

        self.assertEqual(
            manifest_again["surface"], "task_lifecycle_journal_snapshot_batch_ci"
        )
        self.assertNotIn("INJECTED", manifest_again["failure_values"])
        _assert_json_safe(manifest_again)

    def test_output_json_safe(self) -> None:
        result = consume_task_lifecycle_journal_snapshot_batch_ci(
            _rendered_readiness_payload()
        )

        _assert_json_safe(result)

    def test_no_upstream_calls(self) -> None:
        payload = _rendered_readiness_payload()
        with mock.patch(
            "kernel.lifecycle.task_lifecycle_journal_snapshot_batch_readiness"
            ".check_task_lifecycle_journal_snapshot_batch_readiness"
        ) as check_call, mock.patch(
            "kernel.lifecycle.task_lifecycle_journal_snapshot_batch_readiness"
            ".render_task_lifecycle_journal_snapshot_batch_readiness_check"
        ) as render_call:
            consume_task_lifecycle_journal_snapshot_batch_ci(payload)
            self.assertEqual(check_call.call_count, 0)
            self.assertEqual(render_call.call_count, 0)

    def test_no_restore_cli_db_source_creep(self) -> None:
        source = inspect.getsource(ci_module)
        forbidden_imports = (
            "task_lifecycle_journal_snapshot_batch_readiness",
            "task_lifecycle_journal_snapshot_batch",
            "task_lifecycle_journal_snapshot_contract",
            "task_recovery",
            "recovery_session_host",
            "recovery_session_host_cli",
            "recovery_cli",
            "kernel.stores.sqlite",
            "sqlite3",
            "os",
            "pathlib",
        )
        for name in forbidden_imports:
            with self.subTest(name=name):
                self.assertNotIn(f"import {name}", source)
                self.assertNotIn(f"from kernel.lifecycle.{name}", source)
        forbidden_runtime = (
            "open(",
            "os.environ",
            "subprocess.",
            "Path(",
            "TaskRecoveryReader",
            "open_connection",
            "apply_migrations",
            "KernelUnitOfWork",
            ".restore",
            "restore_dry_run",
            "build_parser",
        )
        for term in forbidden_runtime:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


class TestBatchReadinessEndToEnd(unittest.TestCase):
    def test_real_reader_batch_readiness_ci_acceptance(self) -> None:
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

            snapshot = _read_real_snapshot(db_path, task_id)
            rendered_batch = _rendered_batch([snapshot])
            readiness = check_task_lifecycle_journal_snapshot_batch_readiness(
                rendered_batch
            )
            rendered_readiness = (
                render_task_lifecycle_journal_snapshot_batch_readiness_check(
                    readiness
                )
            )
            ci_result = consume_task_lifecycle_journal_snapshot_batch_ci(
                rendered_readiness
            )

            self.assertIs(rendered_batch["ready"], True)
            self.assertIs(readiness.ready, True)
            self.assertIs(rendered_readiness["ready"], True)
            self.assertIs(ci_result["ci_ok"], True)
            self.assertEqual(_table_row_counts(db_path), before_counts)
            self.assertFalse(missing_path.exists())
            _assert_json_safe(rendered_batch)
            _assert_json_safe(rendered_readiness)
            _assert_json_safe(ci_result)

    def test_real_reader_duplicate_batch_failure_end_to_end(self) -> None:
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
            before_counts = _table_row_counts(db_path)

            snapshot = _read_real_snapshot(db_path, task_id)
            rendered_batch = _rendered_batch([snapshot, copy.deepcopy(snapshot)])
            readiness = check_task_lifecycle_journal_snapshot_batch_readiness(
                rendered_batch
            )
            rendered_readiness = (
                render_task_lifecycle_journal_snapshot_batch_readiness_check(
                    readiness
                )
            )
            ci_result = consume_task_lifecycle_journal_snapshot_batch_ci(
                rendered_readiness
            )

            self.assertIs(rendered_batch["ready"], False)
            self.assertEqual(rendered_batch["reason_code"], "not_ready")
            self.assertEqual(readiness.reason_code, "not_ready")
            self.assertIs(ci_result["ci_ok"], False)
            self.assertEqual(ci_result["reason_code"], "not_ready")
            self.assertEqual(_table_row_counts(db_path), before_counts)
            self.assertFalse(missing_path.exists())
            _assert_json_safe(rendered_batch)
            _assert_json_safe(rendered_readiness)
            _assert_json_safe(ci_result)


if __name__ == "__main__":
    unittest.main()
