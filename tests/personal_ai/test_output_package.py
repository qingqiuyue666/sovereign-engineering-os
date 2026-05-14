import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.approval_gate import build_output_approval_request
from kernel.personal_ai.job_package import build_local_job_package
from kernel.personal_ai.output_package import (
    ApprovedOutputPackageResult,
    build_approved_output_package,
)


EXPECTED_OUTPUT_FILES = {
    "approved_output_manifest.json",
    "delivery_summary.json",
    "approval_receipt.json",
    "provenance_chain.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
    "approved_output_validation.json",
}

SPREADSHEET_OUTPUT_SUFFIXES = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xlsm",
    ".xls",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class OutputPackageTests(unittest.TestCase):
    def build_workspace(self, sentinel="RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        job_output_root_dir = root / "jobs"
        output_package_root_dir = root / "approved"
        input_dir.mkdir()
        job_output_root_dir.mkdir()
        output_package_root_dir.mkdir()
        csv_path = input_dir / "data.csv"
        csv_path.write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
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
        return (
            root,
            input_dir,
            output_package_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
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

    def build_output_package(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        return build_approved_output_package(
            job_result.job_dir,
            output_root_dir,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )

    def test_builds_approved_output_package_after_valid_approval(self):
        result = self.build_output_package()

        self.assertIsInstance(result, ApprovedOutputPackageResult)
        self.assertEqual(result.output_package_id, "approved-001")
        self.assertTrue(result.output_package_dir.exists())
        self.assertTrue(result.approved_output_manifest_path.exists())
        self.assertTrue(result.delivery_summary_path.exists())
        self.assertTrue(result.approval_receipt_path.exists())
        self.assertTrue(result.provenance_chain_path.exists())
        self.assertTrue(result.approved_output_validation_path.exists())
        self.assertIs(result.required_human_approval, True)
        self.assertIs(result.approval_verified, True)
        self.assertIs(result.complete, True)
        self.assertEqual(result.missing_artifacts, [])

    def test_output_package_contains_exactly_required_files(self):
        result = self.build_output_package()

        self.assertEqual(
            {path.name for path in result.output_package_dir.iterdir()},
            EXPECTED_OUTPUT_FILES,
        )

    def test_rejects_missing_job_dir(self):
        (
            root,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            _,
        ) = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "job_dir is missing"):
            build_approved_output_package(
                root / "missing-job",
                output_root_dir,
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_rejects_missing_output_root_dir(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "output_root_dir is missing"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir / "missing-root",
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_rejects_invalid_output_package_id(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "output_package_id is invalid"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir,
                approval_decision_path,
                output_package_id="../bad",
                approval_request_path=approval_request_path,
            )

    def test_rejects_existing_output_package_dir(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        (output_root_dir / "approved-001").mkdir()

        with self.assertRaisesRegex(ValueError, "output_package_dir already exists"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir,
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_rejects_invalid_approval(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        invalid_decision = read_json(approval_decision_path)
        invalid_decision["approved"] = False
        write_json(approval_decision_path, invalid_decision)

        with self.assertRaisesRegex(ValueError, "approved must be true"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir,
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_rejects_old_unbound_approval_decision_without_hashes(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        write_json(
            approval_decision_path,
            {
                "decision_type": "personal_ai_local_output_approval_decision",
                "job_id": "job-001",
                "approved": True,
                "approved_action": "create_approved_output_package",
                "human_reviewed": True,
            },
        )

        with self.assertRaisesRegex(ValueError, "missing required keys"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir,
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_does_not_copy_raw_sentinel_value(self):
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace(sentinel=sentinel)

        result = build_approved_output_package(
            job_result.job_dir,
            output_root_dir,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )

        for artifact_path in result.output_package_dir.iterdir():
            self.assertNotIn(
                sentinel,
                artifact_path.read_text(encoding="utf-8"),
                msg=artifact_path.name,
            )

    def test_does_not_modify_input_files(self):
        (
            _,
            input_dir,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        before = {
            path: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in input_dir.iterdir()
            if path.is_file()
        }

        build_approved_output_package(
            job_result.job_dir,
            output_root_dir,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )

        for path, (expected_bytes, expected_mtime) in before.items():
            self.assertEqual(path.read_bytes(), expected_bytes)
            self.assertEqual(path.stat().st_mtime_ns, expected_mtime)

    def test_output_package_manifest_complete_true(self):
        result = self.build_output_package()
        manifest = read_json(result.approved_output_manifest_path)

        self.assertIs(manifest["complete"], True)
        self.assertEqual(manifest["missing_artifacts"], [])
        self.assertIs(manifest["approval_verified"], True)

    def test_approval_receipt_contains_hash_fields(self):
        result = self.build_output_package()
        receipt = read_json(result.approval_receipt_path)

        self.assertIn("approval_request_sha256", receipt)
        self.assertIn("approval_decision_sha256", receipt)
        self.assertIn("final_job_manifest_sha256", receipt)
        self.assertIn("spreadsheet_structural_report_json_sha256", receipt)
        self.assertIn("spreadsheet_structural_report_md_sha256", receipt)
        self.assertIs(receipt["hash_binding_verified"], True)

    def test_delivery_summary_includes_approval_hash_fields(self):
        result = self.build_output_package()
        delivery_summary = read_json(result.delivery_summary_path)

        self.assertIn("approval_request_sha256", delivery_summary)
        self.assertIn("approval_decision_sha256", delivery_summary)
        self.assertIs(delivery_summary["hash_binding_verified"], True)
        self.assertNotIn("provenance_chain_sha256", delivery_summary)

    def test_approved_output_manifest_includes_provenance_and_artifact_hashes(self):
        result = self.build_output_package()
        manifest = read_json(result.approved_output_manifest_path)

        self.assertIs(manifest["artifact_presence"]["provenance_chain"], True)
        self.assertIn("artifact_hashes", manifest)
        self.assertIn("provenance_chain", manifest["artifact_hashes"])
        self.assertNotIn("approved_output_manifest", manifest["artifact_hashes"])

    def test_tampered_final_job_manifest_causes_approval_rejection(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        write_json(job_result.final_job_manifest_path, {"manifest_type": "tampered"})

        with self.assertRaisesRegex(ValueError, "final_job_manifest"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir,
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_tampered_structural_report_causes_approval_rejection(self):
        (
            _,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        write_json(
            job_result.spreadsheet_structural_report_json_path,
            {"report_status": "tampered"},
        )

        with self.assertRaisesRegex(ValueError, "spreadsheet_structural_report"):
            build_approved_output_package(
                job_result.job_dir,
                output_root_dir,
                approval_decision_path,
                output_package_id="approved-001",
                approval_request_path=approval_request_path,
            )

    def test_no_spreadsheet_output_file_is_written(self):
        result = self.build_output_package()

        self.assertEqual(
            {
                path.name
                for path in result.output_package_dir.iterdir()
                if path.suffix in SPREADSHEET_OUTPUT_SUFFIXES
            },
            set(),
        )

    def test_output_package_metadata_is_deterministic(self):
        (
            root,
            _,
            output_root_dir,
            approval_request_path,
            approval_decision_path,
            job_result,
        ) = self.build_workspace()
        first_root = output_root_dir / "first"
        second_root = output_root_dir / "second"
        first_root.mkdir()
        second_root.mkdir()

        first = build_approved_output_package(
            job_result.job_dir,
            first_root,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )
        second = build_approved_output_package(
            job_result.job_dir,
            second_root,
            approval_decision_path,
            output_package_id="approved-001",
            approval_request_path=approval_request_path,
        )

        self.assertEqual(
            read_json(first.delivery_summary_path),
            read_json(second.delivery_summary_path),
        )
        self.assertEqual(
            read_json(first.approval_receipt_path),
            read_json(second.approval_receipt_path),
        )
        first_provenance = read_json(first.provenance_chain_path)
        second_provenance = read_json(second.provenance_chain_path)
        self.assertEqual(
            first_provenance["approval_request_sha256"],
            second_provenance["approval_request_sha256"],
        )
        self.assertEqual(
            first_provenance["approval_decision_sha256"],
            second_provenance["approval_decision_sha256"],
        )
        self.assertIs(first_provenance["hash_binding_verified"], True)
        self.assertIs(second_provenance["hash_binding_verified"], True)
        self.assertTrue(root.exists())


if __name__ == "__main__":
    unittest.main()
