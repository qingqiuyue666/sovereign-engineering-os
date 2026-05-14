import json
import re
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.local_mvp_runner import (
    PersonalAILocalMVPResult,
    run_personal_ai_local_mvp,
)


EXPECTED_REQUIRED_ARTIFACTS = [
    "input_snapshot.json",
    "intake_ledger.jsonl",
    "artifact_profile.json",
    "work_order_proposal.json",
    "review_packet.json",
    "pipeline_manifest.json",
    "task_route.json",
    "spreadsheet_processor_plan.json",
    "spreadsheet_readonly_inspection.json",
    "spreadsheet_report_plan.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "job_summary.json",
    "human_next_steps.md",
]

FORBIDDEN_IMPORT_PATTERN = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(?:requests|urllib|httpx|anthropic|openai|google|subprocess|"
    r"multiprocessing|playwright|selenium|socket|pandas|openpyxl|xlrd|pyarrow)\b",
    re.MULTILINE,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class LocalMVPRunnerTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        return input_dir, output_root_dir

    def write_inputs(self, input_dir, sentinel):
        csv_path = input_dir / "data.csv"
        notes_path = input_dir / "notes.md"
        csv_path.write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        notes_path.write_text("local notes", encoding="utf-8")
        return csv_path, notes_path

    def test_runs_complete_local_mvp_over_real_temporary_input_directory(self):
        input_dir, output_root_dir = self.build_workspace()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        csv_path, notes_path = self.write_inputs(input_dir, sentinel)
        before = {
            path: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in (csv_path, notes_path)
        }

        result = run_personal_ai_local_mvp(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )

        self.assertIsInstance(result, PersonalAILocalMVPResult)
        self.assertEqual(result.job_id, "job-001")
        self.assertEqual(result.job_dir, output_root_dir / "job-001")
        self.assertEqual(result.required_artifacts, EXPECTED_REQUIRED_ARTIFACTS)
        self.assertEqual(result.missing_artifacts, [])
        self.assertIs(result.complete, True)
        self.assertIs(result.required_human_approval, True)
        self.assertEqual(
            {path.name for path in result.job_dir.iterdir()},
            set(EXPECTED_REQUIRED_ARTIFACTS),
        )

        for path, (expected_bytes, expected_mtime) in before.items():
            self.assertEqual(path.read_bytes(), expected_bytes)
            self.assertEqual(path.stat().st_mtime_ns, expected_mtime)
            self.assertTrue(path.exists())

        for artifact_path in result.job_dir.iterdir():
            self.assertNotIn(
                sentinel,
                artifact_path.read_text(encoding="utf-8"),
                msg=artifact_path.name,
            )

    def test_runner_rejects_missing_input_or_output(self):
        input_dir, output_root_dir = self.build_workspace()

        with self.assertRaises(ValueError):
            run_personal_ai_local_mvp(
                input_dir / "missing",
                output_root_dir,
                job_id="job-001",
            )
        with self.assertRaises(ValueError):
            run_personal_ai_local_mvp(
                input_dir,
                output_root_dir / "missing",
                job_id="job-001",
            )

    def test_no_network_api_subprocess_or_external_tool_imports_are_added(self):
        production_files = [
            Path("kernel/personal_ai/local_mvp_runner.py"),
            Path("kernel/personal_ai/spreadsheet_report_planner.py"),
            Path("kernel/personal_ai/spreadsheet_structural_report.py"),
            Path("kernel/personal_ai/job_package.py"),
        ]

        for production_file in production_files:
            with self.subTest(production_file=production_file.as_posix()):
                source = production_file.read_text(encoding="utf-8")
                self.assertIsNone(FORBIDDEN_IMPORT_PATTERN.search(source))
                self.assertNotIn("os.system", source)
                self.assertNotIn(".unlink(", source)
                self.assertNotIn(".rename(", source)

    def test_stable_outputs_can_be_compared_logically(self):
        first_input, first_output = self.build_workspace()
        second_input, second_output = self.build_workspace()
        self.write_inputs(first_input, "FIRST_SENTINEL")
        self.write_inputs(second_input, "SECOND_SENTINEL")

        first = run_personal_ai_local_mvp(
            first_input,
            first_output,
            job_id="job-001",
        )
        second = run_personal_ai_local_mvp(
            second_input,
            second_output,
            job_id="job-001",
        )
        first_summary = read_json(first.job_dir / "job_summary.json")
        second_summary = read_json(second.job_dir / "job_summary.json")

        self.assertEqual(first.required_artifacts, second.required_artifacts)
        self.assertEqual(first.missing_artifacts, second.missing_artifacts)
        self.assertEqual(first.complete, second.complete)
        self.assertEqual(
            first_summary["spreadsheet_report_status"],
            second_summary["spreadsheet_report_status"],
        )
        self.assertEqual(
            first_summary["spreadsheet_issue_categories"],
            second_summary["spreadsheet_issue_categories"],
        )
        self.assertEqual(
            first_summary["spreadsheet_structural_report_status"],
            second_summary["spreadsheet_structural_report_status"],
        )


if __name__ == "__main__":
    unittest.main()
