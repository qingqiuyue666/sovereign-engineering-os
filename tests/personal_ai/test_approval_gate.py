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
from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.job_package import build_local_job_package


EXPECTED_REQUEST_KEYS = {
    "request_type",
    "approval_request_version",
    "authority",
    "execution_capability",
    "job_id",
    "job_dir",
    "requested_action",
    "source_artifacts",
    "source_artifact_hashes",
    "final_job_manifest_sha256",
    "spreadsheet_structural_report_json_sha256",
    "spreadsheet_structural_report_md_sha256",
    "approval_request_sha256_excluding_self",
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
    "provenance_chain.json",
    "approved_output_validation.json",
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

    def build_request(self, root, job_result):
        request_path = root / "approval_request.json"
        request_result = build_output_approval_request(
            job_result.job_dir,
            request_path,
        )
        return request_path, request_result

    def valid_decision(
        self,
        request_result,
        *,
        job_id="job-001",
        approved=True,
        human_reviewed=True,
    ):
        hashes = request_result.source_artifact_hashes
        return {
            "decision_type": "personal_ai_local_output_approval_decision",
            "decision_version": 1,
            "job_id": job_id,
            "approved": approved,
            "approved_action": "create_approved_output_package",
            "human_reviewed": human_reviewed,
            "approval_request_sha256": request_result.approval_request_sha256,
            "final_job_manifest_sha256": hashes["final_job_manifest"],
            "spreadsheet_structural_report_json_sha256": hashes[
                "spreadsheet_structural_report_json"
            ],
            "spreadsheet_structural_report_md_sha256": hashes[
                "spreadsheet_structural_report_markdown"
            ],
        }

    def validation_kwargs(self, job_result, request_path):
        return {
            "expected_job_id": "job-001",
            "approval_request_path": request_path,
            "final_job_manifest_path": job_result.final_job_manifest_path,
            "spreadsheet_structural_report_json_path": (
                job_result.spreadsheet_structural_report_json_path
            ),
            "spreadsheet_structural_report_markdown_path": (
                job_result.spreadsheet_structural_report_markdown_path
            ),
        }

    def write_decision(self, root, payload):
        approval_decision_path = root / "approval_decision.json"
        write_json(approval_decision_path, payload)
        return approval_decision_path

    def test_builds_approval_request_json(self):
        root, _, job_result = self.build_workspace()
        request_path, result = self.build_request(root, job_result)
        request = read_json(request_path)

        self.assertIsInstance(result, OutputApprovalRequestResult)
        self.assertEqual(result.job_dir, job_result.job_dir)
        self.assertEqual(result.output_request_path, request_path)
        self.assertEqual(set(request), EXPECTED_REQUEST_KEYS)
        self.assertEqual(
            request["request_type"],
            "personal_ai_local_output_approval_request",
        )
        self.assertEqual(request["approval_request_version"], 1)
        self.assertEqual(
            request["output_package_contents"],
            EXPECTED_OUTPUT_CONTENTS,
        )
        self.assertEqual(
            request["requested_action"],
            "create_approved_output_package",
        )

    def test_approval_request_contains_source_artifact_hashes(self):
        root, _, job_result = self.build_workspace()
        request_path, result = self.build_request(root, job_result)
        request = read_json(request_path)

        self.assertEqual(
            set(request["source_artifact_hashes"]),
            {
                "final_job_manifest",
                "spreadsheet_structural_report_json",
                "spreadsheet_structural_report_markdown",
            },
        )
        self.assertEqual(
            request["source_artifact_hashes"],
            result.source_artifact_hashes,
        )

    def test_approval_request_contains_required_artifact_hash_fields(self):
        root, _, job_result = self.build_workspace()
        request_path, result = self.build_request(root, job_result)
        request = read_json(request_path)

        self.assertEqual(
            request["final_job_manifest_sha256"],
            result.source_artifact_hashes["final_job_manifest"],
        )
        self.assertEqual(
            request["spreadsheet_structural_report_json_sha256"],
            result.source_artifact_hashes["spreadsheet_structural_report_json"],
        )
        self.assertEqual(
            request["spreadsheet_structural_report_md_sha256"],
            result.source_artifact_hashes[
                "spreadsheet_structural_report_markdown"
            ],
        )

    def test_approval_request_self_hash_verifies_by_recomputing_excluding_self(self):
        root, _, job_result = self.build_workspace()
        request_path, result = self.build_request(root, job_result)
        request = read_json(request_path)
        stored_hash = request.pop("approval_request_sha256_excluding_self")

        self.assertEqual(stored_hash, result.approval_request_sha256)
        self.assertEqual(sha256_canonical_json(request), stored_hash)

    def test_approval_request_is_non_authority(self):
        root, _, job_result = self.build_workspace()
        request_path, _ = self.build_request(root, job_result)
        request = read_json(request_path)

        self.assertEqual(request["authority"], "non_authority")
        self.assertEqual(request["execution_capability"], "not_introduced")
        self.assertTrue(request["boundaries"]["no_runtime_authority"])
        self.assertTrue(
            request["boundaries"]["no_arbitrary_execution_capability"]
        )

    def test_approval_request_requires_human_approval(self):
        root, _, job_result = self.build_workspace()
        request_path, result = self.build_request(root, job_result)
        request = read_json(request_path)

        self.assertIs(result.required_human_approval, True)
        self.assertIs(request["required_human_approval"], True)
        self.assertIs(request["approval_required_before_output_package"], True)
        self.assertEqual(request["next_allowed_action"], "human_approval_required")

    def test_approval_request_does_not_copy_raw_sentinel_value(self):
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        root, _, job_result = self.build_workspace(sentinel=sentinel)
        request_path, _ = self.build_request(root, job_result)

        self.assertNotIn(
            sentinel,
            request_path.read_text(encoding="utf-8"),
        )

    def test_source_artifact_tampering_changes_expected_hash(self):
        root, _, job_result = self.build_workspace()
        request_path, _ = self.build_request(root, job_result)
        request = read_json(request_path)
        original_hash = request["source_artifact_hashes"][
            "spreadsheet_structural_report_json"
        ]

        write_json(
            job_result.spreadsheet_structural_report_json_path,
            {"report_status": "tampered"},
        )

        self.assertNotEqual(
            sha256_file(job_result.spreadsheet_structural_report_json_path),
            original_hash,
        )

    def test_validates_correct_hash_bound_approval_decision_json(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        approval_decision_path = self.write_decision(
            root,
            self.valid_decision(request_result),
        )

        result = validate_output_approval_decision(
            approval_decision_path,
            **self.validation_kwargs(job_result, request_path),
        )

        self.assertIsInstance(result, OutputApprovalDecisionResult)
        self.assertEqual(result.approval_decision_path, approval_decision_path)
        self.assertEqual(result.job_id, "job-001")
        self.assertIs(result.approved, True)
        self.assertEqual(result.approved_action, "create_approved_output_package")
        self.assertIs(result.human_reviewed, True)
        self.assertEqual(
            result.approval_request_sha256,
            request_result.approval_request_sha256,
        )
        self.assertIs(result.hash_binding_verified, True)

    def test_rejects_missing_approval_decision(self):
        root, _, job_result = self.build_workspace()
        request_path, _ = self.build_request(root, job_result)

        with self.assertRaisesRegex(ValueError, "approval_decision_path is missing"):
            validate_output_approval_decision(
                root / "missing.json",
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_malformed_json(self):
        root, _, job_result = self.build_workspace()
        request_path, _ = self.build_request(root, job_result)
        approval_decision_path = root / "approval_decision.json"
        approval_decision_path.write_text("{not-json", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "malformed"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_missing_decision_version(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        del decision["decision_version"]
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "decision_version"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_wrong_decision_version(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["decision_version"] = 2
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "decision_version mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_job_id_mismatch(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        approval_decision_path = self.write_decision(
            root,
            self.valid_decision(request_result, job_id="other-job"),
        )

        with self.assertRaisesRegex(ValueError, "job_id mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_approved_false(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        approval_decision_path = self.write_decision(
            root,
            self.valid_decision(request_result, approved=False),
        )

        with self.assertRaisesRegex(ValueError, "approved must be true"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_human_reviewed_false(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        approval_decision_path = self.write_decision(
            root,
            self.valid_decision(request_result, human_reviewed=False),
        )

        with self.assertRaisesRegex(ValueError, "human_reviewed must be true"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_approved_action_mismatch(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["approved_action"] = "write_spreadsheet_outputs"
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "approved_action mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_decision_type_mismatch(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["decision_type"] = "freeform_approval"
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "decision_type mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_wrong_approval_request_hash(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["approval_request_sha256"] = "0" * 64
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "approval_request_sha256 mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_wrong_final_job_manifest_hash(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["final_job_manifest_sha256"] = "0" * 64
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(ValueError, "final_job_manifest_sha256 mismatch"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_wrong_structural_json_hash(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["spreadsheet_structural_report_json_sha256"] = "0" * 64
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(
            ValueError,
            "spreadsheet_structural_report_json_sha256 mismatch",
        ):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_wrong_structural_markdown_hash(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        decision = self.valid_decision(request_result)
        decision["spreadsheet_structural_report_md_sha256"] = "0" * 64
        approval_decision_path = self.write_decision(root, decision)

        with self.assertRaisesRegex(
            ValueError,
            "spreadsheet_structural_report_md_sha256 mismatch",
        ):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )

    def test_rejects_artifact_tampering_after_approval_request(self):
        root, _, job_result = self.build_workspace()
        request_path, request_result = self.build_request(root, job_result)
        approval_decision_path = self.write_decision(
            root,
            self.valid_decision(request_result),
        )
        write_json(
            job_result.final_job_manifest_path,
            {"manifest_type": "tampered"},
        )

        with self.assertRaisesRegex(ValueError, "final_job_manifest"):
            validate_output_approval_decision(
                approval_decision_path,
                **self.validation_kwargs(job_result, request_path),
            )


if __name__ == "__main__":
    unittest.main()
