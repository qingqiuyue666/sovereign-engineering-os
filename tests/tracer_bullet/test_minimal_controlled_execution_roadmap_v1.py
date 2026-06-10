"""Tracer-bullet tests for Minimal Controlled Execution Roadmap V1."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROADMAP_PATH = Path("governance/roadmap/minimal_controlled_execution_v1.json")
DOC_PATH = Path("docs/roadmap/minimal_controlled_execution_v1.md")
RUNNER_PATHS = (
    Path("kernel/runtime/minimal_controlled_execution_runner.py"),
    Path("kernel/runtime/allowlisted_runner.py"),
    Path("kernel/execution/allowlisted_runner.py"),
)


def _roadmap() -> dict[str, object]:
    return json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))


class MinimalControlledExecutionRoadmapTests(unittest.TestCase):
    def test_roadmap_defines_target_state(self):
        roadmap = _roadmap()
        self.assertEqual(roadmap["object_type"], "MinimalControlledExecutionRoadmap")
        self.assertEqual(roadmap["next_target_state"], "MINIMAL_CONTROLLED_EXECUTION_READY")
        self.assertEqual(roadmap["status"], "ROADMAP_ONLY")

    def test_allowed_command_set_exactly_equals_contract_only_v1_registry(self):
        self.assertEqual(
            _roadmap()["allowed_command_set"],
            [
                "git_status_short",
                "git_diff_check",
            ],
        )

    def test_unittest_and_make_ci_are_deferred_future_only(self):
        roadmap = _roadmap()
        self.assertEqual(
            roadmap["deferred_future_command_ids"],
            [
                "unittest_discover_tests",
                "make_ci",
            ],
        )
        for command_id in roadmap["deferred_future_command_ids"]:
            self.assertNotIn(command_id, roadmap["allowed_command_set"])

    def test_registry_entries_include_required_immutable_metadata(self):
        entries = _roadmap()["registry_entries"]
        self.assertEqual(set(entries), {"git_status_short", "git_diff_check"})
        for command_id, entry in entries.items():
            self.assertEqual(entry["command_class"], "REPOSITORY_READ_ONLY_CHECK")
            self.assertTrue(entry["read_only_expectation"])
            self.assertTrue(entry["allowed_verifier"].endswith("_contract_verifier"))
            self.assertEqual(
                entry["registry_version"],
                "minimal_controlled_execution_registry_v1",
            )
            self.assertIsInstance(entry["fixed_argv"], list)
            self.assertEqual(entry["fixed_argv"][0], "git")

    def test_arbitrary_command_execution_forbidden(self):
        forbidden = set(_roadmap()["explicit_forbidden_commands"])
        self.assertIn("arbitrary shell", forbidden)
        self.assertIn("payload-provided executable", forbidden)
        self.assertIn("subprocess", forbidden)
        self.assertIn("runner", forbidden)
        self.assertIn("launcher", forbidden)
        self.assertIn("CLI entrypoint", forbidden)
        self.assertIn("task graph execution", forbidden)
        self.assertIn("auto re-execution", forbidden)

    def test_command_line_forbidden(self):
        self.assertIn("command_line", _roadmap()["explicit_forbidden_commands"])
        self.assertIn("command", _roadmap()["explicit_forbidden_commands"])

    def test_arbitrary_argv_forbidden(self):
        self.assertIn("arbitrary argv", _roadmap()["explicit_forbidden_commands"])

    def test_network_browser_provider_credential_dcc_comfyui_mcp_plugin_forbidden(self):
        forbidden = set(_roadmap()["explicit_forbidden_commands"])
        for marker in (
            "network calls",
            "browser control",
            "provider API",
            "credentials",
            "DCC launch",
            "ComfyUI launch",
            "MCP execution",
            "CLI plugin execution",
        ):
            self.assertIn(marker, forbidden)

    def test_receipt_requirements_include_digests_and_verifier_result(self):
        requirements = set(_roadmap()["receipt_requirements"])
        self.assertIn("stdout_digest", requirements)
        self.assertIn("stderr_digest", requirements)
        self.assertIn("verifier_result", requirements)
        self.assertIn("execution_performed=false", requirements)

    def test_failure_bundle_requires_human_review(self):
        self.assertIn("human_review_required", _roadmap()["failure_bundle_requirements"])
        self.assertIn("execution_performed=false", _roadmap()["failure_bundle_requirements"])

    def test_non_goals_include_no_general_shell_and_no_gui(self):
        non_goals = set(_roadmap()["non_goals"])
        self.assertIn("no general shell", non_goals)
        self.assertIn("no GUI", non_goals)
        self.assertIn("no dry-run abstraction layer", non_goals)

    def test_this_pr_implements_no_runner(self):
        roadmap = _roadmap()
        doc = DOC_PATH.read_text(encoding="utf-8")
        self.assertFalse(roadmap["implementation_allowed_in_this_pr"])
        self.assertFalse(roadmap["runner_implemented"])
        self.assertFalse(roadmap["allowlisted_runner_implemented"])
        self.assertIn("does not implement execution", doc)
        for path in RUNNER_PATHS:
            self.assertFalse(path.exists(), str(path))


if __name__ == "__main__":
    unittest.main()
