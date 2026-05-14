import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.local_mvp_cli import main


EXPECTED_APPROVED_OUTPUT_FILES = {
    "approved_output_manifest.json",
    "delivery_summary.json",
    "approval_receipt.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
}

FORBIDDEN_IMPORT_PATTERN = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(?:requests|urllib|httpx|anthropic|openai|google|subprocess|"
    r"multiprocessing|playwright|selenium|socket|pandas|openpyxl|xlrd|pyarrow)\b",
    re.MULTILINE,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalMVPCLITests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        return input_dir, output_root_dir

    def valid_decision(self, job_id="job-001", approved=True):
        return {
            "decision_type": "personal_ai_local_output_approval_decision",
            "job_id": job_id,
            "approved": approved,
            "approved_action": "create_approved_output_package",
            "human_reviewed": True,
        }

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, stdout.getvalue()

    def test_cli_runs_full_local_mvp_and_exits_zero(self):
        input_dir, output_root_dir = self.build_workspace()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        (input_dir / "notes.md").write_text("local notes", encoding="utf-8")

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        payload = json.loads(output)

        self.assertEqual(exit_code, 0)
        self.assertIs(payload["complete"], True)
        self.assertEqual(payload["missing_artifacts"], [])
        self.assertIs(payload["required_human_approval"], True)
        self.assertEqual(Path(payload["job_dir"]), output_root_dir / "job-001")
        self.assertTrue((output_root_dir / "job-001" / "final_job_manifest.json").exists())
        self.assertNotIn("approved_output_package_dir", payload)
        self.assertNotIn("approval_verified", payload)
        self.assertNotIn(sentinel, output)

    def test_cli_approval_output_mode_works_with_valid_decision(self):
        input_dir, output_root_dir = self.build_workspace()
        root = input_dir.parent
        output_package_root_dir = root / "approved"
        output_package_root_dir.mkdir()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        first_exit_code, first_output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        first_payload = json.loads(first_output)
        approval_decision_path = root / "approval_decision.json"
        write_json(approval_decision_path, self.valid_decision())

        second_exit_code, second_output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
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

        self.assertEqual(first_exit_code, 0)
        self.assertIs(first_payload["complete"], True)
        self.assertEqual(second_exit_code, 0)
        self.assertIs(second_payload["complete"], True)
        self.assertIs(second_payload["approval_verified"], True)
        self.assertIs(second_payload["output_package_complete"], True)
        self.assertEqual(
            {path.name for path in output_package_dir.iterdir()},
            EXPECTED_APPROVED_OUTPUT_FILES,
        )
        self.assertNotIn(sentinel, second_output)

    def test_cli_rejects_partial_approval_flags(self):
        input_dir, output_root_dir = self.build_workspace()

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--approval-decision",
                (input_dir.parent / "approval_decision.json").as_posix(),
            ]
        )
        payload = json.loads(output)

        self.assertNotEqual(exit_code, 0)
        self.assertIs(payload["complete"], False)
        self.assertIs(payload["approval_verified"], False)
        self.assertIs(payload["output_package_complete"], False)
        self.assertIn("failure_quarantine_path", payload)

    def test_cli_rejects_approval_decision_approved_false(self):
        input_dir, output_root_dir = self.build_workspace()
        root = input_dir.parent
        output_package_root_dir = root / "approved"
        output_package_root_dir.mkdir()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        approval_decision_path = root / "approval_decision.json"
        write_json(approval_decision_path, self.valid_decision(approved=False))

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--approval-decision",
                approval_decision_path.as_posix(),
                "--output-package-root-dir",
                output_package_root_dir.as_posix(),
                "--output-package-id",
                "approved-001",
            ]
        )
        payload = json.loads(output)

        self.assertNotEqual(exit_code, 0)
        self.assertIs(payload["complete"], True)
        self.assertIs(payload["approval_verified"], False)
        self.assertIs(payload["output_package_complete"], False)

    def test_cli_rejects_approval_decision_job_id_mismatch(self):
        input_dir, output_root_dir = self.build_workspace()
        root = input_dir.parent
        output_package_root_dir = root / "approved"
        output_package_root_dir.mkdir()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        approval_decision_path = root / "approval_decision.json"
        write_json(approval_decision_path, self.valid_decision(job_id="other-job"))

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--approval-decision",
                approval_decision_path.as_posix(),
                "--output-package-root-dir",
                output_package_root_dir.as_posix(),
                "--output-package-id",
                "approved-001",
            ]
        )
        payload = json.loads(output)

        self.assertNotEqual(exit_code, 0)
        self.assertIs(payload["complete"], True)
        self.assertIs(payload["approval_verified"], False)
        self.assertIs(payload["output_package_complete"], False)

    def test_cli_approval_mode_reports_output_package_complete_true(self):
        input_dir, output_root_dir = self.build_workspace()
        root = input_dir.parent
        output_package_root_dir = root / "approved"
        output_package_root_dir.mkdir()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        approval_decision_path = root / "approval_decision.json"
        write_json(approval_decision_path, self.valid_decision())

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--approval-decision",
                approval_decision_path.as_posix(),
                "--output-package-root-dir",
                output_package_root_dir.as_posix(),
                "--output-package-id",
                "approved-001",
            ]
        )
        payload = json.loads(output)

        self.assertEqual(exit_code, 0)
        self.assertIs(payload["output_package_complete"], True)
        self.assertEqual(payload["output_package_missing_artifacts"], [])

    def test_cli_exits_nonzero_for_missing_input_and_writes_quarantine(self):
        input_dir, output_root_dir = self.build_workspace()

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                (input_dir / "missing").as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
            ]
        )
        payload = json.loads(output)

        self.assertNotEqual(exit_code, 0)
        self.assertIs(payload["complete"], False)
        self.assertIn("failure_quarantine_path", payload)
        failure_manifest_path = (
            Path(payload["failure_quarantine_path"]) / "failure_manifest.json"
        )
        self.assertTrue(failure_manifest_path.exists())
        failure_manifest = read_json(failure_manifest_path)
        self.assertEqual(failure_manifest["error_type"], "ValueError")
        self.assertEqual(failure_manifest["error_message"], "input_dir is missing")

    def test_cli_supports_recursive(self):
        input_dir, output_root_dir = self.build_workspace()
        nested = input_dir / "nested"
        nested.mkdir()
        (nested / "extra.tsv").write_text("a\tb\n1\t2\n", encoding="utf-8")

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--recursive",
            ]
        )
        payload = json.loads(output)
        ledger_entries = read_jsonl(
            Path(payload["job_dir"]) / "intake_ledger.jsonl"
        )

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "nested/extra.tsv",
            {entry["relative_path"] for entry in ledger_entries},
        )

    def test_cli_supports_include_hidden(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / ".hidden.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        exit_code, output = self.run_cli(
            [
                "--input-dir",
                input_dir.as_posix(),
                "--output-root-dir",
                output_root_dir.as_posix(),
                "--job-id",
                "job-001",
                "--include-hidden",
            ]
        )
        payload = json.loads(output)
        ledger_entries = read_jsonl(
            Path(payload["job_dir"]) / "intake_ledger.jsonl"
        )

        self.assertEqual(exit_code, 0)
        self.assertIn(
            ".hidden.csv",
            {entry["relative_path"] for entry in ledger_entries},
        )

    def test_cli_does_not_import_forbidden_modules(self):
        source = Path("kernel/personal_ai/local_mvp_cli.py").read_text(
            encoding="utf-8",
        )

        self.assertIsNone(FORBIDDEN_IMPORT_PATTERN.search(source))
        self.assertNotIn("os.system", source)
        self.assertNotIn(".unlink(", source)
        self.assertNotIn(".rename(", source)


if __name__ == "__main__":
    unittest.main()
