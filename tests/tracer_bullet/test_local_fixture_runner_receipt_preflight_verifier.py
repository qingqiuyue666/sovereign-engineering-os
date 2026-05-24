import json
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from kernel.capabilities.local_fixture_runner_receipt_preflight_verifier import (
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE,
    run_local_fixture_runner_receipt_preflight_verifier,
)
from kernel.personal_ai.hash_utils import sha256_file, sha256_text
from kernel.personal_ai.io_utils import write_json_atomically


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_receipt_preflight_verifier.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_runner_receipt_preflight_verifier_v1.md"
)
EXPECTED_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalFixtureRunnerReceiptPreflightVerifierTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_dir = root / "sources"
        source_dir.mkdir()
        output_dir = root / "preflight-output"
        output_dir.mkdir()
        stub_path = source_dir / "local_fixture_runner_stub_admission_gate_result.json"
        receipt_path = (
            source_dir / "local_fixture_runner_receipt_contract_draft_result.json"
        )
        human_path = source_dir / "local_fixture_human_approval_artifact_result.json"
        write_json_atomically(stub_path, self.valid_runner_stub_gate_payload())
        write_json_atomically(receipt_path, self.valid_receipt_contract_payload())
        write_json_atomically(human_path, self.valid_human_approval_payload())
        return root, stub_path, receipt_path, human_path, output_dir

    def valid_runner_stub_gate_payload(self):
        payload = {
            "gate_type": "local_fixture_runner_stub_admission_gate_v1",
            "gate_recorded": True,
            "gate_status": "local_fixture_runner_stub_admission_gate_completed",
            "gate_decision": "record_runner_stub_admission_gate_only",
            "metadata_only": True,
            "future_runner_stub_requires_receipt_contract": True,
            "future_runner_stub_requires_no_network": True,
            "future_runner_stub_requires_no_browser": True,
            "future_runner_stub_requires_no_production": True,
            "adapter_id": "local_fixture_runner_stub_admission_gate",
            "source_adapter_id": "bounded_playwright_worker_adapter_draft",
            "source_candidate_id": "github-candidate-microsoft-playwright-v1",
            "source_repo_full_name": "microsoft/playwright",
            "source_local_fixture_sha256": "f" * 64,
            "complete": True,
            "rejection_reasons": [],
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS
            }
        )
        return payload

    def valid_receipt_contract_payload(self):
        payload = {
            "contract_type": "local_fixture_runner_receipt_contract_draft_v1",
            "contract_recorded": True,
            "receipt_contract_status": "local_fixture_runner_receipt_contract_draft_completed",
            "receipt_contract_decision": "record_runner_receipt_contract_draft_only",
            "contract_only": True,
            "metadata_only": True,
            "future_receipt_requires_runner_stub_admission_gate": True,
            "future_receipt_requires_verified_human_approval_artifact": True,
            "future_receipt_requires_verified_runner_contract": True,
            "future_receipt_requires_local_fixture_only": True,
            "future_receipt_requires_artifact_index": True,
            "adapter_id": "local_fixture_runner_receipt_contract_draft",
            "complete": True,
            "rejection_reasons": [],
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS
            }
        )
        return payload

    def valid_human_approval_payload(self):
        payload = {
            "approval_artifact_type": "local_fixture_human_approval_artifact_v1",
            "approval_recorded": True,
            "approval_artifact_status": "local_fixture_human_approval_artifact_completed",
            "approval_artifact_decision": "record_human_approval_artifact_only",
            "metadata_only": True,
            "human_review_recorded": True,
            "required_human_approval": True,
            "non_production": True,
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "local_fixture_sha256": "f" * 64,
            "complete": True,
            "rejection_reasons": [],
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS
            }
        )
        return payload

    def run_preflight(
        self,
        stub_path,
        receipt_path,
        human_path,
        output_dir,
        *,
        preflight_id="runner-receipt-preflight-001",
        reviewer_id="reviewer-001",
        review_attestation=LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION,
    ):
        return run_local_fixture_runner_receipt_preflight_verifier(
            stub_path,
            receipt_path,
            human_path,
            output_dir,
            preflight_id,
            reviewer_id,
            review_attestation,
            project_id="project-001",
            operator_notes="reviewed local-fixture runner receipt preflight",
        )

    def assert_rejects_source_mutation(self, source_name, mutator):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()
        paths = {
            "stub": stub_path,
            "receipt": receipt_path,
            "human": human_path,
        }
        payload = read_json(paths[source_name])
        mutator(payload)
        write_json(paths[source_name], payload)

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)

        self.assertFalse(result.complete)
        self.assertTrue(result.result_path.exists())
        self.assertTrue(read_json(result.result_path)["rejection_reasons"])
        return result

    def test_valid_upstream_artifacts_write_all_seven_output_artifacts(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertTrue(payload["preflight_recorded"])
        self.assertEqual(
            payload["preflight_type"],
            "local_fixture_runner_receipt_preflight_verifier_v1",
        )
        self.assertEqual(
            payload["result_type"],
            "local_fixture_runner_receipt_preflight_verifier_result_v1",
        )
        self.assertEqual(
            payload["authority"],
            "non_authority_runner_receipt_preflight_metadata_only",
        )
        self.assertEqual(
            payload["adapter_id"],
            "local_fixture_runner_receipt_preflight_verifier",
        )
        self.assertEqual(
            payload["capability"],
            "launch_local_fixture_runner_receipt_preflight_verifier",
        )
        self.assertEqual(payload["preflight_id"], "runner-receipt-preflight-001")
        self.assertEqual(payload["reviewer_id"], "reviewer-001")
        self.assertTrue(payload["review_attestation_present"])
        self.assertEqual(
            payload["review_attestation_sha256"],
            sha256_text(LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION),
        )
        self.assertEqual(
            payload["runner_stub_admission_gate_result_path"],
            stub_path.as_posix(),
        )
        self.assertEqual(
            payload["runner_stub_admission_gate_result_sha256"],
            sha256_file(stub_path),
        )
        self.assertEqual(
            payload["runner_receipt_contract_draft_result_path"],
            receipt_path.as_posix(),
        )
        self.assertEqual(
            payload["runner_receipt_contract_draft_result_sha256"],
            sha256_file(receipt_path),
        )
        self.assertEqual(
            payload["human_approval_artifact_result_path"],
            human_path.as_posix(),
        )
        self.assertEqual(
            payload["human_approval_artifact_result_sha256"],
            sha256_file(human_path),
        )
        self.assertEqual(
            payload["preflight_status"],
            "local_fixture_runner_receipt_preflight_verifier_completed",
        )
        self.assertEqual(
            payload["preflight_decision"],
            "record_runner_receipt_preflight_only",
        )
        self.assertTrue(payload["metadata_only"])
        self.assertTrue(payload["runner_receipt_preflight_only"])
        self.assertTrue(payload["future_runner_receipt_requires_separate_pr"])
        self.assertTrue(payload["future_runner_implementation_requires_separate_pr"])
        self.assertTrue(payload["future_execution_requires_separate_runner_receipt"])
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_runner_receipt_preflight_before_receipt_artifact_pr",
        )
        self.assertEqual(payload["rejection_reasons"], [])
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["rejected"])
        self.assertEqual(
            set(path.name for path in output_dir.iterdir()),
            set(EXPECTED_OUTPUT_FILES),
        )
        for file_name in EXPECTED_OUTPUT_FILES:
            self.assertTrue((output_dir / file_name).is_file(), file_name)

    def test_missing_runner_stub_admission_gate_result_rejects(self):
        root, _stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(
            root / "missing-stub.json",
            receipt_path,
            human_path,
            output_dir,
        )

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_stub_admission_gate_result_missing",
            result.rejection_reasons,
        )
        self.assertTrue(result.result_path.exists())

    def test_missing_runner_receipt_contract_draft_result_rejects(self):
        root, stub_path, _receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(
            stub_path,
            root / "missing-receipt-contract.json",
            human_path,
            output_dir,
        )

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_receipt_contract_draft_result_missing",
            result.rejection_reasons,
        )
        self.assertTrue(result.result_path.exists())

    def test_missing_human_approval_artifact_result_rejects(self):
        root, stub_path, receipt_path, _human_path, output_dir = self.make_workspace()

        result = self.run_preflight(
            stub_path,
            receipt_path,
            root / "missing-human.json",
            output_dir,
        )

        self.assertFalse(result.complete)
        self.assertIn(
            "human_approval_artifact_result_missing",
            result.rejection_reasons,
        )
        self.assertTrue(result.result_path.exists())

    def test_symlink_source_rejects(self):
        root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()
        link = root / "stub-link.json"
        link.symlink_to(stub_path)

        result = self.run_preflight(link, receipt_path, human_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_stub_admission_gate_result_is_symlink",
            result.rejection_reasons,
        )

    def test_non_regular_source_rejects(self):
        root, _stub_path, receipt_path, human_path, output_dir = self.make_workspace()
        source_dir = root / "source-dir"
        source_dir.mkdir()

        result = self.run_preflight(source_dir, receipt_path, human_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_stub_admission_gate_result_not_regular_file",
            result.rejection_reasons,
        )

    def test_non_json_source_rejects(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()
        stub_path.write_text("[]\n", encoding="utf-8")

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_stub_admission_gate_result_not_json_object",
            result.rejection_reasons,
        )

    def test_missing_or_mismatched_attestation_rejects(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        missing = self.run_preflight(
            stub_path,
            receipt_path,
            human_path,
            output_dir,
            review_attestation=None,
        )
        self.assertFalse(missing.complete)
        self.assertIn("review_attestation_missing", missing.rejection_reasons)

        second_output = output_dir.parent / "preflight-output-2"
        second_output.mkdir()
        mismatched = self.run_preflight(
            stub_path,
            receipt_path,
            human_path,
            second_output,
            review_attestation="wrong",
        )
        self.assertFalse(mismatched.complete)
        self.assertIn("review_attestation_mismatch", mismatched.rejection_reasons)

    def test_empty_preflight_id_rejects(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(
            stub_path,
            receipt_path,
            human_path,
            output_dir,
            preflight_id="",
        )

        self.assertFalse(result.complete)
        self.assertIn("preflight_id_missing", result.rejection_reasons)

    def test_empty_reviewer_id_rejects(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(
            stub_path,
            receipt_path,
            human_path,
            output_dir,
            reviewer_id="",
        )

        self.assertFalse(result.complete)
        self.assertIn("reviewer_id_missing", result.rejection_reasons)

    def test_output_dir_symlink_rejects(self):
        root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()
        symlink_output = root / "output-link"
        symlink_output.symlink_to(output_dir)

        result = self.run_preflight(
            stub_path,
            receipt_path,
            human_path,
            symlink_output,
        )

        self.assertFalse(result.complete)
        self.assertIn("output_dir_symlink_rejected", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(list(output_dir.iterdir()), [])

    def test_output_collision_rejects_without_overwrite(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()
        collision = (
            output_dir
            / LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
        )
        collision.write_text('{"kept": true}\n', encoding="utf-8")

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(read_json(collision), {"kept": True})
        self.assertEqual([path.name for path in output_dir.iterdir()], [collision.name])

    def test_runner_stub_gate_field_mismatch_rejects(self):
        result = self.assert_rejects_source_mutation(
            "stub",
            lambda payload: payload.update({"gate_status": "wrong"}),
        )
        self.assertIn(
            "runner_stub_admission_gate_gate_status_mismatch",
            result.rejection_reasons,
        )

    def test_runner_receipt_contract_field_mismatch_rejects(self):
        result = self.assert_rejects_source_mutation(
            "receipt",
            lambda payload: payload.update(
                {"receipt_contract_decision": "wrong"}
            ),
        )
        self.assertIn(
            "runner_receipt_contract_receipt_contract_decision_mismatch",
            result.rejection_reasons,
        )

    def test_human_approval_artifact_field_mismatch_rejects(self):
        result = self.assert_rejects_source_mutation(
            "human",
            lambda payload: payload.update({"approval_artifact_status": "wrong"}),
        )
        self.assertIn(
            "human_approval_artifact_approval_artifact_status_mismatch",
            result.rejection_reasons,
        )

    def test_forbidden_true_field_in_any_source_rejects(self):
        result = self.assert_rejects_source_mutation(
            "receipt",
            lambda payload: payload.update({"network_access_performed": True}),
        )
        self.assertIn(
            "runner_receipt_contract_draft_result_network_access_performed_forbidden_true",
            result.rejection_reasons,
        )

    def test_command_materialization_true_field_rejects(self):
        result = self.assert_rejects_source_mutation(
            "stub",
            lambda payload: payload.update({"npx_command_materialized": True}),
        )
        self.assertIn(
            "runner_stub_admission_gate_result_npx_command_materialized_forbidden_true",
            result.rejection_reasons,
        )

    def test_identity_mismatch_rejects(self):
        result = self.assert_rejects_source_mutation(
            "human",
            lambda payload: payload.update({"candidate_id": "wrong-candidate"}),
        )
        self.assertIn("source_candidate_id_mismatch", result.rejection_reasons)

    def test_result_contains_required_false_boundary_fields(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)
        payload = read_json(result.result_path)

        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_artifact_index_includes_all_seven_outputs_and_hashes(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)
        artifact_index = read_json(result.artifact_index_path)
        entries = artifact_index["entries"]

        self.assertEqual(artifact_index["indexed_artifacts"], len(EXPECTED_OUTPUT_FILES))
        self.assertEqual(
            [entry["relative_path"] for entry in entries],
            list(EXPECTED_OUTPUT_FILES),
        )
        deferred = {"artifact_index.json", "artifact_index_manifest.json"}
        for entry in entries:
            path = Path(entry["path"])
            self.assertTrue(path.exists(), entry)
            self.assert_safe_relative_path(entry["relative_path"])
            self.assertTrue(entry["safe_relative_path"], entry)
            self.assertFalse(entry["candidate_repo_file"])
            self.assertFalse(entry["external_candidate_artifact"])
            self.assertFalse(entry["content_indexed"])
            self.assertFalse(entry["raw_content_copied"])
            if entry["relative_path"] not in deferred:
                self.assertEqual(entry["sha256"], sha256_file(path))
                self.assertGreater(entry["size_bytes"], 0)
            else:
                self.assertIsNone(entry["sha256"])
        self.assertFalse(artifact_index["candidate_repo_files_indexed"])
        self.assertFalse(artifact_index["external_candidate_artifacts_indexed"])
        self.assertFalse(artifact_index["content_indexed"])
        self.assertFalse(artifact_index["raw_content_copied"])

    def test_artifact_index_manifest_verifies_artifact_index_hash(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)
        manifest = read_json(result.artifact_index_manifest_path)

        self.assertEqual(
            manifest["artifact_index_path"],
            result.artifact_index_path.as_posix(),
        )
        self.assertEqual(
            manifest["artifact_index_sha256"],
            sha256_file(result.artifact_index_path),
        )
        self.assertTrue(manifest["artifact_index_hash_verified_by_manifest"])
        self.assertTrue(
            manifest["artifact_index_manifest_hash_unavailable_without_self_reference"]
        )
        self.assertEqual(
            manifest["indexed_relative_paths"],
            list(EXPECTED_OUTPUT_FILES),
        )
        self.assertFalse(manifest["candidate_repo_files_indexed"])
        self.assertFalse(manifest["external_candidate_artifacts_indexed"])
        self.assertFalse(manifest["content_indexed"])
        self.assertFalse(manifest["raw_content_copied"])

    def test_summary_contains_warning_language_and_no_executable_command_material(self):
        _root, stub_path, receipt_path, human_path, output_dir = self.make_workspace()

        result = self.run_preflight(stub_path, receipt_path, human_path, output_dir)
        text = result.summary_path.read_text(encoding="utf-8").lower()

        self.assertIn("boundary warning", text)
        self.assertIn("metadata-only", text)
        self.assertIn("this is not a runner", text)
        self.assertIn("future runner receipt implementation requires a separate pr", text)
        forbidden_fragments = (
            "```",
            "$ ",
            "shell snippet",
            "runner command",
            "browser launch command",
            "playwright command",
            "npm install",
            "npx",
            "--url",
            "--target-url",
            "--execute",
            "--approval-token",
            "--execution-token",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, text)

    def test_decision_doc_states_metadata_only_boundary(self):
        text = DECISION_DOC.read_text(encoding="utf-8").lower()

        expected_fragments = (
            "metadata-only preflight verifier",
            "it is not a runner",
            "it is not a runner stub",
            "it does not create a runnable job",
            "it does not issue approval material",
            "it does not issue execution material",
            "it does not execute the adapter",
            "it does not launch playwright",
            "it does not open a browser",
            "it does not access the network",
            "it does not authorize live websites",
            "it does not authorize production",
            "future runner receipt implementation requires a separate pr",
            "future runner implementation requires a separate pr",
            "output-artifact-only",
            "no content indexing",
            "no raw content copying",
            "no candidate repo indexing",
            "no external artifact indexing",
            "artifact_index.json entry has its hash deferred",
            "artifact_index_manifest.json entry records that its own hash is unavailable",
            "records the sha256 of artifact_index.json",
        )
        for fragment in expected_fragments:
            self.assertIn(fragment, text)

    def test_source_module_and_doc_contain_no_forbidden_live_execution_affordances(self):
        combined = (
            MODULE_PATH.read_text(encoding="utf-8")
            + "\n"
            + DECISION_DOC.read_text(encoding="utf-8")
        ).lower()
        forbidden_fragments = (
            "subprocess",
            "os.system",
            "socket",
            "requests",
            "urllib",
            "sync_playwright",
            "async_playwright",
            "browser.launch",
            "page.goto",
            "npm install",
            "npx",
            "--url",
            "--target-url",
            "--execute",
            "--approval-token",
            "--execution-token",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, combined)

    def assert_safe_relative_path(self, value):
        relative_path = PurePosixPath(value)
        self.assertFalse(relative_path.is_absolute(), value)
        self.assertNotEqual(relative_path.parts[:1], ("..",), value)
        self.assertNotIn("..", relative_path.parts, value)


if __name__ == "__main__":
    unittest.main()
