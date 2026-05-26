"""Tests for the callable-only WAL-gated preflight wrapper."""

from __future__ import annotations

import ast
import hashlib
import inspect
from unittest import mock
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_git_diff_check_runner as diff_runner
from kernel.execution import minimal_controlled_git_status_runner as status_runner
from kernel.execution import minimal_controlled_wal_adapter_integration as integration
from kernel.execution import minimal_controlled_wal_gated_preflight_wrapper as wrapper
from kernel.execution.minimal_controlled_execution_contract import (
    DEFERRED_COMMAND_IDS,
    INITIAL_COMMAND_REGISTRY,
)


SOURCE_PATH = Path("kernel/execution/minimal_controlled_wal_gated_preflight_wrapper.py")
RUNNER_PATHS = (
    Path("kernel/execution/minimal_controlled_git_status_runner.py"),
    Path("kernel/execution/minimal_controlled_git_diff_check_runner.py"),
)
PREFLIGHT_SEQUENCE_PATH = Path("kernel/execution/minimal_controlled_preflight_sequence.py")
PREFLIGHT_API_PATH = Path("kernel/execution/minimal_controlled_preflight_api.py")
PREFLIGHT_PATHS = (PREFLIGHT_SEQUENCE_PATH, PREFLIGHT_API_PATH)
WRAPPER_MODULE_NAME = "kernel.execution.minimal_controlled_wal_gated_preflight_wrapper"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _admission_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-wal-gated-preflight",
        "run_id": "run-wal-gated-preflight",
        "preflight_id": "preflight-wal-gated",
        "command_id": "git_status_short",
        "request_hash": _hash("request"),
        "decision_hash": _hash("decision"),
        "admission_record_hash": _hash("admission"),
    }
    payload.update(overrides)
    return payload


def _receipt_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        outcome_type="EXECUTION_RECEIPT",
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
    )
    payload.update(overrides)
    return payload


def _failure_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        record_type="EXECUTION_FAILURE",
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
        "task_id": "task-wal-gated-preflight",
        "run_id": "run-wal-gated-preflight",
        "preflight_id": "preflight-wal-gated",
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


def _wrapper_input(
    *,
    outcome: str = "receipt",
    admission_evidence: dict[str, object] | None = None,
    outcome_evidence: dict[str, object] | None = None,
    binding_evidence: dict[str, object] | None = None,
    preflight_evidence: dict[str, object] | None = None,
    wrapper_input_hash: str = "",
) -> wrapper.MinimalControlledWalGatedPreflightInput:
    outcome_payload = outcome_evidence
    if outcome_payload is None:
        outcome_payload = _receipt_evidence() if outcome == "receipt" else _failure_evidence()
    execution_performed = outcome == "receipt"
    return wrapper.MinimalControlledWalGatedPreflightInput(
        wrapper_input_id="wrapper-input-001",
        wal_gated_preflight_wrapper_version=wrapper.WAL_GATED_PREFLIGHT_WRAPPER_VERSION,
        task_id="task-wal-gated-preflight",
        run_id="run-wal-gated-preflight",
        preflight_id="preflight-wal-gated",
        admission_evidence=admission_evidence or _admission_evidence(),
        outcome_evidence=outcome_payload,
        verifier_binding_evidence=binding_evidence
        or _binding_evidence(execution_performed=execution_performed),
        preflight_result_evidence=preflight_evidence
        or _preflight_evidence(execution_performed=execution_performed),
        wrapper_input_hash=wrapper_input_hash,
    )


