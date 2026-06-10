import contextlib
import io
import json
import stat
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.capabilities import local_only_playwright_fixture_scenario_suite as suite_module
from kernel.capabilities.local_only_playwright_fixture_scenario_suite import (
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIO_RESULT_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE,
    build_local_only_playwright_fixture_scenario_suite_plan,
    run_local_only_playwright_fixture_scenario_suite,
)
from kernel.capabilities.operator_provided_playwright_execution_receipt import (
    ADAPTER_DRAFT_RUN_DIR_NAME,
    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_local_only_playwright_fixture_scenario_suite_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

SUITE_PLAN_OUTPUTS = {
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE,
}
SUITE_ALL_OUTPUTS = SUITE_PLAN_OUTPUTS | {
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE,
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("external path should not be called")


class LocalOnlyPlaywrightFixtureScenarioSuiteTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "suite-output"
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

    def valid_manifest(self):
        return {
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

    def make_fake_node(self, root, *, name="fake-node"):
        fake_node = root / name
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def build_plan(self, matrix_path, manifest_path, output_dir, **kwargs):
        return build_local_only_playwright_fixture_scenario_suite_plan(
            matrix_path,
            manifest_path,
            output_dir,
            kwargs.pop("suite_id", "suite-001"),
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

    def run_suite(self, matrix_path, manifest_path, output_dir, **kwargs):
        return run_local_only_playwright_fixture_scenario_suite(
            matrix_path,
            manifest_path,
            output_dir,
            kwargs.pop("suite_id", "suite-001"),
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

    def create_suite(self, *, mode="success", scenario_set="core"):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(
            self.repo_temp_dir() / "fake-runner.py",
            mode=mode,
        )
        result = self.run_suite(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
            scenario_set=scenario_set,
        )
        return root, matrix_path, manifest_path, output_dir, result

    def no_external_plan_paths(self):
        stack = contextlib.ExitStack()
        stack.enter_context(
            patch(
                "kernel.capabilities.local_only_playwright_fixture_scenario_suite.run_operator_provided_playwright_execution_receipt",
                side_effect=fail_if_called,
            )
        )
        stack.enter_context(patch("subprocess.run", side_effect=fail_if_called))
        stack.enter_context(patch("os.system", side_effect=fail_if_called))
        stack.enter_context(patch("socket.create_connection", side_effect=fail_if_called))
        return stack

    def assert_no_suite_artifacts(self, output_dir):
        if not Path(output_dir).exists():
            return
        for name in SUITE_ALL_OUTPUTS:
            self.assertFalse((Path(output_dir) / name).exists(), name)
            self.assertFalse((Path(output_dir) / name).is_symlink(), name)
        self.assertFalse(
            (Path(output_dir) / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME).exists()
        )

    def assert_false_fields(self, payload):
        for field_name in LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def scenario_dir(self, output_dir, scenario_id="static_click_marker"):
        return (
            Path(output_dir)
            / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME
            / scenario_id
        )

    def receipt_dir(self, output_dir, scenario_id="static_click_marker"):
        return self.scenario_dir(output_dir, scenario_id) / "operator_receipt"

    def receipt_path(self, output_dir, file_name, scenario_id="static_click_marker"):
        return self.receipt_dir(output_dir, scenario_id) / file_name

    def adapter_path(self, output_dir, file_name, scenario_id="static_click_marker"):
        return self.receipt_dir(output_dir, scenario_id) / ADAPTER_DRAFT_RUN_DIR_NAME / file_name

    def smoke_path(self, output_dir, file_name, scenario_id="static_click_marker"):
        return (
            self.receipt_dir(output_dir, scenario_id)
            / ADAPTER_DRAFT_RUN_DIR_NAME
            / "embedded_smoke"
            / file_name
        )

    def scenario_result_path(self, output_dir, scenario_id="static_click_marker"):
        return self.scenario_dir(output_dir, scenario_id) / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIO_RESULT_FILE

    def mutate_json(self, path, mutator):
        payload = read_json(path)
        mutator(payload)
        write_json(path, payload)

    def mutated_scenario_result(self, mutator, scenario_id="static_click_marker"):
        _root, _matrix, _manifest, output_dir, _suite = self.create_suite()
        mutator(output_dir)
        scenario_dir = self.scenario_dir(output_dir, scenario_id)
        return suite_module._scenario_result_payload(
            {
                "scenario_id": scenario_id,
                "scenario_type": scenario_id,
                "requires_marker": True,
                "requires_click": True,
                "requires_status_text": True,
            },
            scenario_dir=scenario_dir,
            receipt_dir=self.receipt_dir(output_dir, scenario_id),
        )

    def assert_rejects_after_mutation(self, mutator, expected_reason):
        scenario = self.mutated_scenario_result(mutator)
        self.assertFalse(scenario["success"])
        self.assertIn(expected_reason, scenario["failure_reasons"])
        return scenario

    def test_A_plan_only_creates_suite_artifacts_without_running_422(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        with self.no_external_plan_paths():
            result = self.build_plan(
                matrix_path,
                manifest_path,
                output_dir,
                node_command=fake_node,
                runner_script=fake_runner,
            )
        self.assertTrue(result.complete)
        self.assertFalse(result.executed)
        for name in SUITE_PLAN_OUTPUTS:
            self.assertTrue((output_dir / name).is_file(), name)
        self.assertFalse((output_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE).exists())
        self.assertFalse((output_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME).exists())

    def test_B_core_run_creates_expected_scenario_dirs_and_results(self):
        _root, _matrix, _manifest, output_dir, result = self.create_suite()
        self.assertTrue(result.complete)
        for scenario_id in (
            "static_click_marker",
            "repeated_local_fixture_execution_a",
            "repeated_local_fixture_execution_b",
        ):
            self.assertTrue(self.receipt_dir(output_dir, scenario_id).is_dir())
            self.assertTrue(self.scenario_result_path(output_dir, scenario_id).is_file())

    def test_C_core_run_passes_with_deterministic_fake_success_runner(self):
        _root, _matrix, _manifest, output_dir, result = self.create_suite()
        suite_result = read_json(result.result_path)
        self.assertTrue(suite_result["suite_success"])
        self.assertEqual(suite_result["scenario_count_passed"], 3)
        repeated = [
            item
            for item in suite_result["scenario_results"]
            if item["scenario_type"] == "repeated_local_fixture_execution"
        ]
        self.assertTrue(all(item["deterministic_equivalence_confirmed"] for item in repeated))

    def test_D_fake_failing_runner_causes_scenario_failure_and_suite_failure(self):
        _root, _matrix, _manifest, _output_dir, result = self.create_suite(mode="failure")
        suite_result = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertFalse(suite_result["suite_success"])
        self.assertGreater(suite_result["scenario_count_failed"], 0)
        self.assertTrue(any(not item["success"] for item in suite_result["scenario_results"]))

    def test_E_extended_run_includes_output_integrity_and_boundary_false(self):
        _root, _matrix, _manifest, output_dir, result = self.create_suite(scenario_set="extended")
        self.assertTrue(result.complete)
        self.assertTrue(self.scenario_result_path(output_dir, "output_integrity_scenario").is_file())
        self.assertTrue(self.scenario_result_path(output_dir, "boundary_false_scenario").is_file())

    def test_F_wrong_operator_attestation_fails_closed_with_no_artifacts(self):
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
        self.assert_no_suite_artifacts(output_dir)

    def test_G_sensitive_wrong_operator_attestation_does_not_leak_raw_text(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        bad_attestation = "SECRET_TOKEN_PASSWORD_API_KEY_COOKIE_BAD"
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation=bad_attestation,
        )
        serialized = json.dumps(result.payload, sort_keys=True)
        self.assertNotIn(bad_attestation, serialized)
        self.assertNotIn("SECRET_TOKEN_PASSWORD", serialized)
        self.assert_no_suite_artifacts(output_dir)

    def test_H_output_dir_missing_fails_closed_with_no_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        missing = root / "missing-output"
        result = self.build_plan(
            matrix_path,
            manifest_path,
            missing,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(missing)

    def test_I_output_dir_symlink_fails_closed_with_no_artifacts(self):
        root, matrix_path, manifest_path, _output_dir = self.workspace()
        real_output = root / "real-output"
        real_output.mkdir()
        link = root / "output-link"
        link.symlink_to(real_output)
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            matrix_path,
            manifest_path,
            link,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(real_output)

    def test_J_existing_suite_output_file_blocks_with_no_overwrite(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        existing = output_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE
        existing.write_text("keep\n", encoding="utf-8")
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep\n")

    def test_K_existing_scenarios_directory_blocks_with_no_overwrite(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        scenarios = output_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME
        scenarios.mkdir()
        sentinel = scenarios / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_L_selection_matrix_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        link = root / "matrix-link.json"
        link.symlink_to(matrix_path)
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            link,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(output_dir)

    def test_M_playwright_candidate_manifest_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        link = root / "manifest-link.json"
        link.symlink_to(manifest_path)
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            matrix_path,
            link,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(output_dir)

    def test_N_node_command_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        link = root / "node-link"
        link.symlink_to(fake_node)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=link,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(output_dir)

    def test_O_runner_script_symlink_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        link = root / "runner-link.py"
        link.symlink_to(fake_runner)
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=link,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(output_dir)

    def test_P_node_command_basename_npm_npx_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root, name="npm")
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=fake_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(output_dir)

    def test_Q_runner_script_outside_repo_or_output_dir_blocks(self):
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
        self.assert_no_suite_artifacts(output_dir)

    def test_R_runner_script_from_candidate_repo_evidence_path_blocks(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        candidate_runner = self.make_fake_runner(
            self.repo_temp_dir() / "capability_candidates" / "fake-runner.py"
        )
        result = self.build_plan(
            matrix_path,
            manifest_path,
            output_dir,
            node_command=fake_node,
            runner_script=candidate_runner,
        )
        self.assertFalse(result.complete)
        self.assert_no_suite_artifacts(output_dir)

    def test_S_scenario_result_records_embedded_fixture_url_and_file_scheme(self):
        _root, _matrix, _manifest, output_dir, _result = self.create_suite()
        scenario = read_json(self.scenario_result_path(output_dir))
        self.assertTrue(str(scenario["embedded_fixture_url"]).startswith("file:"))
        self.assertEqual(scenario["embedded_fixture_url_scheme"], "file")

    def test_T_rejects_non_local_request_count_above_zero_when_mutated(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.smoke_path(output_dir, "playwright_local_fixture_sandbox_smoke_result.json"),
                lambda payload: payload.update(non_local_request_count=1),
            ),
            "embedded_non_local_request_count_not_zero",
        )

    def test_U_rejects_live_website_boundary_true_when_mutated(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(live_website_automation_performed=True),
            ),
            "boundary_false_field_true",
        )

    def test_V_rejects_user_supplied_url_boundary_true_when_mutated(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(user_supplied_url_used=True),
            ),
            "boundary_false_field_true",
        )

    def test_W_rejects_account_login_registration_boundary_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(login_workflow_performed=True),
            ),
            "boundary_false_field_true",
        )

    def test_X_rejects_scraping_bypass_captcha_boundary_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(scraping_performed=True),
            ),
            "boundary_false_field_true",
        )

    def test_Y_rejects_secret_cookie_boundary_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(secret_access_performed=True),
            ),
            "boundary_false_field_true",
        )

    def test_Z_rejects_external_network_install_npm_npx_boundary_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(npm_performed=True),
            ),
            "boundary_false_field_true",
        )

    def test_AA_rejects_candidate_repo_access_import_execution_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(candidate_code_execution_performed=True),
            ),
            "boundary_false_field_true",
        )

    def test_AB_rejects_production_promotion_autonomy_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "operator_provided_playwright_execution_receipt_plan.json"),
                lambda payload: payload.update(
                    production_promotion_granted=True,
                    autonomous_execution_performed=True,
                ),
            ),
            "boundary_false_field_true",
        )

    def test_AC_rejects_artifact_index_path_outside_scenario_dir(self):
        def mutate(output_dir):
            outside = Path(output_dir).parent / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            self.mutate_json(
                self.receipt_path(output_dir, "artifact_index.json"),
                lambda payload: payload["entries"][0].update(path=outside.as_posix()),
            )

        self.assert_rejects_after_mutation(mutate, "artifact_index_path_outside_scenario_dir")

    def test_AD_rejects_indexed_symlink_path(self):
        def mutate(output_dir):
            target = self.receipt_path(
                output_dir,
                "operator_provided_playwright_execution_receipt_summary.md",
            )
            link = self.scenario_dir(output_dir) / "summary-link.md"
            link.symlink_to(target)
            self.mutate_json(
                self.receipt_path(output_dir, "artifact_index.json"),
                lambda payload: payload["entries"][0].update(path=link.as_posix()),
            )

        self.assert_rejects_after_mutation(mutate, "artifact_index_symlink_path")

    def test_AE_rejects_candidate_repo_files_indexed_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "artifact_index.json"),
                lambda payload: payload.update(candidate_repo_files_indexed=True),
            ),
            "candidate_repo_files_indexed",
        )

    def test_AF_rejects_external_candidate_artifacts_indexed_true(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.mutate_json(
                self.receipt_path(output_dir, "artifact_index.json"),
                lambda payload: payload.update(external_candidate_artifacts_indexed=True),
            ),
            "external_candidate_artifacts_indexed",
        )

    def test_AG_rejects_artifact_hash_mismatch(self):
        self.assert_rejects_after_mutation(
            lambda output_dir: self.receipt_path(
                output_dir,
                "operator_provided_playwright_execution_receipt_summary.md",
            ).write_text("changed\n", encoding="utf-8"),
            "artifact_hash_mismatch",
        )

    def test_AH_suite_result_includes_all_scenario_results_and_counts(self):
        _root, _matrix, _manifest, _output_dir, result = self.create_suite()
        payload = read_json(result.result_path)
        self.assertEqual(payload["scenario_count_planned"], 3)
        self.assertEqual(payload["scenario_count_executed"], 3)
        self.assertEqual(len(payload["scenario_results"]), 3)
        self.assertEqual(payload["scenario_count_passed"] + payload["scenario_count_failed"], 3)

    def test_AI_suite_result_keeps_production_live_general_browser_false(self):
        _root, _matrix, _manifest, _output_dir, result = self.create_suite()
        payload = read_json(result.result_path)
        self.assertFalse(payload["production_admission_granted"])
        self.assertFalse(payload["live_website_admission_granted"])
        self.assertFalse(payload["general_browser_automation_admission_granted"])

    def test_AJ_suite_artifacts_and_launcher_payload_preserve_false_fields(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        launcher_result = run_local_only_playwright_fixture_scenario_suite_launcher(
            matrix_path,
            manifest_path,
            output_dir,
            "suite-001",
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
        )
        for path in (
            launcher_result.payload["local_only_playwright_fixture_scenario_suite_plan_path"],
            launcher_result.payload["local_only_playwright_fixture_scenario_suite_manifest_path"],
            launcher_result.payload["local_only_playwright_fixture_scenario_suite_result_path"],
            launcher_result.payload["artifact_index_path"],
            launcher_result.payload["artifact_index_manifest_path"],
        ):
            self.assert_false_fields(read_json(path))
        self.assert_false_fields(launcher_result.to_cli_payload())

    def test_AK_launcher_payload_works_for_core_scenario_set(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        result = run_local_only_playwright_fixture_scenario_suite_launcher(
            matrix_path,
            manifest_path,
            output_dir,
            "suite-001",
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            scenario_set="core",
        )
        payload = result.to_cli_payload()
        self.assertTrue(payload["complete"])
        self.assertEqual(payload["scenario_set"], "core")

    def test_AL_cli_plan_only_path_works(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-local-only-playwright-fixture-scenario-suite",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--suite-id",
                    "suite-cli-001",
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

    def test_AM_cli_core_run_path_works(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-local-only-playwright-fixture-scenario-suite",
                    "--selection-matrix",
                    matrix_path.as_posix(),
                    "--playwright-candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--suite-id",
                    "suite-cli-001",
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
        self.assertEqual(payload["scenario_count_passed"], 3)

    def test_AN_task_graph_node_writes_suite_artifact_outputs(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.suite_graph(matrix_path, manifest_path, output_dir, fake_node, fake_runner),
        )
        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}
        self.assertTrue(result.success)
        self.assertIn("local_only_playwright_fixture_scenario_suite_plan", roles)
        self.assertIn("local_only_playwright_fixture_scenario_suite_result", roles)

    def test_AO_task_graph_node_preserves_disabled_and_performed_false_fields(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py")
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.suite_graph(matrix_path, manifest_path, output_dir, fake_node, fake_runner),
        )
        result = run_local_task_graph_fixture(graph_path, graph_output)
        node = read_json(result.execution_manifest_path)["nodes"][0]
        self.assert_false_fields(node)

    def test_AP_tests_patch_subprocess_os_socket_and_do_not_use_network_clients(self):
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertIn('patch("subprocess.run"', source)
        self.assertIn('patch("os.system"', source)
        self.assertIn('patch("socket.create_connection"', source)
        self.assertNotIn("import requ" + "ests", source)
        self.assertNotIn("from requ" + "ests", source)
        self.assertNotIn("import htt" + "px", source)
        self.assertNotIn("from htt" + "px", source)

    def test_AQ_module_source_contains_no_disallowed_execution_or_cli_paths(self):
        source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "local_only_playwright_fixture_scenario_suite.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "subprocess.run",
            "os.system",
            "os.popen",
            "import socket",
            "create_connection",
            "git clone",
            "fetch(",
            "--target-url",
            "--url",
            "--website",
            "--account",
            "--credential",
            "--cookie",
            "--scrape",
            "--bypass",
            "--captcha",
        ):
            self.assertNotIn(forbidden, source)

    def test_AR_module_only_delegates_execution_to_operator_receipt(self):
        source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "local_only_playwright_fixture_scenario_suite.py"
        ).read_text(encoding="utf-8")
        self.assertIn("run_operator_provided_playwright_execution_receipt", source)
        self.assertNotIn("run_bounded_playwright_worker_adapter_draft", source)
        self.assertNotIn("run_playwright_local_fixture_sandbox_smoke", source)

    def test_AS_suite_never_claims_production_or_live_website_readiness(self):
        _root, _matrix, _manifest, _output_dir, result = self.create_suite()
        plan = read_json(result.plan_path)
        suite_result = read_json(result.result_path)
        self.assertEqual(
            plan["next_allowed_action"],
            "review_local_only_playwright_fixture_scenario_suite",
        )
        self.assertNotIn("production", plan["suite_decision"])
        self.assertFalse(suite_result["production_admission_granted"])
        self.assertFalse(suite_result["live_website_admission_granted"])
        self.assertFalse(suite_result["general_browser_automation_admission_granted"])

    def suite_graph(self, matrix_path, manifest_path, output_dir, fake_node, fake_runner):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "local-only-playwright-fixture-suite-graph",
            "authority": "non_authority",
            "required_human_approval": True,
            "execution_mode": "fixture_execution",
            "nodes": [
                {
                    "node_id": "scenario_suite",
                    "adapter_id": "local_only_playwright_fixture_scenario_suite",
                    "capability": "launch_local_only_playwright_fixture_scenario_suite",
                    "depends_on": [],
                    "execution_mode": "fixture",
                    "approval_checkpoint_required": True,
                    "approval_checkpoint_id": "scenario-suite:human_review",
                    "inputs": {
                        "selection_matrix": Path(matrix_path).as_posix(),
                        "playwright_candidate_manifest": Path(manifest_path).as_posix(),
                        "output_dir": Path(output_dir).as_posix(),
                        "suite_id": "graph-suite-001",
                        "node_command": Path(fake_node).as_posix(),
                        "runner_script": Path(fake_runner).as_posix(),
                        "operator_attestation": OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                        "project_id": "project-001",
                        "scenario_set": "core",
                    },
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
