import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.approval_gate import build_output_approval_request
from kernel.personal_ai.job_package import build_local_job_package
from kernel.personal_ai.output_package import build_approved_output_package
from kernel.personal_ai.output_validator import (
    ApprovedOutputValidationResult,
    build_approved_output_validation,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ApprovedOutputValidationTests(unittest.TestCase):
    def build_output_package(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        job_output_root_dir = root / "jobs"
        output_package_root_dir = root / "approved"
        input_dir.mkdir()
        job_output_root_dir.mkdir()
        output_package_root_dir.mkdir()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        job_result = build_local_job_package(
            input_dir,
            job_output_root_dir,
            job_id="job-001",
        )
        approval_request_path = root / "approval_request.json"
        approval_request = build_output_approval_request(
            job_result.job_dir,
            approval_request_path,
        )
        approval_decision_path = root / "approval_decision.json"
        hashes = approval_request.source_artifact_hashes
        write_json(
            approval_decision_path,
            {
                "decision_type": "personal_ai_local_output_approval_decision",
                "decision_version": 1,
                "job_id": "job-001",
                "approved": True,
                "approved_action": "create_approved_output_package",
                "human_reviewed": True,
                "approval_request_sha256": approval_request.approval_request_sha256,
                "final_job_manifest_sha256": hashes["final_job_manifest"],
                "spreadsheet_structural_report_json_sha256": hashes[
                    "spreadsheet_structural_report_json"
                ],
                "spreadsheet_structural_report_md_sha256": hashes[
                    "spreadsheet_structural_report_markdown"
                ],
            },
        )
        output_result = build_approved_output_package(
            job_result.job_dir,
            output_package_root_dir,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )
        return output_result, sentinel

    def test_writes_complete_approved_output_validation(self):
        output_result, sentinel = self.build_output_package()
        validation = read_json(output_result.approved_output_validation_path)

        self.assertEqual(
            validation["validation_type"],
            "personal_ai_local_v1_approved_output_validation",
        )
        self.assertIs(validation["complete"], True)
        self.assertIs(validation["manifest_hashes_verified"], True)
        self.assertIs(validation["approval_verified"], True)
        self.assertIs(validation["provenance_verified"], True)
        self.assertIs(validation["boundaries_verified"], True)
        self.assertIs(validation["raw_sentinel_leakage_detected"], False)
        self.assertIs(validation["spreadsheet_output_written"], False)
        self.assertNotIn(
            sentinel,
            output_result.approved_output_validation_path.read_text(
                encoding="utf-8",
            ),
        )

    def test_detects_tampered_output_artifact_hash(self):
        output_result, _ = self.build_output_package()
        (output_result.output_package_dir / "delivery_summary.json").write_text(
            json.dumps({"tampered": True}) + "\n",
            encoding="utf-8",
        )

        result = build_approved_output_validation(output_result.output_package_dir)

        self.assertIsInstance(result, ApprovedOutputValidationResult)
        self.assertIs(result.complete, False)
        self.assertIs(result.manifest_hashes_verified, False)

    def test_detects_spreadsheet_output_files(self):
        output_result, _ = self.build_output_package()
        (output_result.output_package_dir / "forbidden_output.xlsx").write_text(
            "not allowed",
            encoding="utf-8",
        )

        result = build_approved_output_validation(output_result.output_package_dir)

        self.assertIs(result.complete, False)
        self.assertEqual(result.spreadsheet_output_files, ["forbidden_output.xlsx"])