class MinimalControlledWalGatedPreflightWrapperV1Tests(unittest.TestCase):
    def test_all_required_exports_exist(self) -> None:
        required_exports = (
            "WAL_GATED_PREFLIGHT_WRAPPER_VERSION",
            "MinimalControlledWalGatedPreflightInput",
            "MinimalControlledWalGatedPreflightResult",
            "build_minimal_controlled_wal_gated_preflight_records",
            "run_minimal_controlled_wal_gated_preflight_wrapper",
        )
        self.assertEqual(tuple(wrapper.__all__), required_exports)
        for symbol in required_exports:
            with self.subTest(symbol=symbol):
                self.assertTrue(hasattr(wrapper, symbol))

    def test_input_hash_is_deterministic(self) -> None:
        first = _wrapper_input()
        second = _wrapper_input()

        self.assertEqual(first.wrapper_input_hash, second.wrapper_input_hash)
        self.assertEqual(
            first.wrapper_input_hash,
            wrapper.minimal_controlled_wal_gated_preflight_input_hash(first),
        )

    def test_result_hash_is_deterministic(self) -> None:
        first = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(),
            lambda record: None,
        )
        second = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(),
            lambda record: None,
        )

        self.assertEqual(first.wrapper_result_hash, second.wrapper_result_hash)
        self.assertEqual(
            first.wrapper_result_hash,
            wrapper.minimal_controlled_wal_gated_preflight_result_hash(first),
        )

    def test_mismatched_supplied_input_hash_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "wrapper_input_hash_mismatch"):
            _wrapper_input(wrapper_input_hash=_hash("wrong-input"))

    def test_mismatched_supplied_result_hash_is_rejected(self) -> None:
        result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(),
            lambda record: None,
        )
        with self.assertRaisesRegex(ValueError, "wrapper_result_hash_mismatch"):
            wrapper.MinimalControlledWalGatedPreflightResult(
                wrapper_result_id=result.wrapper_result_id,
                wal_gated_preflight_wrapper_version=wrapper.WAL_GATED_PREFLIGHT_WRAPPER_VERSION,
                task_id=result.task_id,
                run_id=result.run_id,
                preflight_id=result.preflight_id,
                ordered_record_hashes=result.ordered_record_hashes,
                append_result_hashes=result.append_result_hashes,
                append_plan_hash=result.append_plan_hash,
                batch_hash=result.batch_hash,
                replay_result_hash=result.replay_result_hash,
                integration_result_hash=result.integration_result_hash,
                execution_may_proceed=result.execution_may_proceed,
                accepted=result.accepted,
                rejection_reasons=result.rejection_reasons,
                wrapper_result_hash=_hash("wrong-result"),
            )

    def test_valid_receipt_shaped_evidence_builds_records_in_exact_order(self) -> None:
        records = wrapper.build_minimal_controlled_wal_gated_preflight_records(_wrapper_input())

        self.assertEqual(
            tuple(record.record_type for record in records),
            (
                "EXECUTION_ADMISSION",
                "EXECUTION_RECEIPT",
                "EXECUTION_VERIFIER_BINDING",
                "PREFLIGHT_RESULT",
            ),
        )
        self.assertEqual(tuple(record.sequence for record in records), (1, 2, 3, 4))

    def test_valid_failure_shaped_evidence_builds_records_in_exact_order(self) -> None:
        records = wrapper.build_minimal_controlled_wal_gated_preflight_records(
            _wrapper_input(outcome="failure")
        )

        self.assertEqual(
            tuple(record.record_type for record in records),
            (
                "EXECUTION_ADMISSION",
                "EXECUTION_FAILURE",
                "EXECUTION_VERIFIER_BINDING",
                "PREFLIGHT_RESULT",
            ),
        )
        self.assertEqual(tuple(record.sequence for record in records), (1, 2, 3, 4))

    def test_missing_or_unknown_outcome_type_is_rejected(self) -> None:
        missing = _receipt_evidence()
        missing.pop("outcome_type")
        with self.assertRaisesRegex(ValueError, "outcome_type_required"):
            wrapper.build_minimal_controlled_wal_gated_preflight_records(
                _wrapper_input(outcome_evidence=missing)
            )

        with self.assertRaisesRegex(ValueError, "outcome_type_invalid"):
            wrapper.build_minimal_controlled_wal_gated_preflight_records(
                _wrapper_input(outcome_evidence=_receipt_evidence(outcome_type="EXECUTE_ALL"))
            )

    def test_raw_stdout_stderr_fields_are_rejected(self) -> None:
        raw_fields = (
            "stdout",
            "stderr",
            "raw_stdout",
            "raw_stderr",
            "stdout_text",
            "stderr_text",
            "command_line",
        )
        for evidence_field in _evidence_field_names():
            for field_name in raw_fields:
                with self.subTest(evidence_field=evidence_field, field_name=field_name):
                    with self.assertRaisesRegex(
                        ValueError,
                        "wal_gated_preflight_evidence_field_forbidden",
                    ):
                        _input_with_evidence_override(evidence_field, {field_name: "raw"})

    def test_execution_material_fields_are_rejected(self) -> None:
        execution_material_fields = (
            "argv",
            "cwd",
            "env",
            "path",
            "executable",
            "timeout",
            "shell",
        )
        for evidence_field in _evidence_field_names():
            for field_name in execution_material_fields:
                with self.subTest(evidence_field=evidence_field, field_name=field_name):
                    with self.assertRaisesRegex(
                        ValueError,
                        "wal_gated_preflight_evidence_field_forbidden",
                    ):
                        _input_with_evidence_override(evidence_field, {field_name: "runtime"})

    def test_wrapper_accepts_valid_receipt_evidence_when_append_callable_succeeds(self) -> None:
        appended = []

        result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(),
            appended.append,
        )

        self.assertTrue(result.accepted, result.rejection_reasons)
        self.assertTrue(result.execution_may_proceed)
        self.assertEqual(len(appended), 4)
        self.assertEqual(len(result.append_result_hashes), 4)

    def test_wrapper_accepts_valid_failure_evidence_when_append_callable_succeeds(self) -> None:
        appended = []

        result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(outcome="failure"),
            appended.append,
        )

        self.assertTrue(result.accepted, result.rejection_reasons)
        self.assertTrue(result.execution_may_proceed)
        self.assertEqual(len(appended), 4)
        self.assertEqual(len(result.append_result_hashes), 4)

    def test_wrapper_blocks_execution_when_first_append_fails(self) -> None:
        def fail_first(_record: object) -> None:
            raise RuntimeError("append unavailable")

        result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(),
            fail_first,
        )

        self.assertFalse(result.accepted)
        self.assertFalse(result.execution_may_proceed)
        self.assertIn("WAL_ADAPTER_APPEND_FAILED", result.rejection_reasons)
        self.assertIn("EXECUTION_NOT_ATTEMPTED", result.rejection_reasons)

    def test_wrapper_stops_append_attempts_after_first_append_failure(self) -> None:
        attempted: list[str] = []

        def fail_on_second(record: object) -> None:
            attempted.append(record.record_hash)  # type: ignore[attr-defined]
            if len(attempted) == 2:
                raise RuntimeError("second append failed")

        result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(),
            fail_on_second,
        )

        self.assertFalse(result.accepted)
        self.assertEqual(len(attempted), 2)
        self.assertEqual(len(result.append_result_hashes), 2)

    def test_wrapper_result_includes_append_failure_reasons(self) -> None:
        def fail_first(_record: object) -> None:
            raise RuntimeError("append unavailable")

        result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
            _wrapper_input(outcome="failure"),
            fail_first,
        )

        self.assertIn("WAL_ADAPTER_APPEND_FAILED", result.rejection_reasons)
        self.assertIn("EXECUTION_NOT_ATTEMPTED", result.rejection_reasons)

    def test_wrapper_rejects_replay_or_integration_failure(self) -> None:
        rejected = integration.MinimalControlledWalAdapterIntegrationResult(
            integration_result_id="wal-adapter-integration-result-rejected",
            wal_adapter_integration_version=integration.WAL_ADAPTER_INTEGRATION_VERSION,
            task_id="task-wal-gated-preflight",
            run_id="run-wal-gated-preflight",
            preflight_id="preflight-wal-gated",
            ordered_record_hashes=(_hash("record-1"),),
            batch_hash=_hash("batch"),
            replay_result_hash=_hash("replay"),
            accepted=False,
            rejection_reasons=("record_hash_mismatch",),
        )

        with mock.patch.object(
            wrapper,
            "replay_minimal_controlled_wal_adapter_records",
            return_value=rejected,
        ):
            result = wrapper.run_minimal_controlled_wal_gated_preflight_wrapper(
                _wrapper_input(),
                lambda record: None,
            )

        self.assertFalse(result.accepted)
        self.assertFalse(result.execution_may_proceed)
        self.assertIn("record_hash_mismatch", result.rejection_reasons)
        self.assertEqual(result.integration_result_hash, rejected.integration_result_hash)

    def test_wrapper_does_not_import_subprocess(self) -> None:
        self.assertFalse(_imports_module(SOURCE_PATH, "subprocess"))
        self.assertNotIn("subprocess", _source(SOURCE_PATH))

    def test_wrapper_does_not_import_sqlite3(self) -> None:
        self.assertFalse(_imports_module(SOURCE_PATH, "sqlite3"))
        self.assertNotIn("sqlite3", _source(SOURCE_PATH))

    def test_wrapper_does_not_import_kernel_runtime(self) -> None:
        imported = _imported_modules(SOURCE_PATH)
        self.assertFalse(
            any(module == "kernel.runtime" or module.startswith("kernel.runtime.") for module in imported),
            imported,
        )

    def test_wrapper_does_not_import_cli_scheduler_daemon_provider_browser_dcc_mcp_modules(
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

    def test_wrapper_contains_no_file_write_calls(self) -> None:
        self.assertEqual(_file_write_calls(SOURCE_PATH), ())

    def test_wrapper_does_not_import_existing_runner_modules(self) -> None:
        source = _source(SOURCE_PATH)
        self.assertNotIn("minimal_controlled_git_status_runner", source)
        self.assertNotIn("minimal_controlled_git_diff_check_runner", source)

    def test_wrapper_does_not_import_preflight_api(self) -> None:
        self.assertNotIn("minimal_controlled_preflight_api", _source(SOURCE_PATH))

    def test_wrapper_does_not_call_preflight_sequence(self) -> None:
        source = _source(SOURCE_PATH)
        self.assertNotIn("minimal_controlled_preflight_sequence", source)
        self.assertNotIn("run_minimal_controlled_preflight_sequence", source)

    def test_existing_preflight_api_still_does_not_import_wrapper(self) -> None:
        self.assertFalse(_imports_wrapper(PREFLIGHT_API_PATH))
        self.assertNotIn("minimal_controlled_wal_gated_preflight_wrapper", _source(PREFLIGHT_API_PATH))

    def test_existing_runners_still_do_not_import_wrapper(self) -> None:
        for path in RUNNER_PATHS:
            with self.subTest(path=str(path)):
                self.assertFalse(_imports_wrapper(path))
                self.assertNotIn("minimal_controlled_wal_gated_preflight_wrapper", _source(path))

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

    def test_full_wrapper_path_remains_callable_only_and_human_invoked_by_design(
        self,
    ) -> None:
        signature = inspect.signature(wrapper.run_minimal_controlled_wal_gated_preflight_wrapper)
        self.assertEqual(tuple(signature.parameters), ("wrapper_input", "append_callable"))
        self.assertNotIn("run_minimal_controlled_preflight_sequence", _source(SOURCE_PATH))
        self.assertNotIn("run_minimal_controlled_git_status", _source(SOURCE_PATH))
        self.assertNotIn("run_minimal_controlled_git_diff_check", _source(SOURCE_PATH))

    def test_reserved_preflight_api_integration_name_remains_absent_from_existing_surfaces(
        self,
    ) -> None:
        reserved_name = "run_minimal_controlled_preflight_with_wal_adapter"
        for path in RUNNER_PATHS + PREFLIGHT_PATHS:
            with self.subTest(path=str(path)):
                self.assertNotIn(reserved_name, _source(path))


def _evidence_field_names() -> tuple[str, ...]:
    return (
        "admission_evidence",
        "outcome_evidence",
        "verifier_binding_evidence",
        "preflight_result_evidence",
    )


def _input_with_evidence_override(
    evidence_field: str,
    overrides: dict[str, object],
) -> wrapper.MinimalControlledWalGatedPreflightInput:
    admission = _admission_evidence()
    outcome = _receipt_evidence()
    binding = _binding_evidence()
    preflight = _preflight_evidence()
    mapping = {
        "admission_evidence": admission,
        "outcome_evidence": outcome,
        "verifier_binding_evidence": binding,
        "preflight_result_evidence": preflight,
    }
    mapping[evidence_field].update(overrides)
    return _wrapper_input(
        admission_evidence=admission,
        outcome_evidence=outcome,
        binding_evidence=binding,
        preflight_evidence=preflight,
    )


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path))


def _imported_modules(path: Path) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _imports_module(path: Path, module_name: str) -> bool:
    return module_name in _imported_modules(path)


def _imports_wrapper(path: Path) -> bool:
    imported = _imported_modules(path)
    return WRAPPER_MODULE_NAME in imported or "kernel.execution" in imported and any(
        isinstance(node, ast.ImportFrom)
        and node.module == "kernel.execution"
        and any(alias.name == "minimal_controlled_wal_gated_preflight_wrapper" for alias in node.names)
        for node in ast.walk(_tree(path))
    )


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
