"""P2-02 evidence replay readiness contract and CI consumer tests."""

from __future__ import annotations

import ast
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle import evidence_replay_readiness_ci as ci_module
from kernel.lifecycle import (
    evidence_replay_readiness_contract as contract_module,
)
from kernel.lifecycle.evidence_replay_readiness import (
    build_evidence_replay_readiness_envelope,
    render_evidence_replay_readiness_envelope,
)
from kernel.lifecycle.evidence_replay_readiness_ci import (
    consume_evidence_replay_readiness_ci,
    evidence_replay_readiness_ci_manifest,
)
from kernel.lifecycle.evidence_replay_readiness_contract import (
    EvidenceReplayReadinessContractCheck,
    check_evidence_replay_readiness_contract,
    evidence_replay_readiness_contract_manifest,
    render_evidence_replay_readiness_contract_check,
)
from kernel.stores.sqlite.repositories import AuditRepository
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


EXPECTED_CONTRACT_MANIFEST = {
    "surface": "evidence_replay_readiness_contract",
    "version": 1,
    "input_shape": "rendered_evidence_replay_readiness_envelope",
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_evidence_replay_envelope", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "envelope_invalid",
        "envelope_shape_mismatch",
        "envelope_counter_invalid",
        "envelope_bool_invalid",
        "envelope_list_invalid",
        "envelope_mapping_invalid",
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
    "EvidenceReplayReadinessEnvelope(",
    "EvidenceReplayReadinessContractCheck(",
    " object at 0x",
    "<sqlite3.",
)


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "task_id": "task-001",
        "record_type": "evidence_closure",
        "artifact_refs": ["ra-001"],
        "stage": "evidence",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _rendered_envelope(items: object | None = None) -> dict[str, object]:
    envelope = build_evidence_replay_readiness_envelope(
        items if items is not None else [_item()]
    )
    return render_evidence_replay_readiness_envelope(envelope)


def _rendered_contract_payload(
    rendered_envelope: dict[str, object] | None = None,
) -> dict[str, object]:
    check = check_evidence_replay_readiness_contract(
        rendered_envelope if rendered_envelope is not None else _rendered_envelope()
    )
    return render_evidence_replay_readiness_contract_check(check)


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


