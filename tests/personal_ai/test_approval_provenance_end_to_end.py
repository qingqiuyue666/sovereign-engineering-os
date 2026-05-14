import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.approval_gate import build_output_approval_request
from kernel.personal_ai.job_package import build_local_job_package
from kernel.personal_ai.output_package import build_approved_output_package


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ApprovalProvenanceEndToEndTests(unittest.TestCase):
    def test_local_v1_approval_hash_chain_end_to_end(self):
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
        approval_request_result = build_output_approval_request(
            job_result.job_dir,
            approval_request_path,
        )
        hashes = approval_request_result.source_artifact_hashes
        approval_decision_path = root / "approval_decision.json"
        write_json(
            approval_decision_path,
            {
                "decision_type": "personal_ai_local_output_approval_decision",
                "decision_version": 1,
                "job_id": "job-001",
                "approved": True,
                "approved_action": "create_approved_output_package",
                "human_reviewed": True,
                "approval_request_sha256": (
                    approval_request_result.approval_request_sha256
                ),
                "final_job_manifest_sha256": hashes["final_job_manifest"],
                "spreadsheet_structural_report_json_sha256": hashes[
                    "spreadsheet_structural_report_json"
                ],
                "spreadsheet_structural_report_md_sha256": hashes[
                    "spreadsheet_structural_report_markdown"
                ],
            },
        )

        output_package_result = build_approved_output_package(
            job_result.job_dir,
            output_package_root_dir,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )

        receipt = read_json(output_package_result.approval_receipt_path)
        manifest = read_json(output_package_result.approved_output_manifest_path)
        provenance = read_json(output_package_result.provenance_chain_path)

        self.assertIs(receipt["hash_binding_verified"], True)
        self.assertIs(manifest["complete"], True)
        self.assertIn("provenance_chain", manifest["artifact_hashes"])
        self.assertIs(provenance["chain_complete"], True)
        self.assertIs(provenance["hash_binding_verified"], True)
        self.assertEqual(
            provenance["approved_output_manifest_sha256"],
            manifest["approved_output_manifest_sha256_excluding_self"],
        )
        self.assertEqual(
            provenance["approval_request_sha256"],
            approval_request_result.approval_request_sha256,
        )
        self.assertNotIn(
            sentinel,
            output_package_result.provenance_chain_path.read_text(
                encoding="utf-8"
            ),
        )


if __name__ == "__main__":
    unittest.main()
