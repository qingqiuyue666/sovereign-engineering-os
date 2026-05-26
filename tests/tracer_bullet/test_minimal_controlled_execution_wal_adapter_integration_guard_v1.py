"""Integration guards for future Minimal Controlled Execution WAL adapter wiring."""

from __future__ import annotations

import ast
from dataclasses import fields
import hashlib
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_wal_adapter_contract as contract
from kernel.execution.minimal_controlled_execution_contract import (
    DEFERRED_COMMAND_IDS,
    INITIAL_COMMAND_REGISTRY,
)


EXECUTION_ROOT = Path("kernel/execution")
WAL_ADAPTER_CONTRACT_PATH = EXECUTION_ROOT / "minimal_controlled_wal_adapter_contract.py"
WAL_ADAPTER_INTEGRATION_PATH = EXECUTION_ROOT / "minimal_controlled_wal_adapter_integration.py"
WAL_ADAPTER_MODULE = "kernel.execution.minimal_controlled_wal_adapter_contract"
MINIMAL_CONTROLLED_SOURCE_PATHS = tuple(sorted(EXECUTION_ROOT.glob("minimal_controlled_*.py")))
CURRENT_INTEGRATION_TARGETS = (
    EXECUTION_ROOT / "minimal_controlled_git_status_runner.py",
    EXECUTION_ROOT / "minimal_controlled_git_diff_check_runner.py",
    EXECUTION_ROOT / "minimal_controlled_preflight_sequence.py",
    EXECUTION_ROOT / "minimal_controlled_preflight_api.py",
)
ADAPTER_FACING_SOURCE_PATHS = (
    WAL_ADAPTER_CONTRACT_PATH,
    EXECUTION_ROOT / "minimal_controlled_execution_admission_wal_verifier.py",
    *CURRENT_INTEGRATION_TARGETS,
)
ALLOWED_DELIBERATE_INTEGRATION_MARKERS = (
    "append_minimal_controlled_wal_adapter_record",
    "map_receipt_to_wal_adapter_record",
    "map_failure_to_wal_adapter_record",
    "map_preflight_result_to_wal_adapter_record",
)

RESERVED_FUTURE_WRAPPER_MARKERS = (
    "run_minimal_controlled_preflight_with_wal_adapter",
)

FUTURE_INTEGRATION_MARKERS = (
    *RESERVED_FUTURE_WRAPPER_MARKERS,
    *ALLOWED_DELIBERATE_INTEGRATION_MARKERS,
)
FUTURE_INTEGRATION_FAILURE = (
    "Future WAL adapter integration was detected; update this guard alongside "
    "the deliberate integration tests instead of leaving accidental partial integration."
)
FORBIDDEN_REAL_WAL_IMPORT_PREFIXES = (
    "sqlite3",
    "kernel.runtime",
    "kernel.stores.sqlite",
    "kernel.os_engine",
    "tools.local_execution_kernel",
)
FORBIDDEN_CLI_SCHEDULER_DAEMON_IMPORTS = (
    "argparse",
    "click",
    "typer",
    "schedule",
    "daemon",
)
FORBIDDEN_PROVIDER_BROWSER_DCC_MCP_IMPORTS = (
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
)
RAW_OUTPUT_FIELD_NAMES = {
    "stdout",
    "stderr",
    "raw_stdout",
    "raw_stderr",
    "stdout_text",
    "stderr_text",
    "command_line",
}


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _base_record_payload(
    record_type: str,
    sequence: int,
    *,
    command_id: str = "git_status_short",
    execution_performed: bool = False,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "wal_adapter_record_id": "wal-adapter-record-" + str(sequence),
        "wal_adapter_version": contract.WAL_ADAPTER_VERSION,
        "record_type": record_type,
        "task_id": "task-minimal-controlled-preflight",
        "run_id": "run-minimal-controlled-preflight",
        "command_id": command_id,
        "preflight_id": "preflight-minimal-controlled",
        "sequence": sequence,
        "created_at": "2026-05-26T00:00:00Z",
        "request_hash": "",
        "decision_hash": "",
        "admission_record_hash": "",
        "receipt_hash": "",
        "failure_bundle_hash": "",
        "verifier_input_hash": "",
        "verifier_binding_hash": "",
        "preflight_result_hash": "",
        "ordered_command_ids": (),
        "child_request_hashes": (),
        "child_decision_hashes": (),
        "child_admission_hashes": (),
        "child_receipt_hashes": (),
        "child_failure_bundle_hashes": (),
        "child_verifier_input_hashes": (),
        "child_verifier_binding_hashes": (),
        "pre_snapshot_hashes": (),
        "post_snapshot_hashes": (),
        "execution_performed": execution_performed,
    }
    if record_type == "EXECUTION_ADMISSION":
        payload.update(
            {
                "request_hash": _hash("git-status-request"),
                "decision_hash": _hash("git-status-decision"),
                "admission_record_hash": _hash("git-status-admission"),
            }
        )
    elif record_type == "EXECUTION_RECEIPT":
        payload.update(
            {
                "request_hash": _hash("git-status-request"),
                "decision_hash": _hash("git-status-decision"),
                "admission_record_hash": _hash("git-status-admission"),
                "receipt_hash": _hash("git-status-receipt"),
                "verifier_input_hash": _hash("git-status-verifier-input"),
                "execution_performed": True,
            }
        )
    elif record_type == "EXECUTION_FAILURE":
        payload.update(
            {
                "request_hash": _hash("git-status-request"),
                "decision_hash": _hash("git-status-decision"),
                "failure_bundle_hash": _hash("git-status-failure-bundle"),
                "execution_performed": False,
            }
        )
    elif record_type == "EXECUTION_VERIFIER_BINDING":
        payload.update(
            {
                "verifier_binding_hash": _hash("git-status-verifier-binding"),
                "execution_performed": execution_performed,
            }
        )
    elif record_type == "PREFLIGHT_RESULT":
        payload.update(_preflight_bindings())
        payload["command_id"] = "minimal_controlled_preflight"
        payload["execution_performed"] = execution_performed
    payload.update(overrides)
    return payload


