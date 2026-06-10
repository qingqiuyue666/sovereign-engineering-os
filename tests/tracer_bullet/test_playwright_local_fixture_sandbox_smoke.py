import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
    FIXTURE_APP_JS_FILE,
    FIXTURE_DIR_NAME,
    FIXTURE_INDEX_FILE,
    FIXTURE_MARKER_TEXT,
    FIXTURE_STYLE_CSS_FILE,
    PLAYWRIGHT_BOUNDARY_FALSE_FIELDS,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
    build_playwright_local_fixture_sandbox_smoke_plan,
    run_playwright_local_fixture_sandbox_smoke,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_DIR = REPO_ROOT / "docs" / "capability_candidates" / "github_real_candidates_v1"
SELECTION_MATRIX = PACK_DIR / "candidate_selection_matrix.json"
PLAYWRIGHT_MANIFEST = PACK_DIR / "microsoft_playwright_candidate_manifest.json"

PLAN_OUTPUTS = {
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
}
EXECUTION_OUTPUTS = {
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE,
}
FIXTURE_OUTPUTS = {
    f"{FIXTURE_DIR_NAME}/{FIXTURE_INDEX_FILE}",
    f"{FIXTURE_DIR_NAME}/{FIXTURE_APP_JS_FILE}",
    f"{FIXTURE_DIR_NAME}/{FIXTURE_STYLE_CSS_FILE}",
}
PLAN_ARTIFACT_INDEX_RELATIVE_PATHS = {
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    f"{FIXTURE_DIR_NAME}/{FIXTURE_INDEX_FILE}",
    f"{FIXTURE_DIR_NAME}/{FIXTURE_APP_JS_FILE}",
    f"{FIXTURE_DIR_NAME}/{FIXTURE_STYLE_CSS_FILE}",
}

