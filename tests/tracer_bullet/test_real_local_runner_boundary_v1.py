"""Tracer-bullet tests for the real local runner boundary."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from kernel.personal_ai.adapters.adapter_registry import find_adapter_entry
from kernel.personal_ai.local_mvp_cli import _SUBCOMMANDS, main
from kernel.personal_ai.product_health_check import build_product_health_report
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from kernel.runtime import real_local_runner_boundary as boundary
from kernel.runtime.real_local_runner_boundary import (
    REAL_LOCAL_RUNNER_ADAPTER_ID,
    REAL_LOCAL_RUNNER_APPROVAL_ATTESTATION,
    REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST,
    REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
    REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID,
    REAL_LOCAL_RUNNER_STDOUT_FILE,
    RealLocalRunnerDescriptor,
    build_real_local_runner_task_graph_node,
    preflight_real_local_runner_descriptor,
    run_real_local_runner_boundary,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class RealLocalRunnerBoundaryV1Tests(unittest.TestCase):
    def test_allowlisted_command_executes_and_writes_receipt_replay_and_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "runner"
            output_dir.mkdir()
            approval_path = self.write_approval(root, "diff_check", "run-001")

            result = run_real_local_runner_boundary(
                RealLocalRunnerDescriptor(
                    command_id="diff_check",
                    output_dir=output_dir,
                    approval_artifact_path=approval_path,
                    run_id="run-001",
                    timeout_seconds=30,
                    repo_root=REPO_ROOT,
                )
            )

            receipt = self.read_json(result.receipt_path)
            replay = self.read_json(result.replay_manifest_path)
            artifacts = self.read_json(result.artifact_binding_path)

            self.assertTrue(result.complete)
            self.assertEqual(receipt["command_id"], "diff_check")
            self.assertEqual(receipt["argv"], ["git", "diff", "--check"])
            self.assertEqual(receipt["exit_code"], 0)
            self.assertFalse(receipt["shell"])
            self.assertFalse(receipt["shell_allowed"])
            self.assertFalse(receipt["user_command_line_allowed"])
            self.assertFalse(receipt["user_argv_allowed"])
            self.assertFalse(receipt["network_allowed"])
            self.assertFalse(receipt["browser_allowed"])
            self.assertFalse(receipt["provider_api_allowed"])
            self.assertFalse(receipt["production_autonomy_allowed"])
            self.assertEqual(
                receipt["environment_path_policy_id"],
                REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
            )
            self.assertEqual(
                receipt["executable_resolution_policy_id"],
                REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID,
            )
            self.assertTrue(Path(receipt["resolved_executable_path"]).is_absolute())
            self.assertTrue(Path(receipt["resolved_executable_realpath"]).is_absolute())
            self.assertRegex(
                receipt["resolved_executable_sha256"],
                r"^[0-9a-f]{64}$",
            )
            self.assertIsNone(
                receipt["resolved_executable_sha256_unavailable_reason"]
            )
            self.assertRegex(receipt["resolved_argv_hash"], r"^[0-9a-f]{64}$")
            self.assertTrue(result.stdout_path.is_file())
            self.assertTrue(result.stderr_path.is_file())
            self.assertEqual(replay["command_id"], "diff_check")
            self.assertFalse(replay["automatic_reexecution_allowed"])
            self.assertEqual(replay["executable_path"], receipt["resolved_executable_path"])
            self.assertEqual(replay["executable_sha256"], receipt["resolved_executable_sha256"])
            self.assertRegex(replay["environment_digest"], r"^[0-9a-f]{64}$")
            self.assertRegex(replay["resolution_policy_digest"], r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(artifacts["artifact_count"], 6)
            self.assertIsNone(result.failure_bundle_path)

    def test_preflight_resolves_allowed_command_to_audited_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "runner"
            output_dir.mkdir()
            approval_path = self.write_approval(root, "diff_check", "run-resolve")

            preflight = preflight_real_local_runner_descriptor(
                RealLocalRunnerDescriptor(
                    command_id="diff_check",
                    output_dir=output_dir,
                    approval_artifact_path=approval_path,
                    run_id="run-resolve",
                    timeout_seconds=30,
                    repo_root=REPO_ROOT,
                )
            )

            self.assertTrue(preflight["accepted"])
            self.assertEqual(preflight["command_id"], "diff_check")
            self.assertEqual(
                preflight["environment_path_policy_id"],
                REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
            )
            self.assertEqual(
                preflight["executable_resolution_policy_id"],
                REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID,
            )
            self.assertTrue(Path(preflight["resolved_executable_path"]).is_absolute())
            self.assertRegex(
                preflight["resolved_executable_sha256"],
                r"^[0-9a-f]{64}$",
            )
            self.assertFalse(
                preflight["executable_resolution"]["host_path_used_for_resolution"]
            )

    def test_descriptor_rejects_unknown_command_and_forbidden_command_surfaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "runner"
            output_dir.mkdir()
            approval_path = self.write_approval(root, "diff_check", "run-002")

            for forbidden_field in ("command_line", "argv", "shell"):
                payload = {
                    "approval_artifact_path": approval_path.as_posix(),
                    "command_id": "diff_check",
                    "output_dir": output_dir.as_posix(),
                    "run_id": "run-002",
                    "timeout_seconds": 5,
                    forbidden_field: True if forbidden_field == "shell" else "nope",
                }
                with self.assertRaises(ValueError):
                    RealLocalRunnerDescriptor.from_mapping(payload, repo_root=REPO_ROOT)

            unknown = RealLocalRunnerDescriptor(
                command_id="node",
                output_dir=output_dir,
                approval_artifact_path=approval_path,
                run_id="run-002",
                timeout_seconds=5,
                repo_root=REPO_ROOT,
            )
            preflight = preflight_real_local_runner_descriptor(unknown)
            self.assertFalse(preflight["accepted"])
            self.assertIn(
                "real_local_runner_command_id_not_allowlisted",
                preflight["failure_reasons"],
            )

    def test_path_hijack_missing_and_unsafe_symlink_resolution_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "runner"
            output_dir.mkdir()
            approval_path = self.write_approval(root, "diff_check", "run-path")

            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake_git = fake_bin / "git"
            fake_git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_git.chmod(0o755)
            descriptor = RealLocalRunnerDescriptor(
                command_id="diff_check",
                output_dir=output_dir,
                approval_artifact_path=approval_path,
                run_id="run-path",
                timeout_seconds=5,
                repo_root=REPO_ROOT,
            )
            with mock.patch.dict(
                os.environ,
                {"PATH": fake_bin.as_posix() + os.pathsep + os.environ.get("PATH", "")},
            ):
                hijack_preflight = preflight_real_local_runner_descriptor(descriptor)
            self.assertFalse(hijack_preflight["accepted"])
            self.assertIn(
                "host_path_hijack_forbidden:git",
                hijack_preflight["failure_reasons"],
            )

            with (
                mock.patch.object(boundary, "_SYSTEM_EXECUTABLE_ROOTS", ()),
                mock.patch.object(boundary, "_BREW_EXECUTABLE_ROOTS", ()),
                mock.patch.object(
                    boundary,
                    "_REPO_EXECUTABLE_RELATIVE_ROOTS",
                    ("missing-tools",),
                ),
                mock.patch.dict(os.environ, {"PATH": ""}),
            ):
                missing_preflight = preflight_real_local_runner_descriptor(descriptor)
            self.assertFalse(missing_preflight["accepted"])
            self.assertIn(
                "executable_resolution_missing:git",
                missing_preflight["failure_reasons"],
            )

            unsafe_root = root / "allowed-bin"
            unsafe_root.mkdir()
            unsafe_target = root / "unsafe-git"
            unsafe_target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            unsafe_target.chmod(0o755)
            unsafe_link = unsafe_root / "git"
            unsafe_link.symlink_to(unsafe_target)
            with (
                mock.patch.object(
                    boundary,
                    "_SYSTEM_EXECUTABLE_ROOTS",
                    (unsafe_root.as_posix(),),
                ),
                mock.patch.object(boundary, "_BREW_EXECUTABLE_ROOTS", ()),
                mock.patch.object(boundary, "_REPO_EXECUTABLE_RELATIVE_ROOTS", ()),
                mock.patch.dict(os.environ, {"PATH": ""}),
            ):
                symlink_preflight = preflight_real_local_runner_descriptor(descriptor)
            self.assertFalse(symlink_preflight["accepted"])
            self.assertIn(
                "executable_symlink_unsafe:" + unsafe_link.as_posix(),
                symlink_preflight["failure_reasons"],
            )

    def test_network_browser_node_npm_npx_are_not_allowlisted(self):
        self.assertEqual(
            set(REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST),
            {
                "focused_runner_chain_tests",
                "full_unittest_discover",
                "make_ci",
                "diff_check",
            },
        )
        flattened = {
            token.lower()
            for argv in REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST.values()
            for token in argv
        }

        for forbidden in ("browser", "node", "npm", "npx", "playwright"):
            self.assertNotIn(forbidden, flattened)
            self.assertNotIn(forbidden, REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST)

    def test_timeout_writes_failure_bundle_receipt_and_replay_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "runner"
            output_dir.mkdir()
            approval_path = self.write_approval(
                root,
                "focused_runner_chain_tests",
                "run-timeout",
            )

            result = run_real_local_runner_boundary(
                RealLocalRunnerDescriptor(
                    command_id="focused_runner_chain_tests",
                    output_dir=output_dir,
                    approval_artifact_path=approval_path,
                    run_id="run-timeout",
                    timeout_seconds=0.001,
                    repo_root=REPO_ROOT,
                )
            )

            receipt = self.read_json(result.receipt_path)
            failure = self.read_json(result.failure_bundle_path)
            replay = self.read_json(result.replay_manifest_path)

            self.assertFalse(result.complete)
            self.assertTrue(result.timed_out)
            self.assertEqual(receipt["status"], "timed_out")
            self.assertEqual(failure["failure_class"], "timeout")
            self.assertEqual(replay["failure_bundle_path"], result.failure_bundle_path.as_posix())

    def test_output_overwrite_and_symlink_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "runner"
            output_dir.mkdir()
            approval_path = self.write_approval(root, "diff_check", "run-003")
            (output_dir / REAL_LOCAL_RUNNER_STDOUT_FILE).write_text(
                "existing",
                encoding="utf-8",
            )

            descriptor = RealLocalRunnerDescriptor(
                command_id="diff_check",
                output_dir=output_dir,
                approval_artifact_path=approval_path,
                run_id="run-003",
                timeout_seconds=5,
                repo_root=REPO_ROOT,
            )
            preflight = preflight_real_local_runner_descriptor(descriptor)
            self.assertFalse(preflight["accepted"])
            self.assertIn(
                "output_artifact_overwrite_forbidden:stdout.txt",
                preflight["failure_reasons"],
            )

            target_dir = root / "target"
            target_dir.mkdir()
            symlink_dir = root / "symlink-output"
            symlink_dir.symlink_to(target_dir, target_is_directory=True)
            symlink_descriptor = RealLocalRunnerDescriptor(
                command_id="diff_check",
                output_dir=symlink_dir,
                approval_artifact_path=approval_path,
                run_id="run-003",
                timeout_seconds=5,
                repo_root=REPO_ROOT,
            )
            symlink_preflight = preflight_real_local_runner_descriptor(
                symlink_descriptor
            )
            self.assertFalse(symlink_preflight["accepted"])
            self.assertIn(
                "output_dir_symlink_forbidden",
                symlink_preflight["failure_reasons"],
            )

    def test_cli_registry_product_health_task_graph_and_artifact_binding_visibility(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output_dir = root / "runner-output"
            graph_output_dir = root / "graph-output"
            runner_output_dir.mkdir()
            graph_output_dir.mkdir()
            approval_path = self.write_approval(root, "diff_check", "run-graph")

            entry = find_adapter_entry(REAL_LOCAL_RUNNER_ADAPTER_ID)
            self.assertEqual(entry.admission_status.value, "candidate")
            self.assertEqual(entry.capabilities, ("launch_real_local_runner_boundary",))
            self.assertIn("command_id_only", entry.required_controls)
            self.assertIn("launch-real-local-runner-boundary", _SUBCOMMANDS)

            health = build_product_health_report(REPO_ROOT)
            self.assertIn(
                "real_local_runner_boundary_workflow",
                health["launcher_workflows"],
            )
            self.assertIn(
                "launch-real-local-runner-boundary",
                health["required_cli_subcommands"],
            )

            graph_path = root / "graph.json"
            graph = {
                "authority": "non_authority",
                "execution_mode": "fixture_execution",
                "graph_id": "real-local-runner-graph",
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "nodes": [
                    build_real_local_runner_task_graph_node(
                        node_id="real_runner",
                        command_id="diff_check",
                        output_dir=runner_output_dir,
                        approval_artifact_path=approval_path,
                        run_id="run-graph",
                        timeout_seconds=30,
                    )
                ],
                "required_human_approval": True,
            }
            graph_path.write_text(json.dumps(graph), encoding="utf-8")

            graph_result = run_local_task_graph_fixture(graph_path, graph_output_dir)
            execution_manifest = self.read_json(graph_result.execution_manifest_path)
            artifact_outputs = self.read_json(
                graph_result.artifact_outputs_manifest_path
            )

            self.assertTrue(graph_result.success)
            node = execution_manifest["nodes"][0]
            self.assertTrue(node["real_local_runner_complete"])
            self.assertFalse(node["adapter_route_admitted"])
            self.assertEqual(
                node["adapter_route_policy"],
                "real_local_runner_boundary_candidate_not_production_admitted",
            )
            self.assertFalse(node["network_access_performed"])
            self.assertFalse(node["browser_open_performed"])
            self.assertFalse(node["production_autonomy_enabled"])
            self.assertGreaterEqual(
                artifact_outputs["node_artifact_counts"]["real_runner"],
                6,
            )

            cli_output_dir = root / "cli-output"
            cli_output_dir.mkdir()
            cli_approval_path = self.write_approval(root, "diff_check", "run-cli")
            exit_code, payload = self.run_cli(
                [
                    "launch-real-local-runner-boundary",
                    "--command-id",
                    "diff_check",
                    "--output-dir",
                    cli_output_dir.as_posix(),
                    "--approval-artifact",
                    cli_approval_path.as_posix(),
                    "--run-id",
                    "run-cli",
                    "--timeout-seconds",
                    "30",
                    "--repo-root",
                    REPO_ROOT.as_posix(),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertEqual(payload["command_id"], "diff_check")

    def test_policy_docs_and_source_keep_forbidden_surfaces_closed(self):
        policy = self.read_json("governance/runtime/real_local_runner_boundary_v1.json")
        docs = Path("docs/decisions/real_local_runner_boundary_v1.md").read_text(
            encoding="utf-8"
        ).lower()
        source = Path("kernel/runtime/real_local_runner_boundary.py").read_text(
            encoding="utf-8"
        )

        self.assertEqual(policy["command_model"], "command_id_only")
        self.assertFalse(policy["user_command_line_allowed"])
        self.assertFalse(policy["user_argv_allowed"])
        self.assertFalse(policy["shell_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["production_autonomy_allowed"])
        self.assertFalse(policy["host_path_used_for_executable_resolution"])
        self.assertEqual(
            policy["environment_path_policy_id"],
            REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
        )
        self.assertEqual(
            policy["executable_resolution_policy_id"],
            REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID,
        )
        self.assertIn(
            "network_allowed=false means runner policy does not authorize network use",
            docs,
        )
        self.assertIn("not production admitted", docs)
        self.assertIn("shell=true", docs)
        self.assertIn("subprocess.run", source)
        self.assertIn("shell=False", source)
        self.assertNotIn('"PATH": os.environ.get("PATH"', source)
        for marker in (
            "import requests",
            "import httpx",
            "import urllib",
            "webbrowser.open",
            "from playwright",
            "from selenium",
            "shell=True",
            "exec(",
            "eval(",
        ):
            self.assertNotIn(marker, source)

    def write_approval(self, root, command_id, run_id):
        approval_path = Path(root) / (run_id + "-approval.json")
        approval = {
            "approval_attestation": REAL_LOCAL_RUNNER_APPROVAL_ATTESTATION,
            "approval_type": "real_local_runner_human_approval_v1",
            "approved": True,
            "command_id": command_id,
            "repo_revision": "not_provided",
            "reviewer_id": "test-reviewer",
            "run_id": run_id,
        }
        approval_path.write_text(json.dumps(approval), encoding="utf-8")
        return approval_path

    def read_json(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def run_cli(self, argv):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(argv)
        return exit_code, json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
