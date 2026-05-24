import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.local_fixture_runner_receipt_contract_draft import (
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FORBIDDEN_FUTURE_INPUTS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_TRUE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_TRUE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE,
    run_local_fixture_runner_receipt_contract_draft,
)
from kernel.personal_ai.hash_utils import sha256_file


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_receipt_contract_draft.py"
)
DECISION_DOC = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_runner_receipt_contract_draft_v1.md"
)
EXPECTED_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalFixtureRunnerReceiptContractDraftTests(unittest.TestCase):
    def make_output_dir(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_dir = Path(temp_dir.name) / "receipt-contract-output"
        output_dir.mkdir()
        return Path(temp_dir.name), output_dir

    def run_contract(
        self,
        output_dir,
        *,
        receipt_contract_id="receipt-contract-001",
        reviewer_id="reviewer-001",
        review_attestation=(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION
        ),
    ):
        return run_local_fixture_runner_receipt_contract_draft(
            output_dir,
            receipt_contract_id,
            reviewer_id,
            review_attestation,
            project_id="project-001",
            operator_notes="reviewed local-fixture runner receipt contract draft",
        )

    def test_valid_contract_draft_writes_all_seven_artifacts(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertTrue(result.contract_recorded)
        self.assertEqual(
            payload["contract_type"],
            "local_fixture_runner_receipt_contract_draft_v1",
        )
        self.assertEqual(
            payload["authority"],
            "non_authority_receipt_contract_draft_only",
        )
        self.assertEqual(
            payload["adapter_id"],
            "local_fixture_runner_receipt_contract_draft",
        )
        self.assertEqual(
            payload["capability"],
            "launch_local_fixture_runner_receipt_contract_draft",
        )
        self.assertEqual(payload["receipt_contract_id"], "receipt-contract-001")
        self.assertEqual(payload["reviewer_id"], "reviewer-001")
        self.assertTrue(payload["contract_recorded"])
        self.assertEqual(
            payload["receipt_contract_status"],
            "local_fixture_runner_receipt_contract_draft_completed",
        )
        self.assertEqual(
            payload["receipt_contract_decision"],
            "record_runner_receipt_contract_draft_only",
        )
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_runner_receipt_contract_before_runner_stub_pr",
        )
        self.assertEqual(payload["rejection_reasons"], [])
        self.assertEqual(
            set(path.name for path in output_dir.iterdir()),
            set(EXPECTED_OUTPUT_FILES),
        )
        for file_name in EXPECTED_OUTPUT_FILES:
            self.assertTrue((output_dir / file_name).is_file(), file_name)

    def test_missing_receipt_contract_id_rejects(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir, receipt_contract_id="")
        payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertFalse(payload["contract_recorded"])
        self.assertEqual(
            payload["receipt_contract_status"],
            "local_fixture_runner_receipt_contract_draft_rejected",
        )
        self.assertEqual(
            payload["receipt_contract_decision"],
            "reject_runner_receipt_contract_draft",
        )
        self.assertIn("receipt_contract_id_missing", result.rejection_reasons)
        self.assertEqual(
            payload["next_allowed_action"],
            "fix_runner_receipt_contract_draft_and_retry",
        )

    def test_missing_reviewer_id_rejects(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir, reviewer_id="")
        payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertIn("reviewer_id_missing", result.rejection_reasons)
        self.assertFalse(payload["contract_recorded"])

    def test_missing_review_attestation_rejects(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir, review_attestation=None)
        payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertIn("review_attestation_missing", result.rejection_reasons)
        self.assertFalse(payload["contract_recorded"])

    def test_wrong_review_attestation_rejects(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir, review_attestation="wrong")
        payload = read_json(result.result_path)

        self.assertFalse(result.complete)
        self.assertIn("review_attestation_mismatch", result.rejection_reasons)
        self.assertFalse(payload["contract_recorded"])

    def test_missing_output_dir_rejects_without_creating_it(self):
        root, _output_dir = self.make_output_dir()
        missing_output = root / "missing-output"

        result = self.run_contract(missing_output)

        self.assertFalse(result.complete)
        self.assertIn("output_dir_missing", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertFalse(missing_output.exists())

    def test_symlink_output_dir_rejects(self):
        root, output_dir = self.make_output_dir()
        symlink_output = root / "output-link"
        symlink_output.symlink_to(output_dir)

        result = self.run_contract(symlink_output)

        self.assertFalse(result.complete)
        self.assertIn("output_dir_symlink_rejected", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(list(output_dir.iterdir()), [])

    def test_output_collision_rejects_without_overwriting(self):
        _root, output_dir = self.make_output_dir()
        collision = (
            output_dir / LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE
        )
        collision.write_text('{"existing": true}\n', encoding="utf-8")

        result = self.run_contract(output_dir)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)
        self.assertEqual(collision.read_text(encoding="utf-8"), '{"existing": true}\n')
        self.assertEqual([path.name for path in output_dir.iterdir()], [collision.name])

    def test_result_contains_required_true_fields(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        payload = read_json(result.result_path)

        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_TRUE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertTrue(payload[field_name], field_name)
        expectations = payload["future_receipt_required_field_expectations"]
        for field_name in (
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_TRUE_FIELDS
        ):
            self.assertIs(expectations[field_name], True, field_name)

    def test_result_contains_required_false_fields(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        payload = read_json(result.result_path)

        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        expectations = payload["future_receipt_required_field_expectations"]
        for field_name in (
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FALSE_FIELDS
        ):
            self.assertIs(expectations[field_name], False, field_name)

    def test_result_defines_required_future_inputs(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        payload = read_json(result.result_path)

        self.assertEqual(
            tuple(payload["future_receipt_required_inputs"]),
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS,
        )
        self.assertEqual(
            tuple(payload["future_receipt_required_fields"]),
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS,
        )
        expectations = payload["future_receipt_required_field_expectations"]
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS:
            self.assertIn(field_name, expectations)

    def test_result_defines_required_future_outputs(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        payload = read_json(result.result_path)

        self.assertEqual(
            tuple(payload["future_receipt_required_outputs"]),
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS,
        )

    def test_result_defines_forbidden_future_inputs(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        payload = read_json(result.result_path)

        self.assertEqual(
            tuple(payload["future_receipt_forbidden_inputs"]),
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FORBIDDEN_FUTURE_INPUTS,
        )

    def test_json_output_contains_no_command_or_argv_executable_fields(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)

        forbidden_key_names = {
            "command",
            "argv",
            "runner_command",
            "browser_launch_command",
            "playwright_command",
            "npm_command",
            "npx_command",
            "shell_command",
            "execution_command",
        }
        for json_path in (
            result.contract_path,
            result.result_path,
            result.manifest_path,
            result.artifact_index_path,
            result.artifact_index_manifest_path,
        ):
            payload = read_json(json_path)
            for key, _value in self.walk_json(payload):
                key_lower = key.lower()
                self.assertNotIn(key_lower, forbidden_key_names, (json_path, key))
                self.assertNotIn("command", key_lower, (json_path, key))
                self.assertNotIn("argv", key_lower, (json_path, key))

    def test_summary_contains_warning_language_and_no_executable_material(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
        text = result.summary_path.read_text(encoding="utf-8")

        required_fragments = (
            "This is a receipt contract draft only.",
            "This is not a runner.",
            "This does not create a runner stub.",
            "This does not create a runnable job.",
            "This does not execute adapter.",
            "This does not launch Playwright.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not issue approval material.",
            "This does not issue execution material.",
            "This does not authorize production.",
            "Future runner receipt implementation requires a separate PR.",
            "Future runner stub implementation requires a separate PR.",
            "future receipt required inputs:",
            "future receipt required outputs:",
            "future receipt required fields:",
            "forbidden future input categories:",
            "rejected materialization:",
            "next_allowed_action: human_review_runner_receipt_contract_before_runner_stub_pr",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, text)

        lowered = text.lower()
        forbidden_fragments = (
            "```",
            "$ ",
            "shell snippet",
            "approval token:",
            "execution token:",
            "runner command",
            "browser launch command",
            "playwright command",
            "npm ",
            "npx",
            "python3 ",
            "--output-dir",
            "--receipt-contract-id",
            "--review-attestation",
            "--execute",
            "browser.launch",
            "page.goto",
            "subprocess",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, lowered)

    def test_artifact_index_includes_all_outputs_and_hashes(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
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
                self.assertTrue(
                    entry["hash_deferred_to_manifest"]
                    or entry["hash_unavailable_without_self_reference"]
                )

    def test_artifact_index_manifest_verifies_artifact_index_hash(self):
        _root, output_dir = self.make_output_dir()

        result = self.run_contract(output_dir)
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

    def test_decision_doc_states_contract_only_boundary(self):
        text = " ".join(DECISION_DOC.read_text(encoding="utf-8").split())
        required_fragments = (
            "contract draft only",
            "not a runner",
            "does not create a runner stub",
            "does not create a runnable job",
            "does not issue approval material",
            "does not issue execution material",
            "does not execute the adapter",
            "does not execute Playwright",
            "does not open a browser",
            "does not access the network",
            "does not authorize live websites",
            "does not promote production",
            "does not add a daemon, scheduler, or worker loop",
            "Future receipt implementation requires a separate PR",
            "Future runner stub implementation requires a separate PR",
            "verified runner stub admission gate result path",
            "verified human approval artifact result path",
            "verified runner contract draft result path",
            "local_fixture_runner_receipt.json",
            "local_fixture_runner_receipt_result.json",
            "local_fixture_runner_receipt_manifest.json",
            "local_fixture_runner_receipt_summary.md",
            "local_fixture_runner_receipt_checklist.md",
            "artifact_index_manifest.json",
            "human_review_runner_receipt_contract_before_runner_stub_pr",
            "fix_runner_receipt_contract_draft_and_retry",
        )
        for fragment in required_fragments:
            self.assertIn(" ".join(fragment.split()), text)

    def test_source_module_doc_contain_no_forbidden_live_execution_affordances(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        doc = DECISION_DOC.read_text(encoding="utf-8")
        combined = source + "\n" + doc
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
        lowered = combined.lower()
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment.lower(), lowered)

    def walk_json(self, value, prefix=""):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from self.walk_json(child, str(key))
        elif isinstance(value, list):
            for child in value:
                yield from self.walk_json(child, prefix)
        else:
            yield prefix, value


if __name__ == "__main__":
    unittest.main()