class TestEvidenceReplayReadinessContract(unittest.TestCase):
    def test_accepts_valid_rendered_p2_01_envelope(self) -> None:
        check = check_evidence_replay_readiness_contract(_rendered_envelope())

        self.assertIsInstance(check, EvidenceReplayReadinessContractCheck)
        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        self.assertEqual(
            check.contract["surface"], "evidence_replay_readiness_contract"
        )

    def test_rejects_non_mapping_payload(self) -> None:
        check = check_evidence_replay_readiness_contract("bad")

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "invalid_evidence_replay_envelope")
        self.assertEqual(check.failures, ("payload_not_mapping",))

    def test_rejects_top_level_shape_mismatch(self) -> None:
        payload = _rendered_envelope()
        payload["extra"] = True

        check = check_evidence_replay_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_evidence_replay_envelope")
        self.assertIn("payload_shape_mismatch", check.failures)

    def test_rejects_invalid_failures_list(self) -> None:
        payload = _rendered_envelope()
        payload["failures"] = ["ok", 1]

        check = check_evidence_replay_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_evidence_replay_envelope")
        self.assertIn("payload_failures_invalid", check.failures)

    def test_rejects_invalid_envelope_object(self) -> None:
        payload = _rendered_envelope()
        payload["envelope"] = []

        check = check_evidence_replay_readiness_contract(payload)

        self.assertEqual(check.failures, ("envelope_invalid",))

    def test_rejects_missing_envelope_keys(self) -> None:
        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope.pop("item_count")

        check = check_evidence_replay_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_evidence_replay_envelope")
        self.assertIn("envelope_shape_mismatch", check.failures)

    def test_rejects_invalid_counters_and_bool_as_int(self) -> None:
        for field in (
            "version",
            "item_count",
            "unique_task_count",
            "artifact_ref_count",
            "missing_artifact_ref_count",
            "cli_command_count",
            "runtime_dependency_count",
        ):
            with self.subTest(field=field):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = True

                check = check_evidence_replay_readiness_contract(payload)

                self.assertIn("envelope_counter_invalid", check.failures)

    def test_rejects_invalid_bool_fields(self) -> None:
        for field in (
            "operator_safe",
            "restore_supported",
            "durable_writes",
            "json_safe",
        ):
            with self.subTest(field=field):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = "bad"

                check = check_evidence_replay_readiness_contract(payload)

                self.assertIn("envelope_bool_invalid", check.failures)

    def test_rejects_invalid_list_fields(self) -> None:
        for field in ("task_ids", "duplicate_artifact_refs"):
            with self.subTest(field=field):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = ["ok", 1]

                check = check_evidence_replay_readiness_contract(payload)

                self.assertIn("envelope_list_invalid", check.failures)

    def test_rejects_invalid_mapping_count_fields(self) -> None:
        cases = [
            ("record_type_counts", {"x": True}),
            ("stage_counts", {"x": -1}),
            ("stage_counts", []),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = value

                check = check_evidence_replay_readiness_contract(payload)

                self.assertIn("envelope_mapping_invalid", check.failures)

    def test_detects_status_inconsistency(self) -> None:
        payload = _rendered_envelope()
        payload["reason_code"] = "not_ready"

        check = check_evidence_replay_readiness_contract(payload)

        self.assertIn("status_inconsistent", check.failures)

    def test_detects_safety_inconsistency(self) -> None:
        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope["restore_supported"] = True

        check = check_evidence_replay_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_evidence_replay_envelope")
        self.assertIn("safety_inconsistent", check.failures)

    def test_detects_safety_inconsistency_unique_task_count(self) -> None:
        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope["unique_task_count"] = 5

        check = check_evidence_replay_readiness_contract(payload)

        self.assertIn("safety_inconsistent", check.failures)

    def test_marks_operator_safe_false_envelope_as_not_ready(self) -> None:
        payload = _rendered_envelope([_item(), _item(record_type="stage_entered")])
        self.assertIs(payload["ready"], False)
        self.assertEqual(payload["reason_code"], "not_ready")

        check = check_evidence_replay_readiness_contract(payload)

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "not_ready")
        self.assertEqual(check.failures, ("operator_not_safe",))

    def test_preserves_deterministic_failure_ordering(self) -> None:
        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope["operator_safe"] = "bad"
        envelope["task_ids"] = ["ok", 1]
        payload["failures"] = ["ok", 1]

        check = check_evidence_replay_readiness_contract(payload)

        idx_failures_invalid = check.failures.index("payload_failures_invalid")
        idx_bool = check.failures.index("envelope_bool_invalid")
        idx_list = check.failures.index("envelope_list_invalid")
        self.assertLess(idx_failures_invalid, idx_bool)
        self.assertLess(idx_bool, idx_list)

    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            evidence_replay_readiness_contract_manifest(),
            EXPECTED_CONTRACT_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = evidence_replay_readiness_contract_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"

        self.assertEqual(
            evidence_replay_readiness_contract_manifest(),
            EXPECTED_CONTRACT_MANIFEST,
        )

    def test_renderer_exact_shape(self) -> None:
        check = check_evidence_replay_readiness_contract(_rendered_envelope())

        rendered = render_evidence_replay_readiness_contract_check(check)

        self.assertEqual(
            set(rendered.keys()),
            {"ready", "reason_code", "failures", "contract"},
        )
        self.assertEqual(rendered["ready"], True)
        self.assertEqual(rendered["reason_code"], "ready")
        self.assertEqual(rendered["failures"], [])
        self.assertEqual(rendered["contract"], EXPECTED_CONTRACT_MANIFEST)

    def test_renderer_defensive_copy(self) -> None:
        check = check_evidence_replay_readiness_contract(_rendered_envelope())
        rendered = render_evidence_replay_readiness_contract_check(check)
        rendered["contract"]["surface"] = "tampered"  # type: ignore[index]
        rendered["contract"]["failure_values"].append(  # type: ignore[index]
            "INJECTED"
        )

        rendered_again = render_evidence_replay_readiness_contract_check(check)

        self.assertEqual(rendered_again["contract"], EXPECTED_CONTRACT_MANIFEST)

    def test_output_json_safe(self) -> None:
        rendered = _rendered_contract_payload()
        _assert_json_safe(rendered)

    def test_no_runtime_repr_leakage(self) -> None:
        rendered = _rendered_contract_payload()
        _assert_no_runtime_repr(rendered)

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(contract_module.__all__),
            sorted(
                [
                    "EvidenceReplayReadinessContractCheck",
                    "check_evidence_replay_readiness_contract",
                    "evidence_replay_readiness_contract_manifest",
                    "render_evidence_replay_readiness_contract_check",
                ]
            ),
        )
        check = check_evidence_replay_readiness_contract(_rendered_envelope())
        with self.assertRaises(Exception):
            check.ready = False  # type: ignore[misc]

    def test_no_restore_cli_db_or_runtime_source_creep(self) -> None:
        _assert_no_source_creep(contract_module)


