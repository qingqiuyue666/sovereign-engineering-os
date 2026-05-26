"""Tests for Minimal Controlled Execution WAL Adapter Contract V1."""

from __future__ import annotations

import ast
from dataclasses import fields
import hashlib
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_wal_adapter_contract as contract


SOURCE_PATH = Path("kernel/execution/minimal_controlled_wal_adapter_contract.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _base_record_payload(
    record_type: str = "EXECUTION_ADMISSION",
    sequence: int = 1,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "wal_adapter_record_id": "wal-record-" + str(sequence),
        "wal_adapter_version": contract.WAL_ADAPTER_VERSION,
        "record_type": record_type,
        "task_id": "task-001",
        "run_id": "run-001",
        "command_id": "git_status_short",
        "preflight_id": "preflight-001",
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
        "execution_performed": False,
    }
    if record_type == "EXECUTION_ADMISSION":
        payload.update(
            {
                "request_hash": _hash("request"),
                "decision_hash": _hash("decision"),
                "admission_record_hash": _hash("admission"),
            }
        )
    elif record_type == "EXECUTION_RECEIPT":
        payload.update(
            {
                "request_hash": _hash("request"),
                "decision_hash": _hash("decision"),
                "admission_record_hash": _hash("admission"),
                "receipt_hash": _hash("receipt"),
                "verifier_input_hash": _hash("verifier-input"),
                "execution_performed": True,
            }
        )
    elif record_type == "EXECUTION_FAILURE":
        payload.update(
            {
                "request_hash": _hash("request"),
                "decision_hash": _hash("decision"),
                "failure_bundle_hash": _hash("failure"),
            }
        )
    elif record_type == "EXECUTION_VERIFIER_BINDING":
        payload.update({"verifier_binding_hash": _hash("verifier-binding")})
    elif record_type == "PREFLIGHT_RESULT":
        payload.update(_preflight_bindings())

    payload.update(overrides)
    return payload


def _record(
    record_type: str = "EXECUTION_ADMISSION",
    sequence: int = 1,
    **overrides: object,
) -> contract.MinimalControlledWalAdapterRecord:
    return contract.MinimalControlledWalAdapterRecord(
        **_base_record_payload(record_type, sequence, **overrides)
    )


def _preflight_bindings() -> dict[str, object]:
    return {
        "command_id": "minimal_controlled_preflight",
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
    }


def _batch(
    records: tuple[contract.MinimalControlledWalAdapterRecord, ...],
    **overrides: object,
) -> contract.MinimalControlledWalAdapterBatch:
    ordered_records = tuple(sorted(records, key=lambda record: record.sequence))
    payload: dict[str, object] = {
        "wal_adapter_batch_id": "wal-batch-001",
        "wal_adapter_version": contract.WAL_ADAPTER_VERSION,
        "task_id": "task-001",
        "run_id": "run-001",
        "preflight_id": "preflight-001",
        "ordered_record_hashes": tuple(record.record_hash for record in ordered_records),
        "record_count": len(ordered_records),
        "first_sequence": ordered_records[0].sequence,
        "last_sequence": ordered_records[-1].sequence,
    }
    payload.update(overrides)
    return contract.MinimalControlledWalAdapterBatch(**payload)


