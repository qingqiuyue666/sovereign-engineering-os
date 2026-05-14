import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.approval_gate import build_output_approval_request
from kernel.personal_ai.approval_provenance import (
    ApprovalProvenanceChainResult,
    build_approval_provenance_chain,
)
from kernel.personal_ai.job_package import build_local_job_package
from kernel.personal_ai.output_package import build_approved_output_package


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ApprovalProvenanceTests(unittest.TestCase):
    def build_approved_workspace(
        self,
        sentinel="RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY",
    ):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        job_output_root_dir = root / "jobs"
        output_package_root_dir = root / "approved"
        input_dir.mkdir()
        job_output_root_dir.mkdir()
        output_package_root_dir.mkdir()
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
        approval_decision_path = root / "approval_decision.json"
        write_json(
            approval_decision_path,
            self.valid_decision(approval_request_result),
        )
        output_package_result = build_approved_output_package(
            job_result.job_dir,
            output_package_root_dir,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )
        return (
            root,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )

    def valid_decision(self, approval_request_result):
        hashes = approval_request_result.source_artifact_hashes
        return {
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
        }

    def rebuild_provenance(
        self,
        job_result,
        approval_request_path,
        approval_decision_path,
        output_package_result,
    ):
        return build_approval_provenance_chain(
            job_result.job_dir,
            approval_request_path,
            approval_decision_path,
            output_package_result.output_package_dir,
            output_package_result.provenance_chain_path,
        )

    def test_builds_provenance_chain_json(self):
        (
            _,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        ) = self.build_approved_workspace()

        result = self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )
        provenance = read_json(output_package_result.provenance_chain_path)

        self.assertIsInstance(result, ApprovalProvenanceChainResult)
        self.assertEqual(
            provenance["provenance_type"],
            "personal_ai_local_v1_approval_provenance_chain",
        )
        self.assertIn("artifact_hashes", provenance)

    def test_chain_complete_and_hash_binding_verified_for_valid_package(self):
        (
            _,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        ) = self.build_approved_workspace()

        result = self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )
        provenance = read_json(output_package_result.provenance_chain_path)

        self.assertIs(result.chain_complete, True)
        self.assertIs(result.hash_binding_verified, True)
        self.assertIs(provenance["chain_complete"], True)
        self.assertIs(provenance["hash_binding_verified"], True)

    def test_missing_artifact_makes_chain_incomplete(self):
        (
            _,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        ) = self.build_approved_workspace()
        (output_package_result.output_package_dir / "delivery_summary.json").unlink()

        result = self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )
        provenance = read_json(output_package_result.provenance_chain_path)

        self.assertIs(result.chain_complete, False)
        self.assertIn("delivery_summary", result.missing_artifacts)
        self.assertIs(provenance["hash_binding_verified"], False)

    def test_tampered_approval_decision_marks_hash_binding_unverified(self):
        (
            _,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        ) = self.build_approved_workspace()
        decision = read_json(approval_decision_path)
        decision["approval_request_sha256"] = "0" * 64
        write_json(approval_decision_path, decision)

        result = self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )

        self.assertIs(result.hash_binding_verified, False)

    def test_tampered_output_report_after_approval_marks_hash_binding_unverified(self):
        (
            _,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        ) = self.build_approved_workspace()
        write_json(
            output_package_result.output_package_dir
            / "spreadsheet_structural_report.json",
            {"report_status": "tampered"},
        )

        result = self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )

        self.assertIs(result.hash_binding_verified, False)

    def test_provenance_has_no_raw_sentinel_leakage(self):
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (
            _,
            _,
            _,
            _,
            output_package_result,
        ) = self.build_approved_workspace(sentinel=sentinel)

        self.assertNotIn(
            sentinel,
            output_package_result.provenance_chain_path.read_text(
                encoding="utf-8"
            ),
        )

    def test_provenance_records_non_authority_and_no_execution_capability(self):
        (
            _,
            _,
            _,
            _,
            output_package_result,
        ) = self.build_approved_workspace()
        provenance = read_json(output_package_result.provenance_chain_path)

        self.assertEqual(provenance["authority"], "non_authority")
        self.assertEqual(provenance["execution_capability"], "not_introduced")
        self.assertTrue(provenance["boundaries"]["no_runtime_authority"])

    def test_provenance_output_is_deterministic(self):
        (
            _,
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        ) = self.build_approved_workspace()

        self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )
        first = read_json(output_package_result.provenance_chain_path)
        self.rebuild_provenance(
            job_result,
            approval_request_path,
            approval_decision_path,
            output_package_result,
        )
        second = read_json(output_package_result.provenance_chain_path)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
