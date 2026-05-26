"""Tracer-bullet tests for Minimal Controlled Execution Shared Runner Base V1."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from unittest import mock

from kernel.execution import minimal_controlled_git_diff_check_runner as diff_runner
from kernel.execution import minimal_controlled_git_status_runner as status_runner
from kernel.execution import minimal_controlled_runner_shared as shared
from kernel.execution.minimal_controlled_execution_contract import (
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
)


SHARED_PATH = Path("kernel/execution/minimal_controlled_runner_shared.py")
STATUS_PATH = Path("kernel/execution/minimal_controlled_git_status_runner.py")
DIFF_PATH = Path("kernel/execution/minimal_controlled_git_diff_check_runner.py")


def _request_payload(command_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_token_id": "",
        "caller_intent": "execute a minimal controlled runner slice",
        "command_id": command_id,
        "policy_version": POLICY_VERSION,
        "request_id": "request-" + command_id.replace("_", "-"),
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "shared_runner_test",
        "run_id": "run-001",
        "snapshot_ref": "snapshot:preflight-root",
        "task_id": "task-001",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
    }
    payload.update(overrides)
    return payload


def _completed(args, returncode: int = 0, stdout: str = "", stderr: str = ""):
    return status_runner.subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class MinimalControlledExecutionSharedRunnerBaseV1Tests(unittest.TestCase):
    def test_shared_helper_cannot_execute_arbitrary_command(self):
        source = SHARED_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertNotIn("subprocess", source)
        self.assertFalse(
            any(
                isinstance(node, ast.FunctionDef)
                and any(token in node.name for token in ("run", "execute", "command"))
                for node in ast.walk(tree)
            )
        )

    def test_shared_deterministic_env_matches_required_git_safe_env(self):
        env = shared.deterministic_git_safe_env()
        self.assertEqual(
            dict(env),
            {
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_TERMINAL_PROMPT": "0",
                "HOME": str(shared.REPOSITORY_ROOT),
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                "TZ": "UTC",
            },
        )
        with self.assertRaises(TypeError):
            env["LANG"] = "en_US.UTF-8"  # type: ignore[index]

    def test_shared_bounded_output_metadata_is_digest_only(self):
        raw_output = "secret raw output text"
        metadata = shared.bounded_output_metadata(raw_output, 8)

        self.assertEqual(set(metadata), {"digest", "truncated"})
        self.assertTrue(str(metadata["digest"]).startswith("sha256:"))
        self.assertTrue(metadata["truncated"])
        self.assertNotIn(raw_output, str(metadata))

    def test_git_status_still_only_executes_git_status_short(self):
        with mock.patch.object(
            status_runner.subprocess,
            "run",
            return_value=_completed(["git", "status", "--short"]),
        ) as run:
            result = status_runner.run_minimal_controlled_git_status(
                _request_payload("git_status_short")
            )

        self.assertTrue(result.execution_performed)
        self.assertEqual(status_runner.EXECUTABLE_COMMAND_IDS, ("git_status_short",))
        self.assertEqual(run.call_args.args[0], ["git", "status", "--short"])
        self.assertEqual(result.attempt.argv, INITIAL_COMMAND_REGISTRY["git_status_short"].argv)

        with mock.patch.object(status_runner.subprocess, "run") as rejected_run:
            rejected = status_runner.run_minimal_controlled_git_status(
                _request_payload("git_diff_check")
            )
        rejected_run.assert_not_called()
        self.assertEqual(
            rejected.failure_bundle.failure_type,
            "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE",
        )

    def test_git_diff_still_only_executes_git_diff_check(self):
        with mock.patch.object(
            diff_runner.subprocess,
            "run",
            return_value=_completed(["git", "diff", "--check"]),
        ) as run:
            result = diff_runner.run_minimal_controlled_git_diff_check(
                _request_payload("git_diff_check")
            )

        self.assertTrue(result.execution_performed)
        self.assertEqual(diff_runner.EXECUTABLE_COMMAND_IDS, ("git_diff_check",))
        self.assertEqual(run.call_args.args[0], ["git", "diff", "--check"])
        self.assertEqual(result.attempt.argv, INITIAL_COMMAND_REGISTRY["git_diff_check"].argv)

        with mock.patch.object(diff_runner.subprocess, "run") as rejected_run:
            rejected = diff_runner.run_minimal_controlled_git_diff_check(
                _request_payload("git_status_short")
            )
        rejected_run.assert_not_called()
        self.assertEqual(
            rejected.failure_bundle.failure_type,
            "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE",
        )

    def test_payload_execution_material_is_still_rejected(self):
        rejected_fields = ("argv", "cwd", "env", "path", "executable", "timeout")
        for field_name in rejected_fields:
            with self.subTest(runner="status", field_name=field_name):
                with self.assertRaisesRegex(ValueError, "forbidden_request_field"):
                    status_runner.run_minimal_controlled_git_status(
                        _request_payload("git_status_short", **{field_name: "x"})
                    )
            with self.subTest(runner="diff", field_name=field_name):
                with self.assertRaisesRegex(ValueError, "forbidden_request_field"):
                    diff_runner.run_minimal_controlled_git_diff_check(
                        _request_payload("git_diff_check", **{field_name: "x"})
                    )

    def test_runner_shell_false_and_env_are_still_hardcoded(self):
        for source_path in (STATUS_PATH, DIFF_PATH):
            with self.subTest(path=str(source_path)):
                source = source_path.read_text(encoding="utf-8")
                self.assertIn("shell=False", source)
                self.assertNotIn("shell=True", source)
                self.assertIn("deterministic_git_safe_env(REPOSITORY_ROOT)", source)

    def test_raw_output_still_not_persisted(self):
        with mock.patch.object(
            diff_runner.subprocess,
            "run",
            return_value=_completed(
                ["git", "diff", "--check"],
                stdout="raw stdout should not persist",
                stderr="raw stderr should not persist",
            ),
        ):
            result = diff_runner.run_minimal_controlled_git_diff_check(
                _request_payload("git_diff_check")
            )

        persisted = result.receipt.as_dict()
        self.assertNotIn("raw stdout should not persist", str(persisted))
        self.assertNotIn("raw stderr should not persist", str(persisted))
        self.assertEqual(
            {
                field
                for field in persisted
                if "stdout" in field or "stderr" in field or "output" in field
            },
            {
                "stdout_digest",
                "stderr_digest",
                "stdout_truncated",
                "stderr_truncated",
                "output_limit_bytes",
            },
        )

    def test_no_broad_runner_imports_or_entry_surfaces(self):
        forbidden_import_prefixes = (
            "kernel.runtime",
            "kernel.os_engine",
            "tools.local_execution_kernel",
        )
        for source_path in (SHARED_PATH, STATUS_PATH, DIFF_PATH):
            imported = _imported_modules(source_path)
            source = source_path.read_text(encoding="utf-8")
            with self.subTest(path=str(source_path)):
                self.assertFalse(
                    any(
                        module == prefix or module.startswith(prefix + ".")
                        for module in imported
                        for prefix in forbidden_import_prefixes
                    ),
                    imported,
                )
                for marker in ("argparse", "click", "typer", "scheduler", "daemon"):
                    self.assertNotIn(marker, source)


def _imported_modules(path: Path) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


if __name__ == "__main__":
    unittest.main()
