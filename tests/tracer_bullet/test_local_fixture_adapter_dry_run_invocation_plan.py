import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.local_fixture_adapter_dry_run_invocation_plan import (
    LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS,
    LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS,
    LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_MATERIALIZED_FALSE_FIELDS,
    LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION,
    run_local_fixture_adapter_dry_run_invocation_plan,
)
from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionStatus,
    AdapterCapabilityRequest,
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.adapter_registry import (
    admit_adapter_capability,
    find_adapter_entry,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_local_fixture_adapter_dry_run_invocation_plan_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.product_health_check import build_product_health_report
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_adapter_dry_run_invocation_plan.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_adapter_dry_run_invocation_plan_v1.md"
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalFixtureAdapterDryRunInvocationPlanTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        usage_output = root / "usage-output"
        usage_output.mkdir()
        plan_output = root / "plan-output"
        plan_output.mkdir()
        fixture_path = usage_output / "fixture.html"
        fixture_path.write_text(
            "<!doctype html><title>fixture</title>\n",
            encoding="utf-8",
        )
        receipt_path = usage_output / "local_fixture_adapter_usage_receipt_result.json"
        write_json_atomically(
            receipt_path,
            self.valid_usage_receipt_result(usage_output, fixture_path),
        )
        return root, receipt_path, plan_output, fixture_path, usage_output

    def valid_usage_receipt_result(self, usage_output, fixture_path):
        payload = {
            "receipt_type": "local_fixture_adapter_usage_receipt_v1",
            "authority": "non_authority_local_fixture_usage_receipt_record",
            "execution_capability": "local_fixture_adapter_usage_receipt_only",
            "usage_receipt_id": "usage-001",
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "promotion_result_path": (usage_output / "promotion-result.json").as_posix(),
            "promotion_result_sha256": "b" * 64,
            "promotion_type": "admission_gated_local_adapter_registry_promotion_v1",
            "promotion_status": "local_fixture_adapter_usage_receipt_completed",
            "promotion_decision": "record_one_local_fixture_adapter_usage_receipt",
            "source_gate_decision_type": "local_fixture_playwright_adapter_admission_gate_decision_v1",
            "source_gate_decision_sha256": "a" * 64,
            "source_gate_passed": True,
            "registry_promotion_granted": True,
            "promotion_validated": True,
            "registry_entry_validated": False,
            "aggregation_bound": True,
            "regression_bound": True,
            "local_fixture_only": True,
            "one_usage_receipt_only": True,
            "local_fixture_reference": fixture_path.as_posix(),
            "local_fixture_reference_scheme": "file",
            "local_fixture_path": fixture_path.as_posix(),
            "local_fixture_sha256": sha256_file(fixture_path),
            "local_fixture_exists": True,
            "local_fixture_regular_file": True,
            "local_fixture_symlink_detected": False,
            "local_fixture_under_allowed_root": True,
            "human_review_required": True,
            "required_human_approval": True,
            "non_production": True,
            "production_adapter": False,
            "usage_receipt_granted": True,
            "complete": True,
            "rejected": False,
            "rejection_reasons": [],
            "next_allowed_action": "human_review_local_fixture_usage_receipt_before_any_execution",
            "output_dir": usage_output.as_posix(),
            "no_live_website": True,
            "no_general_browser_automation": True,
            "no_autonomy": True,
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS
            }
        )
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS
            }
        )
        payload["production_promotion_granted"] = False
        return payload

    def run_plan(
        self,
        receipt_path,
        plan_output,
        *,
        review_attestation=LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION,
    ):
        return run_local_fixture_adapter_dry_run_invocation_plan(
            receipt_path,
            plan_output,
            "plan-001",
            review_attestation=review_attestation,
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="reviewed #429 usage receipt for dry-run plan",
        )

    def assert_rejects_receipt_mutation(self, mutator, reason):
        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        payload = read_json(receipt_path)
        mutator(payload)
        write_json(receipt_path, payload)

        result = self.run_plan(receipt_path, plan_output)

        self.assertFalse(result.complete)
        self.assertIn(reason, result.rejection_reasons)
        self.assertTrue(result.result_path.exists())
        self.assertIn(reason, read_json(result.result_path)["rejection_reasons"])

    def test_valid_usage_receipt_plus_existing_fixture_writes_dry_run_plan(self):
        _root, receipt_path, plan_output, fixture_path, _usage_output = (
            self.make_workspace()
        )

        result = self.run_plan(receipt_path, plan_output)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertEqual(
            payload["plan_type"],
            "local_fixture_adapter_dry_run_invocation_plan_v1",
        )
        self.assertEqual(payload["invocation_plan_id"], "plan-001")
        self.assertEqual(payload["adapter_id"], "bounded_playwright_worker_adapter_draft")
        self.assertEqual(payload["candidate_id"], "github-candidate-microsoft-playwright-v1")
        self.assertEqual(payload["repo_full_name"], "microsoft/playwright")
        self.assertEqual(payload["usage_receipt_path"], receipt_path.as_posix())
        self.assertEqual(payload["usage_receipt_sha256"], sha256_file(receipt_path))
        self.assertEqual(payload["usage_receipt_type"], "local_fixture_adapter_usage_receipt_v1")
        self.assertTrue(payload["usage_receipt_validated"])
        self.assertTrue(payload["usage_receipt_granted"])
        self.assertTrue(payload["registry_promotion_granted"])
        self.assertTrue(payload["aggregation_bound"])
        self.assertTrue(payload["regression_bound"])
        self.assertTrue(payload["local_fixture_only"])
        self.assertTrue(payload["one_usage_receipt_bound"])
        self.assertTrue(payload["dry_run_plan_only"])
        self.assertTrue(payload["invocation_plan_granted"])
        self.assertEqual(payload["local_fixture_sha256"], sha256_file(fixture_path))
        self.assertTrue(payload["local_fixture_revalidated"])
        self.assertTrue(payload["local_fixture_exists"])
        self.assertTrue(payload["local_fixture_regular_file"])
        self.assertFalse(payload["local_fixture_symlink_detected"])
        self.assertTrue(payload["local_fixture_under_allowed_root"])
        self.assertEqual(
            payload["local_fixture_allowed_root"],
            receipt_path.parent.as_posix(),
        )
        self.assertEqual(
            payload["invocation_plan_status"],
            "local_fixture_adapter_dry_run_invocation_plan_completed",
        )
        self.assertEqual(
            payload["invocation_plan_decision"],
            "record_dry_run_invocation_plan_only",
        )
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_dry_run_invocation_plan_before_any_execution_gate",
        )
        for path in (
            result.plan_path,
            result.result_path,
            result.manifest_path,
            result.summary_path,
            result.checklist_path,
            result.artifact_index_path,
            result.artifact_index_manifest_path,
        ):
            self.assertTrue(path.exists(), path)

    def test_usage_receipt_file_shape_rejections_are_deterministic(self):
        root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        missing = root / "missing-result.json"
        result = self.run_plan(missing, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("usage_receipt_path_missing", result.rejection_reasons)

        root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        symlink_path = root / "receipt-link.json"
        symlink_path.symlink_to(receipt_path)
        result = self.run_plan(symlink_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("usage_receipt_path_is_symlink", result.rejection_reasons)

        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        receipt_path.write_text("{", encoding="utf-8")
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("usage_receipt_not_json_object", result.rejection_reasons)

    def test_required_usage_receipt_fields_reject_fail_closed(self):
        cases = (
            (lambda payload: payload.update({"receipt_type": "wrong"}), "usage_receipt_type_mismatch"),
            (lambda payload: payload.update({"promotion_status": "wrong"}), "usage_receipt_status_not_completed"),
            (lambda payload: payload.update({"promotion_decision": "wrong"}), "usage_receipt_decision_mismatch"),
            (lambda payload: payload.update({"usage_receipt_granted": False}), "usage_receipt_not_granted"),
            (lambda payload: payload.update({"promotion_validated": False}), "usage_receipt_not_validated"),
            (lambda payload: payload.update({"registry_promotion_granted": False}), "registry_promotion_not_granted"),
            (lambda payload: payload.update({"production_promotion_granted": True}), "production_promotion_claimed"),
            (lambda payload: payload.update({"source_gate_passed": False}), "source_gate_not_passed"),
            (lambda payload: payload.update({"source_gate_decision_type": "wrong"}), "source_gate_decision_type_mismatch"),
            (lambda payload: payload.update({"source_gate_decision_sha256": ""}), "source_gate_decision_sha_missing"),
            (lambda payload: payload.update({"promotion_type": "wrong"}), "promotion_type_mismatch"),
            (lambda payload: payload.update({"promotion_result_sha256": ""}), "promotion_result_sha_missing"),
            (lambda payload: payload.update({"adapter_id": "wrong-adapter"}), "source_adapter_id_mismatch"),
            (lambda payload: payload.update({"candidate_id": "wrong-candidate"}), "source_candidate_id_mismatch"),
            (lambda payload: payload.update({"repo_full_name": "wrong/repo"}), "source_repo_full_name_mismatch"),
            (lambda payload: payload.update({"aggregation_bound": False}), "aggregation_not_bound"),
            (lambda payload: payload.update({"regression_bound": False}), "regression_not_bound"),
            (lambda payload: payload.update({"local_fixture_only": False}), "local_fixture_only_not_true"),
            (lambda payload: payload.update({"one_usage_receipt_only": False}), "one_usage_receipt_only_not_true"),
            (lambda payload: payload.update({"human_review_required": False}), "human_review_not_required"),
            (lambda payload: payload.update({"required_human_approval": False}), "human_approval_not_required"),
            (lambda payload: payload.update({"non_production": False}), "non_production_not_true"),
            (lambda payload: payload.update({"production_adapter": True}), "production_adapter_claimed"),
            (lambda payload: payload.update({"live_website_admission_granted": True}), "forbidden_admission_claimed"),
            (lambda payload: payload.update({"external_network_performed": True}), "performed_forbidden_action"),
            (lambda payload: payload.update({"executable_command_materialized": True}), "executable_material_claimed"),
        )
        for mutator, reason in cases:
            with self.subTest(reason=reason):
                self.assert_rejects_receipt_mutation(mutator, reason)

    def test_missing_performed_false_fields_reject(self):
        for field_name in (
            "external_network_performed",
            "adapter_execution_performed",
            "playwright_execution_performed",
        ):
            with self.subTest(field_name=field_name):
                self.assert_rejects_receipt_mutation(
                    lambda payload, field_name=field_name: payload.pop(field_name),
                    "performed_forbidden_action",
                )

    def test_local_fixture_receipt_metadata_rejections_are_deterministic(self):
        cases = (
            (lambda payload: payload.update({"local_fixture_reference": ""}), "local_fixture_reference_missing"),
            (lambda payload: payload.update({"local_fixture_reference_scheme": "https"}), "local_fixture_reference_forbidden_scheme"),
            (lambda payload: payload.update({"local_fixture_path": ""}), "local_fixture_path_missing"),
            (lambda payload: payload.update({"local_fixture_sha256": ""}), "local_fixture_sha_missing"),
        )
        for mutator, reason in cases:
            with self.subTest(reason=reason):
                self.assert_rejects_receipt_mutation(mutator, reason)

    def test_usage_receipt_output_dir_mismatch_rejects_without_fixture_mutation(self):
        root, receipt_path, plan_output, _fixture_path, usage_output = (
            self.make_workspace()
        )
        payload = read_json(receipt_path)
        payload["output_dir"] = root.as_posix()
        write_json(receipt_path, payload)

        result = self.run_plan(receipt_path, plan_output)
        result_payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertIn(
            "usage_receipt_output_dir_mismatch",
            result.rejection_reasons,
        )
        self.assertNotIn(
            "local_fixture_path_outside_allowed_root",
            result.rejection_reasons,
        )
        self.assertEqual(
            result_payload["local_fixture_allowed_root"],
            usage_output.as_posix(),
        )
        self.assertTrue(result_payload["local_fixture_revalidated"])

    def test_widened_usage_receipt_output_dir_cannot_admit_outside_fixture(self):
        root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        outside_fixture = root / "outside.html"
        outside_fixture.write_text("<!doctype html>\n", encoding="utf-8")
        payload = read_json(receipt_path)
        payload["output_dir"] = root.as_posix()
        payload["local_fixture_path"] = outside_fixture.as_posix()
        payload["local_fixture_sha256"] = sha256_file(outside_fixture)
        write_json(receipt_path, payload)

        result = self.run_plan(receipt_path, plan_output)

        self.assertFalse(result.complete)
        self.assertIn(
            "usage_receipt_output_dir_mismatch",
            result.rejection_reasons,
        )
        self.assertIn(
            "local_fixture_path_outside_allowed_root",
            result.rejection_reasons,
        )

    def test_local_fixture_revalidation_rejections_are_deterministic(self):
        root, receipt_path, plan_output, fixture_path, _usage_output = (
            self.make_workspace()
        )
        fixture_path.unlink()
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("local_fixture_path_missing", result.rejection_reasons)

        root, receipt_path, plan_output, fixture_path, usage_output = (
            self.make_workspace()
        )
        symlink_fixture = usage_output / "fixture-link.html"
        symlink_fixture.symlink_to(fixture_path)
        payload = read_json(receipt_path)
        payload["local_fixture_path"] = symlink_fixture.as_posix()
        write_json(receipt_path, payload)
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("local_fixture_path_is_symlink", result.rejection_reasons)

        root, receipt_path, plan_output, _fixture_path, usage_output = (
            self.make_workspace()
        )
        fixture_dir = usage_output / "fixture-dir"
        fixture_dir.mkdir()
        payload = read_json(receipt_path)
        payload["local_fixture_path"] = fixture_dir.as_posix()
        write_json(receipt_path, payload)
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("local_fixture_path_not_regular_file", result.rejection_reasons)

        root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        outside_fixture = root / "outside.html"
        outside_fixture.write_text("<!doctype html>\n", encoding="utf-8")
        payload = read_json(receipt_path)
        payload["local_fixture_path"] = outside_fixture.as_posix()
        payload["local_fixture_sha256"] = sha256_file(outside_fixture)
        write_json(receipt_path, payload)
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn(
            "local_fixture_path_outside_allowed_root",
            result.rejection_reasons,
        )

        root, receipt_path, plan_output, _fixture_path, usage_output = (
            self.make_workspace()
        )
        target_dir = root / "target-dir"
        target_dir.mkdir()
        linked_fixture = target_dir / "fixture.html"
        linked_fixture.write_text("<!doctype html>\n", encoding="utf-8")
        link_dir = usage_output / "link-dir"
        link_dir.symlink_to(target_dir)
        payload = read_json(receipt_path)
        payload["local_fixture_path"] = (link_dir / "fixture.html").as_posix()
        payload["local_fixture_sha256"] = sha256_file(linked_fixture)
        write_json(receipt_path, payload)
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn(
            "local_fixture_path_has_symlink_component",
            result.rejection_reasons,
        )

        _root, receipt_path, plan_output, fixture_path, _usage_output = (
            self.make_workspace()
        )
        fixture_path.write_text("changed\n", encoding="utf-8")
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("local_fixture_sha_mismatch", result.rejection_reasons)

    def test_usage_manifest_and_artifact_index_hash_mismatch_reject(self):
        _root, receipt_path, plan_output, _fixture_path, usage_output = (
            self.make_workspace()
        )
        manifest_path = usage_output / "local_fixture_adapter_usage_receipt_manifest.json"
        write_json(
            manifest_path,
            {
                "result_path": receipt_path.as_posix(),
                "result_sha256": "0" * 64,
            },
        )
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("usage_manifest_hash_mismatch", result.rejection_reasons)

        _root, receipt_path, plan_output, _fixture_path, usage_output = (
            self.make_workspace()
        )
        artifact_index_path = usage_output / "artifact_index.json"
        write_json(
            artifact_index_path,
            {
                "entries": [
                    {
                        "path": receipt_path.as_posix(),
                        "sha256": "0" * 64,
                        "candidate_repo_file": False,
                        "external_candidate_artifact": False,
                    }
                ],
                "candidate_repo_files_indexed": False,
                "external_candidate_artifacts_indexed": False,
            },
        )
        result = self.run_plan(receipt_path, plan_output)
        self.assertFalse(result.complete)
        self.assertIn("usage_artifact_index_hash_mismatch", result.rejection_reasons)

    def test_output_collision_rejects_without_overwrite(self):
        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        (
            plan_output
            / "local_fixture_adapter_dry_run_invocation_plan_result.json"
        ).write_text("{}\n", encoding="utf-8")

        result = self.run_plan(receipt_path, plan_output)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)

    def test_review_attestation_missing_and_mismatch_reject(self):
        cases = (
            (None, "review_attestation_missing"),
            ("wrong-attestation", "review_attestation_mismatch"),
        )
        for attestation, reason in cases:
            with self.subTest(reason=reason):
                _root, receipt_path, plan_output, _fixture_path, _usage_output = (
                    self.make_workspace()
                )
                result = self.run_plan(
                    receipt_path,
                    plan_output,
                    review_attestation=attestation,
                )
                self.assertFalse(result.complete)
                self.assertIn(reason, result.rejection_reasons)

    def test_successful_output_preserves_denials_and_future_gate(self):
        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )

        result = self.run_plan(receipt_path, plan_output)
        payload = read_json(result.result_path)

        for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_MATERIALIZED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in (
            "adapter_execution_performed",
            "playwright_execution_performed",
            "browser_open_performed",
            "network_probe_performed",
            "fixture_content_execution_performed",
        ):
            self.assertFalse(payload[field_name], field_name)
        self.assertFalse(payload["production_promotion_granted"])
        self.assertFalse(payload["production_adapter"])
        self.assertFalse(payload["live_website_admission_granted"])
        self.assertFalse(payload["general_browser_automation_admission_granted"])
        self.assertFalse(payload["autonomous_execution_admission_granted"])
        self.assertTrue(payload["future_invocation_requires_separate_execution_gate"])
        self.assertTrue(payload["future_execution_requires_human_approval"])

    def test_output_json_contains_no_executable_command_string_fields(self):
        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )

        result = self.run_plan(receipt_path, plan_output)

        for json_path in (
            result.plan_path,
            result.result_path,
            result.manifest_path,
            result.artifact_index_path,
            result.artifact_index_manifest_path,
        ):
            payload = read_json(json_path)
            for key, value in self.walk_json(payload):
                key_lower = key.lower()
                if not isinstance(value, str):
                    continue
                self.assertFalse(
                    key_lower in {"command", "argv"}
                    or key_lower.endswith("_command")
                    or key_lower.endswith("_argv"),
                    (json_path, key, value),
                )

    def walk_json(self, value, prefix=""):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from self.walk_json(child, str(key))
        elif isinstance(value, list):
            for child in value:
                yield from self.walk_json(child, prefix)
        else:
            yield prefix, value

    def test_cli_accepts_required_args_and_emits_dry_run_invocation_plan(self):
        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-local-fixture-adapter-dry-run-invocation-plan",
                    "--usage-receipt",
                    receipt_path.as_posix(),
                    "--output-dir",
                    plan_output.as_posix(),
                    "--invocation-plan-id",
                    "plan-cli",
                    "--review-attestation",
                    LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION,
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(
            Path(
                payload[
                    "local_fixture_adapter_dry_run_invocation_plan_result_path"
                ]
            ).exists()
        )

    def test_launcher_accepts_required_args_and_emits_dry_run_invocation_plan(self):
        _root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )

        result = run_local_fixture_adapter_dry_run_invocation_plan_launcher(
            receipt_path,
            plan_output,
            "plan-launcher",
            review_attestation=(
                LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION
            ),
        )

        self.assertTrue(result.complete)
        self.assertTrue(
            Path(
                result.payload[
                    "local_fixture_adapter_dry_run_invocation_plan_result_path"
                ]
            ).exists()
        )

    def test_task_graph_accepts_dry_run_plan_node_and_writes_artifact_outputs(self):
        root, receipt_path, plan_output, _fixture_path, _usage_output = (
            self.make_workspace()
        )
        graph_path = root / "graph.json"
        graph_output = root / "graph-output"
        graph_output.mkdir()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "dry-run-plan-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "plan_invocation",
                        "adapter_id": "local_fixture_adapter_dry_run_invocation_plan",
                        "capability": "launch_local_fixture_adapter_dry_run_invocation_plan",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "usage_receipt": receipt_path.as_posix(),
                            "output_dir": plan_output.as_posix(),
                            "invocation_plan_id": "plan-graph",
                            "review_attestation": LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION,
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
        self.assertTrue(node["local_fixture_adapter_dry_run_invocation_plan_complete"])
        roles = {
            artifact["artifact_role"]
            for artifact in artifact_outputs["artifacts"]
            if artifact["node_id"] == "plan_invocation"
        }
        self.assertIn("local_fixture_adapter_dry_run_invocation_plan_result", roles)
        self.assertIn("local_fixture_adapter_dry_run_invocation_plan_plan", roles)
        self.assertIn("artifact_index", roles)
        self.assertIn("artifact_index_manifest", roles)

    def test_adapter_registry_includes_dry_run_plan_candidate_local_fixture(self):
        entry = find_adapter_entry("local_fixture_adapter_dry_run_invocation_plan")

        self.assertEqual(entry.admission_status, AdapterAdmissionStatus.CANDIDATE)
        self.assertEqual(entry.mode, AdapterMode.LOCAL_FIXTURE)
        self.assertEqual(entry.risk_class, AdapterRiskClass.LOCAL_READONLY)
        self.assertIn(
            "launch_local_fixture_adapter_dry_run_invocation_plan",
            entry.capabilities,
        )
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id=entry.adapter_id,
                capability="launch_local_fixture_adapter_dry_run_invocation_plan",
                mode=entry.mode,
                risk_class=entry.risk_class,
            )
        )
        self.assertFalse(decision.admitted)
        self.assertIn("adapter_not_admitted", decision.reason_codes)
        self.assertFalse(entry.boundary.network_allowed)

    def test_product_health_check_includes_dry_run_plan_without_live_admission(self):
        report = build_product_health_report(Path.cwd())

        self.assertIn(
            "local_fixture_adapter_dry_run_invocation_plan_workflow",
            report["launcher_workflows"],
        )
        self.assertIn(
            "launch-local-fixture-adapter-dry-run-invocation-plan",
            report["required_cli_subcommands"],
        )
        self.assertTrue(report["launcher_workflows_complete"])
        self.assertTrue(report["cli_subcommands_complete"])
        self.assertTrue(report["runtime_admission_defaults_fail_closed"])
        self.assertFalse(report["network_runtime_allowed_by_default"])
        self.assertFalse(report["browser_runtime_allowed_by_default"])

    def test_module_source_contains_no_execution_or_forbidden_flag_paths(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden_fragments = (
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
            "--execute",
            "--run",
            "--node-command",
            "--runner-script",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, source)

    def test_decision_doc_exists_and_states_dry_run_boundary(self):
        text = " ".join(DECISION_DOC.read_text(encoding="utf-8").split())
        required_fragments = (
            "dry-run invocation plan",
            "does not execute the adapter",
            "does not execute Playwright",
            "does not open a browser",
            "does not execute #422/#424/#425/#426/#427/#428/#429",
            "does not enable production",
            "does not enable live websites",
            "does not enable general browser automation",
            "does not enable arbitrary URLs",
            "does not enable account/login/registration flows",
            "does not enable scraping",
            "does not enable bypass/captcha",
            "does not access secrets/cookies",
            "does not run npm/npx/install/browser download",
            "does not execute candidate repository code",
            "does not grant autonomy",
            "non-executable plan",
            "dry_run_plan_only",
            "local_fixture_only",
            "one_usage_receipt_bound",
            "human_review_required",
            "aggregation_bound",
            "regression_bound",
            "non_production",
            "separate execution gate",
        )
        for fragment in required_fragments:
            self.assertIn(" ".join(fragment.split()), text)


if __name__ == "__main__":
    unittest.main()
