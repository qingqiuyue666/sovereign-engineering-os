import contextlib
import io
import json
import os
import stat
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from kernel.capabilities.operator_provided_playwright_execution_receipt import (
    ADAPTER_DRAFT_RUN_DIR_NAME,
    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE,
    build_operator_provided_playwright_execution_receipt_plan,
    run_operator_provided_playwright_execution_receipt,
)
from kernel.capabilities.bounded_playwright_worker_adapter_draft import (
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE,
)
from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_operator_provided_playwright_execution_receipt_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

RECEIPT_PLAN_OUTPUTS = {
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE,
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("external path should not be called")


class OperatorProvidedPlaywrightExecutionReceiptTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "output"
        output_dir.mkdir()
        matrix_path = root / "selection_matrix.json"
        manifest_path = root / "playwright_manifest.json"
        write_json_atomically(matrix_path, self.valid_matrix())
        write_json_atomically(manifest_path, self.valid_manifest())
        return root, matrix_path, manifest_path, output_dir

    def repo_temp_dir(self):
        temp_dir = tempfile.TemporaryDirectory(dir=REPO_ROOT)
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def valid_matrix(self):
        return {
            "matrix_type": "real_github_candidate_selection_matrix_v1",
            "selection_pack_id": "real-github-candidate-evaluation-pack-v1",
            "authority": "non_authority_candidate_evaluation_record",
            "network_access_performed": False,
            "github_network_search_performed_by_code": False,
            "git_clone_performed": False,
            "git_command_performed": False,
            "dependency_installation_performed": False,
            "third_party_code_execution_performed": False,
            "candidate_code_imported": False,
            "adapter_generated": False,
            "adapter_registered": False,
            "auto_adoption_performed": False,
            "autonomous_execution_performed": False,
            "candidates": [
                {
                    "candidate_id": "github-candidate-microsoft-playwright-v1",
                    "repo_full_name": "microsoft/playwright",
                    "intended_use": "browser_automation",
                    "selection_rank": 1,
                    "decision": "select_for_first_bounded_sandbox_smoke",
                    "next_allowed_action": "create_playwright_local_fixture_sandbox_smoke_plan",
                    "selected_for_first_sandbox_smoke": True,
                    "license_review_required": True,
                    "security_review_required": True,
                    "sandbox_review_required": True,
                    "adapter_generation_allowed": False,
                }
            ],
        }

    def valid_manifest(self, **overrides):
        payload = {
            "candidate_type": "github_capability_candidate_v1",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "candidate_name": "Microsoft Playwright",
            "repo_url": "https://github.com/microsoft/playwright",
            "repo_full_name": "microsoft/playwright",
            "default_branch": "main",
            "source_origin": "web_research",
            "intended_use": "browser_automation",
            "capability_domains": ["browser_automation"],
            "declared_license": "Apache-2.0",
            "declared_runtime_languages": ["TypeScript", "JavaScript"],
            "declared_external_services": ["browser runtimes"],
            "declared_install_commands": ["npm i playwright"],
            "declared_run_commands": ["npx playwright test"],
            "declared_network_requirements": ["web targets require network"],
            "declared_secret_requirements": [],
            "declared_file_system_permissions": ["writes screenshots"],
            "declared_risks": ["browser automation can access live websites"],
            "user_value_hypothesis": "Useful local browser automation substrate.",
            "integration_hypothesis": "Start with local fixture pages only.",
            "evidence_notes": "Selected for first bounded smoke.",
        }
        payload.update(overrides)
        return payload

    def make_fake_node(self, root):
        fake_node = root / "fake-node"
        fake_node.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys
                os.execv(sys.executable, [sys.executable] + sys.argv[1:])
                """
            ),
            encoding="utf-8",
        )
        fake_node.chmod(fake_node.stat().st_mode | stat.S_IXUSR)
        return fake_node

    def make_fake_runner(self, path, *, mode="success"):
        success_value = mode == "success"
        exit_code = 11 if mode == "failure" else 0
        body = f"""\
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--fixture-url", required=True)
parser.add_argument("--output-json", required=True)
parser.add_argument("--screenshot-path", required=True)
args = parser.parse_args()
Path(args.screenshot_path).write_bytes(b"fake-png")
payload = {{
    "runner_type": "playwright_local_fixture_smoke_runner_v1",
    "fixture_url": args.fixture_url,
    "marker_found": {str(success_value).capitalize()},
    "click_completed": {str(success_value).capitalize()},
    "status_text": {"'clicked'" if success_value else "''"},
    "non_local_request_count": 0,
    "non_local_requests": [],
    "screenshot_path": args.screenshot_path,
    "success": {str(success_value).capitalize()},
}}
Path(args.output_json).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
sys.exit({exit_code})
"""
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def build_plan(self, matrix_path, manifest_path, output_dir, **kwargs):
        return build_operator_provided_playwright_execution_receipt_plan(
            matrix_path,
            manifest_path,
            output_dir,
            kwargs.pop("receipt_id", "receipt-001"),
            node_command=kwargs.pop("node_command"),
            runner_script=kwargs.pop("runner_script"),
            operator_attestation=kwargs.pop(
                "operator_attestation",
                OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            ),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop("operator_notes", "local fixture only"),
            **kwargs,
        )

    def run_receipt(self, matrix_path, manifest_path, output_dir, **kwargs):
        return run_operator_provided_playwright_execution_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            kwargs.pop("receipt_id", "receipt-001"),
            node_command=kwargs.pop("node_command"),
            runner_script=kwargs.pop("runner_script"),
            operator_attestation=kwargs.pop(
                "operator_attestation",
                OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            ),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop("operator_notes", "local fixture only"),
            **kwargs,
        )

    def assert_no_artifacts(self, output_dir):
        if not output_dir.exists():
            return
        for name in RECEIPT_PLAN_OUTPUTS | {
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE
        }:
            self.assertFalse((output_dir / name).exists(), name)
            self.assertFalse((output_dir / name).is_symlink(), name)
        self.assertFalse((output_dir / ADAPTER_DRAFT_RUN_DIR_NAME).exists())
        self.assertFalse((output_dir / ADAPTER_DRAFT_RUN_DIR_NAME).is_symlink())

    def assert_false_boundaries(self, payload):
        for field_name in OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_plan_only_creates_receipt_artifacts_without_invoking_adapter_execution(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(
                    "kernel.capabilities.bounded_playwright_worker_adapter_draft.run_bounded_playwright_worker_adapter_draft",
                    side_effect=fail_if_called,
                )
            )
            stack.enter_context(patch("subprocess.run", side_effect=fail_if_called))
            stack.enter_context(patch("os.system", side_effect=fail_if_called))
            stack.enter_context(
                patch("socket.create_connection", side_effect=fail_if_called)
            )
            result = self.build_plan(
                matrix_path,
                manifest_path,
                output_dir,
                node_command=fake_node,
                runner_script=fake_runner,
            )

        self.assertTrue(result.complete)
        self.assertFalse(result.executed)
        for name in RECEIPT_PLAN_OUTPUTS:
            self.assertTrue((output_dir / name).is_file(), name)
        self.assertFalse(
            (output_dir / OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE).exists()
        )
        self.assertFalse((output_dir / ADAPTER_DRAFT_RUN_DIR_NAME).exists())

    def test_run_calls_421_with_execute_local_fixture_smoke_true(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        fake_adapter = SimpleNamespace(
            payload={"success": False},
            success=False,
            complete=False,
            result_path=None,
            plan_path=None,
            manifest_path=None,
            summary_path=None,
            checklist_path=None,
        )
        with patch(
            "kernel.capabilities.bounded_playwright_worker_adapter_draft.run_bounded_playwright_worker_adapter_draft",
            return_value=fake_adapter,
        ) as adapter_mock:
            result = self.run_receipt(
                matrix_path,
                manifest_path,
                output_dir,
                node_command=fake_node,
                runner_script=fake_runner,
            )

        self.assertFalse(result.complete)
        adapter_mock.assert_called_once()
        self.assertIs(adapter_mock.call_args.kwargs["execute_local_fixture_smoke"], True)
        self.assertEqual(adapter_mock.call_args.args[2], output_dir / ADAPTER_DRAFT_RUN_DIR_NAME)

    def test_requires_exact_operator_attestation_and_fails_closed(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation="WRONG",
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_requires_node_command_and_runner_script(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        missing_node_output = root / "missing-node-output"
        missing_node_output.mkdir()
        result = build_operator_provided_playwright_execution_receipt_plan(
            matrix_path,
            manifest_path,
            missing_node_output,
            "receipt-001",
            runner_script=fake_runner,
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_node_output)

        missing_runner_output = root / "missing-runner-output"
        missing_runner_output.mkdir()
        result = build_operator_provided_playwright_execution_receipt_plan(
            matrix_path,
            manifest_path,
            missing_runner_output,
            "receipt-001",
            node_command=fake_node,
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_runner_output)

    def test_node_command_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        node_link = root / "node-link"
        node_link.symlink_to(fake_node)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=node_link,
            runner_script=fake_runner,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_runner_script_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        runner_link = root / "runner-link.py"
        runner_link.symlink_to(fake_runner)

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=runner_link,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_runner_script_outside_repo_and_output_dir_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        outside_runner = self.make_fake_runner(root / "outside-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=outside_runner,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_output_dir_missing_blocks_with_no_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        missing_output = root / "missing-output"

        result = self.build_plan(
            matrix_path,
            manifest_path,
            missing_output,
            node_command=fake_node,
            runner_script=fake_runner,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_output)

    def test_existing_receipt_output_file_blocks_with_no_overwrite(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        existing = output_dir / OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE
        existing.write_text("do not overwrite\n", encoding="utf-8")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )

        self.assertFalse(result.complete)
        self.assertEqual(existing.read_text(encoding="utf-8"), "do not overwrite\n")
        self.assertFalse((output_dir / ADAPTER_DRAFT_RUN_DIR_NAME).exists())

    def test_adapter_draft_run_directory_preexists_blocks_with_no_overwrite(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        adapter_dir = output_dir / ADAPTER_DRAFT_RUN_DIR_NAME
        adapter_dir.mkdir()
        sentinel = adapter_dir / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )

        self.assertFalse(result.complete)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        for name in RECEIPT_PLAN_OUTPUTS:
            self.assertFalse((output_dir / name).exists(), name)

    def test_receipt_plan_records_node_and_runner_hashes_and_sizes(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        plan = read_json(result.plan_path)

        self.assertEqual(plan["node_command_sha256"], sha256_file(fake_node))
        self.assertEqual(plan["node_command_size_bytes"], fake_node.stat().st_size)
        self.assertEqual(plan["runner_script_sha256"], sha256_file(fake_runner))
        self.assertEqual(plan["runner_script_size_bytes"], fake_runner.stat().st_size)

    def test_receipt_plan_has_no_target_or_user_url_fields_except_disabled_boundaries(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        plan = read_json(result.plan_path)

        self.assertEqual(plan["target_url_accepted"], False)
        self.assertEqual(plan["user_supplied_url_accepted"], False)
        url_keys = {key for key in plan if "url" in key}
        self.assertEqual(
            url_keys,
            {
                "target_url_accepted",
                "user_supplied_url_accepted",
                "arbitrary_url_navigation_allowed",
                "user_supplied_url_allowed",
                "arbitrary_url_navigation_performed",
                "user_supplied_url_used",
                "fixture_url_source",
                "fixture_url_scheme",
            },
        )

    def test_receipt_plan_has_all_disabled_fields_false(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        plan = read_json(result.plan_path)

        for field_name in OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS:
            self.assertIn(field_name, plan)
            self.assertFalse(plan[field_name], field_name)

    def test_receipt_plan_has_all_performed_false_fields_false(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assert_false_boundaries(read_json(result.plan_path))

    def test_explicit_fake_runner_success_writes_receipt_adapter_and_smoke_results(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )

        self.assertTrue(result.complete)
        self.assertTrue((output_dir / OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE).is_file())
        self.assertTrue((output_dir / ADAPTER_DRAFT_RUN_DIR_NAME / BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE).is_file())
        self.assertTrue(
            (
                output_dir
                / ADAPTER_DRAFT_RUN_DIR_NAME
                / "embedded_smoke"
                / PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE
            ).is_file()
        )

    def test_receipt_result_maps_embedded_fields_and_adapter_success(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assertTrue(result_payload["embedded_marker_found"])
        self.assertTrue(result_payload["embedded_click_completed"])
        self.assertEqual(result_payload["embedded_status_text"], "clicked")
        self.assertEqual(result_payload["embedded_non_local_request_count"], 0)
        self.assertTrue(result_payload["embedded_success"])
        self.assertTrue(result_payload["adapter_draft_success"])

    def test_fake_runner_failure_writes_failed_receipt_result(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(
            self.repo_temp_dir() / "fake-runner.py",
            mode="failure",
        )

        result = self.run_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertFalse(result_payload["success"])
        self.assertFalse(result_payload["adapter_draft_success"])
        self.assertEqual(
            result_payload["next_allowed_action"],
            "fix_operator_provided_local_fixture_execution_and_retry",
        )

    def test_receipt_result_keeps_all_performed_false_fields_false(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assert_false_boundaries(read_json(result.result_path))

    def test_artifact_index_includes_only_receipt_and_adapter_run_artifacts_under_output_dir(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        artifact_index = read_json(result.artifact_index_path)

        roles = {entry["artifact_role"] for entry in artifact_index["entries"]}
        self.assertIn("operator_provided_playwright_execution_receipt_plan", roles)
        self.assertIn(
            "adapter_draft_run_bounded_playwright_worker_adapter_draft_result_json",
            roles,
        )
        for entry in artifact_index["entries"]:
            artifact_path = Path(entry["path"]).resolve()
            self.assertTrue(artifact_path.is_relative_to(output_dir.resolve()))
            self.assertFalse(entry["candidate_repo_file"])
            self.assertFalse(entry["external_candidate_artifact"])

    def test_artifact_index_does_not_include_candidate_repo_files(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_receipt(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        artifact_index = read_json(result.artifact_index_path)

        for entry in artifact_index["entries"]:
            self.assertFalse(entry["candidate_repo_file"])
            self.assertFalse(entry["external_candidate_artifact"])
            self.assertNotIn("microsoft/playwright", entry["path"])

    def test_launcher_payload_preserves_all_performed_false_fields(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = run_operator_provided_playwright_execution_receipt_launcher(
            matrix_path,
            manifest_path,
            output_dir,
            "receipt-001",
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
        )
        payload = result.to_cli_payload()

        self.assertTrue(payload["complete"])
        self.assert_false_boundaries(payload)

    def test_task_graph_node_writes_receipt_artifact_outputs(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        receipt_output = root / "receipt-output"
        graph_output = root / "graph-output"
        receipt_output.mkdir()
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.receipt_graph(matrix_path, manifest_path, receipt_output, fake_node, fake_runner),
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}

        self.assertTrue(result.success)
        self.assertIn("operator_provided_playwright_execution_receipt_plan", roles)
        self.assertIn("operator_provided_playwright_execution_receipt_result", roles)
        self.assertIn("bounded_playwright_worker_adapter_draft_result", roles)

    def test_task_graph_node_preserves_all_performed_false_fields(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        receipt_output = root / "receipt-output"
        graph_output = root / "graph-output"
        receipt_output.mkdir()
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.receipt_graph(matrix_path, manifest_path, receipt_output, fake_node, fake_runner),
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        node = execution_manifest["nodes"][0]

        self.assertEqual(
            node["adapter_id"],
            "operator_provided_playwright_execution_receipt",
        )
        self.assert_false_boundaries(node)

    def test_cli_plan_only_path_works(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-operator-provided-playwright-execution-receipt",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--receipt-id",
                    "cli-receipt-001",
                    "--node-command",
                    fake_node.as_posix(),
                    "--runner-script",
                    fake_runner.as_posix(),
                    "--operator-attestation",
                    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                    "--plan-only",
                ]
            )
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["executed"])

    def test_cli_explicit_fake_runner_receipt_path_works(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-operator-provided-playwright-execution-receipt",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--receipt-id",
                    "cli-receipt-001",
                    "--node-command",
                    fake_node.as_posix(),
                    "--runner-script",
                    fake_runner.as_posix(),
                    "--operator-attestation",
                    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                ]
            )
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(payload["executed"])
        self.assertTrue(payload["embedded_marker_found"])
        self.assertEqual(payload["embedded_status_text"], "clicked")

    def test_tests_patch_external_paths_and_do_not_use_network_clients(self):
        source = Path(__file__).read_text(encoding="utf-8")

        self.assertIn('patch("subprocess.run"', source)
        self.assertIn('patch("os.system"', source)
        self.assertIn('patch("socket.create_connection"', source)
        self.assertNotIn("import requ" + "ests", source)
        self.assertNotIn("from requ" + "ests", source)
        self.assertNotIn("import htt" + "px", source)
        self.assertNotIn("from htt" + "px", source)
        self.assertNotIn("import url" + "lib", source)
        self.assertNotIn("from url" + "lib", source)

    def test_module_source_has_no_disallowed_execution_or_arbitrary_target_arg_path(self):
        module_source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "operator_provided_playwright_execution_receipt.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("subprocess.run", module_source)
        self.assertNotIn("os.system", module_source)
        self.assertNotIn("git clone", module_source)
        self.assertNotIn("fetch(", module_source)
        self.assertNotIn("--target-url", module_source)
        self.assertNotIn("--url", module_source)
        self.assertNotIn("npm ", module_source)
        self.assertNotIn("npx ", module_source)

    def test_wrong_attestation_with_sensitive_marker_does_not_leak_raw_text(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        bad_attestation = "SECRET_TOKEN_PASSWORD_BAD_ATTESTATION"

        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation=bad_attestation,
        )
        serialized = json.dumps(result.payload, sort_keys=True)

        self.assertFalse(result.complete)
        self.assertNotIn(bad_attestation, serialized)
        self.assertNotIn("SECRET_TOKEN_PASSWORD", serialized)
        self.assert_no_artifacts(output_dir)

    def receipt_graph(self, matrix_path, manifest_path, output_dir, fake_node, fake_runner):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "operator-provided-playwright-receipt-graph",
            "authority": "non_authority",
            "required_human_approval": True,
            "execution_mode": "fixture_execution",
            "nodes": [
                {
                    "node_id": "operator_playwright_receipt",
                    "adapter_id": "operator_provided_playwright_execution_receipt",
                    "capability": "launch_operator_provided_playwright_execution_receipt",
                    "depends_on": [],
                    "execution_mode": "fixture",
                    "approval_checkpoint_required": True,
                    "approval_checkpoint_id": "operator-playwright-receipt:human_review",
                    "inputs": {
                        "selection_matrix": Path(matrix_path).as_posix(),
                        "playwright_candidate_manifest": Path(
                            manifest_path
                        ).as_posix(),
                        "output_dir": Path(output_dir).as_posix(),
                        "receipt_id": "graph-receipt-001",
                        "node_command": Path(fake_node).as_posix(),
                        "runner_script": Path(fake_runner).as_posix(),
                        "operator_attestation": OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                        "project_id": "project-001",
                    },
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