class MinimalControlledExecutionWalAdapterContractV1Tests(unittest.TestCase):
    def test_record_hash_deterministic(self) -> None:
        record = _record()
        self.assertEqual(
            record.record_hash,
            contract.minimal_controlled_wal_adapter_record_hash(record),
        )
        self.assertEqual(_record().record_hash, record.record_hash)

    def test_record_rejects_mismatched_supplied_hash(self) -> None:
        with self.assertRaisesRegex(ValueError, "record_hash_mismatch"):
            _record(record_hash=_hash("wrong-record-hash"))

    def test_batch_hash_deterministic(self) -> None:
        records = (_record(sequence=1), _record("EXECUTION_RECEIPT", sequence=2))
        batch = _batch(records)
        self.assertEqual(batch.batch_hash, contract.minimal_controlled_wal_adapter_batch_hash(batch))
        self.assertEqual(_batch(records).batch_hash, batch.batch_hash)

    def test_replay_input_and_result_hash_deterministic(self) -> None:
        records = (_record(sequence=1), _record("EXECUTION_RECEIPT", sequence=2))
        batch = _batch(records)
        replay_input = contract.MinimalControlledWalAdapterReplayInput(
            replay_input_id="replay-input-001",
            wal_adapter_version=contract.WAL_ADAPTER_VERSION,
            batch_hash=batch.batch_hash,
            ordered_record_hashes=batch.ordered_record_hashes,
            expected_record_count=batch.record_count,
            replay_policy_version=contract.WAL_ADAPTER_REPLAY_POLICY_VERSION,
        )
        replay_result = contract.MinimalControlledWalAdapterReplayResult(
            replay_result_id="replay-result-001",
            wal_adapter_version=contract.WAL_ADAPTER_VERSION,
            accepted=True,
            rejection_reasons=(),
            batch_hash=batch.batch_hash,
            replay_input_hash=replay_input.replay_input_hash,
        )

        self.assertEqual(
            replay_input.replay_input_hash,
            contract.minimal_controlled_wal_adapter_replay_input_hash(replay_input),
        )
        self.assertEqual(
            replay_result.replay_result_hash,
            contract.minimal_controlled_wal_adapter_replay_result_hash(replay_result),
        )

    def test_valid_execution_admission_record_accepted(self) -> None:
        contract.validate_wal_adapter_record(_record("EXECUTION_ADMISSION"))

    def test_valid_execution_receipt_record_accepted(self) -> None:
        contract.validate_wal_adapter_record(_record("EXECUTION_RECEIPT"))

    def test_valid_execution_failure_record_accepted(self) -> None:
        contract.validate_wal_adapter_record(_record("EXECUTION_FAILURE"))

    def test_valid_verifier_binding_record_accepted(self) -> None:
        contract.validate_wal_adapter_record(_record("EXECUTION_VERIFIER_BINDING"))

    def test_valid_preflight_result_record_accepted(self) -> None:
        contract.validate_wal_adapter_record(_record("PREFLIGHT_RESULT"))

    def test_invalid_record_type_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "record_type_invalid"):
            _record("UNBOUNDED_EXECUTION")

    def test_missing_required_preflight_hash_binding_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "preflight_result_hash_required"):
            _record("PREFLIGHT_RESULT", preflight_result_hash="")

    def test_batch_rejects_wrong_record_order(self) -> None:
        records = (_record(sequence=1), _record("EXECUTION_RECEIPT", sequence=2))
        wrong_order = tuple(record.record_hash for record in reversed(records))
        batch = _batch(records, ordered_record_hashes=wrong_order)

        with self.assertRaisesRegex(ValueError, "ordered_record_hashes_mismatch"):
            contract.validate_wal_adapter_batch(batch, records)

    def test_batch_rejects_missing_record(self) -> None:
        records = (_record(sequence=1), _record("EXECUTION_RECEIPT", sequence=2))
        batch = _batch((records[0],))

        with self.assertRaisesRegex(ValueError, "record_count_mismatch"):
            contract.validate_wal_adapter_batch(batch, records)

    def test_batch_rejects_wrong_sequence_range(self) -> None:
        records = (_record(sequence=1), _record("EXECUTION_RECEIPT", sequence=2))
        batch = _batch(records, first_sequence=2, last_sequence=3)

        with self.assertRaisesRegex(ValueError, "first_sequence_mismatch"):
            contract.validate_wal_adapter_batch(batch, records)

    def test_replay_rejects_tampered_record_hash(self) -> None:
        record = _record(sequence=1)
        batch = _batch((record,))
        object.__setattr__(record, "record_hash", _hash("tampered-record"))

        result = contract.replay_wal_adapter_batch(batch, (record,))

        self.assertFalse(result.accepted)
        self.assertIn("record_hash_mismatch", ",".join(result.rejection_reasons))
        self.assertEqual(
            result.replay_result_hash,
            contract.minimal_controlled_wal_adapter_replay_result_hash(result),
        )

    def test_replay_rejects_wrong_batch_hash(self) -> None:
        records = (_record(sequence=1),)
        batch = _batch(records)
        object.__setattr__(batch, "batch_hash", _hash("tampered-batch"))

        result = contract.replay_wal_adapter_batch(batch, records)

        self.assertFalse(result.accepted)
        self.assertIn("batch_hash_mismatch", ",".join(result.rejection_reasons))

    def test_raw_stdout_stderr_fields_are_not_dataclass_fields(self) -> None:
        record_fields = {field.name for field in fields(contract.MinimalControlledWalAdapterRecord)}
        self.assertFalse(record_fields.intersection(contract.WAL_ADAPTER_RAW_OUTPUT_FIELD_NAMES))

    def test_execution_material_fields_are_not_dataclass_fields(self) -> None:
        record_fields = {field.name for field in fields(contract.MinimalControlledWalAdapterRecord)}
        self.assertFalse(
            record_fields.intersection(contract.WAL_ADAPTER_EXECUTION_MATERIAL_FIELD_NAMES)
        )

    def test_source_contains_no_forbidden_runtime_execution_provider_browser_dcc_mcp_imports(
        self,
    ) -> None:
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        forbidden_modules = (
            "kernel.runtime",
            "sqlite3",
            "kernel.stores.sqlite",
            "kernel.os_engine",
            "tools.local_execution_kernel",
            "argparse",
            "click",
            "typer",
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
        for imported_module in imported_modules:
            with self.subTest(imported_module=imported_module):
                self.assertFalse(
                    imported_module == "subprocess"
                    or any(imported_module.startswith(prefix) for prefix in forbidden_modules)
                )

    def test_source_contains_no_subprocess_os_system_popen_exec_eval(self) -> None:
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        forbidden_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "Popen",
                    "exec",
                    "eval",
                }:
                    forbidden_calls.append(node.func.id)
                if isinstance(node.func, ast.Attribute):
                    parent = node.func.value
                    if (
                        isinstance(parent, ast.Name)
                        and parent.id == "os"
                        and node.func.attr == "system"
                    ):
                        forbidden_calls.append("os.system")
                    if node.func.attr == "Popen":
                        forbidden_calls.append("Popen")

        self.assertEqual(forbidden_calls, [])

    def test_adapter_does_not_import_existing_runner_modules(self) -> None:
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        self.assertFalse(
            any(
                "minimal_controlled_git_status_runner" in module
                or "minimal_controlled_git_diff_check_runner" in module
                or "minimal_controlled_preflight_sequence" in module
                or module.endswith("_runner")
                for module in imported_modules
            )
        )

    def test_adapter_does_not_import_kernel_runtime(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("kernel.runtime", source)

    def test_adapter_does_not_import_sqlite3(self) -> None:
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
        self.assertNotIn("sqlite3", imported_modules)

    def test_adapter_can_bind_preflight_child_evidence_hashes_in_exact_order(self) -> None:
        record = _record("PREFLIGHT_RESULT")

        self.assertEqual(record.ordered_command_ids, ("git_status_short", "git_diff_check"))
        self.assertEqual(record.child_request_hashes, (_hash("request-1"), _hash("request-2")))
        self.assertEqual(record.child_receipt_hashes, (_hash("receipt-1"), ""))
        self.assertEqual(record.child_failure_bundle_hashes, ("", _hash("failure-2")))

    def test_adapter_can_produce_accepted_replay_result_for_valid_batch(self) -> None:
        records = (
            _record("EXECUTION_ADMISSION", sequence=1),
            _record("EXECUTION_RECEIPT", sequence=2),
            _record("PREFLIGHT_RESULT", sequence=3),
        )
        batch = _batch(records)

        result = contract.replay_wal_adapter_batch(batch, records)

        self.assertTrue(result.accepted)
        self.assertEqual(result.rejection_reasons, ())

    def test_adapter_produces_rejected_replay_result_for_tampered_batch(self) -> None:
        records = (_record("EXECUTION_ADMISSION", sequence=1),)
        batch = _batch(records)
        object.__setattr__(batch, "ordered_record_hashes", (_hash("wrong-order"),))
        object.__setattr__(
            batch,
            "batch_hash",
            contract.minimal_controlled_wal_adapter_batch_hash(batch),
        )

        result = contract.replay_wal_adapter_batch(batch, records)

        self.assertFalse(result.accepted)
        self.assertIn("ordered_record_hashes_mismatch", ",".join(result.rejection_reasons))


if __name__ == "__main__":
    unittest.main()
