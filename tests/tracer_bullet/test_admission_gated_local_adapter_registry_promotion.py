import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.admission_gated_local_adapter_registry_promotion import (
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION,
    run_admission_gated_local_adapter_registry_promotion,
)
from kernel.capabilities.local_fixture_playwright_adapter_admission_gate import (
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_admission_gated_local_adapter_registry_promotion_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "admission_gated_local_adapter_registry_promotion.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "admission_gated_local_adapter_registry_promotion_v1.md"
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class AdmissionGatedLocalAdapterRegistryPromotionTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "promotion-output"
        output_dir.mkdir()
        decision_path = root / "local_fixture_playwright_adapter_admission_gate_decision.json"
        write_json_atomically(decision_path, self.valid_decision())
        return root, decision_path, output_dir

    def valid_decision(self):
        payload = {
            "decision_type": "local_fixture_playwright_adapter_admission_gate_decision_v1",
            "admission_gate_result": "pass",
            "gate_status": "local_fixture_playwright_adapter_admission_gate_admitted",
            "gate_decision": "admit_local_fixture_only_playwright_adapter",
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "aggregation_evidence_supplied": True,
            "aggregation_evidence_required": True,
            "aggregation_result_valid": True,
            "local_fixture_aggregation_bound_to_admission_gate": True,
            "aggregation_suite_run_count_evaluated": 1,
            "aggregation_suite_run_count_failed": 0,
            "aggregation_suite_run_count_rejected": 0,
            "aggregation_pass_rate_bps": 10000,
            "aggregation_flaky_rate_bps": 0,
            "aggregation_regression_detected": False,
            "aggregation_stale_evidence_detected": False,
            "aggregation_missing_coverage_detected": False,
            "aggregation_hashes_verified_all": True,
            "aggregation_boundaries_false_all": True,
            "regression_evidence_required": True,
            "regression_evidence_present": True,
            "regression_scenario_coverage_complete": True,
            "artifact_hashes_verified": True,
            "candidate_repo_files_indexed": False,
            "external_candidate_artifacts_indexed": False,
            "embedded_fixture_url_scheme": "file",
            "embedded_non_local_request_count": 0,
            "required_human_review": True,
            "required_human_approval": True,
            "security_review_required": True,
            "sandbox_review_required": True,
            "production_review_required": True,
        }
        payload.update(dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS))
        payload["local_fixture_admission_granted"] = True
        payload.update(
            dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS)
        )
        return payload

    def run_promotion(
        self,
        decision_path,
        output_dir,
        *,
        registry_output=None,
        review_attestation=ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION,
    ):
        return run_admission_gated_local_adapter_registry_promotion(
            decision_path,
            output_dir,
            "promotion-001",
            review_attestation=review_attestation,
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="reviewed #427 local fixture gate",
            registry_output=registry_output,
        )

    def assert_rejects_mutation(self, mutator, reason):
        _root, decision_path, output_dir = self.make_workspace()
        payload = read_json(decision_path)
        mutator(payload)
        write_json(decision_path, payload)

        result = self.run_promotion(decision_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(reason, result.rejection_reasons)
        self.assertTrue(result.result_path.exists())
        self.assertIn(reason, read_json(result.result_path)["rejection_reasons"])

    def test_valid_gate_decision_promotes_restricted_local_fixture_registry_record(self):
        _root, decision_path, output_dir = self.make_workspace()
        registry_output = output_dir / "local_registry_entry.json"

        result = self.run_promotion(
            decision_path,
            output_dir,
            registry_output=registry_output,
        )
        payload = read_json(result.result_path)
        registry_record = read_json(registry_output)

        self.assertTrue(result.complete)
        self.assertEqual(payload["promotion_type"], "admission_gated_local_adapter_registry_promotion_v1")
        self.assertEqual(payload["adapter_id"], "bounded_playwright_worker_adapter_draft")
        self.assertEqual(payload["candidate_id"], "github-candidate-microsoft-playwright-v1")
        self.assertEqual(payload["repo_full_name"], "microsoft/playwright")
        self.assertEqual(payload["source_gate_decision_path"], decision_path.as_posix())
        self.assertEqual(payload["source_gate_decision_sha256"], sha256_file(decision_path))
        self.assertTrue(payload["source_gate_passed"])
        self.assertTrue(payload["aggregation_bound"])
        self.assertTrue(payload["regression_bound"])
        self.assertTrue(payload["local_fixture_only"])
        self.assertTrue(payload["human_review_required"])
        self.assertTrue(payload["required_human_approval"])
        self.assertTrue(payload["non_production"])
        self.assertFalse(payload["production_adapter"])
        self.assertTrue(payload["registry_promotion_granted"])
        self.assertFalse(payload["production_promotion_granted"])
        self.assertEqual(payload["promotion_status"], "admission_gated_local_adapter_registry_promotion_completed")
        self.assertEqual(payload["promotion_decision"], "promote_local_fixture_only_adapter_registration")
        self.assertEqual(payload["next_allowed_action"], "use_local_fixture_only_adapter_under_human_review")
        self.assertEqual(registry_record["registry_entry_type"], "local_fixture_only_adapter_registry_entry_v1")
        self.assertEqual(registry_record["registry_entry_status"], "enabled_local_fixture_only")
        self.assertEqual(registry_record["allowed_scope"], "local_fixture_only")

    def test_missing_gate_decision_rejects(self):
        root, _decision_path, output_dir = self.make_workspace()
        result = self.run_promotion(root / "missing-decision.json", output_dir)
        self.assertFalse(result.complete)
        self.assertIn("gate_decision_path_missing", result.rejection_reasons)

    def test_symlink_gate_decision_rejects(self):
        root, decision_path, output_dir = self.make_workspace()
        symlink_path = root / "decision-link.json"
        symlink_path.symlink_to(decision_path)

        result = self.run_promotion(symlink_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("gate_decision_path_is_symlink", result.rejection_reasons)

    def test_invalid_json_rejects(self):
        _root, decision_path, output_dir = self.make_workspace()
        decision_path.write_text("{", encoding="utf-8")

        result = self.run_promotion(decision_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("gate_decision_not_json_object", result.rejection_reasons)

    def test_decision_type_mismatch_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"decision_type": "wrong"}),
            "gate_decision_type_mismatch",
        )

    def test_admission_gate_result_not_pass_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"admission_gate_result": "rejected"}),
            "gate_decision_not_passed",
        )

    def test_gate_status_not_admitted_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"gate_status": "rejected"}),
            "gate_status_not_admitted",
        )

    def test_source_adapter_id_mismatch_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"adapter_id": "wrong-adapter"}),
            "source_adapter_id_mismatch",
        )

    def test_source_candidate_id_mismatch_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"candidate_id": "wrong-candidate"}),
            "source_candidate_id_mismatch",
        )

    def test_source_repo_full_name_mismatch_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"repo_full_name": "wrong/repo"}),
            "source_repo_full_name_mismatch",
        )

    def test_source_identity_mismatches_are_independent(self):
        _root, decision_path, output_dir = self.make_workspace()
        payload = read_json(decision_path)
        payload.update(
            {
                "adapter_id": "wrong-adapter",
                "candidate_id": "wrong-candidate",
                "repo_full_name": "wrong/repo",
            }
        )
        write_json(decision_path, payload)

        result = self.run_promotion(decision_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("source_adapter_id_mismatch", result.rejection_reasons)
        self.assertIn("source_candidate_id_mismatch", result.rejection_reasons)
        self.assertIn("source_repo_full_name_mismatch", result.rejection_reasons)

    def test_local_fixture_admission_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"local_fixture_admission_granted": False}),
            "local_fixture_admission_not_granted",
        )

    def test_production_admission_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"production_admission_granted": True}),
            "production_admission_claimed",
        )

    def test_live_website_admission_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"live_website_admission_granted": True}),
            "live_website_admission_claimed",
        )

    def test_general_browser_automation_admission_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update(
                {"general_browser_automation_admission_granted": True}
            ),
            "general_browser_admission_claimed",
        )

    def test_any_forbidden_admission_claim_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update(
                {"arbitrary_url_navigation_admission_granted": True}
            ),
            "forbidden_admission_claimed",
        )

    def test_aggregation_evidence_supplied_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_evidence_supplied": False}),
            "aggregation_evidence_missing",
        )

    def test_aggregation_evidence_required_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_evidence_required": False}),
            "aggregation_evidence_not_required",
        )

    def test_aggregation_result_valid_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_result_valid": False}),
            "aggregation_result_not_valid",
        )

    def test_aggregation_bound_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update(
                {"local_fixture_aggregation_bound_to_admission_gate": False}
            ),
            "aggregation_not_bound_to_gate",
        )

    def test_aggregation_suite_run_count_zero_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_suite_run_count_evaluated": 0}),
            "aggregation_suite_run_threshold_not_satisfied",
        )

    def test_aggregation_failed_or_rejected_runs_reject(self):
        for field_name in (
            "aggregation_suite_run_count_failed",
            "aggregation_suite_run_count_rejected",
        ):
            with self.subTest(field_name=field_name):
                self.assert_rejects_mutation(
                    lambda payload, field_name=field_name: payload.update({field_name: 1}),
                    "aggregation_failed_or_rejected_runs_present",
                )

    def test_aggregation_pass_rate_below_perfect_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_pass_rate_bps": 9999}),
            "aggregation_pass_rate_not_perfect",
        )

    def test_aggregation_flaky_rate_nonzero_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_flaky_rate_bps": 1}),
            "aggregation_flaky_rate_nonzero",
        )

    def test_aggregation_regression_detected_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_regression_detected": True}),
            "aggregation_regression_detected",
        )

    def test_aggregation_stale_evidence_detected_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_stale_evidence_detected": True}),
            "aggregation_stale_evidence_detected",
        )

    def test_aggregation_missing_coverage_detected_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update(
                {"aggregation_missing_coverage_detected": True}
            ),
            "aggregation_missing_coverage_detected",
        )

    def test_aggregation_hashes_verified_all_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_hashes_verified_all": False}),
            "aggregation_hashes_not_verified",
        )

    def test_aggregation_boundaries_false_all_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"aggregation_boundaries_false_all": False}),
            "aggregation_boundaries_not_false",
        )

    def test_regression_evidence_required_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"regression_evidence_required": False}),
            "regression_evidence_not_required",
        )

    def test_regression_evidence_present_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"regression_evidence_present": False}),
            "regression_evidence_missing",
        )

    def test_regression_scenario_coverage_incomplete_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update(
                {"regression_scenario_coverage_complete": False}
            ),
            "regression_scenario_coverage_incomplete",
        )

    def test_artifact_hashes_verified_false_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"artifact_hashes_verified": False}),
            "artifact_hashes_not_verified",
        )

    def test_candidate_repo_files_indexed_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"candidate_repo_files_indexed": True}),
            "candidate_artifacts_present",
        )

    def test_external_candidate_artifacts_indexed_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"external_candidate_artifacts_indexed": True}),
            "candidate_artifacts_present",
        )

    def test_embedded_fixture_url_scheme_not_file_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"embedded_fixture_url_scheme": "http"}),
            "embedded_fixture_scheme_not_file",
        )

    def test_embedded_non_local_request_count_nonzero_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"embedded_non_local_request_count": 1}),
            "embedded_non_local_request_count_not_zero",
        )

    def test_required_review_fields_false_reject(self):
        cases = (
            ("required_human_review", "human_review_not_required"),
            ("required_human_approval", "human_approval_not_required"),
            ("security_review_required", "security_review_not_required"),
            ("sandbox_review_required", "sandbox_review_not_required"),
            ("production_review_required", "production_review_not_required"),
        )
        for field_name, reason in cases:
            with self.subTest(field_name=field_name):
                self.assert_rejects_mutation(
                    lambda payload, field_name=field_name: payload.update({field_name: False}),
                    reason,
                )

    def test_any_performed_forbidden_action_true_rejects(self):
        self.assert_rejects_mutation(
            lambda payload: payload.update({"external_network_performed": True}),
            "performed_forbidden_action",
        )

    def test_registry_output_symlink_rejects(self):
        root, decision_path, output_dir = self.make_workspace()
        target = root / "target-registry.json"
        target.write_text("{}", encoding="utf-8")
        registry_output = output_dir / "registry-link.json"
        registry_output.symlink_to(target)

        result = self.run_promotion(
            decision_path,
            output_dir,
            registry_output=registry_output,
        )

        self.assertFalse(result.complete)
        self.assertIn("registry_output_is_symlink", result.rejection_reasons)
        self.assertIsNone(result.result_path)

    def test_registry_output_outside_output_dir_rejects(self):
        root, decision_path, output_dir = self.make_workspace()
        result = self.run_promotion(
            decision_path,
            output_dir,
            registry_output=root / "outside-registry.json",
        )

        self.assertFalse(result.complete)
        self.assertIn("registry_output_outside_output_dir", result.rejection_reasons)
        self.assertIsNone(result.result_path)

    def test_success_preserves_production_live_general_autonomy_false(self):
        _root, decision_path, output_dir = self.make_workspace()
        result = self.run_promotion(decision_path, output_dir)
        payload = read_json(result.result_path)

        for field_name in (
            "production_admission_granted",
            "live_website_admission_granted",
            "general_browser_automation_admission_granted",
            "autonomous_execution_admission_granted",
            "production_promotion_granted",
            "autonomous_execution_performed",
        ):
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_success_includes_denied_scope_list(self):
        _root, decision_path, output_dir = self.make_workspace()
        result = self.run_promotion(decision_path, output_dir)
        payload = read_json(result.result_path)

        self.assertEqual(
            payload["denied_scope"],
            list(ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE),
        )

    def test_cli_accepts_required_args_and_emits_promotion_result(self):
        _root, decision_path, output_dir = self.make_workspace()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-admission-gated-local-adapter-registry-promotion",
                    "--admission-gate-decision",
                    decision_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--promotion-id",
                    "promotion-cli",
                    "--review-attestation",
                    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION,
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(
            Path(
                payload[
                    "admission_gated_local_adapter_registry_promotion_result_path"
                ]
            ).exists()
        )

    def test_launcher_accepts_required_args_and_emits_promotion_result(self):
        _root, decision_path, output_dir = self.make_workspace()

        result = run_admission_gated_local_adapter_registry_promotion_launcher(
            decision_path,
            output_dir,
            "promotion-launcher",
            review_attestation=ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION,
        )

        self.assertTrue(result.complete)
        self.assertTrue(
            Path(
                result.payload[
                    "admission_gated_local_adapter_registry_promotion_result_path"
                ]
            ).exists()
        )

    def test_task_graph_accepts_promotion_node_and_writes_artifact_outputs(self):
        root, decision_path, output_dir = self.make_workspace()
        graph_path = root / "graph.json"
        graph_output = root / "graph-output"
        graph_output.mkdir()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "registry-promotion-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "promote_registry",
                        "adapter_id": "admission_gated_local_adapter_registry_promotion",
                        "capability": "launch_admission_gated_local_adapter_registry_promotion",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "admission_gate_decision": decision_path.as_posix(),
                            "output_dir": output_dir.as_posix(),
                            "promotion_id": "promotion-graph",
                            "review_attestation": ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION,
                        },
                    }
                ],
            },
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)

        self.assertTrue(result.success)
        node = execution_manifest["nodes"][0]
        self.assertTrue(
            node["admission_gated_local_adapter_registry_promotion_complete"]
        )
        roles = {
            artifact["artifact_role"]
            for artifact in artifact_outputs["artifacts"]
            if artifact["node_id"] == "promote_registry"
        }
        self.assertIn("admission_gated_local_adapter_registry_promotion_result", roles)
        self.assertIn("artifact_index", roles)
        self.assertIn("artifact_index_manifest", roles)

    def test_module_source_contains_no_forbidden_execution_or_cli_tokens(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden_tokens = (
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
        )

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_decision_doc_exists_and_states_non_production_local_only_boundary(self):
        self.assertTrue(DECISION_DOC.exists())
        text = DECISION_DOC.read_text(encoding="utf-8")

        for phrase in (
            "promoting only a #427 aggregation-bound local-fixture gate pass",
            "not production promotion",
            "does not enable production",
            "does not enable live websites",
            "does not enable general browser automation",
            "does not enable arbitrary URLs",
            "does not enable account/login/registration flows",
            "does not enable scraping",
            "does not enable bypass/captcha",
            "does not access secrets/cookies",
            "does not run npm/npx/install/browser download",
            "does not execute Playwright",
            "does not execute #422",
            "does not execute #424",
            "does not execute #425",
            "does not execute #426",
            "does not execute #427",
            "does not execute candidate repository code",
            "does not grant autonomy",
            "local_fixture_only",
            "human_review_required",
            "aggregation_bound",
            "non_production",
            "separate policy, legal, network, credential, and human-approval gates",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