def _record(
    record_type: str,
    sequence: int,
    *,
    command_id: str = "git_status_short",
    execution_performed: bool = False,
    **overrides: object,
) -> contract.MinimalControlledWalAdapterRecord:
    return contract.MinimalControlledWalAdapterRecord(
        **_base_record_payload(
            record_type,
            sequence,
            command_id=command_id,
            execution_performed=execution_performed,
            **overrides,
        )
    )


def _preflight_bindings() -> dict[str, object]:
    # Digest-shaped values only; this guard does not import or execute runner code.
    return {
        "preflight_result_hash": _hash("preflight-result"),
        "ordered_command_ids": ("git_status_short", "git_diff_check"),
        "child_request_hashes": (_hash("status-request"), _hash("diff-request")),
        "child_decision_hashes": (_hash("status-decision"), _hash("diff-decision")),
        "child_admission_hashes": (_hash("status-admission"), _hash("diff-admission")),
        "child_receipt_hashes": (_hash("status-receipt"), ""),
        "child_failure_bundle_hashes": ("", _hash("diff-failure-bundle")),
        "child_verifier_input_hashes": (
            _hash("status-verifier-input"),
            _hash("diff-verifier-input"),
        ),
        "child_verifier_binding_hashes": (
            _hash("status-verifier-binding"),
            _hash("diff-verifier-binding"),
        ),
        "pre_snapshot_hashes": (_hash("status-pre-snapshot"), _hash("diff-pre-snapshot")),
        "post_snapshot_hashes": (_hash("status-post-snapshot"), _hash("diff-post-snapshot")),
    }


def _representative_records(
    outcome_type: str = "EXECUTION_RECEIPT",
) -> tuple[contract.MinimalControlledWalAdapterRecord, ...]:
    outcome_execution_performed = outcome_type == "EXECUTION_RECEIPT"
    return (
        _record("EXECUTION_ADMISSION", 1),
        _record(outcome_type, 2),
        _record(
            "EXECUTION_VERIFIER_BINDING",
            3,
            execution_performed=outcome_execution_performed,
        ),
        _record(
            "PREFLIGHT_RESULT",
            4,
            command_id="minimal_controlled_preflight",
            execution_performed=outcome_execution_performed,
        ),
    )