class TestEvidenceReplayReadinessCiConsumer(unittest.TestCase):
    def test_accepts_rendered_contract_ready_payload(self) -> None:
        result = consume_evidence_replay_readiness_ci(
            _rendered_contract_payload()
        )

        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["surface"], "evidence_replay_readiness_contract"
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
        result = consume_evidence_replay_readiness_ci(None)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["invalid_ci_payload"])
        self.assertIs(result["contract_ready"], False)
        self.assertEqual(result["contract_reason_code"], "invalid_ci_payload")
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])

    def test_not_ready_payload_returns_ci_ok_false(self) -> None:
        not_ready_envelope = _rendered_envelope(
            [_item(), _item(record_type="stage_entered")]
        )
        payload = _rendered_contract_payload(not_ready_envelope)

        result = consume_evidence_replay_readiness_ci(payload)

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
            ("cli_commands", ["evidence"], "has_cli_commands"),
            ("runtime_dependencies", ["sqlite3"], "has_runtime_dependencies"),
            ("json_safe", False, "not_json_safe"),
        ]
        for field, value, expected_failure in hazard_cases:
            with self.subTest(field=field):
                payload = _rendered_contract_payload()
                contract = payload["contract"]
                assert isinstance(contract, dict)
                contract[field] = value

                result = consume_evidence_replay_readiness_ci(payload)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn(expected_failure, result["failures"])

    def test_output_exact_shape(self) -> None:
        result = consume_evidence_replay_readiness_ci(
            _rendered_contract_payload()
        )

        self.assertEqual(list(result.keys()), EXPECTED_CI_OUTPUT_KEYS)

    def test_manifest_defensive_copy(self) -> None:
        manifest = evidence_replay_readiness_ci_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"
        manifest_again = evidence_replay_readiness_ci_manifest()

        self.assertEqual(
            manifest_again["surface"], "evidence_replay_readiness_ci"
        )
        self.assertNotIn("INJECTED", manifest_again["failure_values"])
        _assert_json_safe(manifest_again)

    def test_output_json_safe(self) -> None:
        result = consume_evidence_replay_readiness_ci(
            _rendered_contract_payload()
        )

        _assert_json_safe(result)

    def test_no_upstream_calls(self) -> None:
        payload = _rendered_contract_payload()
        with mock.patch(
            "kernel.lifecycle.evidence_replay_readiness_contract"
            ".check_evidence_replay_readiness_contract"
        ) as check_call, mock.patch(
            "kernel.lifecycle.evidence_replay_readiness_contract"
            ".render_evidence_replay_readiness_contract_check"
        ) as render_call, mock.patch(
            "kernel.lifecycle.evidence_replay_readiness"
            ".build_evidence_replay_readiness_envelope"
        ) as build_call:
            consume_evidence_replay_readiness_ci(payload)
            self.assertEqual(check_call.call_count, 0)
            self.assertEqual(render_call.call_count, 0)
            self.assertEqual(build_call.call_count, 0)

    def test_no_restore_cli_db_or_runtime_source_creep(self) -> None:
        _assert_no_source_creep(ci_module)


