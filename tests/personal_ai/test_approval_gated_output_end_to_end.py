import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.local_mvp_cli import main


EXPECTED_OUTPUT_FILES = {
    "approved_output_manifest.json",
    "delivery_summary.json",
    "approval_receipt.json",
    "provenance_chain.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
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


def sha256_bytes(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ApprovalGatedOutputEndToEndTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, stdout.getvalue()

    def test_approval_gated_output_package_end_to_end(self):
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
        csv_path = input_dir / "data.csv"
        csv_path.write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        before = {
            csv_path: (
                csv_path.read_bytes(),
                sha256_bytes(csv_path),
                csv_path.stat().st_mtime_ns,
            )
        }

        first_exit_code, first_output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                job_output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        first_payload = json.loads(first_output)
        self.assertEqual(first_exit_code, 0)
        self.assertIs(first_payload["complete"], True)

        approval_request_path = root / "approval_request.json"
        request_exit_code, request_output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                job_output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--write-approval-request",
                approval_request_path.as_posix(),
            ]
        )
        request_payload = json.loads(request_output)
        approval_request = read_json(approval_request_path)
        hashes = approval_request["source_artifact_hashes"]
        self.assertEqual(request_exit_code, 0)
        self.assertEqual(
            request_payload["approval_request_sha256"],
            approval_request["approval_request_sha256_excluding_self"],
        )

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
                "approval_request_sha256": request_payload[
                    "approval_request_sha256"
                ],
                "final_job_manifest_sha256": hashes["final_job_manifest"],
                "spreadsheet_structural_report_json_sha256": hashes[
                    "spreadsheet_structural_report_json"
                ],
                "spreadsheet_structural_report_md_sha256": hashes[
                    "spreadsheet_structural_report_markdown"
                ],
            },
        )

        second_exit_code, second_output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                job_output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--approval-request",
                approval_request_path.as_posix(),
                "--approval-decision",
                approval_decision_path.as_posix(),
                "--output-package-root-dir",
                output_package_root_dir.as_posix(),
                "--output-package-id",
                "approved-001",
            ]
        )
        second_payload = json.loads(second_output)
        output_package_dir = Path(second_payload["approved_output_package_dir"])

        self.assertEqual(second_exit_code, 0)
        self.assertIs(second_payload["complete"], True)
        self.assertIs(second_payload["approval_verified"], True)
        self.assertIs(second_payload["output_package_complete"], True)
        self.assertTrue(output_package_dir.exists())
        self.assertEqual(
            {path.name for path in output_package_dir.iterdir()},
            EXPECTED_OUTPUT_FILES,
        )
        for artifact_name in EXPECTED_OUTPUT_FILES:
            self.assertTrue((output_package_dir / artifact_name).exists())
        for artifact_path in output_package_dir.iterdir():
            self.assertNotIn(
                sentinel,
                artifact_path.read_text(encoding="utf-8"),
                msg=artifact_path.name,
            )

        for path, (expected_bytes, expected_sha, expected_mtime) in before.items():
            self.assertEqual(path.read_bytes(), expected_bytes)
            self.assertEqual(sha256_bytes(path), expected_sha)
            self.assertEqual(path.stat().st_mtime_ns, expected_mtime)

        self.assertEqual(
            {
                path.name
                for path in output_package_dir.iterdir()
                if path.suffix in SPREADSHEET_OUTPUT_SUFFIXES
            },
            set(),
        )
        manifest = read_json(output_package_dir / "approved_output_manifest.json")
        provenance = read_json(output_package_dir / "provenance_chain.json")
        self.assertIs(manifest["complete"], True)
        self.assertIs(provenance["hash_binding_verified"], True)


if __name__ == "__main__":
    unittest.main()