def _batch(
    records: tuple[contract.MinimalControlledWalAdapterRecord, ...],
    **overrides: object,
) -> contract.MinimalControlledWalAdapterBatch:
    ordered_records = tuple(sorted(records, key=lambda record: record.sequence))
    payload: dict[str, object] = {
        "wal_adapter_batch_id": "wal-adapter-batch-001",
        "wal_adapter_version": contract.WAL_ADAPTER_VERSION,
        "task_id": "task-minimal-controlled-preflight",
        "run_id": "run-minimal-controlled-preflight",
        "preflight_id": "preflight-minimal-controlled",
        "ordered_record_hashes": tuple(record.record_hash for record in ordered_records),
        "record_count": len(ordered_records),
        "first_sequence": ordered_records[0].sequence,
        "last_sequence": ordered_records[-1].sequence,
    }
    payload.update(overrides)
    return contract.MinimalControlledWalAdapterBatch(**payload)


class MinimalControlledExecutionWalAdapterIntegrationGuardV1Tests(unittest.TestCase):
    def test_wal_adapter_contract_module_exposes_required_symbols(self) -> None:
        required_symbols = (
            "MinimalControlledWalAdapterRecord",
            "MinimalControlledWalAdapterBatch",
            "MinimalControlledWalAdapterReplayInput",
            "MinimalControlledWalAdapterReplayResult",
            "validate_wal_adapter_record",
            "validate_wal_adapter_batch",
            "replay_wal_adapter_batch",
        )
        for symbol in required_symbols:
            with self.subTest(symbol=symbol):
                self.assertTrue(
                    hasattr(contract, symbol),
                    "WAL adapter contract API missing required symbol: " + symbol,
                )

    def test_current_runners_and_preflight_do_not_import_wal_adapter_contract_yet(self) -> None:
        for path in CURRENT_INTEGRATION_TARGETS:
            with self.subTest(path=str(path)):
                self.assertFalse(
                    _imports_wal_adapter_contract(path),
                    FUTURE_INTEGRATION_FAILURE,
                )

    def test_future_integration_marker_names_are_reserved_and_absent(self) -> None:
        for marker in ALLOWED_DELIBERATE_INTEGRATION_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    _source_paths_containing(marker, (WAL_ADAPTER_INTEGRATION_PATH,)),
                    (str(WAL_ADAPTER_INTEGRATION_PATH),),
                    "Deliberate WAL adapter integration marker must exist only in the narrow integration module.",
                )
                self.assertEqual(
                    _source_paths_containing(marker, CURRENT_INTEGRATION_TARGETS),
                    (),
                    FUTURE_INTEGRATION_FAILURE + " Unexpected runner/preflight marker: " + marker,
                )

        for marker in RESERVED_FUTURE_WRAPPER_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    _source_paths_containing(marker, MINIMAL_CONTROLLED_SOURCE_PATHS),
                    (),
                    FUTURE_INTEGRATION_FAILURE + " Unexpected reserved wrapper marker: " + marker,
                )

    def test_no_accidental_partial_integration_occurred(self) -> None:
        for path in CURRENT_INTEGRATION_TARGETS:
            source = _source(path)
            with self.subTest(path=str(path)):
                self.assertNotIn("minimal_controlled_wal_adapter_contract", source)
                self.assertNotIn("WalAdapter", source)
                self.assertNotIn("wal_adapter_record", source)

    def test_minimal_controlled_sources_have_no_real_wal_or_runtime_coupling(self) -> None:
        for path in MINIMAL_CONTROLLED_SOURCE_PATHS:
            with self.subTest(path=str(path)):
                self.assertEqual(
                    _forbidden_imports(path, FORBIDDEN_REAL_WAL_IMPORT_PREFIXES),
                    (),
                    "Minimal Controlled Execution must not import real WAL/runtime coupling.",
                )

    def test_minimal_controlled_sources_have_no_cli_scheduler_or_daemon_surface(self) -> None:
        for path in MINIMAL_CONTROLLED_SOURCE_PATHS:
            with self.subTest(path=str(path)):
                self.assertEqual(
                    _forbidden_imports(path, FORBIDDEN_CLI_SCHEDULER_DAEMON_IMPORTS),
                    (),
                    "Minimal Controlled Execution must not add CLI, scheduler, or daemon imports.",
                )

    def test_minimal_controlled_sources_have_no_provider_browser_dcc_or_mcp_surface(self) -> None:
        for path in MINIMAL_CONTROLLED_SOURCE_PATHS:
            with self.subTest(path=str(path)):
                self.assertEqual(
                    _forbidden_imports(path, FORBIDDEN_PROVIDER_BROWSER_DCC_MCP_IMPORTS),
                    (),
                    "Minimal Controlled Execution must not import provider/browser/DCC/MCP surfaces.",
                )

    def test_adapter_facing_dataclasses_do_not_persist_raw_output_or_command_line_fields(self) -> None:
        for path in ADAPTER_FACING_SOURCE_PATHS:
            with self.subTest(path=str(path)):
                field_names = _dataclass_field_names(path)
                self.assertFalse(
                    RAW_OUTPUT_FIELD_NAMES.intersection(field_names),
                    "Adapter-facing dataclasses must stay digest-only; stdout_digest "
                    "and stderr_digest remain allowed but raw output fields do not.",
                )
        self.assertIn("stdout_digest", _dataclass_field_names(CURRENT_INTEGRATION_TARGETS[0]))
        self.assertIn("stderr_digest", _dataclass_field_names(CURRENT_INTEGRATION_TARGETS[0]))

    def test_representative_preflight_adapter_batch_replays_with_future_order(self) -> None:
        records = _representative_records("EXECUTION_RECEIPT")
        _assert_future_preflight_integration_order(records)
        batch = _batch(records)

        result = contract.replay_wal_adapter_batch(batch, records)

        self.assertTrue(result.accepted, result.rejection_reasons)

    def test_future_integration_order_allows_failure_outcome_before_verifier_binding(self) -> None:
        records = _representative_records("EXECUTION_FAILURE")
        _assert_future_preflight_integration_order(records)
        batch = _batch(records)

        result = contract.replay_wal_adapter_batch(batch, records)

        self.assertTrue(result.accepted, result.rejection_reasons)

    def test_replay_rejects_reordered_records(self) -> None:
        records = _representative_records()
        reversed_hashes = tuple(record.record_hash for record in reversed(records))
        batch = _batch(records, ordered_record_hashes=reversed_hashes)

        result = contract.replay_wal_adapter_batch(batch, records)

        self.assertFalse(result.accepted)
        self.assertIn("ordered_record_hashes_mismatch", ",".join(result.rejection_reasons))

    def test_replay_rejects_tampered_record_hash(self) -> None:
        records = list(_representative_records())
        object.__setattr__(records[1], "record_hash", _hash("tampered-receipt-record"))
        batch = _batch(tuple(records))

        result = contract.replay_wal_adapter_batch(batch, tuple(records))

        self.assertFalse(result.accepted)
        self.assertIn("record_hash_mismatch", ",".join(result.rejection_reasons))

    def test_preflight_integration_batch_requires_preflight_result_record(self) -> None:
        incomplete_records = _representative_records()[:3]

        with self.assertRaisesRegex(AssertionError, "preflight_result_record_required"):
            _assert_future_preflight_integration_order(incomplete_records)

    def test_future_append_before_execution_rule_is_explicit(self) -> None:
        records = _representative_records("EXECUTION_RECEIPT")
        admission, receipt, _binding, preflight = records

        self.assertEqual(admission.record_type, "EXECUTION_ADMISSION")
        self.assertEqual(receipt.record_type, "EXECUTION_RECEIPT")
        self.assertLess(
            admission.sequence,
            receipt.sequence,
            "Future integration must append admission before any receipt/failure evidence.",
        )
        self.assertEqual(
            preflight.record_type,
            "PREFLIGHT_RESULT",
            "Future integration must append the preflight result last.",
        )
        self.assertEqual(preflight.sequence, max(record.sequence for record in records))

    def test_future_receipt_or_failure_cannot_appear_before_admission(self) -> None:
        records = (
            _record("EXECUTION_RECEIPT", 1),
            _record("EXECUTION_ADMISSION", 2),
            _record("EXECUTION_VERIFIER_BINDING", 3, execution_performed=True),
            _record(
                "PREFLIGHT_RESULT",
                4,
                command_id="minimal_controlled_preflight",
                execution_performed=True,
            ),
        )

        with self.assertRaisesRegex(AssertionError, "admission_must_precede_outcome"):
            _assert_future_preflight_integration_order(records)

    def test_append_failure_blocks_execution_capability_is_not_claimed_yet(self) -> None:
        runner_forbidden_claims = (
            "wal_adapter_append_failure_blocks_execution",
            "WAL_ADAPTER_APPEND_FAILED",
            "execution_performed=true",
        )
        for marker in runner_forbidden_claims:
            with self.subTest(marker=marker):
                self.assertEqual(
                    _source_paths_containing(marker, CURRENT_INTEGRATION_TARGETS),
                    (),
                    FUTURE_INTEGRATION_FAILURE,
                )

        self.assertEqual(
            _source_paths_containing("WAL_ADAPTER_APPEND_FAILED", (WAL_ADAPTER_INTEGRATION_PATH,)),
            (str(WAL_ADAPTER_INTEGRATION_PATH),),
            "Deliberate integration module must expose WAL append failure evidence without wiring runners yet.",
        )

        for marker in RESERVED_FUTURE_WRAPPER_MARKERS:
            self.assertFalse(hasattr(contract, marker), FUTURE_INTEGRATION_FAILURE)

    def test_command_ids_remain_exactly_current_boundary(self) -> None:
        self.assertEqual(tuple(INITIAL_COMMAND_REGISTRY), ("git_status_short", "git_diff_check"))
        self.assertEqual(DEFERRED_COMMAND_IDS, {"unittest_discover_tests", "make_ci"})
        self.assertNotIn("unittest_discover_tests", INITIAL_COMMAND_REGISTRY)
        self.assertNotIn("make_ci", INITIAL_COMMAND_REGISTRY)
        self.assertEqual(
            _assigned_tuple(CURRENT_INTEGRATION_TARGETS[0], "EXECUTABLE_COMMAND_IDS"),
            ("git_status_short",),
        )
        self.assertEqual(
            _assigned_tuple(CURRENT_INTEGRATION_TARGETS[1], "EXECUTABLE_COMMAND_IDS"),
            ("git_diff_check",),
        )
        executable_ids = set(_assigned_tuple(CURRENT_INTEGRATION_TARGETS[0], "EXECUTABLE_COMMAND_IDS"))
        executable_ids.update(_assigned_tuple(CURRENT_INTEGRATION_TARGETS[1], "EXECUTABLE_COMMAND_IDS"))
        self.assertTrue(DEFERRED_COMMAND_IDS.isdisjoint(executable_ids))

    def test_production_module_signature_markers_remain_unintegrated(self) -> None:
        expected_signatures = {
            CURRENT_INTEGRATION_TARGETS[0]: {
                "run_minimal_controlled_git_status": (("request",), ("wal_append",)),
                "verify_minimal_controlled_git_status_result": (("result",), ()),
            },
            CURRENT_INTEGRATION_TARGETS[1]: {
                "run_minimal_controlled_git_diff_check": (("request",), ("wal_append",)),
                "verify_minimal_controlled_git_diff_check_result": (("result",), ()),
            },
            CURRENT_INTEGRATION_TARGETS[2]: {
                "run_minimal_controlled_preflight_sequence": (("payload",), ()),
            },
            CURRENT_INTEGRATION_TARGETS[3]: {
                "run_human_invoked_minimal_controlled_preflight": (("payload",), ()),
            },
        }
        for path, signatures in expected_signatures.items():
            for function_name, expected in signatures.items():
                with self.subTest(path=str(path), function_name=function_name):
                    self.assertEqual(_function_signature(path, function_name), expected)
        self.assertEqual(
            _source_paths_containing("minimal_controlled_wal_adapter_contract", CURRENT_INTEGRATION_TARGETS),
            (),
            FUTURE_INTEGRATION_FAILURE,
        )

    def test_wal_adapter_contract_remains_contract_only(self) -> None:
        self.assertFalse(_imports_module(WAL_ADAPTER_CONTRACT_PATH, "subprocess"))
        self.assertFalse(_imports_module(WAL_ADAPTER_CONTRACT_PATH, "sqlite3"))
        self.assertEqual(
            _forbidden_imports(WAL_ADAPTER_CONTRACT_PATH, ("kernel.runtime",)),
            (),
        )
        self.assertFalse(_calls_subprocess(WAL_ADAPTER_CONTRACT_PATH))
        self.assertEqual(_file_write_calls(WAL_ADAPTER_CONTRACT_PATH), ())
        contract_field_names = set()
        for contract_type in (
            contract.MinimalControlledWalAdapterRecord,
            contract.MinimalControlledWalAdapterBatch,
            contract.MinimalControlledWalAdapterReplayInput,
            contract.MinimalControlledWalAdapterReplayResult,
        ):
            contract_field_names.update(field.name for field in fields(contract_type))
        self.assertFalse(
            RAW_OUTPUT_FIELD_NAMES.intersection(contract_field_names),
            "WAL adapter records must never introduce raw output or command-line fields.",
        )

    def test_next_integration_api_names_are_absent_until_deliberate_pr(self) -> None:
        exported_names = set(getattr(contract, "__all__", ()))
        for marker in ALLOWED_DELIBERATE_INTEGRATION_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(
                    marker,
                    exported_names,
                    "WAL adapter contract must remain contract-only; integration names belong in the integration module.",
                )
                self.assertFalse(
                    hasattr(contract, marker),
                    "WAL adapter contract must not export integration functions.",
                )

        for marker in RESERVED_FUTURE_WRAPPER_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    _source_paths_containing(marker, MINIMAL_CONTROLLED_SOURCE_PATHS),
                    (),
                    FUTURE_INTEGRATION_FAILURE,
                )
                self.assertNotIn(marker, exported_names, FUTURE_INTEGRATION_FAILURE)
                self.assertFalse(hasattr(contract, marker), FUTURE_INTEGRATION_FAILURE)


