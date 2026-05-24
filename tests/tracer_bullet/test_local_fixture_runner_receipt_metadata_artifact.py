import json
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from kernel.capabilities.local_fixture_runner_receipt_metadata_artifact import (
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE,
    run_local_fixture_runner_receipt_metadata_artifact,
)
from kernel.personal_ai.hash_utils import sha256_file, sha256_text
from kernel.personal_ai.io_utils import write_json_atomically


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_receipt_metadata_artifact.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_runner_receipt_metadata_artifact_v1.md"
)
EXPECTED_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE,
)
UPSTREAM_SOURCE_FIELDS = (
    "runner_stub_admission_gate_result_path",
    "runner_stub_admission_gate_result_sha256",
    "runner_receipt_contract_draft_result_path",
    "runner_receipt_contract_draft_result_sha256",
    "human_approval_artifact_result_path",
    "human_approval_artifact_result_sha256",
)
SOURCE_IDENTITY_FIELDS = (
    "source_adapter_id",
    "source_candidate_id",
    "source_repo_full_name",
    "source_local_fixture_sha256",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalFixtureRunnerReceiptMetadataArtifactTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_dir = root / "sources"
        source_dir.mkdir()
        output_dir = root / "receipt-output"
        output_dir.mkdir()
        preflight_path = (
            source_dir
            / "local_fixture_runner_receipt_preflight_verifier_result.json"
        )
        write_json_atomically(preflight_path, self.valid_preflight_payload())
        return root, preflight_path, output_dir

    def valid_preflight_payload(self):
        payload = {
            "preflight_type": "local_fixture_runner_receipt_preflight_verifier_v1",
            "result_type": "local_fixture_runner_receipt_preflight_verifier_result_v1",
            "preflight_recorded": True,
            "preflight_status": "local_fixture_runner_receipt_preflight_verifier_completed",
            "preflight_decision": "record_runner_receipt_preflight_only",
            "metadata_only": True,
            "runner_receipt_preflight_only": True,
            "future_runner_receipt_requires_separate_pr": True,
            "future_runner_implementation_requires_separate_pr": True,
            "future_execution_requires_separate_runner_receipt": True,
            "complete": True,
            "rejected": False,
            "rejection_reasons": [],
            "runner_stub_admission_gate_result_path": "/tmp/local/stub-result.json",
            "runner_stub_admission_gate_result_sha256": "a" * 64,
            "runner_receipt_contract_draft_result_path": "/tmp/local/receipt-contract-result.json",
            "runner_receipt_contract_draft_result_sha256": "b" * 64,
            "human_approval_artifact_result_path": "/tmp/local/human-approval-result.json",
            "human_approval_artifact_result_sha256": "c" * 64,
            "source_adapter_id": "bounded_playwright_worker_adapter_draft",
            "source_candidate_id": "github-candidate-microsoft-playwright-v1",
            "source_repo_full_name": "microsoft/playwright",
            "source_local_fixture_sha256": "f" * 64,
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS
            }
        )
        return payload

    def run_receipt(
        self,
        preflight_path,
        output_dir,
        *,
        runner_receipt_id="runner-receipt-001",
        reviewer_id="reviewer-001",
        review_attestation=LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION,
    ):
        return run_local_fixture_runner_receipt_metadata_artifact(
            preflight_path,
            output_dir,
            runner_receipt_id,
            reviewer_id,
            review_attestation,
            project_id="project-001",
            operator_notes="reviewed local-fixture runner receipt metadata",
        )

    def assert_rejects_preflight_mutation(self, mutator):
        _root, preflight_path, output_dir = self.make_workspace()
        payload = read_json(preflight_path)
        mutator(payload)
        write_json(preflight_path, payload)

        result = self.run_receipt(preflight_path, output_dir)

        self.assertFalse(result.complete)
        self.assertTrue(result.result_path.exists())
        self.assertTrue(read_json(result.result_path)["rejection_reasons"])
        return result

    def test_valid_preflight_result_writes_all_seven_output_artifacts(self):
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(preflight_path, output_dir)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertTrue(payload["receipt_recorded"])
        self.assertEqual(
            payload["receipt_type"],
            "local_fixture_runner_receipt_metadata_artifact_v1",
        )
        self.assertEqual(
            payload["result_type"],
            "local_fixture_runner_receipt_metadata_artifact_result_v1",
        )
        self.assertEqual(
            payload["authority"],
            "non_authority_runner_receipt_metadata_only",
        )
        self.assertEqual(
            payload["adapter_id"],
            "local_fixture_runner_receipt_metadata_artifact",
        )
        self.assertEqual(
            payload["capability"],
            "launch_local_fixture_runner_receipt_metadata_artifact",
        )
        self.assertEqual(payload["runner_receipt_id"], "runner-receipt-001")
        self.assertEqual(payload["reviewer_id"], "reviewer-001")
        self.assertTrue(payload["review_attestation_present"])
        self.assertEqual(
            payload["review_attestation_sha256"],
            sha256_text(LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION),
        )
        self.assertEqual(
            payload["runner_receipt_preflight_result_path"],
            preflight_path.as_posix(),
        )
        self.assertEqual(
            payload["runner_receipt_preflight_result_sha256"],
            sha256_file(preflight_path),
        )
        self.assertEqual(
            payload["receipt_status"],
            "local_fixture_runner_receipt_metadata_artifact_completed",
        )
        self.assertEqual(
            payload["receipt_decision"],
            "record_runner_receipt_metadata_only",
        )
        self.assertTrue(payload["metadata_only"])
        self.assertTrue(payload["runner_receipt_metadata_only"])
        self.assertTrue(payload["future_runner_implementation_requires_separate_pr"])
        self.assertTrue(payload["future_execution_requires_separate_runner_receipt"])
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_runner_receipt_metadata_before_runner_stub_pr",
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

    def test_missing_preflight_result_rejects(self):
        root, _preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(root / "missing-preflight.json", output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_receipt_preflight_result_missing",
            result.rejection_reasons,
        )
        self.assertTrue(result.result_path.exists())

    def test_symlink_preflight_result_rejects(self):
        root, preflight_path, output_dir = self.make_workspace()
        link = root / "preflight-link.json"
        link.symlink_to(preflight_path)

        result = self.run_receipt(link, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_receipt_preflight_result_is_symlink",
            result.rejection_reasons,
        )

    def test_non_regular_preflight_result_rejects(self):
        root, _preflight_path, output_dir = self.make_workspace()
        source_dir = root / "source-dir"
        source_dir.mkdir()

        result = self.run_receipt(source_dir, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_receipt_preflight_result_not_regular_file",
            result.rejection_reasons,
        )

    def test_non_json_preflight_result_rejects(self):
        _root, preflight_path, output_dir = self.make_workspace()
        preflight_path.write_text("[]\n", encoding="utf-8")

        result = self.run_receipt(preflight_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn(
            "runner_receipt_preflight_result_not_json_object",
            result.rejection_reasons,
        )

    def test_missing_or_mismatched_attestation_rejects(self):
        _root, preflight_path, output_dir = self.make_workspace()

        missing = self.run_receipt(
            preflight_path,
            output_dir,
            review_attestation=None,
        )
        self.assertFalse(missing.complete)
        self.assertIn("review_attestation_missing", missing.rejection_reasons)

        second_output = output_dir.parent / "receipt-output-2"
        second_output.mkdir()
        mismatched = self.run_receipt(
            preflight_path,
            second_output,
            review_attestation="wrong",
        )
        self.assertFalse(mismatched.complete)
        self.assertIn("review_attestation_mismatch", mismatched.rejection_reasons)

    def test_empty_runner_receipt_id_rejects(self):
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(
            preflight_path,
            output_dir,
            runner_receipt_id="",
        )

        self.assertFalse(result.complete)
        self.assertIn("runner_receipt_id_missing", result.rejection_reasons)

    def test_empty_reviewer_id_rejects(self):
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(preflight_path, output_dir, reviewer_id="")

        self.assertFalse(result.complete)
        self.assertIn("reviewer_id_missing", result.rejection_reasons)

    def test_output_dir_symlink_rejects(self):
        root, preflight_path, output_dir = self.make_workspace()
        symlink_output = root / "output-link"
        symlink_output.symlink_to(output_dir)

        result = self.run_receipt(preflight_path, symlink_output)

        self.assertFalse(result.complete)
        self.assertIn("output_dir_symlink_rejected", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(list(output_dir.iterdir()), [])

    def test_output_collision_rejects_without_overwrite(self):
        _root, preflight_path, output_dir = self.make_workspace()
        collision = (
            output_dir / LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE
        )
        collision.write_text('{"kept": true}\n', encoding="utf-8")

        result = self.run_receipt(preflight_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(read_json(collision), {"kept": True})
        self.assertEqual([path.name for path in output_dir.iterdir()], [collision.name])

    def test_preflight_type_mismatch_rejects(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.update({"preflight_type": "wrong"})
        )
        self.assertIn("preflight_preflight_type_mismatch", result.rejection_reasons)

    def test_preflight_status_mismatch_rejects(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.update({"preflight_status": "wrong"})
        )
        self.assertIn("preflight_preflight_status_mismatch", result.rejection_reasons)

    def test_preflight_decision_mismatch_rejects(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.update({"preflight_decision": "wrong"})
        )
        self.assertIn(
            "preflight_preflight_decision_mismatch",
            result.rejection_reasons,
        )

    def test_preflight_rejected_complete_mismatch_rejects(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.update({"complete": False, "rejected": True})
        )
        self.assertIn("preflight_complete_not_true", result.rejection_reasons)
        self.assertIn("preflight_rejected_not_false", result.rejection_reasons)

    def test_missing_upstream_source_path_hash_fields_reject(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.pop(
                "runner_receipt_contract_draft_result_sha256"
            )
        )
        self.assertIn(
            "preflight_runner_receipt_contract_draft_result_sha256_missing",
            result.rejection_reasons,
        )

    def test_forbidden_true_field_rejects(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.update({"network_access_performed": True})
        )
        self.assertIn(
            "preflight_network_access_performed_forbidden_true",
            result.rejection_reasons,
        )

    def test_command_materialization_true_field_rejects(self):
        result = self.assert_rejects_preflight_mutation(
            lambda payload: payload.update({"npx_command_materialized": True})
        )
        self.assertIn(
            "preflight_npx_command_materialized_forbidden_true",
            result.rejection_reasons,
        )

    def test_result_contains_required_false_boundary_fields(self):
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(preflight_path, output_dir)
        payload = read_json(result.result_path)

        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_result_carries_upstream_source_paths_hashes(self):
        _root, preflight_path, output_dir = self.make_workspace()
        preflight = read_json(preflight_path)

        result = self.run_receipt(preflight_path, output_dir)
        payload = read_json(result.result_path)

        for field_name in UPSTREAM_SOURCE_FIELDS:
            self.assertEqual(payload[field_name], preflight[field_name])

    def test_result_carries_source_identity_fields_where_present(self):
        _root, preflight_path, output_dir = self.make_workspace()
        preflight = read_json(preflight_path)

        result = self.run_receipt(preflight_path, output_dir)
        payload = read_json(result.result_path)

        for field_name in SOURCE_IDENTITY_FIELDS:
            self.assertEqual(payload[field_name], preflight[field_name])

    def test_artifact_index_includes_all_seven_outputs_and_hashes(self):
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(preflight_path, output_dir)
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
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(preflight_path, output_dir)
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
        _root, preflight_path, output_dir = self.make_workspace()

        result = self.run_receipt(preflight_path, output_dir)
        text = result.summary_path.read_text(encoding="utf-8").lower()

        self.assertIn("boundary warning", text)
        self.assertIn("metadata-only runner receipt artifact", text)
        self.assertIn("this is not a runner", text)
        self.assertIn("future runner implementation requires a separate pr", text)
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
            "this is a metadata-only runner receipt artifact",
            "this is not a runner",
            "this is not a runner stub",
            "this does not create a runnable job",
            "this does not issue approval material",
            "this does not issue execution material",
            "this does not execute the adapter",
            "this does not launch playwright",
            "this does not open a browser",
            "this does not access the network",
            "this does not authorize live websites",
            "this does not authorize production",
            "future runner stub implementation requires a separate pr",
            "future runner implementation requires a separate pr",
            "output-artifact-only",
            "no content indexing",
            "no raw content copying",
            "no candidate repo indexing",
            "no external artifact indexing",
            "self-reference hash handling for artifact_index and artifact_index_manifest",
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
