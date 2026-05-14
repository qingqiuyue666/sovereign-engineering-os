import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.approval_gate import (
    OutputApprovalDecisionResult,
    OutputApprovalRequestResult,
    build_output_approval_request,
    validate_output_approval_decision,
)
from kernel.personal_ai.job_package import build_local_job_package


EXPECTED_REQUEST_KEYS = {
    "request_type",
    "authority",
    "execution_capability",
    "job_id",
    "job_dir",
    "requested_action",
    "source_artifacts",
    "output_package_contents",
    "required_human_approval",
    "approval_required_before_output_package",
    "forbidden_actions",
    "boundaries",
    "next_allowed_action",
}

EXPECTED_OUTPUT_CONTENTS = [
    "approved_output_manifest.json",
    "delivery_summary.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
    "approval_receipt.json",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ApprovalGateTests(unittest.TestCase):
    def build_workspace(self, sentinel="RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "jobs"
        input_dir.mkdir()
        output_root_dir.mkdir()
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        job_result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        return root, input_dir, job_result

    def valid_decision(self, job_id="job-001"):
        return {
            "decision_type": "personal_ai_local_output_approval_decision",
            "job_id": job_id,
            "approved": True,
            "approved_action": "create_approved_output_package",
            "human_reviewed": True,
        }

    def write_decision(self, root, payload):
        approval_decision_path = root / "approval_decision.json"
        write_json(approval_decision_path, payload)
        return approval_decision_path

    def test_builds_approval_request_json(self):
        root, _, job_result = self.build_workspace()
        request_path = root / "approval_request.json"

        result = build_output_approval_request(job_result.job_dir, request_path)
        request = read_json(request_path)

        self.assertIsInstance(result, OutputApprovalRequestResult)
        self.assertEqual(result.job_dir, job_result.job_dir)
        self.assertEqual(result.output_request_path, request_path)
        self.assertEqual(set(request), EXPECTED_REQUEST_KEYS)
        self.assertEqual(
            request["request_type"],
            "personal_ai_local_output_approval_request",
        )
        self.assertEqual(
            request["output_package_contents"],
            EXPECTED_OUTPUT_CONTENTS,
        )
        self.assertEqual(
            request["requested_action"],
            "create_approved_output_package",
        )

    def test_approval_request_is_non_authority(self):
        root, _, job_result = self.build_workspace()
        request_path = root / "approval_request.json"

        build_output_approval_request(job_result.job_dir, request_path)
        request = read_json(request_path)

        self.assertEqual(request["authority"], "non_authority")
        self.assertEqual(request["execution_capability"], "not_introduced")
        self.assertTrue(request["boundaries"]["no_runtime_authority"])
        self.assertTrue(
            request["boundaries"]["no_arbitrary_execution_capability"]
        )

    def test_approval_request_requires_human_approval(self):
        root, _, job_result = self.build_workspace()
        request_path = root / "approval_request.json"

        result = build_output_approval_request(job_result.job_dir, request_path)
        request = read_json(request_path)

        self.assertIs(result.required_human_approval, True)
        self.assertIs(request["required_human_approval"], True)
        self.assertIs(request["approval_required_before_output_package"], True)
        self.assertEqual(request["next_allowed_action"], "human_approval_required")

    def test_validates_correct_approval_decision_json(self):
        root, _, _ = self.build_workspace()
        approval_decision_path = self.write_decision(root, self.valid_decision())

        result = validate_output_approval_decision(
            approval_decision_path,
            expected_job_id="job-001",
        )

        self.assertIsInstance(result, OutputApprovalDecisionResult)
        self.assertEqual(result.approval_decision_path, approval_decision_path)
        self.assertEqual(result.job_id, "job-001")
        self.assertIs(result.approved, True)
        self.assertEqual(result.approved_action, "create_approved_output_package")
        self.assertIs(result.human_reviewed, True)

    def test_rejects_missing_approval_decision(self):
        root, _, _ = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "approval_decision_path is missing"):
            validate_output_approval_decision(
                root / "missing.json",
                expected_job_id="job-001",
            )

    def test_rejects_malformed_json(self):
        root, _, _ = self.build_workspace()
        approval_decision_path = root / "approval_decision.json"
        approval_decision_path.write_text("{not-json", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "malformed"):
            validate_output_approval_decision(
                approval_decision_path,
                expected_job_id="job-001",
            )

    def test_rejects_job_id_mismatch(self):
        root, _, _ = self.build_workspace()
        approval_decision_path = self.write_decision(
            root,
            self.valid_decision(job_id="other-job"),
        )

        with self.assertRaisesRegex(ValueError, "job_id mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                expected_job_id="job-001",
            )

    def test_rejects_approved_false(self):
        root, _, _ = self.build_workspace()
        decision = self.valid_decision()
        decision["approved"] = False
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "approved must be true"):
            validate_output_approval_decision(
                approval_decision_path,
                expected_job_id="job-001",
            )

    def test_rejects_human_reviewed_false(self):
        root, _, _ = self.build_workspace()
        decision = self.valid_decision()
        decision["human_reviewed"] = False
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "human_reviewed must be true"):
            validate_output_approval_decision(
                approval_decision_path,
                expected_job_id="job-001",
            )

    def test_rejects_approved_action_mismatch(self):
        root, _, _ = self.build_workspace()
        decision = self.valid_decision()
        decision["approved_action"] = "write_spreadsheet_outputs"
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "approved_action mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                expected_job_id="job-001",
            )

    def test_rejects_decision_type_mismatch(self):
        root, _, _ = self.build_workspace()
        decision = self.valid_decision()
        decision["decision_type"] = "freeform_approval"
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "decision_type mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                expected_job_id="job-001",
            )

    def test_approval_request_does_not_copy_raw_sentinel_value(self):
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        root, _, job_result = self.build_workspace(sentinel=sentinel)
        request_path = root / "approval_request.json"

        build_output_approval_request(job_result.job_dir, request_path)

        self.assertNotIn(
            sentinel,
            request_path.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
