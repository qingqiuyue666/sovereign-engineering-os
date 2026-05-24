import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.local_fixture_adapter_execution_gate_plan import (
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS,
)
from kernel.capabilities.local_fixture_human_approval_artifact import (
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
    run_local_fixture_human_approval_artifact,
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
    run_local_fixture_human_approval_artifact_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.product_health_check import build_product_health_report
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_human_approval_artifact.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_human_approval_artifact_v1.md"
)
OUTPUT_FILES = {
    "local_fixture_human_approval_artifact.json",
    "local_fixture_human_approval_artifact_result.json",
    "local_fixture_human_approval_artifact_manifest.json",
    "local_fixture_human_approval_artifact_summary.md",
    "local_fixture_human_approval_artifact_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalFixtureHumanApprovalArtifactTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        gate_output = root / "gate-output"
        gate_output.mkdir()
        approval_output = root / "approval-output"
        approval_output.mkdir()
        fixture_path = root / "fixture.html"
        fixture_path.write_text("<!doctype html><title>fixture</title>\n", encoding="utf-8")
        source_path = gate_output / "local_fixture_adapter_execution_gate_plan_result.json"
        write_json_atomically(
            source_path,
            self.valid_execution_gate_plan_result(gate_output, fixture_path),
        )
        return root, source_path, approval_output, fixture_path

    def valid_execution_gate_plan_result(self, gate_output, fixture_path):
        payload = {
            "gate_plan_type": "local_fixture_adapter_execution_gate_plan_v1",
            "authority": "non_authority_local_fixture_execution_gate_plan_record",
            "execution_capability": "local_fixture_adapter_execution_gate_plan_only",
            "execution_gate_plan_id": "gate-001",
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "dry_run_plan_sha256": "d" * 64,
            "dry_run_plan_validated": True,
            "invocation_plan_granted": True,
            "usage_receipt_sha256": "u" * 64,
            "usage_receipt_validated": True,
            "usage_receipt_granted": True,
            "promotion_result_sha256": "p" * 64,
            "source_gate_decision_sha256": "s" * 64,
            "source_gate_passed": True,
            "registry_promotion_granted": True,
            "aggregation_bound": True,
            "regression_bound": True,
            "local_fixture_only": True,
            "one_usage_receipt_bound": True,
            "dry_run_plan_bound": True,
            "execution_gate_plan_only": True,
            "human_approval_request_only": True,
            "execution_gate_plan_granted": True,
            "local_fixture_reference": fixture_path.as_posix(),
            "local_fixture_reference_scheme": "file",
            "local_fixture_path": fixture_path.as_posix(),
            "local_fixture_allowed_root": fixture_path.parent.as_posix(),
            "local_fixture_sha256": sha256_file(fixture_path),
            "local_fixture_revalidated": True,
            "local_fixture_exists": True,
            "local_fixture_regular_file": True,
            "local_fixture_symlink_detected": False,
            "local_fixture_under_allowed_root": True,
            "human_review_required": True,
            "required_human_approval": True,
            "non_production": True,
            "production_adapter": False,
            "production_promotion_granted": False,
            "approval_token_issued": False,
            "auto_approval_performed": False,
            "runnable_job_created": False,
            "execution_runner_created": False,
            "future_execution_requires_separate_human_approval_artifact": True,
            "future_execution_requires_separate_execution_runner_pr": True,
            "execution_gate_plan_status": "local_fixture_adapter_execution_gate_plan_completed",
            "execution_gate_plan_decision": "record_execution_gate_plan_only",
            "complete": True,
            "rejected": False,
            "rejection_reasons": [],
            "next_allowed_action": "human_review_execution_gate_plan_before_any_runner_implementation",
            "output_dir": gate_output.as_posix(),
            "no_live_website": True,
            "no_general_browser_automation": True,
            "no_autonomy": True,
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS
            }
        )
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS
            }
        )
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS
            }
        )
        payload["production_promotion_granted"] = False
        payload["approval_token_issued"] = False
        payload["auto_approval_performed"] = False
        payload["runnable_job_created"] = False
        payload["execution_runner_created"] = False
        return payload

    def run_artifact(
        self,
        source_path,
        approval_output,
        *,
        approval_artifact_id="approval-001",
        reviewer_id="reviewer-001",
        approval_attestation=LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
    ):
        return run_local_fixture_human_approval_artifact(
            source_path,
            approval_output,
            approval_artifact_id,
            reviewer_id,
            approval_attestation,
            project_id="project-001",
            operator_notes="reviewed #431 execution gate plan",
        )

    def assert_rejects_source_mutation(self, mutator):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        payload = read_json(source_path)
        mutator(payload)
        write_json(source_path, payload)

        result = self.run_artifact(source_path, approval_output)

        self.assertFalse(result.complete)
        self.assertTrue(result.result_path.exists())
        self.assertTrue(read_json(result.result_path)["rejection_reasons"])
        return result

    def test_valid_execution_gate_plan_result_writes_approval_artifact(self):
        _root, source_path, approval_output, fixture_path = self.make_workspace()

        result = self.run_artifact(source_path, approval_output)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertTrue(payload["approval_recorded"])
        self.assertEqual(payload["approval_artifact_type"], "local_fixture_human_approval_artifact_v1")
        self.assertEqual(payload["authority"], "human_review_metadata_record_only")
        self.assertEqual(payload["approval_artifact_id"], "approval-001")
        self.assertEqual(payload["reviewer_id"], "reviewer-001")
        self.assertEqual(payload["source_execution_gate_plan_path"], source_path.as_posix())
        self.assertEqual(payload["source_execution_gate_plan_sha256"], sha256_file(source_path))
        self.assertEqual(payload["source_gate_plan_type"], "local_fixture_adapter_execution_gate_plan_v1")
        self.assertEqual(payload["source_gate_plan_status"], "local_fixture_adapter_execution_gate_plan_completed")
        self.assertEqual(payload["source_gate_plan_decision"], "record_execution_gate_plan_only")
        self.assertEqual(payload["source_execution_gate_plan_id"], "gate-001")
        self.assertEqual(payload["adapter_id"], "bounded_playwright_worker_adapter_draft")
        self.assertEqual(payload["candidate_id"], "github-candidate-microsoft-playwright-v1")
        self.assertEqual(payload["repo_full_name"], "microsoft/playwright")
        self.assertEqual(payload["local_fixture_sha256"], sha256_file(fixture_path))
        self.assertEqual(payload["approval_artifact_status"], "local_fixture_human_approval_artifact_completed")
        self.assertEqual(payload["approval_artifact_decision"], "record_human_approval_artifact_only")
        self.assertTrue(payload["human_review_recorded"])
        self.assertTrue(payload["metadata_only"])
        self.assertTrue(payload["future_runner_requires_separate_pr"])
        self.assertTrue(payload["future_execution_requires_separate_runner_receipt"])
        self.assertTrue(payload["future_execution_requires_explicit_local_fixture_runner_gate"])
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_approval_artifact_before_runner_contract_pr",
        )
        for field_name in (
            "approval_token_issued",
            "execution_token_issued",
            "runner_created",
            "runnable_job_created",
            "adapter_execution_performed",
            "playwright_execution_performed",
            "browser_open_performed",
            "network_access_performed",
            "live_website_access_performed",
            "autonomous_execution_performed",
            "production_promotion_granted",
        ):
            self.assertFalse(payload[field_name], field_name)
        self.assertEqual({path.name for path in approval_output.iterdir()}, OUTPUT_FILES)

    def test_missing_execution_gate_plan_rejects(self):
        root, _source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(root / "missing.json", approval_output)
        self.assertFalse(result.complete)
        self.assertIn("source_execution_gate_plan_missing", result.rejection_reasons)

    def test_symlink_execution_gate_plan_rejects(self):
        root, source_path, approval_output, _fixture_path = self.make_workspace()
        link = root / "gate-link.json"
        link.symlink_to(source_path)
        result = self.run_artifact(link, approval_output)
        self.assertFalse(result.complete)
        self.assertIn("source_execution_gate_plan_is_symlink", result.rejection_reasons)

    def test_non_json_execution_gate_plan_rejects(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        source_path.write_text("{", encoding="utf-8")
        result = self.run_artifact(source_path, approval_output)
        self.assertFalse(result.complete)
        self.assertIn("source_execution_gate_plan_not_json_object", result.rejection_reasons)

    def test_rejected_execution_gate_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update(
                {
                    "execution_gate_plan_status": "local_fixture_adapter_execution_gate_plan_rejected",
                    "execution_gate_plan_decision": "reject_execution_gate_plan",
                    "execution_gate_plan_granted": False,
                }
            )
        )
        self.assertIn("source_execution_gate_plan_status_mismatch", result.rejection_reasons)

    def test_missing_approval_attestation_rejects(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output, approval_attestation="")
        self.assertFalse(result.complete)
        self.assertIn("approval_attestation_missing", result.rejection_reasons)

    def test_wrong_approval_attestation_rejects(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output, approval_attestation="wrong")
        self.assertFalse(result.complete)
        self.assertIn("approval_attestation_mismatch", result.rejection_reasons)

    def test_missing_reviewer_rejects(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output, reviewer_id="")
        self.assertFalse(result.complete)
        self.assertIn("reviewer_id_missing", result.rejection_reasons)

    def test_missing_approval_artifact_id_rejects(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output, approval_artifact_id="")
        self.assertFalse(result.complete)
        self.assertIn("approval_artifact_id_missing", result.rejection_reasons)

    def test_output_collision_rejects_without_overwrite(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        collision = approval_output / "local_fixture_human_approval_artifact_result.json"
        collision.write_text('{"kept": true}\n', encoding="utf-8")

        result = self.run_artifact(source_path, approval_output)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(read_json(collision), {"kept": True})

    def test_approval_token_true_in_source_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"approval_token_issued": True})
        )
        self.assertIn("source_approval_token_claimed", result.rejection_reasons)

    def test_runner_created_true_in_source_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"execution_runner_created": True})
        )
        self.assertIn("source_execution_runner_claimed", result.rejection_reasons)

    def test_adapter_execution_true_in_source_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"adapter_execution_performed": True})
        )
        self.assertIn("source_adapter_execution_claimed", result.rejection_reasons)

    def test_browser_open_true_in_source_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"browser_open_performed": True})
        )
        self.assertIn("source_browser_open_claimed", result.rejection_reasons)

    def test_network_access_true_in_source_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"network_access_performed": True})
        )
        self.assertIn("source_forbidden_capability_claimed", result.rejection_reasons)

    def test_production_promotion_true_in_source_plan_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"production_promotion_granted": True})
        )
        self.assertIn("source_production_promotion_claimed", result.rejection_reasons)

    def test_missing_required_false_field_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.pop("approval_token_issued")
        )
        self.assertIn("source_required_false_field_missing", result.rejection_reasons)

    def test_missing_required_true_field_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.pop("dry_run_plan_validated")
        )
        self.assertIn("source_required_true_field_missing", result.rejection_reasons)

    def test_source_identity_mismatch_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"repo_full_name": "wrong/repo"})
        )
        self.assertIn("source_repo_full_name_mismatch", result.rejection_reasons)

    def test_source_hash_fields_missing_reject(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"local_fixture_sha256": ""})
        )
        self.assertIn("source_required_hash_missing", result.rejection_reasons)

    def test_local_fixture_revalidation_false_rejects(self):
        result = self.assert_rejects_source_mutation(
            lambda payload: payload.update({"local_fixture_revalidated": False})
        )
        self.assertIn("source_required_true_field_not_true", result.rejection_reasons)

    def test_summary_markdown_contains_warning_language_and_hashes(self):
        _root, source_path, approval_output, fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output)
        text = result.summary_path.read_text(encoding="utf-8")

        required_fragments = (
            "Metadata-only human approval artifact.",
            "This is not an execution token.",
            "This does not create runner.",
            "This does not execute adapter.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not authorize production.",
            "Separate runner-contract PR required.",
            "Separate local-fixture runner gate required before future execution.",
            "Separate runner receipt required after future runner invocation.",
            "Approval artifact ID: approval-001",
            "Reviewer ID: reviewer-001",
            source_path.as_posix(),
            sha256_file(source_path),
            "Execution gate plan ID: gate-001",
            "Adapter ID: bounded_playwright_worker_adapter_draft",
            "Candidate ID: github-candidate-microsoft-playwright-v1",
            "Repo full name: microsoft/playwright",
            sha256_file(fixture_path),
            "Rejected capabilities:",
            "Next allowed action: human_review_approval_artifact_before_runner_contract_pr",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, text)

    def test_summary_markdown_contains_no_executable_material(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output)
        text = result.summary_path.read_text(encoding="utf-8").lower()

        forbidden_fragments = (
            "argv:",
            "shell snippet",
            "approval token:",
            "runner command",
            "browser launch command",
            "playwright command",
            "npm install",
            "npx ",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, text)

    def test_artifact_index_contains_output_artifacts_and_hashes(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output)
        index = read_json(result.artifact_index_path)

        roles = {entry["artifact_role"]: entry for entry in index["entries"]}
        expected_roles = {
            "local_fixture_human_approval_artifact",
            "local_fixture_human_approval_artifact_result",
            "local_fixture_human_approval_artifact_manifest",
            "local_fixture_human_approval_artifact_summary",
            "local_fixture_human_approval_artifact_checklist",
        }
        self.assertEqual(set(roles), expected_roles)
        for entry in roles.values():
            self.assertTrue(entry["exists"])
            self.assertTrue(entry["sha256"])
            self.assertEqual(entry["sha256"], sha256_file(Path(entry["path"])))

    def test_artifact_index_manifest_verifies_artifact_index_hash(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        result = self.run_artifact(source_path, approval_output)
        manifest = read_json(result.artifact_index_manifest_path)

        self.assertEqual(
            manifest["artifact_index_path"],
            result.artifact_index_path.as_posix(),
        )
        self.assertEqual(
            manifest["artifact_index_sha256"],
            sha256_file(result.artifact_index_path),
        )

    def test_cli_accepts_required_args_and_emits_approval_artifact(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-local-fixture-human-approval-artifact",
                    "--execution-gate-plan",
                    source_path.as_posix(),
                    "--output-dir",
                    approval_output.as_posix(),
                    "--approval-artifact-id",
                    "approval-cli",
                    "--reviewer-id",
                    "reviewer-cli",
                    "--approval-attestation",
                    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(Path(payload["local_fixture_human_approval_artifact_result_path"]).exists())

    def test_launcher_accepts_required_args_and_emits_approval_artifact(self):
        _root, source_path, approval_output, _fixture_path = self.make_workspace()

        result = run_local_fixture_human_approval_artifact_launcher(
            source_path,
            approval_output,
            "approval-launcher",
            "reviewer-launcher",
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
        )

        self.assertTrue(result.complete)
        self.assertTrue(Path(result.payload["local_fixture_human_approval_artifact_result_path"]).exists())

    def test_task_graph_accepts_approval_artifact_node_if_integrated(self):
        root, source_path, approval_output, _fixture_path = self.make_workspace()
        graph_path = root / "graph.json"
        graph_output = root / "graph-output"
        graph_output.mkdir()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "human-approval-artifact-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "approval_artifact",
                        "adapter_id": "local_fixture_human_approval_artifact",
                        "capability": "launch_local_fixture_human_approval_artifact",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "execution_gate_plan": source_path.as_posix(),
                            "output_dir": approval_output.as_posix(),
                            "approval_artifact_id": "approval-graph",
                            "reviewer_id": "reviewer-graph",
                            "approval_attestation": LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
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
        self.assertTrue(node["local_fixture_human_approval_artifact_complete"])
        roles = {
            artifact["artifact_role"]
            for artifact in artifact_outputs["artifacts"]
            if artifact["node_id"] == "approval_artifact"
        }
        self.assertIn("local_fixture_human_approval_artifact_result", roles)
        self.assertIn("local_fixture_human_approval_artifact_summary", roles)
        self.assertIn("artifact_index", roles)
        self.assertIn("artifact_index_manifest", roles)

    def test_product_health_recognizes_capability_if_integrated(self):
        report = build_product_health_report(Path.cwd())

        self.assertIn(
            "local_fixture_human_approval_artifact_workflow",
            report["launcher_workflows"],
        )
        self.assertIn(
            "launch-local-fixture-human-approval-artifact",
            report["required_cli_subcommands"],
        )
        self.assertTrue(report["launcher_workflows_complete"])
        self.assertTrue(report["cli_subcommands_complete"])
        self.assertFalse(report["network_runtime_allowed_by_default"])
        self.assertFalse(report["browser_runtime_allowed_by_default"])

    def test_adapter_registry_includes_non_production_metadata_only_candidate_if_integrated(self):
        entry = find_adapter_entry("local_fixture_human_approval_artifact")

        self.assertEqual(entry.admission_status, AdapterAdmissionStatus.CANDIDATE)
        self.assertEqual(entry.mode, AdapterMode.LOCAL_FIXTURE)
        self.assertEqual(entry.risk_class, AdapterRiskClass.LOCAL_READONLY)
        self.assertIn("launch_local_fixture_human_approval_artifact", entry.capabilities)
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id=entry.adapter_id,
                capability="launch_local_fixture_human_approval_artifact",
                mode=entry.mode,
                risk_class=entry.risk_class,
            )
        )
        self.assertFalse(decision.admitted)
        self.assertIn("adapter_not_admitted", decision.reason_codes)
        self.assertFalse(entry.boundary.network_allowed)
        self.assertFalse(entry.boundary.external_tool_control_allowed)

    def test_source_module_doc_contains_no_forbidden_live_execution_affordances(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        doc_text = DECISION_DOC.read_text(encoding="utf-8")
        for text in (source, doc_text):
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
                "--node-command",
                "--runner-script",
                "--approval-token",
            )
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, text)
        normalized_doc = " ".join(doc_text.split())
        for fragment in (
            "metadata-only human approval artifact",
            "It is not an execution token.",
            "It does not create a runner.",
            "It does not execute the adapter.",
            "It does not open a browser.",
            "It does not access network.",
            "It does not authorize live websites.",
            "It does not authorize production.",
            "separate runner-contract PR",
            "separate local-fixture runner gate",
            "separate runner receipt",
        ):
            self.assertIn(" ".join(fragment.split()), normalized_doc)


if __name__ == "__main__":
    unittest.main()
