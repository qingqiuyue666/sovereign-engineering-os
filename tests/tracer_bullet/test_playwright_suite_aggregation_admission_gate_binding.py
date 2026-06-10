import contextlib
import io
import json
import stat
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.capabilities.local_fixture_playwright_adapter_admission_gate import (
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
    run_local_fixture_playwright_adapter_admission_gate,
)
from kernel.capabilities.operator_provided_playwright_execution_receipt import (
    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
    run_operator_provided_playwright_execution_receipt,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_local_fixture_playwright_adapter_admission_gate_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_SCENARIOS = (
    "static_click_marker",
    "repeated_local_fixture_execution_a",
    "repeated_local_fixture_execution_b",
)
REGRESSION_SCENARIOS = CORE_SCENARIOS + (
    "output_integrity_scenario",
    "boundary_false_scenario",
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
    raise AssertionError("external path should not be called")


class PlaywrightSuiteAggregationAdmissionGateBindingTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        receipt_output = root / "receipt-output"
        gate_output = root / "gate-output"
        aggregation_output = root / "aggregation-output"
        receipt_output.mkdir()
        gate_output.mkdir()
        aggregation_output.mkdir()
        matrix_path = root / "selection_matrix.json"
        manifest_path = root / "playwright_manifest.json"
        write_json_atomically(matrix_path, self.valid_matrix())
        write_json_atomically(manifest_path, self.valid_manifest())
        return root, matrix_path, manifest_path, receipt_output, gate_output, aggregation_output

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

    def repo_temp_dir(self):
        temp_dir = tempfile.TemporaryDirectory(dir=REPO_ROOT)
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

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

    def make_fake_runner(self, root):
        fake_runner = root / "fake-runner.py"
        fake_runner.write_text(
            textwrap.dedent(
                """\
                import argparse
                import json
                from pathlib import Path

                parser = argparse.ArgumentParser()
                parser.add_argument("--fixture-url", required=True)
                parser.add_argument("--output-json", required=True)
                parser.add_argument("--screenshot-path", required=True)
                args = parser.parse_args()
                Path(args.screenshot_path).write_bytes(b"fake-png")
                payload = {
                    "runner_type": "playwright_local_fixture_smoke_runner_v1",
                    "fixture_url": args.fixture_url,
                    "marker_found": True,
                    "click_completed": True,
                    "status_text": "clicked",
                    "non_local_request_count": 0,
                    "non_local_requests": [],
                    "screenshot_path": args.screenshot_path,
                    "success": True,
                }
                Path(args.output_json).write_text(
                    json.dumps(payload, indent=2, sort_keys=True) + "\\n",
                    encoding="utf-8",
                )
                """
            ),
            encoding="utf-8",
        )
        fake_runner.chmod(fake_runner.stat().st_mode | stat.S_IXUSR)
        return fake_runner

    def create_receipt(self):
        root, matrix_path, manifest_path, receipt_output, gate_output, aggregation_output = self.workspace()
        receipt = run_operator_provided_playwright_execution_receipt(
            matrix_path,
            manifest_path,
            receipt_output,
            "receipt-001",
            node_command=self.make_fake_node(root),
            runner_script=self.make_fake_runner(self.repo_temp_dir()),
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="local fixture only",
        )
        self.assertTrue(receipt.complete)
        return root, receipt_output, gate_output, aggregation_output

    def no_external_gate_paths(self):
        stack = contextlib.ExitStack()
        stack.enter_context(patch("subprocess.run", side_effect=fail_if_called))
        stack.enter_context(patch("os.system", side_effect=fail_if_called))
        stack.enter_context(patch("socket.create_connection", side_effect=fail_if_called))
        return stack

    def run_gate(
        self,
        receipt_output,
        gate_output,
        *,
        aggregation_result=None,
        require_aggregation=True,
        require_regression=False,
    ):
        with self.no_external_gate_paths():
            return run_local_fixture_playwright_adapter_admission_gate(
                receipt_output,
                gate_output,
                "gate-001",
                review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
                project_id="project-001",
                reviewer_id="reviewer-001",
                operator_notes="reviewed local fixture receipt",
                aggregation_result=aggregation_result,
                require_aggregation_evidence=require_aggregation,
                require_regression_evidence=require_regression,
            )

    def suite_run_result(self, scenario_ids=CORE_SCENARIOS, *, scenario_set="core"):
        return {
            "suite_run_dir": "/local/suite",
            "suite_success": True,
            "scenario_set": scenario_set,
            "scenario_count_planned": len(scenario_ids),
            "scenario_count_executed": len(scenario_ids),
            "scenario_count_passed": len(scenario_ids),
            "scenario_count_failed": 0,
            "scenario_ids": list(scenario_ids),
            "failed_scenario_ids": [],
            "rejected": False,
            "rejection_reasons": [],
            "hashes_verified": True,
            "boundaries_false": True,
            "artifact_index_under_suite_dir": True,
            "candidate_repo_files_indexed": False,
            "external_candidate_artifacts_indexed": False,
            "stale_evidence": False,
        }

    def aggregation_payload(self, *, regression=False):
        scenarios = REGRESSION_SCENARIOS if regression else CORE_SCENARIOS
        scenario_set = "regression" if regression else "core"
        suite_run_results = [
            self.suite_run_result(scenarios, scenario_set=scenario_set),
            self.suite_run_result(CORE_SCENARIOS, scenario_set="core"),
        ]
        return {
            "result_type": "playwright_local_admission_receipt_aggregation_result_v1",
            "aggregation_id": "aggregation-001",
            "suite_run_count_planned": 2,
            "suite_run_count_evaluated": 2,
            "suite_run_count_passed": 2,
            "suite_run_count_failed": 0,
            "suite_run_count_rejected": 0,
            "scenario_count_total": sum(
                item["scenario_count_executed"] for item in suite_run_results
            ),
            "scenario_count_passed": sum(
                item["scenario_count_passed"] for item in suite_run_results
            ),
            "scenario_count_failed": 0,
            "pass_rate_bps": 10000,
            "flaky_scenario_ids": [],
            "flaky_rate_bps": 0,
            "regression_detected": False,
            "stale_evidence_detected": False,
            "missing_coverage_detected": False,
            "required_core_scenario_ids": list(CORE_SCENARIOS),
            "suite_run_results": suite_run_results,
            "aggregate_success": True,
            "aggregation_status": "playwright_local_admission_receipt_aggregation_passed",
            "aggregation_decision": "playwright_local_admission_receipt_aggregation_passed",
            "next_allowed_action": "review_playwright_local_admission_receipt_aggregation",
            "production_admission_granted": False,
            "live_website_admission_granted": False,
            "general_browser_automation_admission_granted": False,
            "local_fixture_aggregation_passed": True,
            "hashes_verified_all": True,
            "boundaries_false_all": True,
            "candidate_repo_files_indexed_any": False,
            "external_candidate_artifacts_indexed_any": False,
            "minimum_suite_runs_satisfied": True,
            "minimum_pass_rate_satisfied": True,
            "maximum_flaky_rate_satisfied": True,
        }

    def write_aggregation_result(self, aggregation_output, payload=None):
        path = Path(aggregation_output) / "playwright_local_admission_receipt_aggregation_result.json"
        write_json(path, self.aggregation_payload() if payload is None else payload)
        return path

    def assert_rejects(self, mutator, expected_reason):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation = self.aggregation_payload()
        mutator(aggregation, aggregation_output)
        aggregation_path = aggregation_output / "playwright_local_admission_receipt_aggregation_result.json"
        if not aggregation_path.exists() and not aggregation_path.is_symlink():
            write_json(aggregation_path, aggregation)
        result = self.run_gate(receipt_output, gate_output, aggregation_result=aggregation_path)
        decision = read_json(result.decision_path)
        self.assertFalse(result.complete)
        self.assertIn(expected_reason, decision["failed_check_ids"])
        self.assertIn(expected_reason, decision["aggregation_result_rejection_reasons"])
        return decision

    def assert_false_fields(self, payload, *, admitted):
        for field_name in LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            if field_name == "local_fixture_admission_granted":
                self.assertEqual(payload[field_name], admitted)
            else:
                self.assertFalse(payload[field_name], field_name)
        for field_name in LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_A_existing_423_gate_still_passes_without_required_aggregation(self):
        _root, receipt_output, gate_output, _aggregation_output = self.create_receipt()
        result = self.run_gate(
            receipt_output,
            gate_output,
            aggregation_result=None,
            require_aggregation=False,
        )
        decision = read_json(result.decision_path)
        self.assertTrue(result.complete)
        self.assertTrue(decision["local_fixture_admission_granted"])
        self.assertFalse(decision["aggregation_evidence_supplied"])
        self.assertFalse(decision["aggregation_result_valid"])

    def test_B_required_aggregation_missing_rejects(self):
        _root, receipt_output, gate_output, _aggregation_output = self.create_receipt()
        result = self.run_gate(receipt_output, gate_output, aggregation_result=None)
        decision = read_json(result.decision_path)
        self.assertFalse(result.complete)
        self.assertIn("aggregation_evidence_required_but_missing", decision["failed_check_ids"])

    def test_C_aggregation_path_symlink_rejects(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        target = self.write_aggregation_result(aggregation_output)
        link = aggregation_output / "aggregation-link.json"
        link.symlink_to(target)
        result = self.run_gate(receipt_output, gate_output, aggregation_result=link)
        decision = read_json(result.decision_path)
        self.assertFalse(result.complete)
        self.assertIn("aggregation_result_path_is_symlink", decision["failed_check_ids"])

    def test_D_aggregation_result_invalid_json_rejects(self):
        def mutate(_aggregation, aggregation_output):
            (aggregation_output / "playwright_local_admission_receipt_aggregation_result.json").write_text(
                "{bad\n",
                encoding="utf-8",
            )

        self.assert_rejects(mutate, "aggregation_result_not_json_object")

    def test_E_aggregation_result_type_mismatch_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(result_type="wrong"),
            "aggregation_result_type_mismatch",
        )

    def test_F_aggregate_success_false_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(aggregate_success=False),
            "aggregation_result_not_successful",
        )

    def test_G_local_fixture_aggregation_passed_false_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(local_fixture_aggregation_passed=False),
            "local_fixture_aggregation_not_passed",
        )

    def test_H_rejected_suite_runs_reject(self):
        def mutate(payload, _out):
            payload["suite_run_count_rejected"] = 1

        self.assert_rejects(mutate, "aggregation_rejected_suite_runs_present")

    def test_I_failed_suite_runs_reject(self):
        def mutate(payload, _out):
            payload["suite_run_count_failed"] = 1

        self.assert_rejects(mutate, "aggregation_failed_suite_runs_present")

    def test_J_flaky_scenario_ids_non_empty_rejects(self):
        def mutate(payload, _out):
            payload["flaky_scenario_ids"] = ["static_click_marker"]
            payload["flaky_rate_bps"] = 500

        self.assert_rejects(mutate, "aggregation_flaky_scenarios_present")

    def test_K_regression_detected_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(regression_detected=True),
            "aggregation_regression_detected",
        )

    def test_L_stale_evidence_detected_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(stale_evidence_detected=True),
            "aggregation_stale_evidence_detected",
        )

    def test_M_missing_coverage_detected_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(missing_coverage_detected=True),
            "aggregation_missing_coverage_detected",
        )

    def test_N_hashes_verified_all_false_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(hashes_verified_all=False),
            "aggregation_hashes_not_verified",
        )

    def test_O_boundaries_false_all_false_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(boundaries_false_all=False),
            "aggregation_boundaries_not_false",
        )

    def test_P_candidate_repo_files_indexed_any_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(candidate_repo_files_indexed_any=True),
            "aggregation_candidate_artifacts_present",
        )

    def test_Q_external_candidate_artifacts_indexed_any_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(external_candidate_artifacts_indexed_any=True),
            "aggregation_candidate_artifacts_present",
        )

    def test_R_production_admission_granted_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(production_admission_granted=True),
            "aggregation_production_admission_claimed",
        )

    def test_S_live_website_admission_granted_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(live_website_admission_granted=True),
            "aggregation_live_website_admission_claimed",
        )

    def test_T_general_browser_automation_admission_granted_true_rejects(self):
        self.assert_rejects(
            lambda payload, _out: payload.update(general_browser_automation_admission_granted=True),
            "aggregation_general_browser_admission_claimed",
        )

    def test_U_suite_run_result_rejected_true_rejects(self):
        def mutate(payload, _out):
            payload["suite_run_results"][0]["rejected"] = True

        self.assert_rejects(mutate, "aggregation_suite_run_rejected")

    def test_V_suite_run_result_hashes_verified_false_rejects(self):
        def mutate(payload, _out):
            payload["suite_run_results"][0]["hashes_verified"] = False

        self.assert_rejects(mutate, "aggregation_suite_run_hashes_not_verified")

    def test_W_suite_run_result_boundaries_false_false_rejects(self):
        def mutate(payload, _out):
            payload["suite_run_results"][0]["boundaries_false"] = False

        self.assert_rejects(mutate, "aggregation_suite_run_boundaries_not_false")

    def test_X_suite_run_result_artifact_index_under_suite_dir_false_rejects(self):
        def mutate(payload, _out):
            payload["suite_run_results"][0]["artifact_index_under_suite_dir"] = False

        self.assert_rejects(mutate, "aggregation_suite_run_artifact_index_outside_suite_dir")

    def test_Y_core_scenario_coverage_missing_rejects(self):
        def mutate(payload, _out):
            payload["suite_run_results"][0]["scenario_ids"] = ["static_click_marker"]

        self.assert_rejects(mutate, "aggregation_core_coverage_missing")

    def test_Z_require_regression_evidence_rejects_when_missing(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(aggregation_output)
        result = self.run_gate(
            receipt_output,
            gate_output,
            aggregation_result=aggregation_path,
            require_regression=True,
        )
        decision = read_json(result.decision_path)
        self.assertFalse(result.complete)
        self.assertIn("regression_evidence_required_but_missing", decision["failed_check_ids"])
        self.assertIn("regression_scenario_coverage_missing", decision["failed_check_ids"])

    def test_AA_require_regression_evidence_passes_when_complete(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(
            aggregation_output,
            self.aggregation_payload(regression=True),
        )
        result = self.run_gate(
            receipt_output,
            gate_output,
            aggregation_result=aggregation_path,
            require_regression=True,
        )
        decision = read_json(result.decision_path)
        self.assertTrue(result.complete)
        self.assertTrue(decision["regression_evidence_present"])
        self.assertTrue(decision["regression_scenario_coverage_complete"])

    def test_AB_successful_aggregation_binds_into_gate_output_payload(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(aggregation_output)
        result = self.run_gate(receipt_output, gate_output, aggregation_result=aggregation_path)
        decision = read_json(result.decision_path)
        self.assertTrue(result.complete)
        self.assertTrue(decision["aggregation_result_valid"])
        self.assertTrue(decision["local_fixture_aggregation_bound_to_admission_gate"])
        self.assertEqual(decision["aggregation_suite_run_count_evaluated"], 2)
        self.assertEqual(decision["admission_gate_result"], "pass")

    def test_AC_output_preserves_production_live_general_browser_false(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(aggregation_output)
        result = self.run_gate(receipt_output, gate_output, aggregation_result=aggregation_path)
        decision = read_json(result.decision_path)
        self.assertFalse(decision["production_admission_granted"])
        self.assertFalse(decision["live_website_admission_granted"])
        self.assertFalse(decision["general_browser_automation_admission_granted"])

    def test_AD_output_preserves_all_disabled_performed_false_fields(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(aggregation_output)
        result = self.run_gate(receipt_output, gate_output, aggregation_result=aggregation_path)
        self.assert_false_fields(read_json(result.decision_path), admitted=True)

    def test_AE_cli_accepts_aggregation_evidence_args_and_require_flags(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(
            aggregation_output,
            self.aggregation_payload(regression=True),
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-local-fixture-playwright-adapter-admission-gate",
                    "--receipt-dir",
                    receipt_output.as_posix(),
                    "--output-dir",
                    gate_output.as_posix(),
                    "--gate-id",
                    "cli-gate-001",
                    "--review-attestation",
                    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
                    "--aggregation-result",
                    aggregation_path.as_posix(),
                    "--require-aggregation-evidence",
                    "--require-regression-evidence",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(payload["aggregation_result_valid"])

    def test_AF_launcher_accepts_aggregation_evidence_args_and_require_flags(self):
        _root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(
            aggregation_output,
            self.aggregation_payload(regression=True),
        )
        result = run_local_fixture_playwright_adapter_admission_gate_launcher(
            receipt_output,
            gate_output,
            "launcher-gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
            aggregation_result=aggregation_path,
            require_aggregation_evidence=True,
            require_regression_evidence=True,
        )
        payload = result.to_cli_payload()
        self.assertTrue(payload["complete"])
        self.assertTrue(payload["local_fixture_aggregation_bound_to_admission_gate"])

    def test_AG_task_graph_accepts_aggregation_evidence_and_writes_artifact_outputs(self):
        root, receipt_output, gate_output, aggregation_output = self.create_receipt()
        aggregation_path = self.write_aggregation_result(
            aggregation_output,
            self.aggregation_payload(regression=True),
        )
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(
            graph_path,
            self.gate_graph(receipt_output, gate_output, aggregation_path),
        )
        result = run_local_task_graph_fixture(graph_path, graph_output)
        node = read_json(result.execution_manifest_path)["nodes"][0]
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}
        self.assertTrue(result.success)
        self.assertTrue(node["local_fixture_aggregation_bound_to_admission_gate"])
        self.assertIn("local_fixture_playwright_adapter_admission_gate_decision", roles)

    def test_AH_module_source_contains_no_disallowed_execution_or_cli_paths(self):
        source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "local_fixture_playwright_adapter_admission_gate.py"
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

    def test_AI_decision_doc_exists_and_states_local_only_boundary(self):
        doc_path = REPO_ROOT / "docs" / "decisions" / "playwright_suite_aggregation_admission_gate_binding_v1.md"
        self.assertTrue(doc_path.is_file())
        text = doc_path.read_text(encoding="utf-8")
        for required in (
            "binds #425 aggregation evidence into #423 admission gate",
            "#426 regression evidence may be required through the aggregation evidence",
            "local-fixture-only",
            "reads existing evidence only",
            "does not execute Playwright",
            "does not execute #422/#424/#425/#426",
            "does not enable live websites",
            "does not enable arbitrary URLs",
            "does not enable account/login/registration flows",
            "does not enable scraping",
            "does not enable bypass/captcha",
            "does not access secrets/cookies",
            "does not run npm/npx/install/browser download",
            "does not execute candidate repository code",
            "aggregation-bound gate success is not production admission",
            "aggregation-bound gate success is not live website admission",
            "future live website work remains blocked",
        ):
            self.assertIn(required, text)

    def gate_graph(self, receipt_output, gate_output, aggregation_result):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "playwright-suite-aggregation-admission-gate-graph",
            "authority": "non_authority",
            "required_human_approval": True,
            "execution_mode": "fixture_execution",
            "nodes": [
                {
                    "node_id": "admission_gate",
                    "adapter_id": "local_fixture_playwright_adapter_admission_gate",
                    "capability": "launch_local_fixture_playwright_adapter_admission_gate",
                    "depends_on": [],
                    "execution_mode": "fixture",
                    "approval_checkpoint_required": True,
                    "approval_checkpoint_id": "admission-gate:human_review",
                    "inputs": {
                        "receipt_dir": Path(receipt_output).as_posix(),
                        "output_dir": Path(gate_output).as_posix(),
                        "gate_id": "graph-gate-001",
                        "review_attestation": LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
                        "aggregation_result": Path(aggregation_result).as_posix(),
                        "require_aggregation_evidence": True,
                        "require_regression_evidence": True,
                        "project_id": "project-001",
                    },
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