PLAN_DISABLED_FALSE_FIELDS = (
    "live_website_automation_allowed",
    "account_workflow_allowed",
    "scraping_allowed",
    "bypass_allowed",
    "captcha_workflow_allowed",
    "credential_input_allowed",
    "external_network_allowed",
    "package_install_allowed",
    "browser_download_allowed",
    "npx_allowed",
    "npm_allowed",
    "adapter_generation_allowed",
    "adapter_registration_allowed",
    "auto_adoption_allowed",
    "production_promotion_allowed",
    "candidate_repo_access_allowed",
    "candidate_code_execution_allowed",
    "candidate_code_import_allowed",
    "secret_access_allowed",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("external path should not be called")


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class PlaywrightLocalFixtureSandboxSmokeTests(unittest.TestCase):
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
                },
                {
                    "candidate_id": "github-candidate-ultrafunkamsterdam-nodriver-v1",
                    "repo_full_name": "ultrafunkamsterdam/nodriver",
                    "intended_use": "browser_automation",
                    "selection_rank": 2,
                    "decision": "hold_high_risk_reference_only",
                    "next_allowed_action": "require_policy_legal_safety_review_before_any_sandbox",
                    "selected_for_first_sandbox_smoke": False,
                    "license_review_required": True,
                    "security_review_required": True,
                    "sandbox_review_required": True,
                    "adapter_generation_allowed": False,
                },
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
            "capability_domains": [
                "ai_agent_orchestration",
                "browser_automation",
                "observability",
            ],
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

    def write_matrix(self, path, payload):
        write_json_atomically(path, payload)
        return path

    def write_manifest(self, path, payload):
        write_json_atomically(path, payload)
        return path

    def build_plan(self, matrix_path, manifest_path, output_dir):
        return build_playwright_local_fixture_sandbox_smoke_plan(
            matrix_path,
            manifest_path,
            output_dir,
            "smoke-001",
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="local fixture only",
        )

    def run_smoke(self, matrix_path, manifest_path, output_dir, **kwargs):
        return run_playwright_local_fixture_sandbox_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            kwargs.pop("smoke_id", "smoke-001"),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop("operator_notes", "local fixture only"),
            **kwargs,
        )

    def assert_no_artifacts(self, output_dir):
        if not output_dir.exists():
            return
        for name in PLAN_OUTPUTS | EXECUTION_OUTPUTS:
            self.assertFalse((output_dir / name).exists(), name)
            self.assertFalse((output_dir / name).is_symlink(), name)
        self.assertFalse((output_dir / FIXTURE_DIR_NAME).exists())
        self.assertFalse((output_dir / FIXTURE_DIR_NAME).is_symlink())

    def assert_false_boundaries(self, payload):
        for field_name in PLAYWRIGHT_BOUNDARY_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

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
        non_local_count = 1 if mode == "non_local" else 0
        success_value = mode in {"success", "non_local"}
        exit_code = 7 if mode == "nonzero" else 0
        if mode == "malformed":
            body = """\
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--fixture-url", required=True)
parser.add_argument("--output-json", required=True)
parser.add_argument("--screenshot-path", required=True)
args = parser.parse_args()
open(args.output_json, "w", encoding="utf-8").write("{bad json")
"""
        else:
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
    "marker_found": {str(mode != "nonzero").capitalize()},
    "click_completed": {str(mode != "nonzero").capitalize()},
    "status_text": {"'clicked'" if mode != "nonzero" else "''"},
    "non_local_request_count": {non_local_count},
    "non_local_requests": {["https://example.invalid"] if mode == "non_local" else []!r},
    "screenshot_path": args.screenshot_path,
    "success": {str(success_value and mode != "nonzero").capitalize()},
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

    def test_plan_only_creates_artifacts_and_fixture_without_subprocess(self):
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
        self.assertEqual(
            result.payload["smoke_status"],
            "playwright_local_fixture_sandbox_smoke_plan_ready",
        )
        for name in PLAN_OUTPUTS:
            self.assertTrue((output_dir / name).is_file(), name)
        for name in FIXTURE_OUTPUTS:
            self.assertTrue((output_dir / name).is_file(), name)
        for name in EXECUTION_OUTPUTS:
            self.assertFalse((output_dir / name).exists(), name)

    def test_plan_validates_419_selection_matrix_and_manifest(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_dir = Path(temp_dir.name) / "output"
        output_dir.mkdir()

        result = self.build_plan(SELECTION_MATRIX, PLAYWRIGHT_MANIFEST, output_dir)
        plan = read_json(result.plan_path)

        self.assertTrue(result.complete)
        self.assertEqual(plan["candidate_id"], "github-candidate-microsoft-playwright-v1")
        self.assertEqual(plan["repo_full_name"], "microsoft/playwright")
        self.assertEqual(plan["intended_use"], "browser_automation")
        self.assertTrue(plan["license_review_required"])
        self.assertTrue(plan["sandbox_review_required"])
        self.assertFalse(plan["adapter_generation_allowed"])

    def test_plan_blocks_if_selected_candidate_is_not_playwright(self):
        root, _matrix_path, manifest_path, output_dir = self.workspace()
        matrix = self.valid_matrix()
        matrix["candidates"][0]["selected_for_first_sandbox_smoke"] = False
        matrix["candidates"][1]["selected_for_first_sandbox_smoke"] = True
        bad_matrix = self.write_matrix(root / "bad-matrix.json", matrix)

        result = self.build_plan(bad_matrix, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_plan_blocks_if_more_than_one_candidate_is_selected(self):
        root, _matrix_path, manifest_path, output_dir = self.workspace()
        matrix = self.valid_matrix()
        matrix["candidates"][1]["selected_for_first_sandbox_smoke"] = True
        bad_matrix = self.write_matrix(root / "bad-matrix.json", matrix)

        result = self.build_plan(bad_matrix, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_plan_blocks_if_manifest_is_not_microsoft_playwright(self):
        root, matrix_path, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(
            root / "bad-manifest.json",
            self.valid_manifest(repo_full_name="example/not-playwright"),
        )

        result = self.build_plan(matrix_path, bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_plan_blocks_malformed_missing_symlink_selection_matrix_without_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        cases = {
            "missing": root / "missing.json",
            "malformed": root / "malformed.json",
            "symlink": root / "matrix-link.json",
        }
        cases["malformed"].write_text("{bad json", encoding="utf-8")
        cases["symlink"].symlink_to(matrix_path)

        for name, candidate in cases.items():
            with self.subTest(name=name):
                output_dir = root / f"out-{name}"
                output_dir.mkdir()
                result = self.build_plan(candidate, manifest_path, output_dir)
                self.assertFalse(result.complete)
                self.assert_no_artifacts(output_dir)

    def test_plan_blocks_malformed_missing_symlink_candidate_manifest_without_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        cases = {
            "missing": root / "missing-manifest.json",
            "malformed": root / "malformed-manifest.json",
            "symlink": root / "manifest-link.json",
        }
        cases["malformed"].write_text("{bad json", encoding="utf-8")
        cases["symlink"].symlink_to(manifest_path)

        for name, candidate in cases.items():
            with self.subTest(name=name):
                output_dir = root / f"out-{name}"
                output_dir.mkdir()
                result = self.build_plan(matrix_path, candidate, output_dir)
                self.assertFalse(result.complete)
                self.assert_no_artifacts(output_dir)

    def test_output_dir_missing_blocks_with_no_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        missing_output = root / "missing-output"

        result = self.build_plan(matrix_path, manifest_path, missing_output)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_output)

    def test_existing_output_file_blocks_with_no_overwrite(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()
        existing = output_dir / PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE
        existing.write_text("do not overwrite\n", encoding="utf-8")

        result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertEqual(existing.read_text(encoding="utf-8"), "do not overwrite\n")

    def test_output_symlink_collision_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        target = root / "target.json"
        target.write_text("{}\n", encoding="utf-8")
        (output_dir / PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE).symlink_to(
            target
        )

        result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertFalse((output_dir / FIXTURE_DIR_NAME).exists())

    def test_fixture_directory_preexists_blocks_with_no_overwrite(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()
        fixture_dir = output_dir / FIXTURE_DIR_NAME
        fixture_dir.mkdir()
        sentinel = fixture_dir / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")

        result = self.build_plan(matrix_path, manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        for name in PLAN_OUTPUTS:
            self.assertFalse((output_dir / name).exists(), name)

    def test_fixture_html_contains_required_marker_button_and_status(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        html = result.fixture_index_path.read_text(encoding="utf-8")

        self.assertIn(FIXTURE_MARKER_TEXT, html)
        self.assertIn('id="smoke-button"', html)
        self.assertIn('id="smoke-status"', html)

    def test_fixture_files_contain_no_http_or_https_references(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                result.fixture_index_path,
                result.fixture_app_js_path,
                result.fixture_style_css_path,
            )
        )

        self.assertNotIn("http://", combined)
        self.assertNotIn("https://", combined)

    def test_fixture_js_contains_no_network_calls(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        app_js = result.fixture_app_js_path.read_text(encoding="utf-8")

        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource"):
            self.assertNotIn(forbidden, app_js)

    def test_generated_fixture_url_is_file_only(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        plan = read_json(result.plan_path)

        self.assertEqual(plan["fixture_url_scheme"], "file")
        self.assertTrue(plan["fixture_url"].startswith("file://"))
        self.assertNotIn("http://", plan["fixture_url"])
        self.assertNotIn("https://", plan["fixture_url"])

    def test_plan_output_has_disabled_boundary_fields(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        plan = read_json(result.plan_path)

        self.assert_false_boundaries(plan)
        for field_name in PLAN_DISABLED_FALSE_FIELDS:
            self.assertIn(field_name, plan)
            self.assertFalse(plan[field_name], field_name)
        self.assertFalse(plan["fixture_contains_external_url"])
        self.assertFalse(plan["fixture_contains_form"])
        self.assertFalse(plan["fixture_contains_secret"])
        self.assertFalse(plan["fixture_contains_network_call"])

    def test_execution_without_explicit_flag_does_not_call_subprocess(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py")

        with patch("subprocess.run", side_effect=fail_if_called):
            result = self.run_smoke(
                matrix_path,
                manifest_path,
                output_dir,
                node_command=fake_node,
                runner_script=fake_runner,
            )

        self.assertTrue(result.complete)
        self.assertFalse(result.executed)
        self.assertFalse((output_dir / PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE).exists())

    def test_execution_requires_node_command_and_runner_script(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(root / "fake-runner.py")

        missing_node_output = root / "missing-node-output"
        missing_node_output.mkdir()
        missing_runner_output = root / "missing-runner-output"
        missing_runner_output.mkdir()

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            missing_node_output,
            execute_local_fixture_smoke=True,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_node_output)

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            missing_runner_output,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
        )
        self.assertFalse(result.complete)
        self.assert_no_artifacts(missing_runner_output)

    def test_node_command_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        node_link = root / "node-link"
        node_link.symlink_to(fake_node)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py")

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=node_link,
            runner_script=fake_runner,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_runner_script_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(root / "fake-runner.py")
        runner_link = output_dir / "runner-link.py"
        runner_link.symlink_to(fake_runner)

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=runner_link,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_runner_script_outside_repo_and_output_dir_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(root / "outside-runner.py")

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_explicit_execution_uses_fixed_subprocess_args(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py")

        with patch("subprocess.run", return_value=FakeCompleted()) as run_mock:
            result = self.run_smoke(
                matrix_path,
                manifest_path,
                output_dir,
                execute_local_fixture_smoke=True,
                node_command=fake_node,
                runner_script=fake_runner,
            )

        self.assertFalse(result.complete)
        call = run_mock.call_args
        args = call.args[0]
        kwargs = call.kwargs
        self.assertIsInstance(args, list)
        self.assertEqual(args[0], fake_node.as_posix())
        self.assertEqual(args[1], fake_runner.as_posix())
        self.assertIn("--fixture-url", args)
        self.assertIn("--output-json", args)
        self.assertIn("--screenshot-path", args)
        self.assertFalse(kwargs["shell"])
        self.assertLessEqual(kwargs["timeout"], 30)
        self.assertNotIn("npx", args)
        self.assertNotIn("npm", args)

    def test_fake_runner_success_produces_completed_result(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py")

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertTrue(result_payload["marker_found"])
        self.assertTrue(result_payload["click_completed"])
        self.assertEqual(result_payload["status_text"], "clicked")
        self.assertEqual(result_payload["non_local_request_count"], 0)
        self.assertTrue(result_payload["success"])
        self.assertEqual(
            result_payload["smoke_status"],
            "playwright_local_fixture_sandbox_smoke_completed",
        )

    def test_fake_runner_nonzero_exit_produces_failed_result(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py", mode="nonzero")

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertEqual(result_payload["returncode"], 7)
        self.assertFalse(result_payload["success"])
        self.assertEqual(
            result_payload["smoke_status"],
            "playwright_local_fixture_sandbox_smoke_failed",
        )

    def test_fake_runner_malformed_output_produces_failed_result(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py", mode="malformed")

        result = self.run_smoke(
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
        self.assertIn("malformed", result_payload["runner_output_parse_error"])

    def test_fake_runner_non_local_request_count_produces_failed_result(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py", mode="non_local")

        result = self.run_smoke(
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
        self.assertEqual(result_payload["non_local_request_count"], 1)
        self.assertIn("non-local", result_payload["runner_output_validation_error"])

    def test_result_keeps_boundary_performed_fields_false(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py")

        result = self.run_smoke(
            matrix_path,
            manifest_path,
            output_dir,
            execute_local_fixture_smoke=True,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        result_payload = read_json(result.result_path)

        self.assert_false_boundaries(result_payload)
        self.assertFalse(result_payload["production_promotion_performed"])
        self.assertFalse(result_payload["candidate_code_import_performed"])

    def test_artifact_index_includes_only_generated_smoke_and_fixture_artifacts(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        result = self.build_plan(matrix_path, manifest_path, output_dir)
        artifact_index = read_json(result.artifact_index_path)
        manifest = read_json(result.artifact_index_manifest_path)
        relative_paths = {entry["relative_path"] for entry in artifact_index["entries"]}

        self.assertEqual(relative_paths, PLAN_ARTIFACT_INDEX_RELATIVE_PATHS)
        self.assertEqual(
            set(manifest["indexed_relative_paths"]),
            PLAN_ARTIFACT_INDEX_RELATIVE_PATHS,
        )
        for entry in artifact_index["entries"]:
            self.assertFalse(entry["candidate_repo_file"])
            self.assertFalse(entry["external_candidate_artifact"])

    def test_task_graph_node_writes_artifact_outputs(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        smoke_output = root / "smoke-output"
        smoke_output.mkdir()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.playwright_graph(matrix_path, manifest_path, smoke_output),
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}

        self.assertTrue(result.success)
        self.assertIn("playwright_local_fixture_sandbox_smoke_plan", roles)
        self.assertIn("playwright_local_fixture_index_html", roles)
        self.assertIn("artifact_index", roles)

    def test_task_graph_node_preserves_false_boundary_fields(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        smoke_output = root / "smoke-output"
        smoke_output.mkdir()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.playwright_graph(matrix_path, manifest_path, smoke_output),
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        node = execution_manifest["nodes"][0]

        self.assertEqual(node["adapter_id"], "playwright_local_fixture_sandbox_smoke")
        for field_name in PLAYWRIGHT_BOUNDARY_FALSE_FIELDS:
            self.assertIn(field_name, node)
            self.assertFalse(node[field_name], field_name)

    def playwright_graph(self, matrix_path, manifest_path, output_dir):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "playwright-smoke-graph",
            "authority": "non_authority",
            "required_human_approval": True,
            "execution_mode": "fixture_execution",
            "nodes": [
                {
                    "node_id": "playwright-smoke",
                    "adapter_id": "playwright_local_fixture_sandbox_smoke",
                    "capability": "launch_playwright_local_fixture_sandbox_smoke",
                    "depends_on": [],
                    "execution_mode": "fixture",
                    "approval_checkpoint_required": True,
                    "approval_checkpoint_id": "playwright-smoke:human_review",
                    "inputs": {
                        "selection_matrix": matrix_path.as_posix(),
                        "playwright_candidate_manifest": manifest_path.as_posix(),
                        "output_dir": output_dir.as_posix(),
                        "smoke_id": "graph-smoke-001",
                        "project_id": "project-001",
                    },
                }
            ],
        }

    def test_cli_plan_only_smoke_path_works(self):
        _root, matrix_path, manifest_path, output_dir = self.workspace()

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-playwright-local-fixture-sandbox-smoke",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--smoke-id",
                    "cli-smoke-001",
                ]
            )
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["executed"])

    def test_cli_explicit_fake_runner_smoke_path_works(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(output_dir / "fake-runner.py")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-playwright-local-fixture-sandbox-smoke",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--smoke-id",
                    "cli-smoke-001",
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
        self.assertTrue(payload["marker_found"])
        self.assertEqual(payload["status_text"], "clicked")

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
        self.assertNotIn("git " + "clone", source)
        self.assertNotIn("pip " + "install", source)
        self.assertNotIn("npm " + "install", source)


if __name__ == "__main__":
    unittest.main()
