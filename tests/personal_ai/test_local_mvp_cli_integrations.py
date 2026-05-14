import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.local_mvp_cli import main


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class LocalMVPCLIIntegrationCommandTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        approved_root_dir = root / "approved"
        input_dir.mkdir()
        output_root_dir.mkdir()
        approved_root_dir.mkdir()
        (input_dir / "data.csv").write_text(
            "account,value\nalpha,RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY\n",
            encoding="utf-8",
        )
        return root, input_dir, output_root_dir, approved_root_dir

    def test_run_local_subcommand_preserves_legacy_behavior(self):
        _, input_dir, output_root_dir, _ = self.build_workspace()

        exit_code, payload = self.run_cli(
            [
                "run-local",
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertIs(payload["complete"], True)
        self.assertIn("artifact_index_path", payload)
        self.assertIn("job_package_validation_path", payload)

    def test_validate_and_index_subcommands_write_safe_outputs(self):
        _, input_dir, output_root_dir, _ = self.build_workspace()
        _, run_payload = self.run_cli(
            [
                "run-local",
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        job_dir = Path(run_payload["job_dir"])

        validate_exit_code, validate_payload = self.run_cli(
            [
                "validate-job",
                "--job-dir",
                job_dir.as_posix(),
            ]
        )
        index_exit_code, index_payload = self.run_cli(
            [
                "index-artifacts",
                "--job-dir",
                job_dir.as_posix(),
            ]
        )

        self.assertEqual(validate_exit_code, 0)
        self.assertIs(validate_payload["complete"], True)
        self.assertEqual(index_exit_code, 0)
        self.assertGreater(index_payload["indexed_artifacts"], 0)
        self.assertTrue((job_dir / "job_package_validation.json").exists())
        self.assertTrue((job_dir / "artifact_index.json").exists())

    def test_approval_subcommands_create_validated_output_package(self):
        root, input_dir, output_root_dir, approved_root_dir = self.build_workspace()
        _, run_payload = self.run_cli(
            [
                "run-local",
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        job_dir = Path(run_payload["job_dir"])
        approval_request_path = root / "approval_request.json"

        request_exit_code, request_payload = self.run_cli(
            [
                "write-approval-request",
                "--job-dir",
                job_dir.as_posix(),
                "--output-path",
                approval_request_path.as_posix(),
            ]
        )
        approval_request = read_json(approval_request_path)
        hashes = approval_request["source_artifact_hashes"]
        approval_decision_path = root / "approval_decision.json"
        approval_decision_path.write_text(
            json.dumps(
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
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        output_exit_code, output_payload = self.run_cli(
            [
                "create-approved-output",
                "--job-dir",
                job_dir.as_posix(),
                "--approval-request",
                approval_request_path.as_posix(),
                "--approval-decision",
                approval_decision_path.as_posix(),
                "--output-package-root-dir",
                approved_root_dir.as_posix(),
                "--output-package-id",
                "approved-001",
            ]
        )
        output_package_dir = Path(output_payload["approved_output_package_dir"])

        self.assertEqual(request_exit_code, 0)
        self.assertEqual(output_exit_code, 0)
        self.assertIs(output_payload["complete"], True)
        self.assertTrue((output_package_dir / "approved_output_validation.json").exists())
        self.assertIs(
            read_json(output_package_dir / "approved_output_validation.json")[
                "complete"
            ],
            True,
        )
