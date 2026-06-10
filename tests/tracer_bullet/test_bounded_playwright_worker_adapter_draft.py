import contextlib
import io
import json
import os
import stat
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.capabilities.bounded_playwright_worker_adapter_draft import (
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_DISABLED_FIELDS,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE,
    EMBEDDED_SMOKE_DIR_NAME,
    build_bounded_playwright_worker_adapter_draft_plan,
    run_bounded_playwright_worker_adapter_draft,
)
from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
    FIXTURE_APP_JS_FILE,
    FIXTURE_DIR_NAME,
    FIXTURE_INDEX_FILE,
    FIXTURE_STYLE_CSS_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

WRAPPER_PLAN_OUTPUTS = {
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE,
}
WRAPPER_EXECUTION_OUTPUTS = {
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE,
}
EMBEDDED_PLAN_OUTPUTS = {
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
}
EMBEDDED_EXECUTION_OUTPUTS = {
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE,
}
EMBEDDED_FIXTURE_OUTPUTS = {
    f"{FIXTURE_DIR_NAME}/{FIXTURE_INDEX_FILE}",
    f"{FIXTURE_DIR_NAME}/{FIXTURE_APP_JS_FILE}",
    f"{FIXTURE_DIR_NAME}/{FIXTURE_STYLE_CSS_FILE}",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("external path should not be called")


class BoundedPlaywrightWorkerAdapterDraftTests(unittest.TestCase):
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

    def build_plan(self, matrix_path, manifest_path, output_dir):
        return build_bounded_playwright_worker_adapter_draft_plan(
            matrix_path,
            manifest_path,
            output_dir,
            "adapter-draft-001",
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="adapter draft around local fixture only",
        )

    def run_adapter(self, matrix_path, manifest_path, output_dir, **kwargs):
        return run_bounded_playwright_worker_adapter_draft(
            matrix_path,
            manifest_path,
            output_dir,
            kwargs.pop("adapter_draft_id", "adapter-draft-001"),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop(
                "operator_notes",
                "adapter draft around local fixture only",
            ),
            **kwargs,
        )

    def write_matrix(self, path, payload):
        write_json_atomically(path, payload)
        return path

    def write_manifest(self, path, payload):
        write_json_atomically(path, payload)
        return path

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

    def assert_no_artifacts(self, output_dir):
        if not output_dir.exists():
            return
        for name in WRAPPER_PLAN_OUTPUTS | WRAPPER_EXECUTION_OUTPUTS:
            self.assertFalse((output_dir / name).exists(), name)
            self.assertFalse((output_dir / name).is_symlink(), name)
        self.assertFalse((output_dir / EMBEDDED_SMOKE_DIR_NAME).exists())
        self.assertFalse((output_dir / EMBEDDED_SMOKE_DIR_NAME).is_symlink())

    def assert_false_boundaries(self, payload):
        for field_name in BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_plan_only_creates_wrapper_and_embedded_artifacts_without_subprocess(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch("subprocess.run", side_effect=fail_if_called))
            stack.enter_context(patch("os.system", side_effect=fail_if_called))
            stack.enter_context(patch("os.popen", side_effect=fail_if_called))
            stack.enter_context(
                patch("socket.create_connection", side_effect=fail_if_called)
            )
            result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertTrue(result.complete)
        self.assertFalse(result.executed)
        for name in WRAPPER_PLAN_OUTPUTS:
            self.assertTrue((output_dir / name).is_file(), name)
        for name in EMBEDDED_PLAN_OUTPUTS:
            self.assertTrue((output_dir / EMBEDDED_SMOKE_DIR_NAME / name).is_file(), name)
        for name in EMBEDDED_FIXTURE_OUTPUTS:
            self.assertTrue((output_dir / EMBEDDED_SMOKE_DIR_NAME / name).is_file(), name)
        self.assertFalse((output_dir / BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE).exists())

    def test_wrapper_internally_uses_420_smoke_path_and_passes_inputs(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        with patch(
            "kernel.capabilities.bounded_playwright_worker_adapter_draft.run_playwright_local_fixture_sandbox_smoke",
            wraps=run_bounded_playwright_worker_adapter_draft.__globals__[
                "run_playwright_local_fixture_sandbox_smoke"
            ],
        ) as smoke_mock:
            result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertTrue(result.complete)
        smoke_mock.assert_called_once()
        call_args = smoke_mock.call_args.args
        self.assertEqual(call_args[0], matrix_path)
        self.assertEqual(call_args[1], manifest_path)
        self.assertEqual(call_args[2], output_dir / EMBEDDED_SMOKE_DIR_NAME)

    def test_blocks_bad_selection_matrix_with_no_wrapper_artifacts(self):
        root, _matrix_path, manifest_path, output_dir = self.workspace()
        matrix = self.valid_matrix()
        matrix["candidates"][0]["candidate_id"] = "github-candidate-other-v1"
        bad_matrix = self.write_matrix(root / "bad-matrix.json", matrix)

        result = self.build_plan(bad_matrix, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_blocks_bad_playwright_manifest_with_no_wrapper_artifacts(self):
        root, matrix_path, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(
            root / "bad-manifest.json",
            self.valid_manifest(repo_full_name="example/not-playwright"),
        )

        result = self.build_plan(matrix_path, bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_output_dir_missing_blocks_with_no_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        missing_output = root / "missing-output"

        result = self.build_plan(matrix_path, manifest_path, missing_output)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_output)

    def test_existing_wrapper_output_file_blocks_with_no_overwrite(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()
        existing = output_dir / BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE
        existing.write_text("do not overwrite\n", encoding="utf-8")

        result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertEqual(existing.read_text(encoding="utf-8"), "do not overwrite\n")
        self.assertFalse((output_dir / EMBEDDED_SMOKE_DIR_NAME).exists())

    def test_embedded_smoke_directory_preexists_blocks_with_no_overwrite(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()
        embedded_dir = output_dir / EMBEDDED_SMOKE_DIR_NAME
        embedded_dir.mkdir()
        sentinel = embedded_dir / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")

        result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        for name in WRAPPER_PLAN_OUTPUTS:
            self.assertFalse((output_dir / name).exists(), name)

    def test_wrapper_output_symlink_collision_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        target = root / "target.json"
        target.write_text("{}\n", encoding="utf-8")
        (output_dir / BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE).symlink_to(target)

        result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertFalse((output_dir / EMBEDDED_SMOKE_DIR_NAME).exists())

    def test_wrapper_plan_references_embedded_paths_under_output_dir(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        plan = read_json(result.plan_path)

        for field_name in (
            "embedded_smoke_dir",
            "embedded_smoke_plan_path",
            "embedded_smoke_manifest_path",
            "embedded_fixture_dir",
        ):
            self.assertTrue(
                Path(plan[field_name]).resolve().is_relative_to(output_dir.resolve()),
                field_name,
            )
        self.assertIn(f"/{EMBEDDED_SMOKE_DIR_NAME}/", plan["embedded_smoke_plan_path"])

    def test_embedded_fixture_url_is_file_only(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        plan = read_json(result.plan_path)

        self.assertEqual(plan["embedded_fixture_url_scheme"], "file")
        self.assertTrue(plan["embedded_fixture_url"].startswith("file://"))
        self.assertNotIn("http://", plan["embedded_fixture_url"])
        self.assertNotIn("https://", plan["embedded_fixture_url"])

    def test_wrapper_plan_has_disabled_and_performed_false_fields(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        plan = read_json(result.plan_path)

        for field_name in BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_DISABLED_FIELDS:
            self.assertIn(field_name, plan)
            self.assertFalse(plan[field_name], field_name)
        self.assert_false_boundaries(plan)

    def test_explicit_execution_requires_node_command_and_runner_script_through_420(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        repo_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        missing_node_output = root / "missing-node-output"
        missing_node_output.mkdir()
        missing_runner_output = root / "missing-runner-output"
        missing_runner_output.mkdir()

        result = self.run_adapter(
            matrix_path,
            manifest_path,
            missing_node_output,
            execute_local_fixture_smoke=True,
            runner_script=repo_runner,
        )
        self.assertFalse(result.complete)
        self.assertEqual(result.payload["failure_stage"], "preflight_execution")
        self.assert_no_artifacts(missing_node_output)

        result = self.run_adapter(
            matrix_path,
            manifest_path,
            missing_runner_output,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
        )
        self.assertFalse(result.complete)
        self.assertEqual(result.payload["failure_stage"], "preflight_execution")
        self.assert_no_artifacts(missing_runner_output)

    def test_explicit_fake_runner_success_writes_wrapper_and_embedded_results(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_adapter(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )

        self.assertTrue(result.complete)
        self.assertTrue((output_dir / BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE).is_file())
        for name in EMBEDDED_EXECUTION_OUTPUTS:
            self.assertTrue((output_dir / EMBEDDED_SMOKE_DIR_NAME / name).is_file(), name)

    def test_explicit_fake_runner_failure_writes_failed_wrapper_result(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(
            self.repo_temp_dir() / "fake-runner.py",
            mode="failure",
        )

        result = self.run_adapter(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertFalse(result_payload["success"])
        self.assertEqual(
            result_payload["worker_adapter_status"],
            "bounded_playwright_worker_adapter_draft_smoke_failed",
        )

    def test_wrapper_result_maps_embedded_smoke_success_fields(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_adapter(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assertTrue(result_payload["embedded_marker_found"])
        self.assertTrue(result_payload["embedded_click_completed"])
        self.assertEqual(result_payload["embedded_status_text"], "clicked")
        self.assertEqual(result_payload["embedded_non_local_request_count"], 0)
        self.assertTrue(result_payload["embedded_success"])

    def test_wrapper_result_keeps_all_performed_boundary_fields_false(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        result = self.run_adapter(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assert_false_boundaries(result_payload)

    def test_artifact_index_includes_only_output_dir_wrapper_and_embedded_artifacts(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        artifact_index = read_json(result.artifact_index_path)

        roles = {entry["artifact_role"] for entry in artifact_index["entries"]}
        self.assertIn("bounded_playwright_worker_adapter_draft_plan", roles)
        self.assertIn("embedded_playwright_local_fixture_sandbox_smoke_plan", roles)
        self.assertIn("embedded_fixture_index_html", roles)
        for entry in artifact_index["entries"]:
            artifact_path = Path(entry["path"]).resolve()
            self.assertTrue(artifact_path.is_relative_to(output_dir.resolve()))
            self.assertFalse(entry["candidate_repo_file"])
            self.assertFalse(entry["external_candidate_artifact"])

    def test_task_graph_node_writes_wrapper_artifact_outputs(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        adapter_output = root / "adapter-output"
        adapter_output.mkdir()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.adapter_graph(matrix_path, manifest_path, adapter_output),
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}

        self.assertTrue(result.success)
        self.assertIn("bounded_playwright_worker_adapter_draft_plan", roles)
        self.assertIn("embedded_playwright_local_fixture_sandbox_smoke_plan", roles)
        self.assertIn("embedded_fixture_index_html", roles)

    def test_task_graph_node_preserves_performed_false_boundary_fields(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        adapter_output = root / "adapter-output"
        adapter_output.mkdir()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.adapter_graph(matrix_path, manifest_path, adapter_output),
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        node = execution_manifest["nodes"][0]

        self.assertEqual(node["adapter_id"], "bounded_playwright_worker_adapter_draft")
        for field_name in BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS:
            self.assertIn(field_name, node)
            self.assertFalse(node[field_name], field_name)

    def adapter_graph(self, matrix_path, manifest_path, output_dir):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "bounded-playwright-adapter-draft-graph",
            "authority": "non_authority",
            "required_human_approval": True,
            "execution_mode": "fixture_execution",
            "nodes": [
                {
                    "node_id": "bounded-playwright-adapter-draft",
                    "adapter_id": "bounded_playwright_worker_adapter_draft",
                    "capability": "launch_bounded_playwright_worker_adapter_draft",
                    "depends_on": [],
                    "execution_mode": "fixture",
                    "approval_checkpoint_required": True,
                    "approval_checkpoint_id": "bounded-playwright-adapter-draft:human_review",
                    "inputs": {
                        "selection_matrix": matrix_path.as_posix(),
                        "playwright_candidate_manifest": manifest_path.as_posix(),
                        "output_dir": output_dir.as_posix(),
                        "adapter_draft_id": "graph-adapter-draft-001",
                        "project_id": "project-001",
                    },
                }
            ],
        }

    def test_cli_plan_only_path_works(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-bounded-playwright-worker-adapter-draft",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--adapter-draft-id",
                    "cli-adapter-draft-001",
                ]
            )
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["executed"])

    def test_cli_explicit_fake_runner_path_works(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-bounded-playwright-worker-adapter-draft",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--adapter-draft-id",
                    "cli-adapter-draft-001",
                    "--node-command",
                    fake_node.as_posix(),
                    "--runner-script",
                    fake_runner.as_posix(),
                    "--execute-local-fixture-smoke",
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

    def test_no_code_path_accepts_target_or_arbitrary_url_input(self):
        module_source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "bounded_playwright_worker_adapter_draft.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("target_url", module_source)
        self.assertNotIn("--target-url", module_source)
        self.assertNotIn("user_supplied_target", module_source)

    def test_no_code_path_uses_package_install_clone_fetch_or_npm_npx_commands(self):
        module_source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "bounded_playwright_worker_adapter_draft.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("subprocess.run", module_source)
        self.assertNotIn("os.system", module_source)
        self.assertNotIn("git clone", module_source)
        self.assertNotIn("npm ", module_source)
        self.assertNotIn("npx ", module_source)
        self.assertNotIn("fetch(", module_source)


if __name__ == "__main__":
    unittest.main()
