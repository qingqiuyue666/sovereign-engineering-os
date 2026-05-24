import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.local_fixture_runner_stub_admission_gate import (
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE,
    run_local_fixture_runner_stub_admission_gate,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_stub_admission_gate.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_runner_stub_admission_gate_v1.md"
)
EXPECTED_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalFixtureRunnerStubAdmissionGateTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_dir = root / "sources"
        source_dir.mkdir()
        output_dir = root / "gate-output"
        output_dir.mkdir()
        human_path = source_dir / "local_fixture_human_approval_artifact_result.json"
        contract_path = source_dir / "local_fixture_runner_contract_draft_result.json"
        write_json_atomically(human_path, self.valid_human_approval_payload())
        write_json_atomically(contract_path, self.valid_runner_contract_payload())
        return root, human_path, contract_path, output_dir

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
            "future_runner_requires_separate_pr": True,
            "future_execution_requires_separate_runner_receipt": True,
            "future_execution_requires_explicit_local_fixture_runner_gate": True,
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "local_fixture_sha256": "f" * 64,
            "complete": True,
            "rejection_reasons": [],
        }
        payload.update({field_name: False for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS})
        return payload

    def valid_runner_contract_payload(self):
        payload = {
            "contract_type": "local_fixture_runner_contract_draft_v1",
            "contract_recorded": True,
            "runner_contract_status": "local_fixture_runner_contract_draft_completed",
            "runner_contract_decision": "record_runner_contract_draft_only",
            "contract_only": True,
            "metadata_only": True,
            "future_runner_requires_separate_implementation_pr": True,
            "future_runner_requires_verified_human_approval_artifact": True,
            "future_runner_requires_verified_execution_gate_plan": True,
            "future_runner_requires_local_fixture_only": True,
            "future_runner_requires_runner_receipt": True,
            "future_runner_requires_artifact_index": True,
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "local_fixture_sha256": "f" * 64,
            "complete": True,
            "rejection_reasons": [],
        }
        payload.update({field_name: False for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS})
        return payload

    def run_gate(
        self,
        human_path,
        contract_path,
        output_dir,
        *,
        gate_id="runner-stub-gate-001",
        reviewer_id="reviewer-001",
        review_attestation=LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION,
    ):
        return run_local_fixture_runner_stub_admission_gate(
            human_path,
            contract_path,
            output_dir,
            gate_id,
            reviewer_id,
            review_attestation,
        )

    def assert_rejects_human_mutation(self, mutator):
        _root, human_path, contract_path, output_dir = self.make_workspace()
        payload = read_json(human_path)
        mutator(payload)
        write_json(human_path, payload)

        result = self.run_gate(human_path, contract_path, output_dir)

        self.assertFalse(result.complete)
        self.assertTrue(result.result_path.exists())
        self.assertTrue(read_json(result.result_path)["rejection_reasons"])
        return result

    def assert_rejects_contract_mutation(self, mutator):
        _root, human_path, contract_path, output_dir = self.make_workspace()
        payload = read_json(contract_path)
        mutator(payload)
        write_json(contract_path, payload)

        result = self.run_gate(human_path, contract_path, output_dir)

        self.assertFalse(result.complete)
        self.assertTrue(result.result_path.exists())
        self.assertTrue(read_json(result.result_path)["rejection_reasons"])
        return result

    def test_valid_sources_write_all_seven_artifacts(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, contract_path, output_dir)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertTrue(payload["gate_recorded"])
        self.assertEqual(payload["gate_type"], "local_fixture_runner_stub_admission_gate_v1")
        self.assertEqual(payload["authority"], "non_authority_runner_stub_admission_metadata_only")
        self.assertEqual(payload["adapter_id"], "local_fixture_runner_stub_admission_gate")
        self.assertEqual(payload["capability"], "launch_local_fixture_runner_stub_admission_gate")
        self.assertEqual(payload["gate_id"], "runner-stub-gate-001")
        self.assertEqual(payload["reviewer_id"], "reviewer-001")
        self.assertEqual(payload["human_approval_artifact_result_path"], human_path.as_posix())
        self.assertEqual(payload["human_approval_artifact_result_sha256"], sha256_file(human_path))
        self.assertEqual(payload["runner_contract_draft_result_path"], contract_path.as_posix())
        self.assertEqual(payload["runner_contract_draft_result_sha256"], sha256_file(contract_path))
        self.assertEqual(payload["gate_status"], "local_fixture_runner_stub_admission_gate_completed")
        self.assertEqual(payload["gate_decision"], "record_runner_stub_admission_gate_only")
        self.assertTrue(payload["metadata_only"])
        self.assertTrue(payload["future_runner_stub_requires_separate_pr"])
        self.assertTrue(payload["future_runner_stub_requires_no_network"])
        self.assertTrue(payload["future_runner_stub_requires_no_browser"])
        self.assertTrue(payload["future_runner_stub_requires_no_production"])
        self.assertTrue(payload["future_runner_stub_requires_receipt_contract"])
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_runner_stub_admission_gate_before_runner_stub_pr",
        )
        self.assertEqual(payload["rejection_reasons"], [])
        for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        self.assertEqual(set(path.name for path in output_dir.iterdir()), set(EXPECTED_OUTPUT_FILES))

    def test_missing_human_approval_result_rejects(self):
        root, _human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(root / "missing-human.json", contract_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("human_approval_artifact_result_missing", result.rejection_reasons)
        self.assertTrue(result.result_path.exists())

    def test_missing_runner_contract_result_rejects(self):
        root, human_path, _contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, root / "missing-contract.json", output_dir)

        self.assertFalse(result.complete)
        self.assertIn("runner_contract_draft_result_missing", result.rejection_reasons)
        self.assertTrue(result.result_path.exists())

    def test_symlink_source_rejects(self):
        root, human_path, contract_path, output_dir = self.make_workspace()
        link = root / "human-link.json"
        link.symlink_to(human_path)

        result = self.run_gate(link, contract_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("human_approval_artifact_result_is_symlink", result.rejection_reasons)

    def test_non_json_source_rejects(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()
        human_path.write_text("{", encoding="utf-8")

        result = self.run_gate(human_path, contract_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("human_approval_artifact_result_not_json_object", result.rejection_reasons)

    def test_missing_or_mismatched_attestation_rejects(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        missing = self.run_gate(
            human_path,
            contract_path,
            output_dir,
            review_attestation=None,
        )
        self.assertFalse(missing.complete)
        self.assertIn("review_attestation_missing", missing.rejection_reasons)

        second_output = output_dir.parent / "gate-output-2"
        second_output.mkdir()
        mismatched = self.run_gate(
            human_path,
            contract_path,
            second_output,
            review_attestation="wrong",
        )
        self.assertFalse(mismatched.complete)
        self.assertIn("review_attestation_mismatch", mismatched.rejection_reasons)

    def test_empty_gate_id_rejects(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, contract_path, output_dir, gate_id="")

        self.assertFalse(result.complete)
        self.assertIn("gate_id_missing", result.rejection_reasons)

    def test_empty_reviewer_id_rejects(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, contract_path, output_dir, reviewer_id="")

        self.assertFalse(result.complete)
        self.assertIn("reviewer_id_missing", result.rejection_reasons)

    def test_output_collision_rejects_without_overwrite(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()
        collision = output_dir / LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE
        collision.write_text('{"kept": true}\n', encoding="utf-8")

        result = self.run_gate(human_path, contract_path, output_dir)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(read_json(collision), {"kept": True})
        self.assertEqual([path.name for path in output_dir.iterdir()], [collision.name])

    def test_human_approval_token_issued_true_rejects(self):
        result = self.assert_rejects_human_mutation(
            lambda payload: payload.update({"approval_token_issued": True})
        )
        self.assertIn("human_approval_token_issued_forbidden_true", result.rejection_reasons)

    def test_human_runner_created_true_rejects(self):
        result = self.assert_rejects_human_mutation(
            lambda payload: payload.update({"runner_created": True})
        )
        self.assertIn("human_runner_created_forbidden_true", result.rejection_reasons)

    def test_human_adapter_execution_performed_true_rejects(self):
        result = self.assert_rejects_human_mutation(
            lambda payload: payload.update({"adapter_execution_performed": True})
        )
        self.assertIn("human_adapter_execution_performed_forbidden_true", result.rejection_reasons)

    def test_runner_contract_execution_token_issued_true_rejects(self):
        result = self.assert_rejects_contract_mutation(
            lambda payload: payload.update({"execution_token_issued": True})
        )
        self.assertIn(
            "runner_contract_execution_token_issued_forbidden_true",
            result.rejection_reasons,
        )

    def test_runner_contract_browser_open_performed_true_rejects(self):
        result = self.assert_rejects_contract_mutation(
            lambda payload: payload.update({"browser_open_performed": True})
        )
        self.assertIn(
            "runner_contract_browser_open_performed_forbidden_true",
            result.rejection_reasons,
        )

    def test_runner_contract_network_access_performed_true_rejects(self):
        result = self.assert_rejects_contract_mutation(
            lambda payload: payload.update({"network_access_performed": True})
        )
        self.assertIn(
            "runner_contract_network_access_performed_forbidden_true",
            result.rejection_reasons,
        )

    def test_source_identity_mismatch_rejects(self):
        result = self.assert_rejects_contract_mutation(
            lambda payload: payload.update({"repo_full_name": "wrong/repo"})
        )
        self.assertIn("source_repo_full_name_mismatch", result.rejection_reasons)

    def test_artifact_index_includes_all_output_artifacts_and_hashes(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, contract_path, output_dir)
        artifact_index = read_json(result.artifact_index_path)
        entries = artifact_index["entries"]

        self.assertEqual(artifact_index["indexed_artifacts"], len(EXPECTED_OUTPUT_FILES))
        self.assertEqual(
            {entry["relative_path"] for entry in entries},
            set(EXPECTED_OUTPUT_FILES),
        )
        deferred = {"artifact_index.json", "artifact_index_manifest.json"}
        for entry in entries:
            path = Path(entry["path"])
            self.assertTrue(path.exists(), entry)
            if entry["relative_path"] not in deferred:
                self.assertEqual(entry["sha256"], sha256_file(path))
                self.assertGreater(entry["size_bytes"], 0)
            else:
                self.assertIsNone(entry["sha256"])

    def test_artifact_index_manifest_verifies_artifact_index_hash(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, contract_path, output_dir)
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
        self.assertEqual(
            set(manifest["indexed_relative_paths"]),
            set(EXPECTED_OUTPUT_FILES),
        )

    def test_summary_contains_no_executable_command_material(self):
        _root, human_path, contract_path, output_dir = self.make_workspace()

        result = self.run_gate(human_path, contract_path, output_dir)
        text = result.summary_path.read_text(encoding="utf-8").lower()

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

    def test_source_module_doc_contain_no_forbidden_live_execution_affordances(self):
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


if __name__ == "__main__":
    unittest.main()
