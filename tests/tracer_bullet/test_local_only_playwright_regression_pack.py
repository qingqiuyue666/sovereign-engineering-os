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
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS,
    build_local_only_playwright_fixture_scenario_suite_plan,
    run_local_only_playwright_fixture_scenario_suite,
)
from kernel.capabilities.operator_provided_playwright_execution_receipt import (
    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_local_only_playwright_fixture_scenario_suite_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_SCENARIOS = (
    "static_click_marker",
    "repeated_local_fixture_execution_a",
    "repeated_local_fixture_execution_b",
)
EXTENDED_SCENARIOS = CORE_SCENARIOS + (
    "output_integrity_scenario",
    "boundary_false_scenario",
)
REGRESSION_SCENARIOS = EXTENDED_SCENARIOS + (
    "delayed_render_marker",
    "dom_mutation_click_state",
    "local_form_like_interaction_no_account",
    "screenshot_required",
    "blocked_external_request_claim_rejection",
    "deterministic_runner_schema",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("direct lower Playwright path should not be called")


class LocalOnlyPlaywrightRegressionPackTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name).resolve()
        output_dir = root / "suite-output"
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

    def make_fake_node(self, root):
        fake_node = Path(root) / "fake-node"
        fake_node.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        fake_node.chmod(fake_node.stat().st_mode | stat.S_IXUSR)
        return fake_node

    def make_fake_runner(self, output_dir):
        fake_runner = Path(output_dir) / "fake-runner.py"
        fake_runner.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import sys
                sys.exit(0)
                """
            ),
            encoding="utf-8",
        )
        fake_runner.chmod(fake_runner.stat().st_mode | stat.S_IXUSR)
        return fake_runner

    def build_plan(self, scenario_set):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        return build_local_only_playwright_fixture_scenario_suite_plan(
            matrix_path,
            manifest_path,
            output_dir,
            "suite-001",
            node_command=self.make_fake_node(root),
            runner_script=self.make_fake_runner(output_dir),
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="local fixture only",
            scenario_set=scenario_set,
        )

    def assert_false_fields(self, payload):
        for field_name in LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def fake_receipt_for_scenario(
        self,
        scenario_id,
        *,
        runner_overrides=None,
        runner_remove=(),
        smoke_overrides=None,
        smoke_remove=(),
    ):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self._cleanup_temp(root))
        scenario_dir = root / "scenarios" / scenario_id
        receipt_dir = scenario_dir / "operator_receipt"
        self.write_fake_receipt_tree(
            receipt_dir,
            runner_overrides=runner_overrides,
            runner_remove=runner_remove,
            smoke_overrides=smoke_overrides,
            smoke_remove=smoke_remove,
        )
        return suite_module._scenario_result_payload(
            {
                "scenario_id": scenario_id,
                "scenario_type": scenario_id,
                "requires_marker": True,
                "requires_click": True,
                "requires_status_text": True,
            },
            scenario_dir=scenario_dir,
            receipt_dir=receipt_dir,
        )

    def _cleanup_temp(self, root):
        for path in sorted(Path(root).rglob("*"), reverse=True):
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        Path(root).rmdir()

    def write_fake_receipt_tree(
        self,
        receipt_dir,
        *,
        runner_overrides=None,
        runner_remove=(),
        smoke_overrides=None,
        smoke_remove=(),
    ):
        receipt_dir = Path(receipt_dir)
        adapter_dir = receipt_dir / "adapter_draft_run"
        embedded_dir = adapter_dir / "embedded_smoke"
        fixture_dir = embedded_dir / "fixture"
        fixture_dir.mkdir(parents=True)
        scenario_dir = receipt_dir.parent
        fixture_url = (fixture_dir / "index.html").as_uri()
        screenshot_path = embedded_dir / "screenshot.png"
        false_fields = {}
        false_fields.update(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS)
        false_fields.update(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS)

        (fixture_dir / "index.html").write_text("<p>marker</p>\n", encoding="utf-8")
        (fixture_dir / "app.js").write_text("window.clicked = true;\n", encoding="utf-8")
        (fixture_dir / "style.css").write_text("body { color: #111; }\n", encoding="utf-8")
        screenshot_path.write_bytes(b"fake-png")

        runner_output = {
            "runner_type": "playwright_local_fixture_smoke_runner_v1",
            "fixture_url": fixture_url,
            "marker_found": True,
            "click_completed": True,
            "status_text": "clicked",
            "non_local_request_count": 0,
            "non_local_requests": [],
            "screenshot_path": screenshot_path.as_posix(),
            "success": True,
            **false_fields,
        }
        runner_output.update(runner_overrides or {})
        for field_name in runner_remove:
            runner_output.pop(field_name, None)

        smoke_result = {
            "result_type": "playwright_local_fixture_bounded_sandbox_smoke_result_v1",
            "fixture_url": fixture_url,
            "fixture_url_scheme": "file",
            "marker_found": True,
            "click_completed": True,
            "status_text": "clicked",
            "non_local_request_count": 0,
            "non_local_requests": [],
            "screenshot_path": screenshot_path.as_posix(),
            "success": True,
            **false_fields,
        }
        smoke_result.update(smoke_overrides or {})
        for field_name in smoke_remove:
            smoke_result.pop(field_name, None)

        payloads = {
            receipt_dir / "operator_provided_playwright_execution_receipt_plan.json": {
                "fixture_url_scheme": "file",
                **false_fields,
            },
            receipt_dir / "operator_provided_playwright_execution_receipt_result.json": {
                "success": True,
                "embedded_fixture_url": fixture_url,
                "embedded_fixture_url_scheme": "file",
                "embedded_marker_found": True,
                "embedded_click_completed": True,
                "embedded_status_text": "clicked",
                "embedded_non_local_request_count": 0,
                **false_fields,
            },
            adapter_dir / "bounded_playwright_worker_adapter_draft_plan.json": {
                "embedded_fixture_url_scheme": "file",
                **false_fields,
            },
            adapter_dir / "bounded_playwright_worker_adapter_draft_result.json": {
                "success": True,
                "embedded_fixture_url": fixture_url,
                "embedded_fixture_url_scheme": "file",
                "embedded_marker_found": True,
                "embedded_click_completed": True,
                "embedded_status_text": "clicked",
                "embedded_non_local_request_count": 0,
                **false_fields,
            },
            embedded_dir / "playwright_local_fixture_sandbox_smoke_plan.json": {
                "fixture_url": fixture_url,
                "fixture_url_scheme": "file",
                **false_fields,
            },
            embedded_dir / "playwright_local_fixture_sandbox_smoke_result.json": smoke_result,
            embedded_dir / "playwright_local_fixture_sandbox_smoke_runner_output.json": runner_output,
        }
        for path, payload in payloads.items():
            write_json(path, payload)

        write_json(
            receipt_dir / "operator_provided_playwright_execution_receipt_manifest.json",
            {
                "plan_path": (receipt_dir / "operator_provided_playwright_execution_receipt_plan.json").as_posix(),
                "plan_sha256": sha256_file(receipt_dir / "operator_provided_playwright_execution_receipt_plan.json"),
                **false_fields,
            },
        )
        write_json(
            adapter_dir / "bounded_playwright_worker_adapter_draft_manifest.json",
            {
                "result_path": (adapter_dir / "bounded_playwright_worker_adapter_draft_result.json").as_posix(),
                "result_sha256": sha256_file(adapter_dir / "bounded_playwright_worker_adapter_draft_result.json"),
                **false_fields,
            },
        )
        write_json(
            embedded_dir / "playwright_local_fixture_sandbox_smoke_manifest.json",
            {
                "result_path": (embedded_dir / "playwright_local_fixture_sandbox_smoke_result.json").as_posix(),
                "result_sha256": sha256_file(embedded_dir / "playwright_local_fixture_sandbox_smoke_result.json"),
                "screenshot_path": screenshot_path.as_posix(),
                "screenshot_sha256": sha256_file(screenshot_path),
                **false_fields,
            },
        )
        for path in (
            receipt_dir / "operator_provided_playwright_execution_receipt_summary.md",
            receipt_dir / "operator_provided_playwright_execution_receipt_checklist.md",
            adapter_dir / "bounded_playwright_worker_adapter_draft_summary.md",
            adapter_dir / "bounded_playwright_worker_adapter_draft_checklist.md",
            embedded_dir / "playwright_local_fixture_sandbox_smoke_summary.md",
            embedded_dir / "playwright_local_fixture_sandbox_smoke_checklist.md",
        ):
            path.write_text("local fixture only\n", encoding="utf-8")

        self.write_artifact_index(
            receipt_dir / "artifact_index.json",
            scenario_dir,
            [
                receipt_dir / "operator_provided_playwright_execution_receipt_plan.json",
                receipt_dir / "operator_provided_playwright_execution_receipt_result.json",
                adapter_dir / "bounded_playwright_worker_adapter_draft_result.json",
                embedded_dir / "playwright_local_fixture_sandbox_smoke_result.json",
                embedded_dir / "playwright_local_fixture_sandbox_smoke_runner_output.json",
                screenshot_path,
            ],
        )
        self.write_artifact_index(
            adapter_dir / "artifact_index.json",
            scenario_dir,
            [
                adapter_dir / "bounded_playwright_worker_adapter_draft_plan.json",
                adapter_dir / "bounded_playwright_worker_adapter_draft_result.json",
                embedded_dir / "playwright_local_fixture_sandbox_smoke_result.json",
                screenshot_path,
            ],
        )
        self.write_artifact_index(
            embedded_dir / "artifact_index.json",
            scenario_dir,
            [
                embedded_dir / "playwright_local_fixture_sandbox_smoke_plan.json",
                embedded_dir / "playwright_local_fixture_sandbox_smoke_result.json",
                embedded_dir / "playwright_local_fixture_sandbox_smoke_runner_output.json",
                fixture_dir / "index.html",
                fixture_dir / "app.js",
                fixture_dir / "style.css",
                screenshot_path,
            ],
        )
        for index_path in (
            receipt_dir / "artifact_index_manifest.json",
            adapter_dir / "artifact_index_manifest.json",
            embedded_dir / "artifact_index_manifest.json",
        ):
            write_json(index_path, {"entries": [], **false_fields})

    def write_artifact_index(self, index_path, scenario_dir, paths):
        entries = []
        for path in paths:
            entries.append(
                {
                    "artifact_name": path.name,
                    "artifact_role": path.stem,
                    "path": path.as_posix(),
                    "relative_path": path.relative_to(scenario_dir).as_posix(),
                    "exists": path.exists() and path.is_file() and not path.is_symlink(),
                    "sha256": sha256_file(path),
                    "candidate_repo_file": False,
                    "external_candidate_artifact": False,
                }
            )
        write_json(
            index_path,
            {
                "entries": entries,
                "candidate_repo_files_indexed": False,
                "external_candidate_artifacts_indexed": False,
            },
        )

    def fake_422(self, *_args, **_kwargs):
        receipt_dir = Path(_args[2])
        receipt_id = str(_args[3])
        scenario_id = receipt_id.split("__", 1)[-1]
        evidence = {
            "delayed_marker_found": True,
            "dom_mutation_observed": True,
            "local_form_interaction_completed": True,
        }
        self.write_fake_receipt_tree(receipt_dir, runner_overrides=evidence)
        return None

    def test_A_regression_scenario_set_is_accepted_and_plans_11_scenarios(self):
        result = self.build_plan("regression")
        plan = read_json(result.plan_path)
        self.assertTrue(result.complete)
        self.assertEqual(plan["scenario_set"], "regression")
        self.assertEqual(plan["scenario_count_planned"], 11)
        self.assertEqual(
            [item["scenario_id"] for item in plan["planned_scenarios"]],
            list(REGRESSION_SCENARIOS),
        )

    def test_B_core_scenario_set_remains_3_scenarios(self):
        plan = read_json(self.build_plan("core").plan_path)
        self.assertEqual(plan["scenario_count_planned"], 3)

    def test_C_extended_scenario_set_remains_5_scenarios(self):
        plan = read_json(self.build_plan("extended").plan_path)
        self.assertEqual(plan["scenario_count_planned"], 5)

    def test_D_invalid_scenario_set_still_fails_closed(self):
        result = self.build_plan("production")
        self.assertFalse(result.complete)
        self.assertEqual(result.payload["failure_stage"], "preflight_scenario_set")

    def test_E_regression_run_delegates_only_through_422_receipt_path(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        calls = []

        def fake_receipt(*args, **kwargs):
            calls.append(args[3])
            return self.fake_422(*args, **kwargs)

        with patch(
            "kernel.capabilities.local_only_playwright_fixture_scenario_suite.run_operator_provided_playwright_execution_receipt",
            side_effect=fake_receipt,
        ):
            result = run_local_only_playwright_fixture_scenario_suite(
                matrix_path,
                manifest_path,
                output_dir,
                "suite-001",
                node_command=self.make_fake_node(root),
                runner_script=self.make_fake_runner(output_dir),
                operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                scenario_set="regression",
            )
        self.assertTrue(result.complete)
        self.assertEqual(len(calls), 11)
        self.assertTrue(all("__" + scenario in calls[index] for index, scenario in enumerate(REGRESSION_SCENARIOS)))

    def test_F_no_direct_420_or_421_execution_calls_are_introduced(self):
        source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "local_only_playwright_fixture_scenario_suite.py"
        ).read_text(encoding="utf-8")
        self.assertIn("run_operator_provided_playwright_execution_receipt", source)
        self.assertNotIn("run_bounded_playwright_worker_adapter_draft", source)
        self.assertNotIn("run_playwright_local_fixture_sandbox_smoke", source)

    def test_G_delayed_render_marker_fails_when_evidence_is_missing(self):
        result = self.fake_receipt_for_scenario("delayed_render_marker")
        self.assertFalse(result["success"])
        self.assertIn("delayed_render_marker_evidence_missing", result["failure_reasons"])

    def test_H_delayed_render_marker_passes_with_fake_receipt_evidence(self):
        result = self.fake_receipt_for_scenario(
            "delayed_render_marker",
            runner_overrides={"delayed_marker_found": True},
        )
        self.assertTrue(result["success"])

    def test_I_dom_mutation_click_state_fails_when_evidence_is_missing(self):
        result = self.fake_receipt_for_scenario("dom_mutation_click_state")
        self.assertFalse(result["success"])
        self.assertIn("dom_mutation_click_state_evidence_missing", result["failure_reasons"])

    def test_J_dom_mutation_click_state_passes_with_dom_mutation_field(self):
        result = self.fake_receipt_for_scenario(
            "dom_mutation_click_state",
            runner_overrides={"dom_mutation_observed": True},
        )
        self.assertTrue(result["success"])

    def test_K_local_form_like_interaction_fails_when_evidence_missing(self):
        result = self.fake_receipt_for_scenario("local_form_like_interaction_no_account")
        self.assertFalse(result["success"])
        self.assertIn("local_form_like_interaction_evidence_missing", result["failure_reasons"])

    def test_L_local_form_like_interaction_passes_with_false_account_flags(self):
        result = self.fake_receipt_for_scenario(
            "local_form_like_interaction_no_account",
            runner_overrides={
                "local_form_interaction_completed": True,
                "account_workflow_performed": False,
                "login_workflow_performed": False,
                "registration_workflow_performed": False,
                "credential_input_performed": False,
            },
        )
        self.assertTrue(result["success"])

    def test_M_screenshot_required_fails_when_screenshot_path_is_missing(self):
        result = self.fake_receipt_for_scenario(
            "screenshot_required",
            runner_remove=("screenshot_path",),
            smoke_remove=("screenshot_path",),
        )
        self.assertFalse(result["success"])
        self.assertIn("screenshot_path_missing", result["failure_reasons"])

    def test_N_screenshot_required_fails_when_path_escapes_scenario_dir(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self._cleanup_temp(root))
        outside = root / "outside.png"
        outside.write_bytes(b"outside")
        result = self.fake_receipt_for_scenario(
            "screenshot_required",
            runner_overrides={"screenshot_path": outside.as_posix()},
            smoke_overrides={"screenshot_path": outside.as_posix()},
        )
        self.assertFalse(result["success"])
        self.assertIn("screenshot_path_outside_scenario_dir", result["failure_reasons"])

    def test_O_screenshot_required_fails_when_path_is_symlink(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self._cleanup_temp(root))
        scenario_dir = root / "scenarios" / "screenshot_required"
        receipt_dir = scenario_dir / "operator_receipt"
        self.write_fake_receipt_tree(receipt_dir)
        link = scenario_dir / "screenshot-link.png"
        link.symlink_to(
            receipt_dir / "adapter_draft_run" / "embedded_smoke" / "screenshot.png"
        )
        for path in (
            receipt_dir / "adapter_draft_run" / "embedded_smoke" / "playwright_local_fixture_sandbox_smoke_runner_output.json",
            receipt_dir / "adapter_draft_run" / "embedded_smoke" / "playwright_local_fixture_sandbox_smoke_result.json",
        ):
            payload = read_json(path)
            payload["screenshot_path"] = link.as_posix()
            write_json(path, payload)
        result = suite_module._scenario_result_payload(
            {
                "scenario_id": "screenshot_required",
                "scenario_type": "screenshot_required",
                "requires_marker": True,
                "requires_click": True,
                "requires_status_text": True,
            },
            scenario_dir=scenario_dir,
            receipt_dir=receipt_dir,
        )
        self.assertFalse(result["success"])
        self.assertIn("screenshot_path_is_symlink", result["failure_reasons"])

    def test_P_screenshot_required_passes_when_screenshot_hash_verifies(self):
        result = self.fake_receipt_for_scenario("screenshot_required")
        self.assertTrue(result["success"])

    def test_Q_blocked_external_request_claim_rejects_non_local_count(self):
        result = self.fake_receipt_for_scenario(
            "blocked_external_request_claim_rejection",
            runner_overrides={"non_local_request_count": 1},
        )
        self.assertFalse(result["success"])
        self.assertIn("blocked_external_request_claim_present", result["failure_reasons"])

    def test_R_blocked_external_request_claim_rejects_non_empty_requests(self):
        result = self.fake_receipt_for_scenario(
            "blocked_external_request_claim_rejection",
            runner_overrides={"non_local_requests": ["https://example.invalid"]},
        )
        self.assertFalse(result["success"])
        self.assertIn("blocked_external_request_claim_present", result["failure_reasons"])

    def test_S_blocked_external_request_claim_rejects_external_network_true(self):
        result = self.fake_receipt_for_scenario(
            "blocked_external_request_claim_rejection",
            runner_overrides={"external_network_performed": True},
        )
        self.assertFalse(result["success"])
        self.assertIn("blocked_external_request_claim_present", result["failure_reasons"])

    def test_T_deterministic_runner_schema_fails_without_required_fields(self):
        result = self.fake_receipt_for_scenario(
            "deterministic_runner_schema",
            runner_remove=("runner_type",),
        )
        self.assertFalse(result["success"])
        self.assertIn("deterministic_runner_schema_invalid", result["failure_reasons"])

    def test_U_deterministic_runner_schema_passes_with_valid_fake_schema(self):
        result = self.fake_receipt_for_scenario("deterministic_runner_schema")
        self.assertTrue(result["success"])

    def test_V_regression_suite_preserves_admission_false(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        with patch(
            "kernel.capabilities.local_only_playwright_fixture_scenario_suite.run_operator_provided_playwright_execution_receipt",
            side_effect=self.fake_422,
        ):
            result = run_local_only_playwright_fixture_scenario_suite(
                matrix_path,
                manifest_path,
                output_dir,
                "suite-001",
                node_command=self.make_fake_node(root),
                runner_script=self.make_fake_runner(output_dir),
                operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                scenario_set="regression",
            )
        payload = read_json(result.result_path)
        self.assertFalse(payload["production_admission_granted"])
        self.assertFalse(payload["live_website_admission_granted"])
        self.assertFalse(payload["general_browser_automation_admission_granted"])

    def test_W_regression_suite_payload_preserves_disabled_performed_false_fields(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        with patch(
            "kernel.capabilities.local_only_playwright_fixture_scenario_suite.run_operator_provided_playwright_execution_receipt",
            side_effect=self.fake_422,
        ):
            result = run_local_only_playwright_fixture_scenario_suite(
                matrix_path,
                manifest_path,
                output_dir,
                "suite-001",
                node_command=self.make_fake_node(root),
                runner_script=self.make_fake_runner(output_dir),
                operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                scenario_set="regression",
            )
        self.assert_false_fields(read_json(result.result_path))

    def test_X_cli_supports_scenario_set_regression(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
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
                    self.make_fake_node(root).as_posix(),
                    "--runner-script",
                    self.make_fake_runner(output_dir).as_posix(),
                    "--operator-attestation",
                    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                    "--scenario-set",
                    "regression",
                    "--plan-only",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["scenario_set"], "regression")
        self.assertEqual(payload["scenario_count_planned"], 11)

    def test_Y_launcher_supports_scenario_set_regression(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        result = run_local_only_playwright_fixture_scenario_suite_launcher(
            matrix_path,
            manifest_path,
            output_dir,
            "suite-launcher-001",
            node_command=self.make_fake_node(root),
            runner_script=self.make_fake_runner(output_dir),
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            scenario_set="regression",
            plan_only=True,
        )
        self.assertTrue(result.complete)
        self.assertEqual(result.payload["scenario_set"], "regression")
        self.assertEqual(result.payload["scenario_count_planned"], 11)

    def test_Z_task_graph_supports_regression_and_writes_artifact_outputs(self):
        root, matrix_path, manifest_path, output_dir = self.workspace()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "local-only-playwright-regression-suite-graph",
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
                            "selection_matrix": matrix_path.as_posix(),
                            "playwright_candidate_manifest": manifest_path.as_posix(),
                            "output_dir": output_dir.as_posix(),
                            "suite_id": "graph-suite-001",
                            "node_command": self.make_fake_node(root).as_posix(),
                            "runner_script": self.make_fake_runner(output_dir).as_posix(),
                            "operator_attestation": OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
                            "project_id": "project-001",
                            "scenario_set": "regression",
                            "plan_only": True,
                        },
                    }
                ],
            },
        )
        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}
        node = read_json(result.execution_manifest_path)["nodes"][0]
        self.assertTrue(result.success)
        self.assertEqual(node["scenario_set"], "regression")
        self.assertIn("local_only_playwright_fixture_scenario_suite_plan", roles)

    def test_AA_module_source_contains_no_disallowed_execution_or_cli_paths(self):
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

    def test_AB_regression_pack_decision_doc_exists_and_states_boundary(self):
        doc_path = REPO_ROOT / "docs" / "decisions" / "local_only_playwright_regression_pack_v1.md"
        self.assertTrue(doc_path.is_file())
        text = doc_path.read_text(encoding="utf-8")
        for required in (
            "local-only regression scenario definitions and validation",
            "file fixture only",
            "does not enable live websites",
            "does not enable arbitrary URLs",
            "does not enable account/login/registration flows",
            "does not enable scraping",
            "does not enable bypass/captcha",
            "does not access secrets/cookies",
            "does not run npm/npx/install/browser download",
            "does not execute candidate repository code",
            "regression success is not production admission",
            "regression success is not live website admission",
            "future live website work remains blocked",
        ):
            self.assertIn(required, text)

    def test_AC_artifact_index_entry_missing_sha256_rejects(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self._cleanup_temp(root))
        scenario_dir = root / "scenarios" / "deterministic_runner_schema"
        receipt_dir = scenario_dir / "operator_receipt"
        self.write_fake_receipt_tree(receipt_dir)

        artifact_index_path = receipt_dir / "artifact_index.json"
        artifact_index = read_json(artifact_index_path)
        artifact_index["entries"][0].pop("sha256", None)
        write_json(artifact_index_path, artifact_index)

        result = suite_module._scenario_result_payload(
            {
                "scenario_id": "deterministic_runner_schema",
                "scenario_type": "deterministic_runner_schema",
                "requires_marker": True,
                "requires_click": True,
                "requires_status_text": True,
            },
            scenario_dir=scenario_dir,
            receipt_dir=receipt_dir,
        )
        self.assertFalse(result["success"])
        self.assertFalse(result["artifact_hashes_verified"])
        self.assertIn("artifact_hash_mismatch", result["failure_reasons"])


if __name__ == "__main__":
    unittest.main()
