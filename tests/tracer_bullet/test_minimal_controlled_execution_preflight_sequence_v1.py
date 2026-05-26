"""Tracer-bullet tests for Minimal Controlled Execution Preflight Sequence V1."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from kernel.execution import minimal_controlled_preflight_sequence as preflight


SOURCE_PATH = Path("kernel/execution/minimal_controlled_preflight_sequence.py")


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "preflight_id": "preflight-001",
        "task_id": "task-001",
        "run_id": "run-001",
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "preflight_test",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
        "snapshot_ref": "snapshot:preflight-root",
        "caller_intent": "run fixed minimal controlled preflight",
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


class MinimalControlledExecutionPreflightSequenceV1Tests(unittest.TestCase):
    def test_preflight_runs_fixed_order_and_binds_child_hashes(self):
        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"]),
                _completed(["git", "diff", "--check"]),
            ],
        ) as run:
            result = preflight.run_minimal_controlled_preflight_sequence(_payload())

        self.assertEqual(result.ordered_command_ids, ("git_status_short", "git_diff_check"))
        self.assertEqual(result.overall_status, "PREFLIGHT_PASSED")
        self.assertTrue(result.execution_performed)
        self.assertEqual(len(result.child_request_hashes), 2)
        self.assertEqual(len(result.child_decision_hashes), 2)
        self.assertEqual(len(result.child_admission_hashes), 2)
        self.assertEqual(len(result.child_receipt_hashes), 2)
        self.assertEqual(len(result.child_verifier_input_hashes), 2)
        self.assertEqual(len(result.child_verifier_binding_hashes), 2)
        self.assertEqual(len(result.pre_snapshot_hashes), 2)
        self.assertEqual(len(result.post_snapshot_hashes), 2)
        self.assertTrue(result.preflight_result_hash.startswith("sha256:"))
        self.assertEqual(run.call_args_list[0].args[0], ["git", "status", "--short"])
        self.assertEqual(run.call_args_list[1].args[0], ["git", "diff", "--check"])

    def test_preflight_result_hash_detects_tamper(self):
        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"]),
                _completed(["git", "diff", "--check"]),
            ],
        ):
            result = preflight.run_minimal_controlled_preflight_sequence(_payload())

        tampered = result.as_dict()
        tampered["overall_status"] = "PREFLIGHT_FAILED"
        self.assertNotEqual(
            result.preflight_result_hash,
            preflight.minimal_controlled_preflight_result_hash(tampered),
        )

    def test_failure_status_binds_failure_hashes(self):
        with mock.patch(
            "subprocess.run",
            side_effect=[
                _completed(["git", "status", "--short"]),
                _completed(["git", "diff", "--check"], returncode=1),
            ],
        ):
            result = preflight.run_minimal_controlled_preflight_sequence(_payload())

        self.assertEqual(result.overall_status, "PREFLIGHT_FAILED")
        self.assertTrue(result.child_receipt_hashes[1])
        self.assertTrue(result.child_failure_bundle_hashes[1])
        self.assertIn("NONZERO_EXIT", result.failure_reasons)

    def test_preflight_rejects_command_lists_and_execution_material(self):
        forbidden_fields = (
            "command_ids",
            "commands",
            "steps",
            "graph",
            "argv",
            "cwd",
            "env",
            "path",
            "executable",
            "timeout",
            "shell",
        )
        for field_name in forbidden_fields:
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "preflight_field_forbidden"):
                    preflight.run_minimal_controlled_preflight_sequence(
                        _payload(**{field_name: "payload-supplied"})
                    )

    def test_preflight_source_has_no_direct_execution_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for marker in (
            "subprocess",
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
            "kernel.runtime.",
            "kernel.os_engine",
            "tools.local_execution_kernel.",
        ):
            self.assertNotIn(marker, source)

    def test_preflight_order_is_exactly_status_then_diff_check(self):
        self.assertEqual(preflight.PREFLIGHT_ORDER, ("git_status_short", "git_diff_check"))


if __name__ == "__main__":
    unittest.main()
