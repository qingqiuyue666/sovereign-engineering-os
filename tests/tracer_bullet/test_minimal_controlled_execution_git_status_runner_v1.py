"""Tracer-bullet tests for Minimal Controlled Execution Git Status Runner V1."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
import json
import unittest
from pathlib import Path
from unittest import mock

from kernel.execution import minimal_controlled_git_status_runner as runner
from kernel.execution.minimal_controlled_execution_contract import (
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
    receipt_hash,
)


SOURCE_PATH = Path("kernel/execution/minimal_controlled_git_status_runner.py")


def _request_payload(command_id: str = "git_status_short", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_token_id": "",
        "caller_intent": "execute the minimal git status slice",
        "command_id": command_id,
        "policy_version": POLICY_VERSION,
        "request_id": "request-" + command_id.replace("_", "-"),
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "runner_test",
        "run_id": "run-001",
        "snapshot_ref": "snapshot:preflight-root",
        "task_id": "task-001",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
    }
    payload.update(overrides)
    return payload


def _completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return runner.subprocess.CompletedProcess(
        args=["git", "status", "--short"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _run_success(stdout: str = " M README.md\n") -> runner.MinimalControlledExecutionRunResult:
    with mock.patch.object(runner.subprocess, "run", return_value=_completed(stdout=stdout)):
        return runner.run_minimal_controlled_git_status(_request_payload())


class MinimalControlledExecutionGitStatusRunnerV1Tests(unittest.TestCase):
    def test_git_status_short_executes_with_fixed_argv_only(self):
        with mock.patch.object(
            runner.subprocess,
            "run",
            return_value=_completed(stdout=" M README.md\n"),
        ) as run:
            result = runner.run_minimal_controlled_git_status(_request_payload())

        self.assertEqual(result.receipt.command_id, "git_status_short")
        self.assertTrue(result.execution_performed)
        self.assertTrue(result.verifier_binding.execution_performed)
        self.assertEqual(run.call_args.args[0], ["git", "status", "--short"])
        self.assertEqual(run.call_args.kwargs["cwd"], str(runner.REPOSITORY_ROOT))
        self.assertEqual(
            run.call_args.kwargs["timeout"],
            INITIAL_COMMAND_REGISTRY["git_status_short"].timeout_ms / 1000,
        )
        self.assertEqual(result.attempt.argv, ("git", "status", "--short"))

    def test_subprocess_receives_required_git_safe_env(self):
        with mock.patch.object(runner.subprocess, "run", return_value=_completed()) as run:
            runner.run_minimal_controlled_git_status(_request_payload())

        env = run.call_args.kwargs["env"]
        self.assertEqual(env["GIT_OPTIONAL_LOCKS"], "0")
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(env["LANG"], "C")
        self.assertEqual(env["LC_ALL"], "C")
        self.assertEqual(env["TZ"], "UTC")

    def test_shell_false_is_enforced(self):
        with mock.patch.object(runner.subprocess, "run", return_value=_completed()) as run:
            result = runner.run_minimal_controlled_git_status(_request_payload())

        self.assertIs(run.call_args.kwargs["shell"], False)
        self.assertIs(result.attempt.shell, False)
        self.assertNotIn("shell=True", SOURCE_PATH.read_text(encoding="utf-8"))

    def test_payload_cannot_provide_execution_material(self):
        required_fields = {
            "argv",
            "cwd",
            "env",
            "path",
            "executable",
            "timeout",
            "command",
            "command_line",
            "shell",
        }
        self.assertTrue(required_fields.issubset(EXECUTION_REQUEST_FORBIDDEN_FIELDS))
        for field_name in sorted(required_fields):
            payload = _request_payload(**{field_name: "payload-supplied"})
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "forbidden_request_field"):
                    runner.run_minimal_controlled_git_status(payload)

    def test_git_diff_check_is_registered_but_not_executable_in_this_slice(self):
        with mock.patch.object(runner.subprocess, "run") as run:
            result = runner.run_minimal_controlled_git_status(_request_payload("git_diff_check"))

        run.assert_not_called()
        self.assertTrue(result.policy_decision.accepted)
        self.assertIsNone(result.receipt)
        self.assertEqual(
            result.failure_bundle.failure_type,
            "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE",
        )
        self.assertFalse(result.execution_performed)

    def test_deferred_command_ids_are_rejected(self):
        for command_id in ("unittest_discover_tests", "make_ci"):
            with self.subTest(command_id=command_id):
                with mock.patch.object(runner.subprocess, "run") as run:
                    result = runner.run_minimal_controlled_git_status(
                        _request_payload(command_id)
                    )
                run.assert_not_called()
                self.assertEqual(result.failure_bundle.failure_type, "DEFERRED_COMMAND_ID")
                self.assertIn("DEFERRED_COMMAND_ID", result.failure_bundle.failure_reasons)
                self.assertFalse(result.execution_performed)

    def test_unknown_command_id_is_rejected(self):
        with mock.patch.object(runner.subprocess, "run") as run:
            result = runner.run_minimal_controlled_git_status(_request_payload("unknown_command"))

        run.assert_not_called()
        self.assertEqual(result.failure_bundle.failure_type, "UNKNOWN_COMMAND_ID")
        self.assertIn("UNKNOWN_COMMAND_ID", result.failure_bundle.failure_reasons)
        self.assertFalse(result.execution_performed)

    def test_raw_stdout_and_stderr_are_not_stored_in_receipt_or_wal(self):
        raw_stdout = "raw status text"
        raw_stderr = "raw error text"
        with mock.patch.object(
            runner.subprocess,
            "run",
            return_value=_completed(stdout=raw_stdout, stderr=raw_stderr),
        ):
            result = runner.run_minimal_controlled_git_status(_request_payload())

        persisted = [result.receipt.as_dict()] + [record.as_dict() for record in result.wal_records]
        for payload in persisted:
            serialized = json.dumps(payload, sort_keys=True)
            self.assertNotIn(raw_stdout, serialized)
            self.assertNotIn(raw_stderr, serialized)
            for raw_field in ("stdout", "stderr", "raw_stdout", "raw_stderr"):
                self.assertNotIn(raw_field, payload)

    def test_receipt_stores_only_digest_truncation_and_limit_output_metadata(self):
        result = _run_success()
        receipt_payload = result.receipt.as_dict()
        output_fields = {
            field_name
            for field_name in receipt_payload
            if "stdout" in field_name or "stderr" in field_name or "output" in field_name
        }
        self.assertEqual(
            output_fields,
            {
                "stdout_digest",
                "stderr_digest",
                "stdout_truncated",
                "stderr_truncated",
                "output_limit_bytes",
            },
        )
        self.assertTrue(str(receipt_payload["stdout_digest"]).startswith("sha256:"))
        self.assertTrue(str(receipt_payload["stderr_digest"]).startswith("sha256:"))

    def test_timeout_creates_failure_bundle(self):
        timeout = runner.subprocess.TimeoutExpired(
            cmd=["git", "status", "--short"],
            timeout=INITIAL_COMMAND_REGISTRY["git_status_short"].timeout_ms / 1000,
        )
        with mock.patch.object(runner.subprocess, "run", side_effect=timeout):
            result = runner.run_minimal_controlled_git_status(_request_payload())

        self.assertIsNone(result.receipt)
        self.assertEqual(result.failure_bundle.failure_type, "EXECUTION_TIMEOUT")
        self.assertFalse(result.execution_performed)
        self.assertIsNotNone(result.attempt)

    def test_nonzero_exit_creates_failure_bundle(self):
        with mock.patch.object(
            runner.subprocess,
            "run",
            return_value=_completed(returncode=1, stderr="not clean"),
        ):
            result = runner.run_minimal_controlled_git_status(_request_payload())

        self.assertEqual(result.receipt.exit_code, 1)
        self.assertEqual(result.failure_bundle.failure_type, "NONZERO_EXIT")
        self.assertTrue(result.failure_bundle.execution_performed)
        self.assertTrue(result.execution_performed)

    def test_output_limit_exceeded_creates_truncation_and_failure_evidence(self):
        limit = INITIAL_COMMAND_REGISTRY["git_status_short"].output_limit_bytes
        with mock.patch.object(
            runner.subprocess,
            "run",
            return_value=_completed(stdout="x" * (limit + 1)),
        ):
            result = runner.run_minimal_controlled_git_status(_request_payload())

        self.assertTrue(result.receipt.stdout_truncated)
        self.assertFalse(result.receipt.stderr_truncated)
        self.assertEqual(result.receipt.output_limit_bytes, limit)
        self.assertEqual(result.failure_bundle.failure_type, "OUTPUT_LIMIT_EXCEEDED")
        self.assertTrue(result.failure_bundle.execution_performed)

    def test_verifier_rejects_tampered_receipt_hash(self):
        result = _run_success()
        receipt = copy.deepcopy(result.receipt)
        object.__setattr__(receipt, "receipt_hash", "sha256:" + "0" * 64)
        verification = runner.verify_minimal_controlled_git_status_result(
            replace(result, receipt=receipt)
        )

        self.assertFalse(verification.accepted)
        self.assertIn("receipt_hash_mismatch", verification.rejection_reasons)

    def test_verifier_rejects_wrong_registry_entry_hash(self):
        result = _run_success()
        receipt = copy.deepcopy(result.receipt)
        object.__setattr__(receipt, "registry_entry_hash", "sha256:" + "f" * 64)
        object.__setattr__(receipt, "receipt_hash", receipt_hash(receipt))
        verification = runner.verify_minimal_controlled_git_status_result(
            replace(result, receipt=receipt)
        )

        self.assertFalse(verification.accepted)
        self.assertIn("registry_entry_hash_mismatch", verification.rejection_reasons)

    def test_verifier_rejects_command_id_other_than_git_status_short(self):
        result = _run_success()
        receipt = copy.deepcopy(result.receipt)
        object.__setattr__(receipt, "command_id", "git_diff_check")
        object.__setattr__(receipt, "receipt_hash", receipt_hash(receipt))
        verification = runner.verify_minimal_controlled_git_status_result(
            replace(result, receipt=receipt)
        )

        self.assertFalse(verification.accepted)
        self.assertIn("receipt_command_id_mismatch", verification.rejection_reasons)

    def test_wal_append_failure_prevents_execution(self):
        def fail_append(_record):
            raise RuntimeError("append failed")

        with mock.patch.object(runner.subprocess, "run") as run:
            result = runner.run_minimal_controlled_git_status(
                _request_payload(),
                wal_append=fail_append,
            )

        run.assert_not_called()
        self.assertEqual(result.failure_bundle.failure_type, "WAL_APPEND_FAILED")
        self.assertIn("EXECUTION_NOT_ATTEMPTED", result.failure_bundle.failure_reasons)
        self.assertFalse(result.execution_performed)

    def test_runner_failure_bundle_covers_required_failure_types(self):
        self.assertTrue(
            {
                "POLICY_REJECTED",
                "UNKNOWN_COMMAND_ID",
                "DEFERRED_COMMAND_ID",
                "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE",
                "WORKTREE_NOT_CLEAN",
                "EXECUTION_TIMEOUT",
                "NONZERO_EXIT",
                "OUTPUT_LIMIT_EXCEEDED",
                "RECEIPT_VERIFICATION_FAILED",
                "WAL_APPEND_FAILED",
                "EXECUTION_NOT_ATTEMPTED",
            }.issubset(runner.RUNNER_FAILURE_TYPES)
        )

    def test_no_import_of_existing_runtime_runner_modules(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        for forbidden_import in (
            "kernel.os_engine.local_job_runner",
            "kernel.runtime.sqlite_wal_execution_journal",
            "kernel.runtime.router_wal_binding",
            "kernel.runtime.command_envelope_admission_router",
            "kernel.runtime.",
            "local_execution_kernel",
            "local_job_runner",
            "tools.local_execution_kernel.",
        ):
            self.assertFalse(
                any(forbidden_import in imported for imported in imported_modules),
                imported_modules,
            )

    def test_static_source_forbids_broader_execution_surfaces(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for marker in (
            "os.system",
            "Popen",
            "shell=True",
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
            "mcp",
            "kernel.runtime.sqlite_wal_execution_journal",
            "kernel.runtime.router_wal_binding",
            "kernel.runtime.command_envelope_admission_router",
            "kernel.runtime.",
            "kernel.os_engine.local_job_runner",
            "tools.local_execution_kernel.",
        ):
            self.assertNotIn(marker, source)

    def test_registry_remains_exactly_two_known_git_commands(self):
        self.assertEqual(tuple(INITIAL_COMMAND_REGISTRY), ("git_status_short", "git_diff_check"))
        self.assertEqual(
            INITIAL_COMMAND_REGISTRY["git_status_short"].argv,
            ("git", "status", "--short"),
        )
        self.assertEqual(
            INITIAL_COMMAND_REGISTRY["git_diff_check"].argv,
            ("git", "diff", "--check"),
        )

    def test_executable_slice_contains_exactly_git_status_short(self):
        self.assertEqual(runner.EXECUTABLE_COMMAND_IDS, ("git_status_short",))


if __name__ == "__main__":
    unittest.main()
