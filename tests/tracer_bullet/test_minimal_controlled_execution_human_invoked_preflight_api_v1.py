"""Tests for the human-invoked Minimal Controlled Execution preflight API."""

from __future__ import annotations

import ast
import copy
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from kernel.execution import minimal_controlled_preflight_api as api


SOURCE_PATH = Path("kernel/execution/minimal_controlled_preflight_api.py")


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "preflight_id": "preflight-api-001",
        "task_id": "task-001",
        "run_id": "run-001",
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "api_test",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
        "snapshot_ref": "snapshot:preflight-root",
        "caller_intent": "run human-invoked minimal controlled preflight",
    }
    payload.update(overrides)
    return payload


def _completed(args, returncode: int = 0):
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout="",
        stderr="",
    )


class MinimalControlledExecutionHumanInvokedPreflightApiV1Tests(unittest.TestCase):
    def test_accepts_only_governance_metadata_and_returns_manifest(self):
        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"]),
                _completed(["git", "diff", "--check"]),
            ],
        ):
            response = api.run_human_invoked_minimal_controlled_preflight(_payload())

        result = response.preflight_result
        manifest = response.evidence_manifest
        self.assertEqual(response.api_invocation_id, "human-preflight-api-preflight-api-001")
        self.assertEqual(result.ordered_command_ids, ("git_status_short", "git_diff_check"))
        self.assertEqual(manifest.ordered_command_ids, result.ordered_command_ids)
        self.assertEqual(manifest.preflight_result_hash, result.preflight_result_hash)
        self.assertEqual(manifest.child_request_hashes, result.child_request_hashes)
        self.assertEqual(manifest.child_decision_hashes, result.child_decision_hashes)
        self.assertEqual(manifest.child_admission_hashes, result.child_admission_hashes)
        self.assertEqual(manifest.child_receipt_hashes, result.child_receipt_hashes)
        self.assertEqual(
            manifest.child_verifier_binding_hashes,
            result.child_verifier_binding_hashes,
        )
        self.assertTrue(manifest.manifest_hash.startswith("sha256:"))
        self.assertTrue(response.execution_performed)

    def test_rejects_command_lists(self):
        for field_name in ("command_id", "command_ids", "commands", "steps", "tasks", "graph"):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "human_preflight_field_forbidden"):
                    api.run_human_invoked_minimal_controlled_preflight(
                        _payload(**{field_name: "payload-supplied"})
                    )

    def test_rejects_execution_material(self):
        for field_name in ("argv", "cwd", "env", "path", "executable", "timeout", "shell"):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "human_preflight_field_forbidden"):
                    api.run_human_invoked_minimal_controlled_preflight(
                        _payload(**{field_name: "payload-supplied"})
                    )

    def test_calls_fixed_preflight_sequence(self):
        with mock.patch.object(api, "run_minimal_controlled_preflight_sequence") as run:
            run.return_value = _fake_preflight_result()
            response = api.run_human_invoked_minimal_controlled_preflight(_payload())

        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0]["preflight_id"],
            "preflight-api-001",
        )
        self.assertEqual(
            response.evidence_manifest.ordered_command_ids,
            ("git_status_short", "git_diff_check"),
        )

    def test_manifest_hash_rejects_tamper(self):
        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"]),
                _completed(["git", "diff", "--check"]),
            ],
        ):
            response = api.run_human_invoked_minimal_controlled_preflight(_payload())

        tampered = copy.deepcopy(response.evidence_manifest.as_dict())
        tampered["overall_status"] = "PREFLIGHT_FAILED"
        self.assertNotEqual(
            response.evidence_manifest.manifest_hash,
            api.human_preflight_manifest_hash(tampered),
        )

    def test_no_cli_or_broad_runner_imports(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        for marker in (
            "argparse",
            "click",
            "typer",
            "subprocess",
            "kernel.runtime.",
            "kernel.os_engine",
            "tools.local_execution_kernel.",
        ):
            self.assertNotIn(marker, source)
        self.assertFalse(
            any(
                module.startswith("kernel.runtime")
                or module.startswith("kernel.os_engine")
                or module.startswith("tools.local_execution_kernel")
                for module in imported
            ),
            imported,
        )


def _fake_preflight_result():
    from kernel.execution.minimal_controlled_preflight_sequence import (
        MinimalControlledPreflightResult,
    )

    return MinimalControlledPreflightResult(
        preflight_id="preflight-api-001",
        task_id="task-001",
        run_id="run-001",
        ordered_command_ids=("git_status_short", "git_diff_check"),
        child_request_hashes=("sha256:" + "1" * 64, "sha256:" + "2" * 64),
        child_decision_hashes=("sha256:" + "3" * 64, "sha256:" + "4" * 64),
        child_admission_hashes=("sha256:" + "5" * 64, "sha256:" + "6" * 64),
        child_receipt_hashes=("sha256:" + "7" * 64, "sha256:" + "8" * 64),
        child_failure_bundle_hashes=("", ""),
        child_verifier_input_hashes=("sha256:" + "9" * 64, "sha256:" + "a" * 64),
        child_verifier_binding_hashes=("sha256:" + "b" * 64, "sha256:" + "c" * 64),
        pre_snapshot_hashes=("sha256:" + "d" * 64, "sha256:" + "e" * 64),
        post_snapshot_hashes=("sha256:" + "f" * 64, "sha256:" + "0" * 64),
        overall_status="PREFLIGHT_PASSED",
        failure_reasons=(),
        execution_performed=True,
    )


if __name__ == "__main__":
    unittest.main()
