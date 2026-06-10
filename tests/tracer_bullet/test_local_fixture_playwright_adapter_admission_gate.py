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
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
    build_local_fixture_playwright_adapter_admission_gate_plan,
    run_local_fixture_playwright_adapter_admission_gate,
)
from kernel.capabilities.operator_provided_playwright_execution_receipt import (
    ADAPTER_DRAFT_RUN_DIR_NAME,
    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE,
    run_operator_provided_playwright_execution_receipt,
)
from kernel.capabilities.bounded_playwright_worker_adapter_draft import (
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE,
)
from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_local_fixture_playwright_adapter_admission_gate_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

GATE_PLAN_OUTPUTS = {
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
}
GATE_ALL_OUTPUTS = GATE_PLAN_OUTPUTS | {
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE,
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("external path should not be called")


class LocalFixturePlaywrightAdapterAdmissionGateTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        receipt_output = root / "receipt-output"
        gate_output = root / "gate-output"
        receipt_output.mkdir()
        gate_output.mkdir()
        matrix_path = root / "selection_matrix.json"
        manifest_path = root / "playwright_manifest.json"
        write_json_atomically(matrix_path, self.valid_matrix())
        write_json_atomically(manifest_path, self.valid_manifest())
        return root, matrix_path, manifest_path, receipt_output, gate_output

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

    def create_receipt(self, *, mode="success"):
        root, matrix_path, manifest_path, receipt_output, gate_output = self.workspace()
        fake_node = self.make_fake_node(root)
        fake_runner = self.make_fake_runner(self.repo_temp_dir() / "fake-runner.py", mode=mode)
        receipt = run_operator_provided_playwright_execution_receipt(
            matrix_path,
            manifest_path,
            receipt_output,
            "receipt-001",
            node_command=fake_node,
            runner_script=fake_runner,
            operator_attestation=OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="local fixture only",
        )
        return root, receipt_output, gate_output, receipt

    def run_gate(self, receipt_output, gate_output, *, gate_id="gate-001"):
        with self.no_external_gate_paths():
            return run_local_fixture_playwright_adapter_admission_gate(
                receipt_output,
                gate_output,
                gate_id,
                review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
                project_id="project-001",
                reviewer_id="reviewer-001",
                operator_notes="reviewed local fixture receipt",
            )

    def no_external_gate_paths(self):
        stack = contextlib.ExitStack()
        stack.enter_context(patch("subprocess.run", side_effect=fail_if_called))
        stack.enter_context(patch("os.system", side_effect=fail_if_called))
        stack.enter_context(patch("socket.create_connection", side_effect=fail_if_called))
        return stack

    def assert_no_gate_artifacts(self, output_dir):
        if not Path(output_dir).exists():
            return
        for name in GATE_ALL_OUTPUTS:
            self.assertFalse((Path(output_dir) / name).exists(), name)
            self.assertFalse((Path(output_dir) / name).is_symlink(), name)

    def assert_admission_false_fields(self, payload, *, admitted=False):
        for field_name in LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            if field_name == "local_fixture_admission_granted":
                self.assertEqual(payload[field_name], admitted)
            else:
                self.assertFalse(payload[field_name], field_name)
        for field_name in LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def mutate_json(self, path, mutator):
        payload = read_json(path)
        mutator(payload)
        write_json(path, payload)

    def receipt_path(self, receipt_output, name):
        return Path(receipt_output) / name

    def adapter_path(self, receipt_output, name):
        return Path(receipt_output) / ADAPTER_DRAFT_RUN_DIR_NAME / name

    def smoke_path(self, receipt_output, name):
        return Path(receipt_output) / ADAPTER_DRAFT_RUN_DIR_NAME / "embedded_smoke" / name

    def assert_rejects_after_mutation(self, mutator, expected_check_id):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        mutator(receipt_output)
        result = self.run_gate(receipt_output, gate_output)
        decision = read_json(result.decision_path)
        self.assertFalse(result.complete)
        self.assertFalse(decision["local_fixture_admission_granted"])
        self.assertIn(expected_check_id, decision["failed_check_ids"])
        return decision

    def test_A_plan_only_creates_gate_plan_manifest_summary_checklist_index_without_evaluating_admission(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        with self.no_external_gate_paths():
            result = build_local_fixture_playwright_adapter_admission_gate_plan(
                receipt_output,
                gate_output,
                "gate-001",
                review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
                project_id="project-001",
                reviewer_id="reviewer-001",
                operator_notes="plan only",
            )
        self.assertTrue(result.complete)
        for name in GATE_PLAN_OUTPUTS:
            self.assertTrue((gate_output / name).is_file(), name)
        self.assertFalse((gate_output / LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE).exists())
        plan = read_json(result.plan_path)
        self.assertEqual(plan["gate_decision"], "ready_to_evaluate_local_fixture_playwright_adapter_admission")
        self.assertFalse(plan["local_fixture_admission_granted"])

    def test_B_run_gate_admits_valid_422_receipt_generated_by_fake_runner_success(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        result = self.run_gate(receipt_output, gate_output)
        decision = read_json(result.decision_path)
        self.assertTrue(result.complete)
        self.assertTrue(decision["local_fixture_admission_granted"])
        self.assertEqual(decision["admitted_scope"], "local_fixture_only")
        self.assertEqual(decision["admission_checks_failed"], 0)

    def test_C_run_gate_rejects_422_receipt_generated_by_fake_runner_failure(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt(mode="failure")
        result = self.run_gate(receipt_output, gate_output)
        decision = read_json(result.decision_path)
        self.assertFalse(result.complete)
        self.assertFalse(decision["local_fixture_admission_granted"])
        self.assertIn("receipt_success_true", decision["failed_check_ids"])

    def test_D_missing_receipt_dir_fails_closed_with_no_artifacts(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: None)
        output_dir = root / "out"
        output_dir.mkdir()
        result = run_local_fixture_playwright_adapter_admission_gate(
            root / "missing",
            output_dir,
            "gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assert_no_gate_artifacts(output_dir)

    def test_E_receipt_dir_symlink_fails_closed_with_no_artifacts(self):
        root, _receipt_output, gate_output, _receipt = self.create_receipt()
        target = root / "target"
        target.mkdir()
        link = root / "receipt-link"
        link.symlink_to(target)
        result = run_local_fixture_playwright_adapter_admission_gate(
            link,
            gate_output,
            "gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assert_no_gate_artifacts(gate_output)

    def test_F_output_dir_missing_fails_closed_with_no_artifacts(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        missing = gate_output.parent / "missing-output"
        result = run_local_fixture_playwright_adapter_admission_gate(
            receipt_output,
            missing,
            "gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assert_no_gate_artifacts(missing)

    def test_G_output_dir_symlink_fails_closed_with_no_artifacts(self):
        root, receipt_output, _gate_output, _receipt = self.create_receipt()
        real_output = root / "real-output"
        real_output.mkdir()
        link = root / "output-link"
        link.symlink_to(real_output)
        result = run_local_fixture_playwright_adapter_admission_gate(
            receipt_output,
            link,
            "gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assert_no_gate_artifacts(real_output)

    def test_H_existing_gate_output_file_blocks_with_no_overwrite(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        existing = gate_output / LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE
        existing.write_text("keep\n", encoding="utf-8")
        result = run_local_fixture_playwright_adapter_admission_gate(
            receipt_output,
            gate_output,
            "gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
        )
        self.assertFalse(result.complete)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse((gate_output / LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE).exists())

    def test_I_wrong_review_attestation_fails_closed_with_no_artifacts(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        result = run_local_fixture_playwright_adapter_admission_gate(
            receipt_output,
            gate_output,
            "gate-001",
            review_attestation="WRONG",
        )
        self.assertFalse(result.complete)
        self.assert_no_gate_artifacts(gate_output)

    def test_J_sensitive_wrong_review_attestation_does_not_leak_raw_text(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        bad_attestation = "SECRET_TOKEN_PASSWORD_API_KEY_COOKIE_BAD"
        result = run_local_fixture_playwright_adapter_admission_gate(
            receipt_output,
            gate_output,
            "gate-001",
            review_attestation=bad_attestation,
        )
        serialized = json.dumps(result.payload, sort_keys=True)
        self.assertNotIn(bad_attestation, serialized)
        self.assertNotIn("SECRET_TOKEN_PASSWORD", serialized)
        self.assert_no_gate_artifacts(gate_output)

    def test_K_missing_receipt_result_rejects_does_not_admit(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE).unlink(),
            "receipt_result_exists",
        )

    def test_L_malformed_receipt_json_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE).write_text("{bad\n", encoding="utf-8"),
            "receipt_result_type_expected",
        )

    def test_M_wrong_receipt_type_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(receipt_type="wrong")),
            "receipt_type_expected",
        )

    def test_N_wrong_candidate_id_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE), lambda payload: payload.update(candidate_id="wrong")),
            "candidate_id_expected",
        )

    def test_O_wrong_repo_full_name_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE), lambda payload: payload.update(repo_full_name="wrong/repo")),
            "repo_full_name_expected",
        )

    def test_P_receipt_success_false_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE), lambda payload: payload.update(success=False)),
            "receipt_success_true",
        )

    def test_Q_adapter_draft_success_false_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.adapter_path(receipt_output, BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE), lambda payload: payload.update(success=False)),
            "adapter_draft_success_true",
        )

    def test_R_embedded_smoke_success_false_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.smoke_path(receipt_output, PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE), lambda payload: payload.update(success=False)),
            "embedded_smoke_success_true",
        )

    def test_S_embedded_fixture_scheme_http_https_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.smoke_path(receipt_output, PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE), lambda payload: payload.update(fixture_url_scheme="https", fixture_url="https://example.invalid")),
            "embedded_fixture_scheme_file",
        )

    def test_T_embedded_non_local_request_count_above_zero_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.smoke_path(receipt_output, PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE), lambda payload: payload.update(non_local_request_count=1)),
            "embedded_non_local_request_count_zero",
        )

    def test_U_any_live_website_boundary_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(live_website_automation_performed=True)),
            "live_website_not_allowed_or_performed",
        )

    def test_V_any_arbitrary_url_user_url_boundary_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(user_supplied_url_used=True)),
            "user_supplied_url_not_used",
        )

    def test_W_any_account_login_registration_boundary_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(login_workflow_performed=True)),
            "account_scraping_bypass_captcha_not_allowed_or_performed",
        )

    def test_X_any_scraping_bypass_captcha_boundary_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(scraping_performed=True)),
            "account_scraping_bypass_captcha_not_allowed_or_performed",
        )

    def test_Y_any_secret_cookie_boundary_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(secret_access_performed=True)),
            "secrets_cookies_not_allowed_or_performed",
        )

    def test_Z_any_external_network_install_npm_npx_boundary_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(npm_performed=True)),
            "install_download_npm_npx_not_allowed_or_performed",
        )

    def test_AA_candidate_repo_access_import_execution_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(candidate_code_execution_performed=True)),
            "candidate_repo_code_not_accessed_or_executed",
        )

    def test_AB_production_promotion_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(production_promotion_granted=True)),
            "production_promotion_not_granted",
        )

    def test_AC_autonomy_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_plan.json"), lambda payload: payload.update(autonomous_execution_performed=True)),
            "autonomy_not_granted_or_performed",
        )

    def test_AD_artifact_index_path_outside_receipt_dir_rejects(self):
        def mutate(receipt_output):
            outside = Path(receipt_output).parent / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            self.mutate_json(
                self.receipt_path(receipt_output, LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE),
                lambda payload: payload["entries"][0].update(path=outside.as_posix()),
            )
        self.assert_rejects_after_mutation(mutate, "receipt_artifact_index_paths_under_receipt_dir")

    def test_AE_artifact_index_symlink_path_rejects(self):
        def mutate(receipt_output):
            target = self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_summary.md")
            link = Path(receipt_output) / "summary-link.md"
            link.symlink_to(target)
            self.mutate_json(
                self.receipt_path(receipt_output, LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE),
                lambda payload: payload["entries"][0].update(path=link.as_posix()),
            )
        self.assert_rejects_after_mutation(mutate, "receipt_artifact_index_no_symlink_paths")

    def test_AF_candidate_repo_files_indexed_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE), lambda payload: payload.update(candidate_repo_files_indexed=True)),
            "candidate_repo_files_not_indexed",
        )

    def test_AG_external_candidate_artifacts_indexed_true_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE), lambda payload: payload.update(external_candidate_artifacts_indexed=True)),
            "external_candidate_artifacts_not_indexed",
        )

    def test_AH_receipt_artifact_hash_mismatch_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.receipt_path(receipt_output, "operator_provided_playwright_execution_receipt_summary.md").write_text("changed\n", encoding="utf-8"),
            "receipt_artifact_hashes_match_existing_files",
        )

    def test_AI_adapter_draft_artifact_hash_mismatch_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.adapter_path(receipt_output, "bounded_playwright_worker_adapter_draft_summary.md").write_text("changed\n", encoding="utf-8"),
            "adapter_draft_artifact_hashes_match_existing_files",
        )

    def test_AJ_embedded_smoke_artifact_hash_mismatch_rejects(self):
        self.assert_rejects_after_mutation(
            lambda receipt_output: self.smoke_path(receipt_output, "playwright_local_fixture_sandbox_smoke_summary.md").write_text("changed\n", encoding="utf-8"),
            "embedded_smoke_artifact_hashes_match_existing_files",
        )

    def test_AK_decision_file_includes_full_check_list_and_failed_check_ids(self):
        decision = self.assert_rejects_after_mutation(
            lambda receipt_output: self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE).unlink(),
            "receipt_result_exists",
        )
        self.assertGreaterEqual(decision["admission_checks_total"], 41)
        self.assertEqual(
            decision["admission_checks_total"],
            len(decision["admission_check_results"]),
        )
        self.assertIn("receipt_result_exists", decision["failed_check_ids"])

    def test_AL_admitted_decision_sets_local_fixture_true_but_production_live_general_browser_false(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        result = self.run_gate(receipt_output, gate_output)
        decision = read_json(result.decision_path)
        self.assert_admission_false_fields(decision, admitted=True)
        self.assertFalse(decision["production_admission_granted"])
        self.assertFalse(decision["live_website_admission_granted"])
        self.assertFalse(decision["general_browser_automation_admission_granted"])

    def test_AM_rejected_decision_keeps_local_fixture_false_and_production_live_false(self):
        decision = self.assert_rejects_after_mutation(
            lambda receipt_output: self.mutate_json(self.receipt_path(receipt_output, OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE), lambda payload: payload.update(success=False)),
            "receipt_success_true",
        )
        self.assert_admission_false_fields(decision, admitted=False)

    def test_AN_launcher_payload_preserves_all_admission_false_and_performed_false_fields(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        result = run_local_fixture_playwright_adapter_admission_gate_launcher(
            receipt_output,
            gate_output,
            "gate-001",
            review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
        )
        payload = result.to_cli_payload()
        self.assert_admission_false_fields(payload, admitted=True)

    def test_AO_task_graph_node_writes_gate_artifact_outputs(self):
        root, receipt_output, gate_output, _receipt = self.create_receipt()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(graph_path, self.gate_graph(receipt_output, gate_output))
        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}
        self.assertTrue(result.success)
        self.assertIn("local_fixture_playwright_adapter_admission_gate_plan", roles)
        self.assertIn("local_fixture_playwright_adapter_admission_gate_decision", roles)

    def test_AP_task_graph_node_preserves_all_admission_false_and_performed_false_fields(self):
        root, receipt_output, gate_output, _receipt = self.create_receipt()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json_atomically(graph_path, self.gate_graph(receipt_output, gate_output))
        result = run_local_task_graph_fixture(graph_path, graph_output)
        node = read_json(result.execution_manifest_path)["nodes"][0]
        self.assert_admission_false_fields(node, admitted=True)

    def test_AQ_cli_plan_only_path_works(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
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
                    "--plan-only",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["evaluated"])

    def test_AR_cli_run_gate_path_works(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
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
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(payload["local_fixture_admission_granted"])

    def test_AS_tests_patch_subprocess_os_socket_external_paths_and_do_not_use_network_clients(self):
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertIn('patch("subprocess.run"', source)
        self.assertIn('patch("os.system"', source)
        self.assertIn('patch("socket.create_connection"', source)
        self.assertNotIn("import requ" + "ests", source)
        self.assertNotIn("from requ" + "ests", source)
        self.assertNotIn("import htt" + "px", source)
        self.assertNotIn("from htt" + "px", source)

    def test_AT_module_source_contains_no_execution_or_disallowed_cli_argument_paths(self):
        source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "local_fixture_playwright_adapter_admission_gate.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.run", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("os.popen", source)
        self.assertNotIn("import socket", source)
        self.assertNotIn("create_connection", source)
        self.assertNotIn("git clone", source)
        self.assertNotIn("fetch(", source)
        for forbidden_arg in (
            "--node-command",
            "--runner-script",
            "--target-url",
            "--url",
            "--website",
            "--account",
            "--credential",
            "--cookie",
            "--execute",
        ):
            self.assertNotIn(forbidden_arg, source)

    def test_AU_no_code_path_executes_421_or_420_it_only_reads_artifacts(self):
        _root, receipt_output, gate_output, _receipt = self.create_receipt()
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(
                    "kernel.capabilities.bounded_playwright_worker_adapter_draft.run_bounded_playwright_worker_adapter_draft",
                    side_effect=fail_if_called,
                )
            )
            stack.enter_context(
                patch(
                    "kernel.capabilities.playwright_local_fixture_sandbox_smoke.run_playwright_local_fixture_sandbox_smoke",
                    side_effect=fail_if_called,
                )
            )
            stack.enter_context(patch("subprocess.run", side_effect=fail_if_called))
            stack.enter_context(patch("os.system", side_effect=fail_if_called))
            stack.enter_context(patch("socket.create_connection", side_effect=fail_if_called))
            result = run_local_fixture_playwright_adapter_admission_gate(
                receipt_output,
                gate_output,
                "gate-001",
                review_attestation=LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION,
            )
        self.assertTrue(result.complete)

    def gate_graph(self, receipt_output, gate_output):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "local-fixture-admission-gate-graph",
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
                        "project_id": "project-001",
                    },
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