class TestEvidenceReplayReadinessEndToEnd(unittest.TestCase):
    def test_real_audit_record_full_pipeline_to_ci_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "evidence-readiness.db"
            conn = open_connection(db_path)
            try:
                apply_migrations(conn)
                ledger = AppendOnlyLedger(
                    repository=AuditRepository(conn),
                    actor_identity="p2_02_contract_ci_test",
                )
                audit_id = ledger.append(
                    record_type="evidence_closure",
                    task_id="task-real",
                    root_revision_id="rev-real",
                    artifact_refs=["ra-real", "rev-real"],
                    payload={"stage": "evidence"},
                    replay_anchor_id="ra-real",
                )
                row = conn.execute(
                    "SELECT * FROM audit_records WHERE audit_record_id = ?;",
                    (audit_id,),
                ).fetchone()
                self.assertIsNotNone(row)
                payload = json.loads(row["payload_json"])
                rendered = {
                    "task_id": row["task_id"],
                    "record_type": row["record_type"],
                    "artifact_refs": json.loads(row["artifact_refs"]),
                    "stage": payload.get("stage"),
                    "created_at": row["created_at"],
                }
            finally:
                conn.close()

            before_counts = _table_row_counts(db_path)
            envelope = build_evidence_replay_readiness_envelope([rendered])
            rendered_envelope = render_evidence_replay_readiness_envelope(
                envelope
            )
            contract_check = check_evidence_replay_readiness_contract(
                rendered_envelope
            )
            rendered_contract = render_evidence_replay_readiness_contract_check(
                contract_check
            )
            ci_result = consume_evidence_replay_readiness_ci(rendered_contract)
            after_counts = _table_row_counts(db_path)

        self.assertEqual(before_counts, after_counts)
        self.assertIs(ci_result["ci_ok"], True)
        self.assertEqual(ci_result["reason_code"], "ready")
        self.assertEqual(ci_result["failures"], [])
        self.assertEqual(
            ci_result["surface"], "evidence_replay_readiness_contract"
        )
        _assert_json_safe(ci_result)

    def test_failure_pipeline_duplicate_artifact_ref(self) -> None:
        not_ready_envelope = _rendered_envelope(
            [_item(), _item(record_type="stage_entered")]
        )
        self.assertIs(not_ready_envelope["ready"], False)
        self.assertEqual(not_ready_envelope["reason_code"], "not_ready")

        contract_check = check_evidence_replay_readiness_contract(
            not_ready_envelope
        )
        rendered_contract = render_evidence_replay_readiness_contract_check(
            contract_check
        )
        ci_result = consume_evidence_replay_readiness_ci(rendered_contract)

        self.assertIs(contract_check.ready, False)
        self.assertEqual(contract_check.reason_code, "not_ready")
        self.assertEqual(contract_check.failures, ("operator_not_safe",))
        self.assertIs(ci_result["ci_ok"], False)
        self.assertEqual(ci_result["reason_code"], "not_ready")
        _assert_json_safe(ci_result)

    def test_failure_pipeline_missing_artifact_ref(self) -> None:
        not_ready_envelope = _rendered_envelope([_item(artifact_refs=[])])
        self.assertIs(not_ready_envelope["ready"], False)

        contract_check = check_evidence_replay_readiness_contract(
            not_ready_envelope
        )
        rendered_contract = render_evidence_replay_readiness_contract_check(
            contract_check
        )
        ci_result = consume_evidence_replay_readiness_ci(rendered_contract)

        self.assertIs(contract_check.ready, False)
        self.assertEqual(contract_check.reason_code, "not_ready")
        self.assertIs(ci_result["ci_ok"], False)
        self.assertEqual(ci_result["reason_code"], "not_ready")


def _assert_no_source_creep(module: object) -> None:
    source = inspect.getsource(module)
    forbidden_substrings = (
        "sqlite",
        "open_connection",
        "AuditRepository",
        "AppendOnlyLedger",
        "UnitOfWork",
        "KernelUnitOfWork",
        "subprocess",
        "os.environ",
        "argparse",
        "click",
        "socket",
        "queue",
        "threading",
        "asyncio",
        "restore_task",
        "restore_if_allowed",
        "restore_task_from_snapshot",
        "recovery_session_host",
        "task_lifecycle_journal_snapshot",
        "apply_migrations",
    )
    for term in forbidden_substrings:
        if term in source:
            raise AssertionError(f"forbidden source string leaked: {term}")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(node.module or "")
    forbidden_imports = {
        "sqlite3",
        "kernel.stores.sqlite.repositories",
        "kernel.stores.sqlite.unit_of_work",
        "kernel.stores.sqlite.wal_recovery",
        "kernel.evidence.append_only_ledger",
        "kernel.lifecycle.recovery_cli",
        "kernel.lifecycle.recovery_session_host",
        "kernel.lifecycle.recovery_session_host_cli",
        "kernel.lifecycle.task_lifecycle_journal_snapshot_batch",
        "kernel.lifecycle.task_lifecycle_journal_snapshot_batch_ci",
        "kernel.lifecycle.task_lifecycle_journal_snapshot_batch_readiness",
        "kernel.lifecycle.task_lifecycle_journal_snapshot_contract",
        "argparse",
        "click",
        "subprocess",
        "asyncio",
        "socket",
        "queue",
        "threading",
        "os",
        "pathlib",
    }
    leaked = forbidden_imports.intersection(imported_modules)
    if leaked:
        raise AssertionError(f"forbidden imports leaked: {sorted(leaked)}")


if __name__ == "__main__":
    unittest.main()
