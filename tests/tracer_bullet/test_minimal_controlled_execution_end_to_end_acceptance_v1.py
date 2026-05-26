"""End-to-end acceptance tests for the Minimal Controlled Execution chain."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from kernel.execution import minimal_controlled_git_diff_check_runner as diff_runner
from kernel.execution import minimal_controlled_git_status_runner as status_runner
from kernel.execution import minimal_controlled_preflight_api as preflight_api
from kernel.execution import minimal_controlled_preflight_sequence as preflight_sequence
from kernel.execution.minimal_controlled_execution_admission_wal_verifier import (
    admission_record_hash,
    wal_record_hash,
)
from kernel.execution.minimal_controlled_execution_contract import (
    COMMAND_REGISTRY_HASH,
    DEFERRED_COMMAND_IDS,
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
    command_registry_hash,
    receipt_hash,
)
from kernel.execution.minimal_controlled_runner_shared import REPOSITORY_ROOT


MINIMAL_SOURCE_PATHS = (
    Path("kernel/execution/minimal_controlled_execution_contract.py"),
    Path("kernel/execution/minimal_controlled_execution_admission_wal_verifier.py"),
    Path("kernel/execution/minimal_controlled_git_status_runner.py"),
    Path("kernel/execution/minimal_controlled_git_diff_check_runner.py"),
    Path("kernel/execution/minimal_controlled_preflight_sequence.py"),
    Path("kernel/execution/minimal_controlled_preflight_api.py"),
    Path("kernel/execution/minimal_controlled_runner_shared.py"),
)


def _api_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "preflight_id": "preflight-acceptance-001",
        "task_id": "task-acceptance-001",
        "run_id": "run-acceptance-001",
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "acceptance_test",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
        "snapshot_ref": "snapshot:acceptance-root",
        "caller_intent": "run human-invoked minimal controlled acceptance preflight",
    }
    payload.update(overrides)
    return payload


def _request_payload(command_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_token_id": "",
        "caller_intent": "run minimal controlled acceptance slice",
        "command_id": command_id,
        "policy_version": POLICY_VERSION,
        "request_id": "request-" + command_id.replace("_", "-"),
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "acceptance_test",
        "run_id": "run-acceptance-001",
        "snapshot_ref": "snapshot:acceptance-root",
        "task_id": "task-acceptance-001",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
    }
    payload.update(overrides)
    return payload


def _completed(args: list[str], stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class MinimalControlledExecutionEndToEndAcceptanceV1Tests(unittest.TestCase):
    def test_required_core_surface_is_present_and_narrow(self):
        self.assertEqual(tuple(INITIAL_COMMAND_REGISTRY), ("git_status_short", "git_diff_check"))
        self.assertEqual(DEFERRED_COMMAND_IDS, {"unittest_discover_tests", "make_ci"})
        self.assertEqual(COMMAND_REGISTRY_HASH, command_registry_hash())
        self.assertEqual(status_runner.EXECUTABLE_COMMAND_IDS, ("git_status_short",))
        self.assertEqual(diff_runner.EXECUTABLE_COMMAND_IDS, ("git_diff_check",))
        self.assertEqual(preflight_sequence.PREFLIGHT_ORDER, ("git_status_short", "git_diff_check"))

        self.assertNotIn("command_id", preflight_api.HUMAN_PREFLIGHT_ALLOWED_FIELDS)
        self.assertIn("command_id", preflight_api.HUMAN_PREFLIGHT_FORBIDDEN_FIELDS)
        self.assertIn("argv", preflight_api.HUMAN_PREFLIGHT_FORBIDDEN_FIELDS)

    def test_human_api_runs_fixed_order_and_binds_digest_only_manifest(self):
        raw_status_stdout = "raw-status-acceptance-output"
        raw_diff_stderr = "raw-diff-acceptance-error"
        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"], stdout=raw_status_stdout),
                _completed(["git", "diff", "--check"], stderr=raw_diff_stderr),
            ],
        ) as run:
            response = preflight_api.run_human_invoked_minimal_controlled_preflight(
                _api_payload()
            )

        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [["git", "status", "--short"], ["git", "diff", "--check"]],
        )
        for command_id, call in zip(preflight_sequence.PREFLIGHT_ORDER, run.call_args_list):
            entry = INITIAL_COMMAND_REGISTRY[command_id]
            self.assertEqual(call.kwargs["cwd"], str(REPOSITORY_ROOT))
            self.assertEqual(call.kwargs["timeout"], entry.timeout_ms / 1000)
            self.assertIs(call.kwargs["shell"], False)
            self.assertEqual(call.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
            self.assertEqual(call.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(call.kwargs["env"]["HOME"], str(REPOSITORY_ROOT))
            self.assertEqual(call.kwargs["env"]["LANG"], "C")
            self.assertEqual(call.kwargs["env"]["LC_ALL"], "C")
            self.assertEqual(call.kwargs["env"]["TZ"], "UTC")

        result = response.preflight_result
        manifest = response.evidence_manifest
        self.assertEqual(result.overall_status, "PREFLIGHT_PASSED")
        self.assertEqual(manifest.ordered_command_ids, ("git_status_short", "git_diff_check"))
        self.assertEqual(manifest.preflight_result_hash, result.preflight_result_hash)
        self.assertEqual(manifest.child_request_hashes, result.child_request_hashes)
        self.assertEqual(manifest.child_decision_hashes, result.child_decision_hashes)
        self.assertEqual(manifest.child_admission_hashes, result.child_admission_hashes)
        self.assertEqual(manifest.child_receipt_hashes, result.child_receipt_hashes)
        self.assertEqual(
            manifest.child_verifier_input_hashes,
            result.child_verifier_input_hashes,
        )
        self.assertEqual(
            manifest.child_verifier_binding_hashes,
            result.child_verifier_binding_hashes,
        )
        self.assertTrue(manifest.manifest_hash.startswith("sha256:"))

        serialized = json.dumps(response.as_dict(), sort_keys=True)
        self.assertNotIn(raw_status_stdout, serialized)
        self.assertNotIn(raw_diff_stderr, serialized)
        self.assertNotIn("raw_stdout", serialized)
        self.assertNotIn("raw_stderr", serialized)

    def test_runner_wal_and_verifier_evidence_bind_the_executed_slices(self):
        status_events: list[tuple[str, object]] = []

        def append_status_wal(record):
            status_events.append(("wal", record.command_id))

        def run_status(*args, **_kwargs):
            status_events.append(("run", tuple(args[0])))
            return _completed(["git", "status", "--short"])

        with mock.patch.object(status_runner.subprocess, "run", side_effect=run_status):
            status_result = status_runner.run_minimal_controlled_git_status(
                _request_payload("git_status_short"),
                wal_append=append_status_wal,
            )

        self.assertEqual(
            status_events,
            [("wal", "git_status_short"), ("run", ("git", "status", "--short"))],
        )
        self.assertTrue(status_result.execution_performed)
        self.assertEqual(
            status_result.admission_record.admission_record_hash,
            admission_record_hash(status_result.admission_record),
        )
        self.assertEqual(
            status_result.wal_records[0].wal_record_hash,
            wal_record_hash(status_result.wal_records[0]),
        )
        self.assertEqual(
            status_result.wal_records[0].admission_record_hash,
            status_result.admission_record.admission_record_hash,
        )
        self.assertEqual(status_result.receipt.receipt_hash, receipt_hash(status_result.receipt))
        self.assertEqual(
            status_result.verifier_input.receipt_hash,
            status_result.receipt.receipt_hash,
        )
        self.assertEqual(
            status_result.verifier_binding.admission_record_hash,
            status_result.admission_record.admission_record_hash,
        )
        self.assertTrue(status_result.verifier_binding.verifier_binding_hash.startswith("sha256:"))

        diff_events: list[tuple[str, object]] = []

        def append_diff_wal(record):
            diff_events.append(("wal", record.command_id))

        def run_diff(*args, **_kwargs):
            diff_events.append(("run", tuple(args[0])))
            return _completed(["git", "diff", "--check"])

        with mock.patch.object(diff_runner.subprocess, "run", side_effect=run_diff):
            diff_result = diff_runner.run_minimal_controlled_git_diff_check(
                _request_payload("git_diff_check"),
                wal_append=append_diff_wal,
            )

        self.assertEqual(
            diff_events,
            [("wal", "git_diff_check"), ("run", ("git", "diff", "--check"))],
        )
        self.assertTrue(diff_result.execution_performed)
        self.assertEqual(
            diff_result.admission_record.admission_record_hash,
            admission_record_hash(diff_result.admission_record),
        )
        self.assertEqual(
            diff_result.wal_records[0].wal_record_hash,
            wal_record_hash(diff_result.wal_records[0]),
        )
        self.assertEqual(diff_result.receipt.receipt_hash, receipt_hash(diff_result.receipt))
        self.assertEqual(
            diff_result.verifier_binding.admission_record_hash,
            diff_result.admission_record.admission_record_hash,
        )

    def test_fail_closed_rejections_do_not_execute(self):
        with self.assertRaisesRegex(ValueError, "human_preflight_field_forbidden"):
            preflight_api.run_human_invoked_minimal_controlled_preflight(
                _api_payload(commands=["git_status_short"])
            )
        with self.assertRaisesRegex(ValueError, "human_preflight_field_forbidden"):
            preflight_api.run_human_invoked_minimal_controlled_preflight(
                _api_payload(argv=["git", "status", "--short"])
            )

        with mock.patch.object(status_runner.subprocess, "run") as run:
            result = status_runner.run_minimal_controlled_git_status(
                _request_payload("git_diff_check")
            )
        run.assert_not_called()
        self.assertEqual(result.failure_bundle.failure_type, "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE")
        self.assertFalse(result.execution_performed)

        with mock.patch.object(diff_runner.subprocess, "run") as run:
            result = diff_runner.run_minimal_controlled_git_diff_check(
                _request_payload("git_status_short")
            )
        run.assert_not_called()
        self.assertEqual(result.failure_bundle.failure_type, "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE")
        self.assertFalse(result.execution_performed)

        def fail_append(_record):
            raise RuntimeError("append failed")

        with mock.patch.object(status_runner.subprocess, "run") as run:
            result = status_runner.run_minimal_controlled_git_status(
                _request_payload("git_status_short"),
                wal_append=fail_append,
            )
        run.assert_not_called()
        self.assertEqual(result.failure_bundle.failure_type, "WAL_APPEND_FAILED")
        self.assertFalse(result.execution_performed)

    def test_hash_binding_rejects_tampered_receipt_and_manifest(self):
        with mock.patch.object(
            status_runner.subprocess,
            "run",
            return_value=_completed(["git", "status", "--short"]),
        ):
            status_result = status_runner.run_minimal_controlled_git_status(
                _request_payload("git_status_short")
            )

        receipt = copy.deepcopy(status_result.receipt)
        object.__setattr__(receipt, "receipt_hash", "sha256:" + "0" * 64)
        verification = status_runner.verify_minimal_controlled_git_status_result(
            replace(status_result, receipt=receipt)
        )
        self.assertFalse(verification.accepted)
        self.assertIn("receipt_hash_mismatch", verification.rejection_reasons)

        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"]),
                _completed(["git", "diff", "--check"]),
            ],
        ):
            response = preflight_api.run_human_invoked_minimal_controlled_preflight(
                _api_payload()
            )

        manifest_payload = response.evidence_manifest.as_dict()
        manifest_payload["ordered_command_ids"] = ("git_diff_check", "git_status_short")
        with self.assertRaisesRegex(ValueError, "manifest_preflight_order_mismatch"):
            preflight_api.MinimalControlledPreflightEvidenceManifest(**manifest_payload)

        tampered_payload = response.evidence_manifest.as_dict()
        tampered_payload["overall_status"] = "PREFLIGHT_FAILED"
        self.assertNotEqual(
            response.evidence_manifest.manifest_hash,
            preflight_api.human_preflight_manifest_hash(tampered_payload),
        )

    def test_minimal_controlled_sources_do_not_add_forbidden_surfaces(self):
        forbidden_markers = (
            "shell=True",
            "Popen",
            "os.system",
            "kernel.runtime.",
            "kernel.os_engine",
            "tools.local_execution_kernel.",
        )
        forbidden_imports = (
            "argparse",
            "click",
            "typer",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "openai",
            "anthropic",
            "bpy",
            "hou",
            "unreal",
            "comfyui",
        )
        for path in MINIMAL_SOURCE_PATHS:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                for marker in forbidden_markers:
                    self.assertNotIn(marker, source)
                tree = ast.parse(source)
                imported_modules: set[str] = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_modules.update(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported_modules.add(node.module)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, {"eval", "exec"})
                for module in imported_modules:
                    self.assertFalse(
                        any(
                            module == forbidden
                            or module.startswith(forbidden + ".")
                            for forbidden in forbidden_imports
                        ),
                        module,
                    )


if __name__ == "__main__":
    unittest.main()
