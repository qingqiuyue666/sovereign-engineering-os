"""Tests for Minimal Controlled Execution WAL Adapter Integration V1."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_git_diff_check_runner as diff_runner
from kernel.execution import minimal_controlled_git_status_runner as status_runner
from kernel.execution import minimal_controlled_wal_adapter_integration as integration
from kernel.execution.minimal_controlled_execution_contract import (
    DEFERRED_COMMAND_IDS,
    INITIAL_COMMAND_REGISTRY,
)
from kernel.execution import minimal_controlled_wal_adapter_contract as contract


SOURCE_PATH = Path("kernel/execution/minimal_controlled_wal_adapter_integration.py")
RUNNER_PATHS = (
    Path("kernel/execution/minimal_controlled_git_status_runner.py"),
    Path("kernel/execution/minimal_controlled_git_diff_check_runner.py"),
)
PREFLIGHT_PATHS = (
    Path("kernel/execution/minimal_controlled_preflight_sequence.py"),
    Path("kernel/execution/minimal_controlled_preflight_api.py"),
)


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _AsDictEvidence:
    payload: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return dict(self.payload)


def _admission_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-wal-adapter",
        "run_id": "run-wal-adapter",
        "preflight_id": "preflight-wal-adapter",
        "command_id": "git_status_short",
        "request_hash": _hash("request"),
        "decision_hash": _hash("decision"),
        "admission_record_hash": _hash("admission"),
    }
    payload.update(overrides)
    return payload


def _receipt_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
    )
    payload.update(overrides)
    return payload


def _failure_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        failure_bundle_hash=_hash("failure"),
        execution_performed=False,
    )
    payload.pop("admission_record_hash")
    payload.update(overrides)
    return payload


def _binding_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
        execution_performed=True,
    )
    payload.update(overrides)
    return payload


def _preflight_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-wal-adapter",
        "run_id": "run-wal-adapter",
        "preflight_id": "preflight-wal-adapter",
        "preflight_result_hash": _hash("preflight-result"),
        "ordered_command_ids": ("git_status_short", "git_diff_check"),
        "child_request_hashes": (_hash("request-1"), _hash("request-2")),
        "child_decision_hashes": (_hash("decision-1"), _hash("decision-2")),
        "child_admission_hashes": (_hash("admission-1"), _hash("admission-2")),
        "child_receipt_hashes": (_hash("receipt-1"), ""),
        "child_failure_bundle_hashes": ("", _hash("failure-2")),
        "child_verifier_input_hashes": (
            _hash("verifier-input-1"),
            _hash("verifier-input-2"),
        ),
        "child_verifier_binding_hashes": (
            _hash("verifier-binding-1"),
            _hash("verifier-binding-2"),
        ),
        "pre_snapshot_hashes": (_hash("pre-snapshot-1"), _hash("pre-snapshot-2")),
        "post_snapshot_hashes": (_hash("post-snapshot-1"), _hash("post-snapshot-2")),
        "execution_performed": True,
    }
    payload.update(overrides)
    return payload


def _records(
    outcome: str = "receipt",
) -> tuple[contract.MinimalControlledWalAdapterRecord, ...]:
    outcome_record = (
        integration.map_receipt_to_wal_adapter_record(_receipt_evidence(), 2)
        if outcome == "receipt"
        else integration.map_failure_to_wal_adapter_record(_failure_evidence(), 2)
    )
    return (
        integration.map_admission_to_wal_adapter_record(_admission_evidence(), 1),
        outcome_record,
        integration.map_verifier_binding_to_wal_adapter_record(
            _binding_evidence(execution_performed=outcome == "receipt"),
            3,
        ),
        integration.map_preflight_result_to_wal_adapter_record(
            _preflight_evidence(execution_performed=outcome == "receipt"),
            4,
        ),
    )


class MinimalControlledExecutionWalAdapterIntegrationV1Tests(unittest.TestCase):
    def test_all_required_exports_exist(self) -> None:
        required_exports = (
            "WAL_ADAPTER_INTEGRATION_VERSION",
            "MinimalControlledWalAdapterAppendResult",
            "MinimalControlledWalAdapterAppendPlan",
            "MinimalControlledWalAdapterIntegrationResult",
            "map_admission_to_wal_adapter_record",
            "map_receipt_to_wal_adapter_record",
            "map_failure_to_wal_adapter_record",
            "map_verifier_binding_to_wal_adapter_record",
            "map_preflight_result_to_wal_adapter_record",
            "build_minimal_controlled_wal_adapter_batch",
            "replay_minimal_controlled_wal_adapter_records",
            "append_minimal_controlled_wal_adapter_record",
            "append_minimal_controlled_wal_adapter_records",
            "prepare_append_before_execution_plan",
        )
        self.assertEqual(tuple(integration.__all__), required_exports)
        for symbol in required_exports:
            with self.subTest(symbol=symbol):
                self.assertTrue(hasattr(integration, symbol))

    def test_mapper_hashes_are_deterministic(self) -> None:
        first = integration.map_admission_to_wal_adapter_record(
            _AsDictEvidence(_admission_evidence()),
            1,
        )
        second = integration.map_admission_to_wal_adapter_record(_admission_evidence(), 1)

        self.assertEqual(first.record_hash, second.record_hash)
        self.assertEqual(
            first.record_hash,
            contract.minimal_controlled_wal_adapter_record_hash(first),
        )

    def test_mapper_rejects_mismatched_supplied_hash_through_contract_constructor(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "record_hash_mismatch"):
            integration.map_admission_to_wal_adapter_record(
                _admission_evidence(record_hash=_hash("wrong-record")),
                1,
            )

    def test_integration_dataclasses_reject_mismatched_supplied_hashes(self) -> None:
        record = _records()[0]
        append_result = integration.append_minimal_controlled_wal_adapter_record(
            record,
            lambda appended: None,
        )
        with self.assertRaisesRegex(ValueError, "append_result_hash_mismatch"):
            integration.MinimalControlledWalAdapterAppendResult(
                append_result_id=append_result.append_result_id,
                wal_adapter_integration_version=integration.WAL_ADAPTER_INTEGRATION_VERSION,
                accepted=True,
                rejection_reasons=(),
                attempted_record_hash=record.record_hash,
                append_result_hash=_hash("wrong-append-result"),
            )

    def test_map_admission_to_wal_adapter_record_creates_execution_admission(self) -> None:
        record = integration.map_admission_to_wal_adapter_record(_admission_evidence(), 1)

        self.assertEqual(record.record_type, "EXECUTION_ADMISSION")
        self.assertFalse(record.execution_performed)
        self.assertEqual(record.request_hash, _hash("request"))

    def test_map_receipt_to_wal_adapter_record_creates_execution_receipt(self) -> None:
        record = integration.map_receipt_to_wal_adapter_record(_receipt_evidence(), 2)

        self.assertEqual(record.record_type, "EXECUTION_RECEIPT")
        self.assertTrue(record.execution_performed)
        self.assertEqual(record.receipt_hash, _hash("receipt"))

    def test_map_failure_to_wal_adapter_record_creates_execution_failure(self) -> None:
        record = integration.map_failure_to_wal_adapter_record(
            _failure_evidence(execution_performed=True),
            2,
        )

        self.assertEqual(record.record_type, "EXECUTION_FAILURE")
        self.assertTrue(record.execution_performed)
        self.assertEqual(record.failure_bundle_hash, _hash("failure"))

    def test_map_verifier_binding_to_wal_adapter_record_creates_binding(self) -> None:
        record = integration.map_verifier_binding_to_wal_adapter_record(
            _binding_evidence(),
            3,
        )

        self.assertEqual(record.record_type, "EXECUTION_VERIFIER_BINDING")
        self.assertEqual(record.verifier_binding_hash, _hash("verifier-binding"))

    def test_map_preflight_result_to_wal_adapter_record_preserves_child_order(self) -> None:
        record = integration.map_preflight_result_to_wal_adapter_record(
            _preflight_evidence(),
            4,
        )

        self.assertEqual(record.record_type, "PREFLIGHT_RESULT")
        self.assertEqual(record.command_id, "minimal_controlled_preflight")
        self.assertEqual(record.ordered_command_ids, ("git_status_short", "git_diff_check"))
        self.assertEqual(record.child_request_hashes, (_hash("request-1"), _hash("request-2")))

    def test_mappers_reject_raw_output_and_command_line_fields(self) -> None:
        raw_fields = (
            "stdout",
            "stderr",
            "raw_stdout",
            "raw_stderr",
            "stdout_text",
            "stderr_text",
            "command_line",
        )
        for mapper, evidence_factory in _mapper_cases():
            for field_name in raw_fields:
                evidence = evidence_factory(**{field_name: "raw"})
                with self.subTest(mapper=mapper.__name__, field_name=field_name):
                    with self.assertRaisesRegex(ValueError, "wal_adapter_evidence_field_forbidden"):
                        mapper(evidence, 1)

    def test_mappers_reject_execution_material_fields(self) -> None:
        execution_material_fields = (
            "argv",
            "cwd",
            "env",
            "path",
            "executable",
            "timeout",
            "shell",
        )
        for mapper, evidence_factory in _mapper_cases():
            for field_name in execution_material_fields:
                evidence = evidence_factory(**{field_name: "runtime material"})
                with self.subTest(mapper=mapper.__name__, field_name=field_name):
                    with self.assertRaisesRegex(ValueError, "wal_adapter_evidence_field_forbidden"):
                        mapper(evidence, 1)

    def test_mappers_reject_missing_required_hashes(self) -> None:
        cases = (
            (
                integration.map_admission_to_wal_adapter_record,
                _admission_evidence,
                "request_hash",
            ),
            (integration.map_receipt_to_wal_adapter_record, _receipt_evidence, "receipt_hash"),
            (
                integration.map_failure_to_wal_adapter_record,
                _failure_evidence,
                "failure_bundle_hash",
            ),
            (
                integration.map_verifier_binding_to_wal_adapter_record,
                _binding_evidence,
                "verifier_binding_hash",
            ),
            (
                integration.map_preflight_result_to_wal_adapter_record,
                _preflight_evidence,
                "preflight_result_hash",
            ),
        )
        for mapper, evidence_factory, field_name in cases:
            evidence = evidence_factory()
            evidence.pop(field_name)
            with self.subTest(mapper=mapper.__name__, field_name=field_name):
                with self.assertRaisesRegex(ValueError, field_name + "_required"):
                    mapper(evidence, 1)

    def test_mappers_reject_invalid_sha256_hashes(self) -> None:
        for mapper, evidence_factory in _mapper_cases():
            evidence = evidence_factory(request_hash="not-a-sha256")
            if mapper is integration.map_preflight_result_to_wal_adapter_record:
                evidence = evidence_factory(preflight_result_hash="not-a-sha256")
            with self.subTest(mapper=mapper.__name__):
                with self.assertRaisesRegex(ValueError, "must_be_sha256"):
                    mapper(evidence, 1)

    def test_mappers_reject_non_positive_sequence(self) -> None:
        for mapper, evidence_factory in _mapper_cases():
            with self.subTest(mapper=mapper.__name__):
                with self.assertRaisesRegex(ValueError, "sequence_must_be_positive"):
                    mapper(evidence_factory(), 0)

    def test_mappers_reject_record_type_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "record_type_override_not_allowed"):
            integration.map_receipt_to_wal_adapter_record(
                _receipt_evidence(record_type="UNBOUNDED_EXECUTION"),
                2,
            )

    def test_build_minimal_controlled_wal_adapter_batch_accepts_ordered_records(self) -> None:
        records = _records()
        batch = integration.build_minimal_controlled_wal_adapter_batch(records)

        self.assertEqual(batch.record_count, 4)
        self.assertEqual(batch.first_sequence, 1)
        self.assertEqual(batch.last_sequence, 4)
        self.assertEqual(
            batch.batch_hash,
            contract.minimal_controlled_wal_adapter_batch_hash(batch),
        )

    def test_replay_minimal_controlled_wal_adapter_records_accepts_valid_records(self) -> None:
        result = integration.replay_minimal_controlled_wal_adapter_records(_records())

        self.assertTrue(result.accepted, result.rejection_reasons)
        self.assertEqual(result.rejection_reasons, ())

    def test_replay_rejects_reordered_or_tampered_records(self) -> None:
        reordered = (
            integration.map_receipt_to_wal_adapter_record(_receipt_evidence(), 1),
            integration.map_admission_to_wal_adapter_record(_admission_evidence(), 2),
            integration.map_verifier_binding_to_wal_adapter_record(_binding_evidence(), 3),
            integration.map_preflight_result_to_wal_adapter_record(_preflight_evidence(), 4),
        )
        reordered_result = integration.replay_minimal_controlled_wal_adapter_records(reordered)
        self.assertFalse(reordered_result.accepted)
        self.assertIn("admission_must_be_first", reordered_result.rejection_reasons)

        tampered = list(_records())
        object.__setattr__(tampered[1], "record_hash", _hash("tampered-record"))
        tampered_result = integration.replay_minimal_controlled_wal_adapter_records(
            tuple(tampered)
        )
        self.assertFalse(tampered_result.accepted)
        self.assertIn("record_hash_mismatch", ",".join(tampered_result.rejection_reasons))

    def test_append_minimal_controlled_wal_adapter_record_accepts_success(self) -> None:
        appended: list[contract.MinimalControlledWalAdapterRecord] = []
        record = _records()[0]

        result = integration.append_minimal_controlled_wal_adapter_record(
            record,
            appended.append,
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.attempted_record_hash, record.record_hash)
        self.assertEqual(appended, [record])

    def test_append_minimal_controlled_wal_adapter_record_fails_closed(self) -> None:
        def failing_append(_record: contract.MinimalControlledWalAdapterRecord) -> None:
            raise RuntimeError("append unavailable")

        result = integration.append_minimal_controlled_wal_adapter_record(
            _records()[0],
            failing_append,
        )

        self.assertFalse(result.accepted)
        self.assertIn("WAL_ADAPTER_APPEND_FAILED", result.rejection_reasons)
        self.assertIn("EXECUTION_NOT_ATTEMPTED", result.rejection_reasons)

    def test_append_minimal_controlled_wal_adapter_records_stops_after_first_failure(
        self,
    ) -> None:
        records = _records()
        attempted: list[str] = []

        def fail_on_second(record: contract.MinimalControlledWalAdapterRecord) -> None:
            attempted.append(record.record_hash)
            if len(attempted) == 2:
                raise RuntimeError("second append failed")

        results = integration.append_minimal_controlled_wal_adapter_records(
            records,
            fail_on_second,
        )

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].accepted)
        self.assertFalse(results[1].accepted)
        self.assertEqual(attempted, [records[0].record_hash, records[1].record_hash])

    def test_prepare_append_before_execution_plan_allows_after_admission_success(self) -> None:
        records = _records()
        append_result = integration.append_minimal_controlled_wal_adapter_record(
            records[0],
            lambda appended: None,
        )

        plan = integration.prepare_append_before_execution_plan(records, (append_result,))

        self.assertTrue(plan.append_before_execution)
        self.assertTrue(plan.execution_may_proceed)
        self.assertEqual(plan.rejection_reasons, ())

    def test_prepare_append_before_execution_plan_blocks_after_admission_failure(self) -> None:
        records = _records()

        def fail(_record: contract.MinimalControlledWalAdapterRecord) -> None:
            raise RuntimeError("append failed")

        append_result = integration.append_minimal_controlled_wal_adapter_record(
            records[0],
            fail,
        )
        plan = integration.prepare_append_before_execution_plan(records, (append_result,))

        self.assertFalse(plan.execution_may_proceed)
        self.assertIn("WAL_ADAPTER_APPEND_FAILED", plan.rejection_reasons)
        self.assertIn("EXECUTION_PERFORMED_CLAIM_BLOCKED", plan.rejection_reasons)

    def test_prepare_append_before_execution_plan_rejects_outcome_before_admission(
        self,
    ) -> None:
        records = (
            integration.map_receipt_to_wal_adapter_record(_receipt_evidence(), 1),
            integration.map_admission_to_wal_adapter_record(_admission_evidence(), 2),
            integration.map_verifier_binding_to_wal_adapter_record(_binding_evidence(), 3),
            integration.map_preflight_result_to_wal_adapter_record(_preflight_evidence(), 4),
        )
        append_result = integration.append_minimal_controlled_wal_adapter_record(
            records[0],
            lambda appended: None,
        )

        plan = integration.prepare_append_before_execution_plan(records, (append_result,))

        self.assertFalse(plan.execution_may_proceed)
        self.assertIn("admission_must_be_first", plan.rejection_reasons)

    def test_prepare_append_before_execution_plan_requires_preflight_result_last(self) -> None:
        records = (
            integration.map_admission_to_wal_adapter_record(_admission_evidence(), 1),
            integration.map_receipt_to_wal_adapter_record(_receipt_evidence(), 2),
            integration.map_preflight_result_to_wal_adapter_record(_preflight_evidence(), 3),
            integration.map_verifier_binding_to_wal_adapter_record(_binding_evidence(), 4),
        )
        append_result = integration.append_minimal_controlled_wal_adapter_record(
            records[0],
            lambda appended: None,
        )

        plan = integration.prepare_append_before_execution_plan(records, (append_result,))

        self.assertFalse(plan.execution_may_proceed)
        self.assertIn("preflight_result_must_be_last", plan.rejection_reasons)

    def test_source_contains_no_process_module(self) -> None:
        self.assertNotIn("subprocess", _source())

    def test_source_contains_no_sqlite3(self) -> None:
        self.assertNotIn("sqlite3", _source())

    def test_source_contains_no_broad_runtime_imports(self) -> None:
        imported = _imported_modules(SOURCE_PATH)
        self.assertFalse(
            any(module == "kernel.runtime" or module.startswith("kernel.runtime.") for module in imported),
            imported,
        )

    def test_source_contains_no_cli_scheduler_daemon_provider_browser_dcc_mcp_imports(
        self,
    ) -> None:
        forbidden = {
            "argparse",
            "click",
            "typer",
            "schedule",
            "daemon",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "bpy",
            "hou",
            "unreal",
            "comfyui",
            "mcp",
        }
        self.assertFalse(forbidden.intersection(_imported_modules(SOURCE_PATH)))

    def test_source_contains_no_file_write_calls(self) -> None:
        self.assertEqual(_file_write_calls(SOURCE_PATH), ())

    def test_source_does_not_export_reserved_preflight_runner(self) -> None:
        reserved_name = "run_minimal_controlled_preflight_with_wal_adapter"
        self.assertNotIn(reserved_name, integration.__all__)
        self.assertFalse(hasattr(integration, reserved_name))
        self.assertNotIn(reserved_name, _source())

    def test_no_production_runner_source_changed_by_integration(self) -> None:
        for path in RUNNER_PATHS + PREFLIGHT_PATHS:
            with self.subTest(path=str(path)):
                self.assertNotIn("minimal_controlled_wal_adapter_integration", path.read_text())
        self.assertEqual(status_runner.EXECUTABLE_COMMAND_IDS, ("git_status_short",))
        self.assertEqual(diff_runner.EXECUTABLE_COMMAND_IDS, ("git_diff_check",))

    def test_no_new_command_ids_were_added(self) -> None:
        self.assertEqual(tuple(INITIAL_COMMAND_REGISTRY), ("git_status_short", "git_diff_check"))

    def test_unittest_discover_tests_and_make_ci_remain_deferred_non_executable(
        self,
    ) -> None:
        self.assertEqual(DEFERRED_COMMAND_IDS, {"unittest_discover_tests", "make_ci"})
        self.assertNotIn("unittest_discover_tests", INITIAL_COMMAND_REGISTRY)
        self.assertNotIn("make_ci", INITIAL_COMMAND_REGISTRY)
        executable_ids = set(status_runner.EXECUTABLE_COMMAND_IDS)
        executable_ids.update(diff_runner.EXECUTABLE_COMMAND_IDS)
        self.assertTrue(DEFERRED_COMMAND_IDS.isdisjoint(executable_ids))


def _mapper_cases():
    return (
        (integration.map_admission_to_wal_adapter_record, _admission_evidence),
        (integration.map_receipt_to_wal_adapter_record, _receipt_evidence),
        (integration.map_failure_to_wal_adapter_record, _failure_evidence),
        (integration.map_verifier_binding_to_wal_adapter_record, _binding_evidence),
        (integration.map_preflight_result_to_wal_adapter_record, _preflight_evidence),
    )


def _source() -> str:
    return SOURCE_PATH.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _imported_modules(path: Path) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _file_write_calls(path: Path) -> tuple[str, ...]:
    calls: list[str] = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"write_text", "write_bytes"}:
                calls.append(node.func.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "open" and _open_call_writes(node):
                calls.append("open")
    return tuple(calls)


def _open_call_writes(node: ast.Call) -> bool:
    mode: object = "r"
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        mode = node.args[1].value
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            mode = keyword.value.value
    return isinstance(mode, str) and any(flag in mode for flag in ("w", "a", "+", "x"))


if __name__ == "__main__":
    unittest.main()