def _assert_future_preflight_integration_order(
    records: tuple[contract.MinimalControlledWalAdapterRecord, ...],
) -> None:
    record_types_by_sequence = tuple(
        record.record_type for record in sorted(records, key=lambda record: record.sequence)
    )
    if "PREFLIGHT_RESULT" not in record_types_by_sequence:
        raise AssertionError("preflight_result_record_required")
    if record_types_by_sequence[-1] != "PREFLIGHT_RESULT":
        raise AssertionError("preflight_result_must_be_last")
    if not record_types_by_sequence or record_types_by_sequence[0] != "EXECUTION_ADMISSION":
        raise AssertionError("admission_must_precede_outcome")
    if len(record_types_by_sequence) < 2 or record_types_by_sequence[1] not in (
        "EXECUTION_RECEIPT",
        "EXECUTION_FAILURE",
    ):
        raise AssertionError("receipt_or_failure_must_follow_admission")
    expected_order = (
        "EXECUTION_ADMISSION",
        record_types_by_sequence[1],
        "EXECUTION_VERIFIER_BINDING",
        "PREFLIGHT_RESULT",
    )
    if record_types_by_sequence != expected_order:
        raise AssertionError("future_wal_adapter_integration_order_mismatch")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path))


def _imports_wal_adapter_contract(path: Path) -> bool:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            if any(alias.name == WAL_ADAPTER_MODULE for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == WAL_ADAPTER_MODULE:
                return True
            if node.module == "kernel.execution" and any(
                alias.name == "minimal_controlled_wal_adapter_contract"
                for alias in node.names
            ):
                return True
    return False


def _imports_module(path: Path, module_name: str) -> bool:
    return module_name in _imported_modules(path)


def _imported_modules(path: Path) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _forbidden_imports(path: Path, forbidden_prefixes: tuple[str, ...]) -> tuple[str, ...]:
    imported = _imported_modules(path)
    violations = sorted(
        module
        for module in imported
        for prefix in forbidden_prefixes
        if module == prefix or module.startswith(prefix + ".")
    )
    return tuple(violations)


def _source_paths_containing(marker: str, paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(str(path) for path in paths if marker in _source(path))


def _dataclass_field_names(path: Path) -> set[str]:
    field_names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_decorator_name(decorator) == "dataclass" for decorator in node.decorator_list):
            continue
        for statement in node.body:
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                field_names.add(statement.target.id)
    return field_names


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _assigned_tuple(path: Path, name: str) -> tuple[str, ...]:
    for statement in _tree(path).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in statement.targets
        ):
            value = ast.literal_eval(statement.value)
            return tuple(value)
    raise AssertionError("assignment_not_found:" + str(path) + ":" + name)


def _function_signature(path: Path, function_name: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return (
                tuple(arg.arg for arg in node.args.args),
                tuple(arg.arg for arg in node.args.kwonlyargs),
            )
    raise AssertionError("function_not_found:" + str(path) + ":" + function_name)


def _calls_subprocess(path: Path) -> bool:
    for node in ast.walk(_tree(path)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            return True
    return False


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
