import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.playwright_local_admission_receipt_aggregation import (
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE,
    build_playwright_local_admission_receipt_aggregation_plan,
    run_playwright_local_admission_receipt_aggregation,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.local_launcher import (
    run_playwright_local_admission_receipt_aggregation_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

AGGREGATION_PLAN_OUTPUTS = {
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE,
}
AGGREGATION_ALL_OUTPUTS = AGGREGATION_PLAN_OUTPUTS | {
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE,
}
CORE_SCENARIOS = (
    "static_click_marker",
    "repeated_local_fixture_execution_a",
    "repeated_local_fixture_execution_b",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class PlaywrightLocalAdmissionReceiptAggregationTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name).resolve()
        output_dir = root / "aggregation-output"
        output_dir.mkdir()
        manifest_path = root / "suite-run-dirs.json"
        return root, manifest_path, output_dir

    def suite_dirs_manifest(self, path, suite_run_dirs):
        write_json(
            path,
            {
                "manifest_type": "playwright_local_fixture_suite_run_dirs_manifest_v1",
                "suite_run_dirs": [Path(item).as_posix() for item in suite_run_dirs],
            },
        )
        return path

    def run_aggregation(self, manifest_path, output_dir, **kwargs):
        return run_playwright_local_admission_receipt_aggregation(
            manifest_path,
            output_dir,
            kwargs.pop("aggregation_id", "aggregation-001"),
            review_attestation=kwargs.pop(
                "review_attestation",
                PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
            ),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop("operator_notes", "local fixture only"),
            **kwargs,
        )

    def build_plan(self, manifest_path, output_dir, **kwargs):
        return build_playwright_local_admission_receipt_aggregation_plan(
            manifest_path,
            output_dir,
            kwargs.pop("aggregation_id", "aggregation-001"),
            review_attestation=kwargs.pop(
                "review_attestation",
                PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
            ),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop("operator_notes", "local fixture only"),
            **kwargs,
        )

    def make_suite_run(
        self,
        root,
        name,
        *,
        scenario_statuses=None,
        scenario_ids=CORE_SCENARIOS,
        suite_success=None,
    ):
        suite_dir = root / name
        suite_dir.mkdir()
        scenario_statuses = dict(scenario_statuses or {})
        scenario_results = []
        scenario_result_paths = []
        for scenario_id in scenario_ids:
            scenario_dir = suite_dir / "scenarios" / scenario_id
            scenario_dir.mkdir(parents=True)
            success = scenario_statuses.get(scenario_id, True)
            scenario_payload = {
                "scenario_id": scenario_id,
                "scenario_type": scenario_id,
                "scenario_dir": scenario_dir.as_posix(),
                "success": success,
                "failure_reasons": [] if success else ["synthetic_failure"],
                "candidate_repo_files_indexed": False,
                "external_candidate_artifacts_indexed": False,
                "all_boundaries_false": True,
                "artifact_hashes_verified": True,
            }
            scenario_result_path = scenario_dir / "scenario_result.json"
            write_json(scenario_result_path, scenario_payload)
            scenario_result_paths.append(scenario_result_path)
            scenario_results.append(scenario_payload)
        passed = sum(1 for item in scenario_results if item["success"])
        failed = len(scenario_results) - passed
        if suite_success is None:
            suite_success = failed == 0
        plan_path = suite_dir / "local_only_playwright_fixture_scenario_suite_plan.json"
        result_path = suite_dir / "local_only_playwright_fixture_scenario_suite_result.json"
        manifest_path = suite_dir / "local_only_playwright_fixture_scenario_suite_manifest.json"
        summary_path = suite_dir / "local_only_playwright_fixture_scenario_suite_summary.md"
        checklist_path = suite_dir / "local_only_playwright_fixture_scenario_suite_checklist.md"
        artifact_index_path = suite_dir / "artifact_index.json"
        artifact_index_manifest_path = suite_dir / "artifact_index_manifest.json"
        false_fields = {}
        false_fields.update(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS)
        false_fields.update(
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS
        )
        plan = {
            "suite_type": "local_only_playwright_fixture_scenario_suite_v1",
            "suite_id": name,
            "local_execution_scope": "file_fixture_only",
            "fixture_url_scheme": "file",
            "selected_candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "required_human_review": True,
            "required_human_approval": True,
            **false_fields,
        }
        result = {
            "result_type": "local_only_playwright_fixture_scenario_suite_result_v1",
            "suite_id": name,
            "scenario_set": "core",
            "scenario_count_planned": len(scenario_results),
            "scenario_count_executed": len(scenario_results),
            "scenario_count_passed": passed,
            "scenario_count_failed": failed,
            "scenario_results": scenario_results,
            "suite_success": suite_success,
            "suite_status": "local_only_playwright_fixture_scenario_suite_completed"
            if suite_success
            else "local_only_playwright_fixture_scenario_suite_failed",
            "suite_decision": "local_only_playwright_fixture_scenario_suite_passed"
            if suite_success
            else "fix_local_only_playwright_fixture_scenario_suite_and_retry",
            "next_allowed_action": "review_local_only_playwright_fixture_scenario_suite"
            if suite_success
            else "fix_local_only_playwright_fixture_scenario_suite_and_retry",
            "selected_candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "local_execution_scope": "file_fixture_only",
            "fixture_url_scheme": "file",
            "required_human_review": True,
            "required_human_approval": True,
            **false_fields,
        }
        write_json(plan_path, plan)
        write_json(result_path, result)
        summary_path.write_text("suite summary\n", encoding="utf-8")
        checklist_path.write_text("suite checklist\n", encoding="utf-8")
        manifest = {
            "manifest_type": "local_only_playwright_fixture_scenario_suite_manifest_v1",
            "suite_id": name,
            "job_dir": suite_dir.as_posix(),
            "plan_path": plan_path.as_posix(),
            "plan_sha256": sha256_file(plan_path),
            "result_path": result_path.as_posix(),
            "result_sha256": sha256_file(result_path),
            "summary_path": summary_path.as_posix(),
            "summary_sha256": sha256_file(summary_path),
            "checklist_path": checklist_path.as_posix(),
            "checklist_sha256": sha256_file(checklist_path),
            "suite_success": suite_success,
            "local_execution_scope": "file_fixture_only",
            "fixture_url_scheme": "file",
            "required_human_review": True,
            "required_human_approval": True,
            **false_fields,
        }
        write_json(manifest_path, manifest)
        artifact_paths = [
            ("suite_plan", plan_path),
            ("suite_result", result_path),
            ("suite_manifest", manifest_path),
            ("suite_summary", summary_path),
            ("suite_checklist", checklist_path),
        ] + [
            ("scenario_result_" + str(index), path)
            for index, path in enumerate(scenario_result_paths, start=1)
        ]
        artifact_index = {
            "index_type": "local_only_playwright_fixture_scenario_suite_artifact_index_v1",
            "job_dir": suite_dir.as_posix(),
            "indexed_artifacts": len(artifact_paths),
            "entries": [
                {
                    "artifact_role": role,
                    "artifact_name": role,
                    "path": path.as_posix(),
                    "relative_path": path.relative_to(suite_dir).as_posix(),
                    "exists": True,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "candidate_repo_file": False,
                    "external_candidate_artifact": False,
                }
                for role, path in artifact_paths
            ],
            "candidate_repo_files_indexed": False,
            "external_candidate_artifacts_indexed": False,
            "required_human_review": True,
            "required_human_approval": True,
            **false_fields,
        }
        write_json(artifact_index_path, artifact_index)
        artifact_index_manifest = {
            "manifest_type": "local_only_playwright_fixture_scenario_suite_artifact_index_manifest_v1",
            "job_dir": suite_dir.as_posix(),
            "artifact_index_path": artifact_index_path.as_posix(),
            "artifact_index_sha256": sha256_file(artifact_index_path),
            "indexed_artifacts": len(artifact_paths),
            "candidate_repo_files_indexed": False,
            "external_candidate_artifacts_indexed": False,
            "required_human_review": True,
            "required_human_approval": True,
            **false_fields,
        }
        write_json(artifact_index_manifest_path, artifact_index_manifest)
        return suite_dir

    def refresh_suite_hashes(self, suite_dir):
        manifest_path = suite_dir / "local_only_playwright_fixture_scenario_suite_manifest.json"
        if manifest_path.exists() and not manifest_path.is_symlink():
            manifest = read_json(manifest_path)
            for prefix in ("plan", "result", "summary", "checklist"):
                path = Path(manifest[prefix + "_path"])
                manifest[prefix + "_sha256"] = sha256_file(path)
            write_json(manifest_path, manifest)
        artifact_index_path = suite_dir / "artifact_index.json"
        if artifact_index_path.exists() and not artifact_index_path.is_symlink():
            artifact_index = read_json(artifact_index_path)
            for entry in artifact_index["entries"]:
                path = Path(entry["path"])
                if path.exists() and path.is_file():
                    entry["sha256"] = sha256_file(path)
                    entry["size_bytes"] = path.stat().st_size
            write_json(artifact_index_path, artifact_index)
        artifact_index_manifest_path = suite_dir / "artifact_index_manifest.json"
        if artifact_index_manifest_path.exists() and not artifact_index_manifest_path.is_symlink():
            artifact_index_manifest = read_json(artifact_index_manifest_path)
            artifact_index_manifest["artifact_index_sha256"] = sha256_file(
                artifact_index_path
            )
            write_json(artifact_index_manifest_path, artifact_index_manifest)

    def assert_false_fields(self, payload):
        for field_name in PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def assert_no_aggregation_artifacts(self, output_dir):
        for name in AGGREGATION_ALL_OUTPUTS:
            self.assertFalse((Path(output_dir) / name).exists(), name)
            self.assertFalse((Path(output_dir) / name).is_symlink(), name)

    def valid_two_run_workspace(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        return root, manifest_path, output_dir, suite_a, suite_b

    def test_A_plan_only_writes_plan_artifacts_without_evaluating_suite_runs(self):
        root, manifest_path, output_dir = self.workspace()
        missing_a = root / "missing-a"
        missing_b = root / "missing-b"
        self.suite_dirs_manifest(manifest_path, [missing_a, missing_b])
        result = self.build_plan(manifest_path, output_dir)
        self.assertTrue(result.complete)
        self.assertIsNone(result.result_path)
        for name in AGGREGATION_PLAN_OUTPUTS:
            self.assertTrue((output_dir / name).is_file(), name)
        self.assertFalse((output_dir / PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE).exists())

    def test_B_valid_two_suite_run_dirs_aggregate_successfully(self):
        _root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertTrue(result.complete)
        self.assertTrue(payload["aggregate_success"])
        self.assertEqual(payload["suite_run_count_passed"], 2)
        self.assertEqual(payload["pass_rate_bps"], 10000)

    def test_C_minimum_suite_run_threshold_rejects_one_run(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        self.suite_dirs_manifest(manifest_path, [suite_a])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertFalse(payload["minimum_suite_runs_satisfied"])

    def test_D_failed_suite_run_rejects_aggregate(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(
            root,
            "suite-run-002",
            scenario_statuses={"static_click_marker": False},
        )
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertEqual(payload["suite_run_count_failed"], 1)
        self.assertLess(payload["pass_rate_bps"], 10000)

    def test_E_flaky_scenario_rejects_aggregate(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(
            root,
            "suite-run-001",
            scenario_statuses={"static_click_marker": False},
        )
        suite_b = self.make_suite_run(root, "suite-run-002")
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(
            manifest_path,
            output_dir,
            minimum_pass_rate_bps=0,
        )
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("static_click_marker", payload["flaky_scenario_ids"])
        self.assertFalse(payload["regression_detected"])

    def test_F_regression_sequence_rejects_aggregate(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(
            root,
            "suite-run-002",
            scenario_statuses={"static_click_marker": False},
        )
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(
            manifest_path,
            output_dir,
            minimum_pass_rate_bps=0,
            maximum_flaky_rate_bps=10000,
        )
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertTrue(payload["regression_detected"])

    def test_G_missing_core_scenario_coverage_rejects_aggregate(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(
            root,
            "suite-run-002",
            scenario_ids=("static_click_marker", "repeated_local_fixture_execution_a"),
        )
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertTrue(payload["missing_coverage_detected"])

    def test_H_stale_evidence_rejects_aggregate_when_age_metadata_exists(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        result_payload = read_json(
            suite_b / "local_only_playwright_fixture_scenario_suite_result.json"
        )
        result_payload["evidence_age_days"] = 31
        write_json(
            suite_b / "local_only_playwright_fixture_scenario_suite_result.json",
            result_payload,
        )
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertTrue(payload["stale_evidence_detected"])

    def test_I_suite_run_dir_symlink_blocks(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        real_suite_b = self.make_suite_run(root, "suite-run-real")
        suite_b = root / "suite-run-link"
        suite_b.symlink_to(real_suite_b, target_is_directory=True)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertTrue(payload["suite_run_results"][1]["rejected"])
        self.assertIn("suite_run_dir_must_not_be_symlink", payload["suite_run_results"][1]["rejection_reasons"])

    def test_J_suite_run_manifest_path_symlink_blocks(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        manifest = suite_b / "local_only_playwright_fixture_scenario_suite_manifest.json"
        real_manifest = suite_b / "real-suite-manifest.json"
        manifest.rename(real_manifest)
        manifest.symlink_to(real_manifest)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("suite_manifest_must_not_be_symlink", payload["suite_run_results"][1]["rejection_reasons"])

    def test_K_suite_artifact_index_path_outside_suite_dir_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        outside = root / "outside.json"
        write_json(outside, {"outside": True})
        index_path = suite_b / "artifact_index.json"
        index = read_json(index_path)
        index["entries"][0]["path"] = outside.as_posix()
        index["entries"][0]["sha256"] = sha256_file(outside)
        write_json(index_path, index)
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("artifact_index_path_outside_suite_dir", payload["suite_run_results"][1]["rejection_reasons"])

    def test_L_indexed_symlink_path_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        target = suite_b / "local_only_playwright_fixture_scenario_suite_summary.md"
        link = suite_b / "summary-link.md"
        link.symlink_to(target)
        index_path = suite_b / "artifact_index.json"
        index = read_json(index_path)
        index["entries"][0]["path"] = link.as_posix()
        index["entries"][0]["sha256"] = sha256_file(link)
        write_json(index_path, index)
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("artifact_index_symlink_path", payload["suite_run_results"][1]["rejection_reasons"])

    def test_M_hash_mismatch_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        (suite_b / "local_only_playwright_fixture_scenario_suite_summary.md").write_text(
            "changed\n",
            encoding="utf-8",
        )
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("artifact_hash_mismatch", payload["suite_run_results"][1]["rejection_reasons"])

    def test_N_candidate_repo_files_indexed_true_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        index_path = suite_b / "artifact_index.json"
        index = read_json(index_path)
        index["candidate_repo_files_indexed"] = True
        write_json(index_path, index)
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("candidate_repo_files_indexed", payload["suite_run_results"][1]["rejection_reasons"])

    def test_O_external_candidate_artifacts_indexed_true_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        index_path = suite_b / "artifact_index.json"
        index = read_json(index_path)
        index["external_candidate_artifacts_indexed"] = True
        write_json(index_path, index)
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("external_candidate_artifacts_indexed", payload["suite_run_results"][1]["rejection_reasons"])

    def test_P_live_prod_general_admission_true_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        result_path = suite_b / "local_only_playwright_fixture_scenario_suite_result.json"
        payload = read_json(result_path)
        payload["live_website_admission_granted"] = True
        write_json(result_path, payload)
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        aggregation = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("boundary_false_field_true", aggregation["suite_run_results"][1]["rejection_reasons"])

    def test_Q_forbidden_boundary_true_rejects(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        suite_b = self.make_suite_run(root, "suite-run-002")
        plan_path = suite_b / "local_only_playwright_fixture_scenario_suite_plan.json"
        payload = read_json(plan_path)
        payload["candidate_code_execution_performed"] = True
        write_json(plan_path, payload)
        self.refresh_suite_hashes(suite_b)
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_b])
        result = self.run_aggregation(manifest_path, output_dir)
        aggregation = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertIn("boundary_false_field_true", aggregation["suite_run_results"][1]["rejection_reasons"])

    def test_R_duplicate_suite_run_dirs_rejected(self):
        root, manifest_path, output_dir = self.workspace()
        suite_a = self.make_suite_run(root, "suite-run-001")
        self.suite_dirs_manifest(manifest_path, [suite_a, suite_a])
        result = self.run_aggregation(
            manifest_path,
            output_dir,
            minimum_pass_rate_bps=0,
        )
        payload = read_json(result.result_path)
        self.assertFalse(result.complete)
        self.assertEqual(payload["suite_run_count_rejected"], 2)
        self.assertIn("duplicate_suite_run_dir", payload["suite_run_results"][0]["rejection_reasons"])

    def test_S_wrong_attestation_fails_closed_with_no_artifacts(self):
        _root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        result = self.run_aggregation(
            manifest_path,
            output_dir,
            review_attestation="WRONG",
        )
        self.assertFalse(result.complete)
        self.assert_no_aggregation_artifacts(output_dir)

    def test_T_sensitive_attestation_redacted(self):
        _root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        bad = "SECRET_TOKEN_PASSWORD_CREDENTIAL_API_KEY_COOKIE_BAD"
        result = self.run_aggregation(
            manifest_path,
            output_dir,
            review_attestation=bad,
            operator_notes=bad,
        )
        serialized = json.dumps(result.payload, sort_keys=True)
        self.assertNotIn(bad, serialized)
        self.assertNotIn("SECRET_TOKEN_PASSWORD", serialized)
        self.assert_no_aggregation_artifacts(output_dir)

    def test_U_cli_plan_only_works(self):
        root, manifest_path, output_dir = self.workspace()
        self.suite_dirs_manifest(manifest_path, [root / "missing-a", root / "missing-b"])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-playwright-local-admission-receipt-aggregation",
                    "--suite-run-dirs",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--aggregation-id",
                    "aggregation-cli-001",
                    "--review-attestation",
                    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
                    "--plan-only",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["evaluated"])

    def test_V_cli_aggregation_works(self):
        _root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-playwright-local-admission-receipt-aggregation",
                    "--suite-run-dirs",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--aggregation-id",
                    "aggregation-cli-001",
                    "--review-attestation",
                    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(payload["local_fixture_aggregation_passed"])

    def test_W_launcher_payload_preserves_false_fields(self):
        _root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        launcher_result = run_playwright_local_admission_receipt_aggregation_launcher(
            manifest_path,
            output_dir,
            "aggregation-launcher-001",
            review_attestation=PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
        )
        for path in (
            launcher_result.payload["playwright_local_admission_receipt_aggregation_plan_path"],
            launcher_result.payload["playwright_local_admission_receipt_aggregation_manifest_path"],
            launcher_result.payload["playwright_local_admission_receipt_aggregation_result_path"],
            launcher_result.payload["artifact_index_path"],
            launcher_result.payload["artifact_index_manifest_path"],
        ):
            self.assert_false_fields(read_json(path))
        self.assert_false_fields(launcher_result.to_cli_payload())

    def test_X_task_graph_node_writes_artifact_outputs(self):
        root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        graph_output = root / "graph-output"
        graph_output.mkdir()
        graph_path = root / "graph.json"
        write_json(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "playwright-local-aggregation-graph",
                "authority": "non_authority",
                "required_human_approval": True,
                "execution_mode": "fixture_execution",
                "nodes": [
                    {
                        "node_id": "aggregation",
                        "adapter_id": "playwright_local_admission_receipt_aggregation",
                        "capability": "launch_playwright_local_admission_receipt_aggregation",
                        "depends_on": [],
                        "execution_mode": "fixture",
                        "approval_checkpoint_required": True,
                        "approval_checkpoint_id": "aggregation:human_review",
                        "inputs": {
                            "suite_run_dirs": manifest_path.as_posix(),
                            "output_dir": output_dir.as_posix(),
                            "aggregation_id": "graph-aggregation-001",
                            "review_attestation": PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION,
                        },
                    }
                ],
            },
        )
        result = run_local_task_graph_fixture(graph_path, graph_output)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        roles = {artifact["artifact_role"] for artifact in artifact_outputs["artifacts"]}
        self.assertTrue(result.success)
        self.assertIn("playwright_local_admission_receipt_aggregation_plan", roles)
        self.assertIn("playwright_local_admission_receipt_aggregation_result", roles)

    def test_Y_source_contains_no_disallowed_execution_or_cli_paths(self):
        source = (
            REPO_ROOT
            / "kernel"
            / "capabilities"
            / "playwright_local_admission_receipt_aggregation.py"
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

    def test_Z_aggregation_never_claims_production_live_or_general_readiness(self):
        _root, manifest_path, output_dir, _suite_a, _suite_b = self.valid_two_run_workspace()
        result = self.run_aggregation(manifest_path, output_dir)
        payload = read_json(result.result_path)
        self.assertTrue(payload["aggregate_success"])
        self.assertFalse(payload["production_admission_granted"])
        self.assertFalse(payload["live_website_admission_granted"])
        self.assertFalse(payload["general_browser_automation_admission_granted"])
        self.assertNotIn("production", payload["next_allowed_action"])


if __name__ == "__main__":
    unittest.main()
